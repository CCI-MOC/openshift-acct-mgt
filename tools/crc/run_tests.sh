# Runs the tests in a virtualenvironment
#
# Requires prior `oc login` and running from root of repo.

sudo yum install python3 python-virtualenv -y

virtualenv .venv -p "$(command -v python3)"
source .venv/bin/activate

pip install -r test-requirements.txt

python -m pytest acct-mgt-test.py --amurl https://openshift-onboarding.apps-crc.testing
