# pylint: disable=missing-module-docstring,wrong-import-position,redefined-outer-name
from unittest import mock

import pytest

from acct_mgt import kubeclient


@pytest.fixture
def session_req():
    with mock.patch("requests.Session.request") as fake_request:
        yield fake_request


# pylint: disable=unused-argument
@pytest.fixture
def kube():
    yield kubeclient.Client(baseurl="http://fake", token="fake", verify=False)


def test_init(kube):
    """Test that kubeclient.Client object has expected values"""

    assert kube.baseurl == "http://fake"
    assert kube.verify is False
    assert kube.token == "fake"


def test_get_token(kube):
    with mock.patch("builtins.open", mock.mock_open(read_data="fake-token")):
        res = kube.get_token()
        assert res == "fake-token"


def test_get_url(kube):
    assert kube.get_url() == kubeclient.INCLUSTER_KUBERNETES_URL


def test_get_ca_path(kube):
    assert kube.get_ca_path() is None


def test_get_ca_path_exists(kube):
    with mock.patch("os.path.exists") as fake_exists:
        fake_exists.return_value = True

        assert kube.get_ca_path() == kubeclient.INCLUSTER_CA_PATH


def test_request_get_fully_qualified(kube, session_req):
    """Test request for a fully qualified URL"""

    kube.get("http://example.com")
    assert (
        mock.call("GET", "http://example.com", allow_redirects=True)
        in session_req.mock_calls
    )


def test_request_get_absolute(kube, session_req):
    """Test request for an absolute path"""

    kube.get("/test-path")
    assert (
        mock.call("GET", "http://fake/test-path", allow_redirects=True)
        in session_req.mock_calls
    )


def test_request_get_relative(kube, session_req):
    """Test request for a relative path"""

    kube.get("test-path")
    assert (
        mock.call("GET", "http://fake/test-path", allow_redirects=True)
        in session_req.mock_calls
    )
