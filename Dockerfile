FROM quay.io/jupyter/minimal-notebook:latest

USER root

COPY . .

RUN rm -rf .git .gitignore

# Set up package manager
RUN apt-get install -y apt-transport-https && \
    apt-get clean && apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository multiverse && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install some base software
RUN apt-get update --yes && \
    apt-get install --yes \
    fonts-dejavu \
    unixodbc \
    unixodbc-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Add sudo to jovyan user
RUN apt update && \
    apt install -y sudo && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# This is where we can control which root permissions the jovyan user will have
ARG PRIV_CMDS='/bin/ch*,/bin/cat,/bin/gunzip,/bin/tar,/bin/mkdir,/bin/ps,/bin/mv,/bin/cp,/usr/bin/apt*,/usr/bin/pip*,/bin/yum,/opt,/opt/conda/bin/*,/usr/bin/*'

RUN usermod -aG sudo jovyan && \
    echo "$LOCAL_USER ALL=NOPASSWD: $PRIV_CMDS" >> /etc/sudoers
RUN addgroup jovyan
RUN usermod -aG jovyan jovyan

# Update permissions for /opt/conda
RUN chown -R jovyan:users /opt/conda/share /usr/local/share /usr/local/bin/start-notebook.d

USER jovyan

# Install jupyterlab and rstudio dependencies
RUN conda install -c conda-forge \
    jupyter_client \
    jupyter_core \
    jupyterlab_server \
    jupyter_server \
    r-rgl \
    r-htmlwidgets \
    r-htmltools && \
    jupyter lab clean

# Install Jupyter Lab Proxy extensions (cards in Launcher)
RUN pip install jupyter-server-proxy jupyterlab-git

# Install Mamba Gator package manager
RUN rm -f ~/.jupyter/lab/workspaces/default* && \
    mamba install -y -c conda-forge mamba_gator

# Install and configure jupyter lab 
COPY jupyter_notebook_config.json /opt/conda/etc/jupyter/jupyter_notebook_config.json

# Rebuild the Jupyter Lab with new tools
RUN jupyter lab build

# Build Conda environment
RUN conda update -y conda && \
    conda config --remove channels conda-forge && \
    conda config --add channels conda-forge
WORKDIR /home/jovyan
COPY environment.yml /home/jovyan/
RUN mamba env create -f /home/jovyan/environment.yml
RUN . /opt/conda/etc/profile.d/conda.sh && conda deactivate && conda activate hyr-sense && python -m ipykernel install --name hyr-sense && pip install jupyter_contrib_nbextensions