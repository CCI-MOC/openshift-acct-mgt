"""Test identity operations in acct_mgt.moc_openshift"""

from unittest import mock


def test_identity_exists(moc_api):
    moc_api.client.get.return_value = mock.Mock(status_code=200)
    assert moc_api.identity_exists("test-identity")


def test_identity_not_exists(moc_api):
    moc_api.client.get.return_value = mock.Mock(status_code=404)
    assert not moc_api.identity_exists("test-identity")


def test_create_identity(moc_api):
    moc_api.client.post.return_value = mock.Mock(status_code=200)
    res = moc_api.create_identity("test-user")
    assert res.status_code == 200
    assert moc_api.client.create.called_with(
        "/apis/user.openshift.io/v1/identities",
        json={
            "kind": "Identity",
            "apiVersion": "user.openshift.io/v1",
            "providerName": "fake",
            "providerUserName": "test-user",
        },
    )


def test_delete_identity(moc_api):
    moc_api.client.delete.return_value = mock.Mock(status_code=200)
    res = moc_api.delete_identity("test-user")
    assert res.status_code == 200
    assert moc_api.client.delete.called_with(
        "/apis/user.openshift.io/v1/identities/fake:test-user",
    )


def test_create_useridentitymapping(moc_api):
    moc_api.client.post.return_value = mock.Mock(status_code=200)
    res = moc_api.create_useridentitymapping("test-user", "test-user")
    assert res.status_code == 200
    assert moc_api.client.create.called_with(
        "/apis/user.openshift.io/v1/identities",
        json={
            "kind": "UserIdentityMapping",
            "apiVersion": "user.openshift.io/v1",
            "user": {"name": "test-user"},
            "identity": {"name": "fake:test-user"},
        },
    )
