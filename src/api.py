import os
import re
import calendar
from datetime import datetime, timedelta
import getpass
from typing import Tuple, List, Union
import urllib
from http.cookiejar import CookieJar
from shapely.geometry import Polygon
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup


PROJ_DIR = os.path.dirname(os.path.dirname(__file__))


class EcostressCloudAPI:
    _BASE_CLOUD_URL = 'https://e4ftl01.cr.usgs.gov/ECOSTRESS/ECO2CLD.001/'
    _XML_DIR = os.path.join(PROJ_DIR, 'xml_files')

    def __init__(self):
        self._username, self._password = self._cred_query()
        self._file_re = r'ECOSTRESS\_L2\_CLOUD\_(?P<orbit>\d{5})\_(?P<scene_id>\d{3})\_(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})T(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})\_(?P<build_id>\d{4})\_(?P<version>\d{2})\.h5$'
        os.makedirs(self._XML_DIR, exist_ok=True)

    @staticmethod
    def _cred_query() -> Tuple[str, str]:
        """
        Ask the user for their urs.earthdata.nasa.gov username and login
        Returns:
            username (str): urs.earthdata.nasa.gov username
            password (str): urs.earthdata.nasa.gov password
        """
        print('Please input your earthdata.nasa.gov username and password. If you do not have one, you can register'
              ' here: https://urs.earthdata.nasa.gov/users/new')
        username = input('Username:')
        password = getpass.getpass('Password:', stream=None)

        return username, password
    
    @staticmethod
    def retrieve_links(url: str) -> List[str]:
        """
        Creates a list of all the links found on a webpage
        Args:
            url (str): The URL of the webpage for which you would like a list of links

        Returns:
            (list): All the links on the input URL's webpage
        """
        request = requests.get(url)
        soup = BeautifulSoup(request.text, 'html.parser')
        return [link.get('href') for link in soup.find_all('a')]
    
    def _download(self, query: Tuple[str, str]) -> None:
        """
        Downloads data from the NASA earthdata servers. Authentication is established using the username and password
        found in the local ~/.netrc file.
        Args:
            query (tuple): Contains the remote location and the local path destination, respectively
        """
        link = query[0]
        dest = query[1]
        if os.path.exists(dest):
            print(f'Skipping {dest}')
            return

        pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        pm.add_password(None, "https://urs.earthdata.nasa.gov", self._username, self._password)
        cookie_jar = CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPBasicAuthHandler(pm),
            urllib.request.HTTPCookieProcessor(cookie_jar)
        )
        urllib.request.install_opener(opener)
        myrequest = urllib.request.Request(link)
        response = urllib.request.urlopen(myrequest)
        response.begin()
        with open(dest, 'wb') as fd:
            while True:
                chunk = response.read()
                if chunk:
                    fd.write(chunk)
                else:
                    break

    def _parse_bbox_from_xml(self, xml_url: str) -> Polygon:
        filename = os.path.basename(xml_url)
        file_path = os.path.join(self._XML_DIR, filename)

        if not os.path.exists(file_path):
            self.download((xml_url, file_path))

        # Parse the XML content
        root = ET.fromstring(open(file_path, 'rb').read())
        bounding_rect = root.find('.//BoundingRectangle')
        west = float(bounding_rect.find('WestBoundingCoordinate').text)
        north = float(bounding_rect.find('NorthBoundingCoordinate').text)
        east = float(bounding_rect.find('EastBoundingCoordinate').text)
        south = float(bounding_rect.find('SouthBoundingCoordinate').text)
        return Polygon([(west, north), (east, north), (east, south), (west, south)])

    def _overlaps_bbox(self, target_bbox: List[int], xml_url: str):
        # Now apply spatial filter by downloading the xml files and checking if they overlap the bounding box
        min_lon, min_lat, max_lon, max_lat = target_bbox[0], target_bbox[1], target_bbox[2], target_bbox[3]
        target_bbox = Polygon([(min_lon, max_lat), (max_lon, max_lat), (max_lon, min_lat), (min_lon, min_lat)])
        file_bbox = self._parse_bbox_from_xml(xml_url)
        return file_bbox.intersects(target_bbox)
    
    @staticmethod
    def _get_last_day_of_month(year, month):
        # TODO: Add unit tests
        # monthrange returns a tuple (weekday of first day of the month, number of days in month)
        _, num_days = calendar.monthrange(year, month)
        return num_days
    
    def _parse_datetime_from_file_name(self, file_name: str) -> Union[None, datetime]:
        # TODO: Add unit tests
        match = re.match(self._file_re, file_name)
        if match:
            group_dict = match.groupdict()
            return datetime(int(group_dict['year']), int(group_dict['month']), int(group_dict['day']), int(group_dict['hour']), int(group_dict['minute']), int(group_dict['second']))
        return None
    
    def _create_day_urls(self, start_date: datetime, end_date: datetime):
        day_urls = []
        while start_date <= end_date:
            day_urls.append(urllib.parse.urljoin(self._BASE_CLOUD_URL, start_date.strftime('%Y.%m.%d') + '/'))
            start_date += timedelta(days=1)
        return day_urls

    def download(self, start_date: datetime, end_date: datetime, bbox: List[int], output_dir: str) -> List[Tuple[str, str, str]]:
        day_urls = self._create_day_urls(start_date, end_date)
        file_links = []
        for day_url in day_urls:
            file_urls = self.retrieve_links(day_url)
            for file_url in file_urls:
                link = urllib.parse.urljoin(day_url, file_url)
                file_date = self._parse_datetime_from_file_name(file_url)
                if file_date is not None and start_date <= file_date <= end_date and self._overlaps_bbox(bbox, link + '.xml'):
                    file_links.append(link)

        file_requests = [(link, os.path.join(output_dir, os.path.basename(link))) for link in file_links]

        for request in file_requests:
            self._download(request)
