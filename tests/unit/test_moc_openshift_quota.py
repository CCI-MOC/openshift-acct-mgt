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


@pytest.mark.xfail(reason="raises a KeyError")
def test_resolve_quotas_invalid(moc_api):
    """What happens if the quota request doesn't have a Quotas element?"""
    quotadefs = {
        ":configmaps": {"base": 2, "coefficient": 1},
    }

    with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(quotadefs))):
        moc_api.resolve_quotas({})


@pytest.mark.xfail(reason="returns a quota with a value of None")
def test_resolve_quotas_no_multiplier(moc_api):
    """What happens if the quota request doesn't have a QuotaMultiplier element?"""
    quotadefs = {
        ":configmaps": {"base": 2, "coefficient": 1},
    }

    with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(quotadefs))):
        quota_def = moc_api.resolve_quotas({"Quota": {}})
        assert quota_def == {
            ":configmaps": {"base": 2, "coefficient": 1, "value": 2},
        }


def test_resolve_quotas_valid(moc_api):
    """What happens if the quota definition is valid?"""
    base = 2
    coefficient = 2
    quotadefs = {
        ":configmaps": {"base": base, "coefficient": coefficient},
    }

    with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(quotadefs))):
        for mult in [0, 1, 2, 3]:
            quota_def = moc_api.resolve_quotas({"Quota": {"QuotaMultiplier": mult}})
            assert quota_def == {
                ":configmaps": {
                    "base": base,
                    "coefficient": coefficient,
                    "value": (base + coefficient * mult),
                },
            }


def test_create_shift_quotas(moc_api):
    quotadefs = {
        ":configmaps": {"base": 2, "coefficient": 1},
    }

    moc_api.client.post.return_value = mock.Mock(status_code=200)

    with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(quotadefs))):
        quota_def = moc_api.resolve_quotas({"Quota": {"QuotaMultiplier": 2}})
        res = moc_api.create_shift_quotas("test-project", quota_def)
        assert res.status_code == 200
        assert res.data == b"All quota from test-project successfully created"
        assert moc_api.client.post.call_args_list[0][1]["json"]["spec"] == {
            "hard": {"configmaps": 4}
        }


def test_create_shift_quotas_failure(moc_api):
    quotadefs = {
        ":configmaps": {"base": 2, "coefficient": 1},
    }

    moc_api.client.post.return_value = mock.Mock(status_code=400)

    with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(quotadefs))):
        quota_def = moc_api.resolve_quotas({"Quota": {"QuotaMultiplier": 2}})
        res = moc_api.create_shift_quotas("test-project", quota_def)
        assert res.status_code == 400
        assert b"creation failed" in res.data


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


def test_replace_moc_quota(moc_api):
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
        res = moc_api.replace_moc_quota("test-project", quotareq)
        assert res.status_code == 200


def test_replace_moc_quota_delete_fails(moc_api):
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
        res = moc_api.replace_moc_quota("test-project", quotareq)
        assert res.status_code == 404


def test_replace_moc_quota_create_fails(moc_api):
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
        res = moc_api.replace_moc_quota("test-project", quotareq)
        assert res.status_code == 400
