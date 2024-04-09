import os
import shutil
from datetime import datetime

from src.api import EcostressCloudAPI
import unittest
from unittest.mock import patch, Mock, MagicMock, call
from shapely import Polygon


TEST_DIR = os.path.dirname(__file__)
TEST_XML_DIR = os.path.join(TEST_DIR, "xml_dir")
DATA_FILE_PATH = os.path.join(TEST_DIR, "data.txt")


class TestEcostressCloudAPI(unittest.TestCase):
    def setUp(self) -> None:

        if os.path.exists(DATA_FILE_PATH):
            os.remove(DATA_FILE_PATH)
        
        if os.path.exists(TEST_XML_DIR):
            shutil.rmtree(TEST_XML_DIR)

        return super().setUp()

    def tearDown(self) -> None:

        if os.path.exists(DATA_FILE_PATH):
            os.remove(DATA_FILE_PATH)
        
        if os.path.exists(TEST_XML_DIR):
            shutil.rmtree(TEST_XML_DIR)

        return super().tearDown()

    @patch.object(EcostressCloudAPI, "_cred_query", return_value=("username", "password"))
    @patch("src.api.EcostressCloudAPI._XML_DIR", TEST_XML_DIR)
    def test_init(self, mock_cred_query):
        self.assertFalse(os.path.exists(TEST_XML_DIR))

        api = EcostressCloudAPI()
        self.assertIsNotNone(api)
        self.assertEqual("username", api._username)
        self.assertEqual("password", api._password)
        self.assertIsNotNone(api._file_re)

        self.assertTrue(os.path.exists(TEST_XML_DIR))
        

    @patch('src.api.input', return_value='username')
    @patch('src.api.getpass.getpass', return_value='password')
    def test_cred_query(self, mock_input, mock_get_pass):
        api = EcostressCloudAPI()
        username, password = api._cred_query()
        self.assertEqual("username", username)
        self.assertEqual("password", password)

    @patch('src.api.requests.get')
    def test_retrieve_links(self, mock_requests):
        test_url = "https://www.example.com"
        test_html = """
        <html>
        <body>
            <img src="/icons/unknown.gif" alt="[   ]">
            <a href="ECOSTRESS_L4_WUE_25858_029_20230127T082948_0601_01.h5">ECOSTRESS_L4_WUE_25858_029_20230127T082948_0601_01.h5</a>     2023-02-11 08:30  116M
            <img src="/icons/unknown.gif" alt="[   ]"> 
            <a href="ECOSTRESS_L4_WUE_25858_029_20230127T082948_0601_01.h5.xml">ECOSTRESS_L4_WUE_25858_029_20230127T082948_0601_01.h5.xml</a> 2023-02-11 08:30  3.9K  
            <img src="/icons/image2.gif" alt="[IMG]"> 
            <a href="ECOSTRESS_L4_WUE_25863_020_20230127T162232_0601_01.1.jpg">ECOSTRESS_L4_WUE_25863_020_20230127T162232_0601_01.1.jpg</a>  2023-02-11 17:35  107K
        </body>
        </html>
        """

        mock_response = mock_requests.return_value
        mock_response.text = test_html

        result = EcostressCloudAPI.retrieve_links(test_url)

        self.assertEqual(result, [
            "ECOSTRESS_L4_WUE_25858_029_20230127T082948_0601_01.h5",
            "ECOSTRESS_L4_WUE_25858_029_20230127T082948_0601_01.h5.xml", 
            "ECOSTRESS_L4_WUE_25863_020_20230127T162232_0601_01.1.jpg"
        ] )

    @patch('src.api.urllib.request.urlopen')
    @patch('src.api.os.path.exists')
    @patch.object(EcostressCloudAPI, "_cred_query", return_value=("username", "password"))
    def test_download(self, mock_cred_query, mock_exists, mock_urlopen):
        mock_exists.return_value = False

        mock_response = unittest.mock.Mock()
        mock_response.read.side_effect = [b'data_chunk1', b'data_chunk2', b'']
        mock_urlopen.return_value = mock_response

        api = EcostressCloudAPI()

        query = ('https://example.com/data.txt', 'data.txt')
        api._download(query)

        with open('data.txt', 'rb') as f:
            data_written = f.read()
        self.assertEqual(data_written, b'data_chunk1data_chunk2')

    @patch('src.api.os.path.exists')
    @patch('src.api.EcostressCloudAPI.download')
    @patch.object(EcostressCloudAPI, "_cred_query", return_value=("username", "password"))
    @patch("src.api.EcostressCloudAPI._XML_DIR", TEST_XML_DIR)
    @patch('builtins.open')
    def test_parse_bbox_from_xml(self, mock_open, mock_cred_query, mock_download, mock_exists):
        mock_exists.return_value = True

        # mock_xml_content = MagicMock()
        # mock_xml_content.find.return_value = MagicMock(
        #     text='1.0', spec_set=['text']
        # )
        # mock_fromstring.return_value = mock_xml_content

        mock_open.return_value.read.return_value = """
        <GranuleMetaDataFile>
            <GranuleURMetaData>
                <SpatialDomainContainer>
                    <HorizontalSpatialDomainContainer>
                        <BoundingRectangle>
                            <WestBoundingCoordinate>-122.778572</WestBoundingCoordinate>
                            <NorthBoundingCoordinate>38.030651</NorthBoundingCoordinate>
                            <EastBoundingCoordinate>-117.125183</EastBoundingCoordinate>
                            <SouthBoundingCoordinate>32.858040</SouthBoundingCoordinate>
                        </BoundingRectangle>
                    </HorizontalSpatialDomainContainer>
                </SpatialDomainContainer>
            </GranuleURMetaData>
        </GranuleMetaDataFile>
        """

        api = EcostressCloudAPI()

        xml_url = 'https://example.com/xml_data.xml'
        polygon = api._parse_bbox_from_xml(xml_url)

        # Check if the correct Polygon object is returned
        expected_polygon = Polygon([
            (-122.778572, 38.030651),
            (-117.125183, 38.030651),
            (-117.125183, 32.858040),
            (-122.778572, 32.858040)
        ])
        self.assertEqual(polygon, expected_polygon)

        # Check if os.path.exists and open methods were called with the correct arguments
        mock_open.assert_called_once_with(os.path.join(TEST_XML_DIR, 'xml_data.xml'), 'rb')

    @patch.object(EcostressCloudAPI, "_cred_query", return_value=("username", "password"))
    @patch.object(EcostressCloudAPI, '_parse_bbox_from_xml')
    def test_overlaps_bbox(self, mock_parse_bbox, mock_cred_query):
        mock_parse_bbox.return_value = Polygon([
            (-122.778572, 38.030651),
            (-117.125183, 38.030651),
            (-117.125183, 32.858040),
            (-122.778572, 32.858040)
        ])

        your_class_instance = EcostressCloudAPI()

        target_bbox = [-120, 35, -118, 36]
        xml_url = 'https://example.com/xml_data.xml'
        result = your_class_instance._overlaps_bbox(target_bbox, xml_url)

        self.assertTrue(result)

        mock_parse_bbox.assert_called_once_with(xml_url)

    @patch.object(EcostressCloudAPI, "_cred_query", return_value=("username", "password"))
    @patch.object(EcostressCloudAPI, '_parse_bbox_from_xml')
    def test_does_not_overlap_bbox(self, mock_parse_bbox, mock_cred_query):
        mock_parse_bbox.return_value = Polygon([
            (-122.778572, 38.030651),
            (-117.125183, 38.030651),
            (-117.125183, 32.858040),
            (-122.778572, 32.858040)
        ])

        your_class_instance = EcostressCloudAPI()

        target_bbox = [-95, 35, -90, 36]  # Example target bounding box
        xml_url = 'https://example.com/xml_data.xml'
        result = your_class_instance._overlaps_bbox(target_bbox, xml_url)

        self.assertFalse(result)

        mock_parse_bbox.assert_called_once_with(xml_url)

    
    @patch.object(EcostressCloudAPI, "_cred_query", return_value=("username", "password"))
    def test_create_day_urls(self, mock_cred_query):
        start_date = datetime(2022, 1, 29)
        end_date = datetime(2022, 2, 2)

        api = EcostressCloudAPI()
        urls = api._create_day_urls(start_date, end_date)

        self.assertListEqual(
            sorted([
                'https://e4ftl01.cr.usgs.gov/ECOSTRESS/ECO2CLD.001/2022.01.29/',
                'https://e4ftl01.cr.usgs.gov/ECOSTRESS/ECO2CLD.001/2022.01.30/',
                'https://e4ftl01.cr.usgs.gov/ECOSTRESS/ECO2CLD.001/2022.01.31/',
                'https://e4ftl01.cr.usgs.gov/ECOSTRESS/ECO2CLD.001/2022.02.01/',
                'https://e4ftl01.cr.usgs.gov/ECOSTRESS/ECO2CLD.001/2022.02.02/'
             ]), sorted(urls)
        )

    @patch.object(EcostressCloudAPI, 'retrieve_links')
    @patch.object(EcostressCloudAPI, '_overlaps_bbox')
    @patch('src.api.EcostressCloudAPI._download')
    @patch.object(EcostressCloudAPI, "_cred_query", return_value=("username", "password"))
    def test_download(self, mock_cred_query, mock_download, mock_overlaps_bbox, mock_retrieve_links):
        # Mocking return values
        mock_retrieve_links.side_effect = [
            [
                'ECOSTRESS_L2_CLOUD_19843_018_20220105T013409_0601_01.h5',
                'ECOSTRESS_L2_CLOUD_19850_014_20220105T122719_0601_01.h5'
            ],
            [
                'ECOSTRESS_L2_CLOUD_19858_016_20220106T004717_0601_01.h5',
                'ECOSTRESS_L2_CLOUD_19872_026_20220106T230842_0601_01.h5'
            ]
        ]
        mock_overlaps_bbox.side_effect = [False, True]

        api = EcostressCloudAPI()

        # Call the download method
        start_date = datetime(2022, 1, 5, 10)
        end_date = datetime(2022, 1, 6, 17)
        bbox = [-120, 35, -118, 36]
        output_dir = '/output/dir/'
        api.download(start_date, end_date, bbox, output_dir)
        
        expected_file_links = ['https://e4ftl01.cr.usgs.gov/ECOSTRESS/ECO2CLD.001/2022.01.06/ECOSTRESS_L2_CLOUD_19858_016_20220106T004717_0601_01.h5']
        expected_file_requests = [(link, f'/output/dir/{link.split("/")[-1]}') for link in expected_file_links]
        mock_retrieve_links.assert_has_calls([call('https://e4ftl01.cr.usgs.gov/ECOSTRESS/ECO2CLD.001/2022.01.05/'), call('https://e4ftl01.cr.usgs.gov/ECOSTRESS/ECO2CLD.001/2022.01.06/')])
        mock_overlaps_bbox.assert_has_calls([call([-120, 35, -118, 36], 'https://e4ftl01.cr.usgs.gov/ECOSTRESS/ECO2CLD.001/2022.01.05/ECOSTRESS_L2_CLOUD_19850_014_20220105T122719_0601_01.h5.xml'),
                                              call([-120, 35, -118, 36], 'https://e4ftl01.cr.usgs.gov/ECOSTRESS/ECO2CLD.001/2022.01.06/ECOSTRESS_L2_CLOUD_19858_016_20220106T004717_0601_01.h5.xml')])
        mock_download.assert_has_calls([call(request) for request in expected_file_requests])



if __name__ == '__main__':
    unittest.main()