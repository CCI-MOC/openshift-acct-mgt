# pylint: disable=missing-module-docstring,redefined-outer-name
import pytest

from .conftest import oc


def test_project_quota_project_notfound(session):
    """Test that a request for the quota of a project that does not exist fails
    as expected"""
    res = session.get("/projects/does-not-exist/quota")
    assert res.status_code == 400


def test_project_quota_no_quota(session, a_project):
    """Test that a request for the quota of a project that has no quota
    returns a null quota"""

    res = session.get(f"/projects/{a_project}/quota")
    assert res.status_code == 200
    data = res.json()
    assert data["Kind"] == "MocQuota"
    assert all(data["Quota"][k] is None for k in data["Quota"])


@pytest.mark.parametrize("limit", ["5", "10", "20"])
def test_project_quota_patch_granular(session, a_project, limit):
    """Test that setting a quota with patch replaces only the sent values"""

    expected = {
        "requests.cpu": f"{limit}m",
    }

    res = session.patch(
        f"/projects/{a_project}/quota", json={"Quota": {":requests.cpu": f"{limit}m"}}
    )
    assert res.status_code == 200

    res = session.get(f"/projects/{a_project}/quota")
    assert res.status_code == 200
    assert res.json()["Quota"] == {
        ":requests.cpu": f"{limit}m",
    }

    res, data = oc("get", "resourcequota", f"{a_project}-project", namespace=a_project)
    assert res.returncode == 0
    assert data["spec"]["hard"] == expected


@pytest.mark.parametrize("limit", ["5", "10", "20"])
def test_project_quota_put_granular(session, a_project, limit):
    """Test that setting a quota with a put removes all other values"""

    expected = {
        "resourcequotas": "100",
        "services": limit,
    }

    res = session.put(
        f"/projects/{a_project}/quota",
        json={"Quota": {":resourcequotas": "100", ":services": limit}},
    )
    assert res.status_code == 200

    res, data = oc("get", "resourcequota", f"{a_project}-project", namespace=a_project)
    assert res.returncode == 0
    assert data["spec"]["hard"] == expected


def test_project_quota_violate_quota(session, a_project):
    """Test that a quota successfully prevents us from creating too many
    ConfigMaps

    Note that this expects the service to be running with the example quota definitions
    from k8s/base/quotas.json.
    """

    for i in range(10):
        res, _ = oc("create", "configmap", f"test-configmap-{i}", namespace=a_project)
        assert res.returncode == 0

    for i in range(10):
        res, _ = oc(
            "delete",
            "configmap",
            f"test-configmap-{i}",
            namespace=a_project,
            output="name",
        )
        assert res.returncode == 0

    res = session.put(
        f"/projects/{a_project}/quota", json={"Quota": {":configmaps": 0}}
    )
    assert res.status_code == 200

    for i in range(10):
        res, _ = oc("create", "configmap", f"test-configmap-{i}", namespace=a_project)
        if res.returncode == 1:
            break

    assert res.returncode == 1
    assert b"exceeded quota" in res.stderr


def test_project_quota_delete_quota(session, a_project):
    """Test that we are able to delete the quota for a project"""

    res = session.put(
        f"/projects/{a_project}/quota", json={"Quota": {":configmaps": 0}}
    )
    assert res.status_code == 200

    res, _ = oc("get", "resourcequota", f"{a_project}-project", namespace=a_project)
    assert res.returncode == 0

    res = session.delete(f"/projects/{a_project}/quota")
    assert res.status_code == 200

    res, _ = oc("get", "resourcequota", f"{a_project}-project", namespace=a_project)
    assert res.returncode == 1
    assert b"NotFound" in res.stderr
