FROM python:3.9 AS base

#
ADD scripts /csi/

# Setup Python environment
RUN /bin/bash -c set -ex; \
    pip3 install -r /csi/requirements.txt --no-cache-dir

# Required kinpy dependency on libgl
RUN /bin/bash -c set -ex; \
    apt-get update ; \
    apt-get install -y --no-install-recommends libgl1


# Patch kinpy fixed-joint issue
RUN /bin/bash -c set -ex; \
    cp /csi/patch/kinpy/chain.py /usr/local/lib/python3.9/site-packages/kinpy/

# Prepare build
ADD build /build

# Cleanup and expose build input/output dir
RUN /bin/bash -c set -ex; \
    rm -rf /build/unity_Data/StreamingAssets/CSI/Databases; \
    mkdir /csi/databases; \
    ln -s /csi/databases /build/unity_Data/StreamingAssets/CSI/Databases; \
    rm -rf /build/unity_Data/StreamingAssets/CSI/Configuration; \
    mkdir /csi/configuration; \
    ln -s /csi/configuration /build/unity_Data/StreamingAssets/CSI/Configuration;

VOLUME /csi/configuration
VOLUME /csi/databases

# Run IK server and build
ADD entrypoint.sh /
CMD /bin/bash /entrypoint.sh
