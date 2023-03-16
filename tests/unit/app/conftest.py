# pylint: disable=missing-module-docstring,wrong-import-position,redefined-outer-name

from unittest import mock
import pytest

from acct_mgt.app import create_app
from acct_mgt.moc_openshift import MocOpenShift4x

fake_200_response = mock.Mock(status_code=200, response="it worked", charset="utf-8")

test_config = {
    "DISABLE_ENV_CONFIG": True,
    "TESTING": True,
    "AUTH_DISABLED": "true",
    "ADMIN_PASS": "secret",
    "OPENSHIFT_URL": "http://fake",
    "AUTH_TOKEN": "fake",
    "IDENTITY_PROVIDER": "fake",
    "QUOTA_DEF_FILE": "/dev/null",
    "LIMIT_DEF_FILE": "/dev/null",
}


@pytest.fixture
def app():
    """An app instance with authentication disabled"""

    with mock.patch("acct_mgt.app.get_dynamic_client"):
        app = create_app(**test_config)
        yield app


@pytest.fixture
def app_auth():
    """An app instance with authentication enabled"""

    with mock.patch("acct_mgt.app.get_dynamic_client"):
        app = create_app(**(test_config | {"AUTH_DISABLED": "false"}))
        yield app


@pytest.fixture
def client(app):
    """A test client that does not use authentication"""

    with app.test_client() as client:
        yield client


@pytest.fixture
def client_auth(app_auth):
    """A test client that uses authentication"""

    with app_auth.test_client() as client:
        yield client


@pytest.fixture()
def moc():
    with mock.patch("acct_mgt.app.get_openshift") as fake_get_openshift:
        fake_openshift = mock.Mock(spec=MocOpenShift4x)
        fake_get_openshift.return_value = fake_openshift
        yield fake_openshift
