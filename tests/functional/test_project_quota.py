# pylint: disable=missing-module-docstring,redefined-outer-name
import pytest

from .conftest import oc


# LKS: Cannot differentiate between "project does not exist" and
# "operation failed for some other reason".
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


@pytest.mark.parametrize("multiplier", [0, 1, 2])
def test_project_quota_set_quota(session, a_project, multiplier):
    """Test that setting a quota with different multipliers results in
    the expected quota values"""

    expected = {
        "configmaps": "4",
        "limits.ephemeral-storage": f"{2 + (8 * multiplier)}Gi",
        "requests.ephemeral-storage": f"{2 + (8 * multiplier)}Gi",
        "openshift.io/imagestreams": "2",
        "persistentvolumeclaims": "2",
        "replicationcontrollers": "2",
        "requests.storage": "2",
        "resourcequotas": "5",
        "secrets": "4",
        "services": "4",
        "services.loadbalancers": "2",
        "services.nodeports": "2",
    }
    res = session.put(
        f"/projects/{a_project}/quota", json={"Quota": {"QuotaMultiplier": multiplier}}
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
        f"/projects/{a_project}/quota", json={"Quota": {"QuotaMultiplier": 0}}
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
        f"/projects/{a_project}/quota", json={"Quota": {"QuotaMultiplier": 0}}
    )
    assert res.status_code == 200

    res, _ = oc("get", "resourcequota", f"{a_project}-project", namespace=a_project)
    assert res.returncode == 0

    res = session.delete(f"/projects/{a_project}/quota")
    assert res.status_code == 200

    res, _ = oc("get", "resourcequota", f"{a_project}-project", namespace=a_project)
    assert res.returncode == 1
    assert b"NotFound" in res.stderr
