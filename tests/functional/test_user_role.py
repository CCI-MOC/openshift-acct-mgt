# pylint: disable=missing-module-docstring,redefined-outer-name
from .conftest import oc


def test_user_role_does_not_haver_role(session, a_project, a_user):
    """Test response when a user does not have the requested role"""

    res = session.get(f"/users/{a_user}/projects/{a_project}/roles/admin")
    assert res.status_code == 404
    assert "user role does not exist" in res.json()["msg"]


def test_user_role_user_notfound(session, a_project):
    """Test response when request role information for a user that does not exist"""
    res = session.get(f"/users/does-not-exist/projects/{a_project}/roles/admin")
    assert res.status_code == 404


def test_user_role_project_notfound(session, a_user):
    """Test response when request role information for a project that does not exist"""
    res = session.get(f"/users/{a_user}/projects/does-not-exist/roles/admin")
    assert res.status_code == 404


def test_user_role_add_role_invalid(session, a_project, a_user):
    """Test that an attempt to grant a user an invalid role fails as expected"""

    res = session.put(f"/users/{a_user}/projects/{a_project}/roles/does-not-exist")
    assert res.status_code == 400
    assert "invalid role" in res.json()["msg"].lower()


def test_user_role_add_role(session, a_project, a_user):
    """Test that we can successfully grant a role to a user"""

    url = f"/users/{a_user}/projects/{a_project}/roles/admin"

    res = session.put(url)
    assert res.status_code == 200

    res, data = oc("get", "rolebinding", "admin", namespace=a_project)
    assert res.returncode == 0
    assert data["subjects"][0]["kind"] == "User"
    assert data["subjects"][0]["name"] == a_user

    res = session.delete(url)
    assert res.status_code == 200
    res, data = oc("get", "rolebinding", "admin", namespace=a_project)
    assert res.returncode == 0
    assert "subjects" not in data
