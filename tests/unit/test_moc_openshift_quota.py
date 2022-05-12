"""Test quota operations in acct_mgt.moc_openshift"""

import json
from unittest import mock

import pytest


@pytest.mark.xfail(reason="propagates FileNotFoundError")
def test_get_quota_definitions_missing(moc_api):
    """What happens if the quota file is missing?"""
    with mock.patch("acct_mgt.moc_openshift.open", mock.mock_open()) as mock_open:
        mock_open.side_effect = FileNotFoundError()
        res = moc_api.get_quota_definitions()
        assert res == {}


@pytest.mark.xfail(reason="raises JSONDecodeError")
def test_get_quota_definitions_empty(moc_api):
    """What happens if the quota file exists but is empty?"""
    with mock.patch("builtins.open", mock.mock_open(read_data="")):
        res = moc_api.get_quota_definitions()
        assert res == {}


@pytest.mark.xfail(reason="raises TypeError")
def test_get_quota_definitions_invalid(moc_api):
    """What happens if the quota file exists but contains invalid data?"""
    with mock.patch("builtins.open", mock.mock_open(read_data='{"foo": "bar"}')):
        res = moc_api.get_quota_definitions()
        assert res == {}


def test_get_quota_definitions_valid(moc_api):
    """What happens if a valid quota file exists?"""
    quotadefs = {
        ":configmaps": {"base": 2, "coefficient": 0},
    }
    with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(quotadefs))):
        res = moc_api.get_quota_definitions()
        quotadefs[":configmaps"]["value"] = None
        assert res == quotadefs


def test_split_quota_name(moc_api):
    assert moc_api.split_quota_name(":foo") == ("Project", "foo")
    assert moc_api.split_quota_name("scope:foo") == ("scope", "foo")


def test_get_resourcequotas(moc_api):
    moc_api.client.get.return_value = mock.Mock(
        json=lambda: {
            "items": [
                {"metadata": {"name": "q1"}},
                {"metadata": {"name": "q2"}},
            ]
        },
    )
    res = moc_api.get_resourcequotas("test-project")
    moc_api.client.get.assert_called_with(
        "/api/v1/namespaces/test-project/resourcequotas"
    )
    assert res == ["q1", "q2"]


def test_delete_quota(moc_api):
    moc_api.delete_quota("test-project", "test-quota")
    assert moc_api.client.delete.called_with(
        "/api/v1/namespaces/test-project/resourcequotas/test-quota"
    )


def test_delete_moc_quota(moc_api):
    moc_api.client.get.return_value = mock.Mock(
        json=lambda: {
            "items": [
                {"metadata": {"name": "q1"}},
                {"metadata": {"name": "q2"}},
            ]
        },
    )
    moc_api.client.delete.return_value = mock.Mock(status_code=200)
    res = moc_api.delete_moc_quota("test-project")
    assert res.status_code == 200
    moc_api.client.get.assert_called_with(
        "/api/v1/namespaces/test-project/resourcequotas"
    )
    for qname in ["q1", "q2"]:
        url = f"/api/v1/namespaces/test-project/resourcequotas/{qname}"
        moc_api.client.delete.assert_any_call(url)


def test_delete_moc_quota_failure(moc_api):
    moc_api.client.get.return_value = mock.Mock(
        json=lambda: {
            "items": [
                {"metadata": {"name": "q1"}},
                {"metadata": {"name": "q2"}},
            ]
        },
    )
    moc_api.client.delete.return_value = mock.Mock(status_code=400)
    res = moc_api.delete_moc_quota("test-project")
    assert res.status_code == 400
    assert b"deletion failed" in res.data


@pytest.mark.xfail(reason="bug")
def test_get_moc_quota(moc_api):
    quotadefs = {
        ":configmaps": {"base": 2, "coefficient": 0},
    }
    with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(quotadefs))):
        res = moc_api.get_moc_quota("test-project")
        assert res["Kind"] == "MocQuota"
        assert res["Quota"] == quotadefs


def test_update_moc_quota(moc_api):
    quotadefs = {
        ":configmaps": {"base": 2, "coefficient": 0},
    }
    quotareq = {
        "Quota": {
            "QuotaMultiplier": 1,
        },
    }
    moc_api.client.delete.return_value = mock.Mock(status_code=200)
    moc_api.client.post.return_value = mock.Mock(status_code=200)
    moc_api.get_resourcequotas = mock.Mock(return_value=[])

    with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(quotadefs))):
        res = moc_api.update_moc_quota("test-project", quotareq)
        assert res.status_code == 200


def test_update_moc_quota_delete_fails(moc_api):
    quotadefs = {
        ":configmaps": {"base": 2, "coefficient": 0},
    }
    quotareq = {
        "Quota": {
            "QuotaMultiplier": 1,
        },
    }
    moc_api.client.delete.return_value = mock.Mock(status_code=404)
    moc_api.get_resourcequotas = mock.Mock(return_value=[{}])

    with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(quotadefs))):
        res = moc_api.update_moc_quota("test-project", quotareq)
        assert res.status_code == 404


def test_update_moc_quota_create_fails(moc_api):
    quotadefs = {
        ":configmaps": {"base": 2, "coefficient": 0},
    }
    quotareq = {
        "Quota": {
            "QuotaMultiplier": 1,
        },
    }
    moc_api.client.delete.return_value = mock.Mock(status_code=200)
    moc_api.client.post.return_value = mock.Mock(status_code=500)
    moc_api.get_resourcequotas = mock.Mock(return_value=[{}])

    with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(quotadefs))):
        res = moc_api.update_moc_quota("test-project", quotareq)
        assert res.status_code == 400
