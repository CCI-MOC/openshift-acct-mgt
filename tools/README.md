This directory contains a set of helper scripts.
Unless otherwise noted, scripts expect to be run from the root directory
of the repo.

# crc/

## ./crc/setup.sh <pullstring.json>
Sets up a CodeReady Containers installation on a Mac/CentOS 7 host.

## ./crc/deploy.sh
Build the `openshift-acct-mgt` container image, pushes it to the internal
container registry of CodeReady Containers and applies the necessary specs
for a deployment.

## ./crc/run_tests.sh
Creates a virtual environment `.venv/`, install the necessary requirements
and runs the tests for the previously deployed service running on CRC.
