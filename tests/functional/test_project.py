# pylint: disable=missing-module-docstring,redefined-outer-name
import json
import time

from .conftest import oc


def delete_project(session, projectname):
    """Test that we can successfully delete a project"""

    res = session.delete(f"/projects/{projectname}")
    assert res.status_code in [200, 400]

    tries = 10
    while True:
        res = session.get(f"/projects/{projectname}")
        assert res.status_code in [200, 400]
        if res.status_code == 400:
            break

        tries -= 1
        assert tries > 0
        time.sleep(1)


def test_create_project_with_annotations(session, suffix):
    """Test that wwe can create a project with json metadata"""

    headers = {"Content-type": "application/json"}
    annotations = {"cf_project_id": "cf_proj", "cf_pi": "cf_pi_uuid"}
    payload = {"annotations": annotations, "displayName": "Test Project"}
    try:
        session.put(
            f"/projects/test-project-{suffix}",
            data=json.dumps(payload),
            headers=headers,
        )
        res, data = oc("get", "project", f"test-project-{suffix}")
        assert res.returncode == 0
        assert data["metadata"]["name"] == f"test-project-{suffix}"
        assert (
            data["metadata"]["annotations"]["openshift.io/display-name"]
            == "Test Project"
        )
        assert data["metadata"]["annotations"]["cf_project_id"] == "cf_proj"
        assert data["metadata"]["annotations"]["cf_pi"] == "cf_pi_uuid"

    finally:
        session.delete(f"/projects/test-project-{suffix}")


def test_create_project_invalid(session):
    """Test that we cannot create a project with an invalid name"""

    res = session.put("/projects/Invalid%20Project%20Name/owner/test-owner")
    assert res.status_code == 400
    assert "project name must match" in res.json()["msg"]


def test_create_project_no_owner(session, suffix):
    """Test that we can create a project without an owner"""

    try:
        res = session.put(f"/projects/test-project-{suffix}")
        assert res.status_code == 200
    finally:
        session.delete(f"/projects/test-project-{suffix}")


def test_create_project_exists_409(session, a_project):
    """Test that creating a project with a conflicting name results in
    a 409 CONFLICT error."""

    res = session.put(f"/projects/{a_project}/owner/test-owner")
    assert res.status_code == 409


def test_get_project_notfound(session):
    """Test that a request for a project that does not exist fails as expected"""

    res = session.get("/projects/does-not-exist")
    assert res.status_code == 400


def test_get_project_exists(session, a_project):
    """Test that we can get information about a project that exists"""

    res = session.get(f"/projects/{a_project}")
    assert res.status_code == 200
    res, data = oc("get", "project", a_project)
    assert res.returncode == 0
    assert data["metadata"]["name"] == a_project
    assert data["metadata"]["annotations"]["openshift.io/requester"] == "test-owner"
    assert (
        data["metadata"]["annotations"]["openshift.io/display-name"] == "Test Project"
    )


def test_get_project_users(session, a_project, suffix):
    """Test that we can list users associated with a project"""

    # create 2 test users
    username1 = f"test-user-alice-{suffix}"
    username2 = f"test-user-bob-{suffix}"
    res = session.put(f"/users/{username1}")
    assert res.status_code == 200
    res = session.put(f"/users/{username2}")
    assert res.status_code == 200

    # add users to the project
    res = session.put(f"/users/{username1}/projects/{a_project}/roles/view")
    assert res.status_code == 200
    res = session.put(f"/users/{username2}/projects/{a_project}/roles/view")
    assert res.status_code == 200

    # check that we can retrieve the users from this project
    res = session.get(f"/projects/{a_project}/users")
    assert res.status_code == 200
    assert set(json.loads(res.content)) == set([username1, username2])

    # Delete the users
    res = session.delete(f"/users/{username1}")
    assert res.status_code == 200
    res = session.delete(f"/users/{username2}")
    assert res.status_code == 200


def test_delete_project_notfound(session):
    """Test that an attempt to delete a project that does not exist succeeds as expected"""
    res = session.delete("/projects/does-not-exist")
    assert res.status_code == 200


def test_delete_project_exists(session, a_project):
    """Test that we can successfully delete a project"""

    delete_project(session, a_project)
    res, _ = oc("get", "project", a_project)
    assert res.returncode == 1
    assert b"NotFound" in res.stderr
