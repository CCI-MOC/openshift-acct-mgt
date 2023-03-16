# pylint: disable=missing-module-docstring
from unittest import mock
import kubernetes.dynamic.exceptions as kexc


def test_get_quota(moc, client):
    moc.get_moc_quota.return_value = {}
    res = client.get("/projects/fake-project/quota")
    assert res.status_code == 200
    moc.get_moc_quota.assert_called_with("fake-project")


def test_get_quota_project_not_found(moc, client):
    moc.get_moc_quota.side_effect = kexc.NotFoundError(mock.Mock())
    res = client.get("/projects/fake-project/quota")
    assert res.status_code == 400


def test_put_quota(moc, client):
    moc.update_moc_quota.return_value = {}
    res = client.put("/projects/fake-project/quota", data="{}")
    assert res.status_code == 200
    moc.update_moc_quota.assert_called_with("fake-project", {}, patch=False)


def test_patch_quota(moc, client):
    moc.update_moc_quota.return_value = {}
    res = client.patch("/projects/fake-project/quota", data="{}")
    assert res.status_code == 200
    moc.update_moc_quota.assert_called_with("fake-project", {}, patch=True)


def test_delete_quota(moc, client):
    moc.delete_moc_quota.return_value = {}
    res = client.delete("/projects/fake-project/quota")
    assert res.status_code == 200
    moc.delete_moc_quota.assert_called_with("fake-project")
