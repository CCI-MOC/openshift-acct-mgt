# pylint: disable=missing-module-docstring,wrong-import-position,redefined-outer-name
from unittest import mock
import pytest

from acct_mgt.app import create_app

fake_200_response = mock.Mock(status_code=200, response="it worked", charset="utf-8")
fake_400_response = mock.Mock(status_code=400, response="it failed", charset="utf-8")


@pytest.fixture
def moc():
    """Cause acct_mgt.app.get_openshift to return a Mock object

    This allows us to mock out all aspects of the backend api while testing the
    web application.
    """

    with mock.patch("acct_mgt.app.get_openshift") as fake_get_openshift:
        fake_openshift = mock.Mock()
        fake_get_openshift.return_value = fake_openshift
        yield fake_openshift


@pytest.fixture
def app():
    """An app instance with authentication disabled"""

    with mock.patch("acct_mgt.app.kubeclient"):
        app = create_app(
            DISABLE_ENV_CONFIG=True,
            TESTING=True,
            AUTH_DISABLED="True",
            OPENSHIFT_URL="http://fake",
            AUTH_TOKEN="fake",
            IDENTITY_PROVIDER="fake",
        )

        yield app


@pytest.fixture
def app_auth():
    """An app instance with authentication enabled"""

    with mock.patch("acct_mgt.app.kubeclient"):
        app = create_app(
            DISABLE_ENV_CONFIG=True,
            TESTING=True,
            AUTH_DISABLED="False",
            ADMIN_PASS="pass",
            OPENSHIFT_URL="http://fake",
            AUTH_TOKEN="fake",
            IDENTITY_PROVIDER="fake",
        )

        yield app


@pytest.fixture
def client(app):
    """A test client that does not use authentication"""

    with app.test_client() as client:
        yield client


@pytest.fixture
def client_auth(app_auth):
    """A test client that does not use authentication"""

    with app_auth.test_client() as client:
        yield client
