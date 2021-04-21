######## [1] ########
# Create ISCE RPM

# Use hysds/dev:v4.0.0-rc.7
FROM hysds/dev:v4.0.0-rc.7

# Set an encoding to make things work smoothly.
ENV LANG en_US.UTF-8

# Set ISCE repo
ENV ISCE_ORG isce-framework

# set to root user
USER root

# install tools for RPM generation
RUN set -ex \
 && yum update -y \
 && yum groupinstall -y "development tools" \
 && yum install -y \
      make ruby-devel rpm-build rubygems \
 && gem install ffi -v 1.12.2 \
 && gem install --no-ri --no-rdoc fpm -v 1.11.0

# install isce requirements
RUN set -ex \
 && . /opt/conda/bin/activate root \
 && conda install --yes \
      cython \
      gdal \
      git \
      h5py \
      libgdal \
      pytest \
      numpy \
      fftw \
      scipy \
      scons \
      hdf4 \
      hdf5 \
      libgcc \
      libstdcxx-ng \
      cmake \
 && yum install -y uuid-devel x11-devel motif-devel jq \
    opencv opencv-devel opencv-python \
 && ln -sf /opt/conda/bin/cython /opt/conda/bin/cython3 \
 && mkdir -p /opt/isce2/src

# override system libuuid into conda env to link in libXm and libXt
RUN set -ex \
 && cd /opt/conda/lib \
 && unlink libuuid.so \
 && unlink libuuid.so.1 \
 && ln -s /lib64/libuuid.so.1.3.0 libuuid.so \
 && ln -s /lib64/libuuid.so.1.3.0 libuuid.so.1

# install libgfortran.so.3 and create missing link
RUN set -ex \
 && yum install -y gcc-gfortran \
 && cd /lib64 \
 && ( test -f libgfortran.so || ln -sv libgfortran.so.*.* libgfortran.so )

# get repo and build ISCE (isce2: whyjay patch)
RUN set -ex \
 && . /opt/conda/bin/activate root \
 && cd /opt/isce2/src \
 && git clone https://github.com/whyjz/isce2.git \
 && cd /opt/isce2/src/isce2 \
 && git checkout patch-wjz \
 && source docker/build_env.sh \
 && mkdir -p $BUILD_DIR \
 && cp docker/SConfigISCE configuration/SConfigISCE \
 && scons install \
 && cp docker/isce_env.sh $ISCE_INSTALL_ROOT \
 && cd /tmp \
 && mkdir -p /tmp/rpm-build/opt \
 && mv $ISCE_INSTALL_ROOT /tmp/rpm-build/opt \
 && curl -s https://api.github.com/repos/$ISCE_ORG/isce2/git/refs/heads/main \
    > /tmp/rpm-build/opt/isce2/version.json \
 && hash=$(cat /tmp/rpm-build/opt/isce2/version.json | jq -r .object.sha) \
 && short_hash=$(echo $hash | cut -c1-5) \
 && fpm -s dir -t rpm -C /tmp/rpm-build --name isce \
      --prefix=/ --version=2.4.2 --provides=isce \
      --maintainer=piyush.agram@jpl.nasa.gov \
      --description="InSAR Scientific Computing Environment v2 (${hash})"

######## [2] ########
# Install ISCE from RPM and other packages

# Use hysds/pge-base:v4.0.0
# This comes with a user called "ops" with UID of 1000
FROM hysds/pge-base:v4.0.0

# Make sure we are using the ops user
USER ops

# Set an encoding to make things work smoothly.
ENV LANG en_US.UTF-8

# install jupyter interface (https://mybinder.readthedocs.io/en/latest/tutorials/dockerfile.html)
RUN set -ex \
 && sudo /opt/conda/bin/pip install --no-cache-dir notebook jupyterlab

# Override home dir with /tmp to avoid write permission issues
ENV HOME /tmp
WORKDIR ${HOME}

# copy the ISCE RPM to hysds/pge-base: v4.0.0
COPY --from=0 /tmp/isce-2.4.2-1.x86_64.rpm /tmp/isce-2.4.2-1.x86_64.rpm

# install isce and its minimal requirements
RUN set -ex \
 && sudo /opt/conda/bin/conda install --yes \
      gdal \
      h5py \
      libgdal \
      pytest \
      numpy \
      fftw \
      scipy \
      hdf4 \
      hdf5 \
 && sudo yum update -y \
 && sudo yum install -y uuid-devel x11-devel motif-devel gcc-gfortran \
 && cd /opt/conda/lib \
 && sudo unlink libuuid.so \
 && sudo unlink libuuid.so.1 \
 && sudo ln -s /lib64/libuuid.so.1.3.0 libuuid.so \
 && sudo ln -s /lib64/libuuid.so.1.3.0 libuuid.so.1 \
 && cd /lib64 \
 && ( test -f libgfortran.so || sudo ln -sv libgfortran.so.*.* libgfortran.so ) \
 && sudo yum install -y /tmp/isce-2.4.2-1.x86_64.rpm \
 && sudo yum clean all \
 && sudo rm -rf /var/cache/yum \
 && sudo rm /tmp/isce-2.4.2-1.x86_64.rpm

# install jupyter interface (https://mybinder.readthedocs.io/en/latest/tutorials/dockerfile.html)
# RUN set -ex \
#  && sudo /opt/conda/bin/conda install --yes \
#       jupyter \
#       jupyterlab \
#  && sudo /opt/conda/bin/pip install --no-cache-dir notebook==5.*

# set up environment variables
ENV PYTHONPATH="/opt/isce2:${PYTHONPATH}" PATH="/opt/isce2/isce/applications:$PATH"

# Install CARST and scikit-image (the latter will be installed with CARST in the future)
RUN set -ex \
 && sudo /opt/conda/bin/pip install carst scikit-image

# Install other imagexs required by EZTrack
RUN set -ex \
 && sudo /opt/conda/bin/pip install scikit-learn boto3 xarray ipyleaflet fsspec xlrd openpyxl netcdf4 requests aiohttp h5netcdf

# # Binder settings (creating a jovyan user instead of using root)
# ARG NB_USER=jovyan
# ARG NB_UID=1000
# ENV USER ${NB_USER}
# ENV NB_UID ${NB_UID}
# ENV HOME /home/${NB_USER}
# RUN sudo adduser \
#     --comment "Default user" \
#     --uid 1002 \
#     jovyan

# # Make sure the contents of our repo are in ${HOME}
# # RUN mkdir ${HOME}
COPY . ${HOME}
# USER root
RUN set -ex \
 && sudo chown -R 1000 ${HOME}
# chown -R ${NB_UID} ${HOME}
# # USER ${NB_USER}
