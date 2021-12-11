# This script sets up CodeReady Containers on Mac or a CentOS 7 host.
#
# Requires pullstring file location to be passed as first argument.
# https://cloud.redhat.com/openshift/create/local

set -e

if [ "$(uname)" == "Darwin" ]; then
    URL="https://mirror.openshift.com/pub/openshift-v4/clients/crc/1.24.0/crc-macos-amd64.tar.xz"
else  # CentOS 7
    URL="https://mirror.openshift.com/pub/openshift-v4/clients/crc/1.24.0/crc-linux-amd64.tar.xz"
    sudo yum update -y
    sudo yum install NetworkManager podman -y
    sudo systemctl enable --now NetworkManager
fi

# Check for CRC command already existing
if [[ $(command -v crc) == "" ]]; then
  # Download and extract to a temporary working directory
  curl -o /tmp/crc.tar.xz $URL
  mkdir temp_crc && cd temp_crc && tar -xvf /tmp/crc.tar.xz
  # Copy the `crc` binary to /usr/local/bin and cleanup
  find . -name crc -exec mv {} . \;
  sudo mv crc /usr/local/bin
  cd ../ && rm -rf /tmp/crc.tar.xz temp_crc
fi

crc config set consent-telemetry no
crc setup

crc start -p $1
