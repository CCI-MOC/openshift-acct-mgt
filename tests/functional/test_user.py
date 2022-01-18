# pylint: disable=missing-module-docstring,redefined-outer-name
import pytest

from .conftest import oc


def test_get_user_unauthenticated(session_noauth, admin_password):
    """Test that an unauthenticated request fails with 401 UNAUTHORIZED when
    authentication is enabled"""

    if admin_password is None:
        pytest.skip("authentication is disabled")
    res = session_noauth.get("/users/does-not-matter")
    assert res.status_code == 401


# LKS: Cannot differentiate between "user does not exist" and "operation failed
# for some other reason".
def test_get_user_notfound(session):
    """Test response code when we attempt to get information about a user
    that does not exist"""

    res = session.get("/users/does-not-exist")
    assert res.status_code == 400


@pytest.mark.xfail(reason="not supported by service")
def test_get_user_notfound_404(session):
    """Test that an attempt to get information about a user that does not
    exist results in a 404 NOTFOUND response code"""

    res = session.get("/users/does-not-exist")
    assert res.status_code == 404


def test_get_user_exists(a_user):
    """Test that a user has been created with the expected information"""

    res, data = oc("get", "user", a_user)
    assert res.returncode == 0
    assert data["metadata"]["name"] == a_user


# LKS: cannot differentiate between "user was deleted" and "user did
# not exist".
def test_delete_user_notfound(session):
    """Test response code when we attempt to delete a user that does not exist"""

    res = session.delete("/users/does-not-exist")
    assert res.status_code == 200


@pytest.mark.xfail(reason="not supported by service")
def test_delete_user_notfound_404(session):
    """Test response code when we attempt to delete a user that does not exist"""

    res = session.delete("/users/does-not-exist")
    assert res.status_code == 404


def test_delete_user_exists(session, a_user):
    """Test that we can successfully delete a user"""

    res = session.delete(f"/users/{a_user}")
    assert res.status_code == 200
    res, _ = oc("get", "user", a_user)
    assert res.returncode == 1
    assert b"NotFound" in res.stderr


# LKS: Cannot differentiate between "conflict with existing user" and
# "operation failed for some other reason"
def test_create_user_exists(session, a_user):
    """Test that we cannot create a new user that conflicts with an existing
    user"""
    res = session.put(f"/users/{a_user}")
    assert res.status_code == 400


@pytest.mark.xfail(reason="not supported by service")
def test_create_user_exists_409(session, a_user):
    """Test that an attempt to create new user that conflicts with
    an existing user results in a 409 CONFLICT response"""

    res = session.put(f"/users/{a_user}")
    assert res.status_code == 409
