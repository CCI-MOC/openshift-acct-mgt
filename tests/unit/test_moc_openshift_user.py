"""Test user operations in acct_mgt.moc_openshift"""

from unittest import mock


def test_get_user(moc_api):
    moc_api.get_user("test_user")
    assert moc_api.client.get.called_with("/apis/user.openshift.io/v1/users/test-user")


def test_user_exists(moc_api):
    moc_api.client.get.return_value = mock.Mock(status_code=200)
    assert moc_api.user_exists("test-user")


def test_user_not_exists(moc_api):
    moc_api.client.get.return_value = mock.Mock(status_code=404)
    assert not moc_api.user_exists("test-user")


def test_create_user(moc_api):
    moc_api.client.post.return_value = mock.Mock(status_code=200)
    res = moc_api.create_user("test-user", "Test User")
    assert res.status_code == 200
    assert moc_api.client.create.called_with(
        "/apis/user.openshift.io/v1/users",
        json={
            "kind": "User",
            "apiVersion": "user.openshift.io/v1",
            "metadata": {"name": "test-user"},
            "fullName": "Test User",
        },
    )


def test_delete_user(moc_api):
    moc_api.client.delete.return_value = mock.Mock(status_code=200)
    res = moc_api.delete_user("test-user")
    assert res.status_code == 200
    assert moc_api.client.delete.called_with(
        "/apis/user.openshift.io/v1/users/test-user",
    )
