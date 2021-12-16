# pylint: disable=missing-module-docstring,redefined-outer-name

import json
import random
import string
import subprocess

from urllib.parse import urljoin

import pytest
import requests


class Session(requests.Session):
    """Wrapper for requests.Session that adds base url to requests"""

    def __init__(self, baseurl, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.baseurl = baseurl

    def request(self, method, url, *args, **kwargs):
        url = urljoin(self.baseurl, url)
        return super().request(method, url, *args, **kwargs)


def kwargs_to_flags(**kwargs):
    """Helper function that transforms keyword arguments into command line options"""

    args = []
    for k, v in kwargs.items():
        if (isinstance(v, bool) and v) or (v is None):
            args.append(f"--{k}")
        else:
            args.append(f"--{k}={v}")

    return args


# pylint: disable=subprocess-run-check
def oc(*args, **kwargs):
    """Wrapper for running oc command lines"""

    cmd = ["oc", "--output=json"] + kwargs_to_flags(**kwargs) + list(args)
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0:
        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError:
            data = None
    else:
        data = None

    return (res, data)


def pytest_addoption(parser):
    parser.addoption("--api-endpoint", action="store", default="http://localhost:8080")
    parser.addoption("--admin-user", action="store", default="admin")
    parser.addoption("--admin-password", "--admin-pass", action="store")


@pytest.fixture
def api_endpoint(request):
    return request.config.getoption("--api-endpoint")


@pytest.fixture
def admin_user(request):
    return request.config.getoption("--admin-user")


@pytest.fixture
def admin_password(request):
    return request.config.getoption("--admin-password")


@pytest.fixture
def session_noauth(api_endpoint):
    """An unauthenticated Session"""

    s = Session(api_endpoint)
    s.headers["content-type"] = "application/json"
    return s


@pytest.fixture
def session(api_endpoint, admin_user, admin_password):
    """An authenticated Session (if authentication is enabled)"""

    s = Session(api_endpoint)
    s.headers["content-type"] = "application/json"
    if admin_password is not None:
        s.auth = (admin_user, admin_password)
    return s


@pytest.fixture
def suffix():
    """A random string used to generate unique user and project names"""

    return "".join(random.sample(string.ascii_lowercase + string.digits, 6))


@pytest.fixture
def a_user(session, suffix):
    """Create a unique user and return the generated name.

    Delete the user when the tests complete.
    """

    username = f"test-user-{suffix}"
    res = session.put(f"/users/{username}")
    assert res.status_code == 200
    yield username
    res = session.delete(f"/users/{username}")
    assert res.status_code == 200


@pytest.fixture
def a_project(session, suffix):
    """Create a unique project and return the generated name.

    Delete the project when the tests complete.
    """

    projectname = f"test-project-{suffix}"
    res = session.put(
        f"/projects/{projectname}/owner/test-owner",
        json={"displayName": "Test Project"},
    )
    assert res.status_code == 200
    yield projectname
    res = session.delete(f"/projects/{projectname}")
    assert res.status_code in [200, 400]
