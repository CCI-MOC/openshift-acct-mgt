# pylint: disable=missing-module-docstring


def test_get_moc_user_exists_auth_failure(client_auth):
    """Verify we get 401 UNAUTHORIZED when authentication is required.

    This is the only method that makes use of the authenticating client."""
    res = client_auth.get("/users/test-user")
    assert res.status_code == 401


def test_get_moc_user_exists(moc, client):
    moc.user_exists.return_value = True
    res = client.get("/users/test-user")
    assert res.status_code == 200


def test_get_moc_user_not_exists(moc, client):
    moc.user_exists.return_value = False
    res = client.get("/users/test-user")
    assert res.status_code == 404
    moc.user_exists.assert_called_with("test-user")


def test_create_moc_user_create_user_fails(moc, client):
    moc.user_exists.return_value = False
    moc.create_user.side_effect = ValueError("dummy error message")
    res = client.put("/users/test-user")
    assert res.status_code == 400


def test_create_moc_user_create_identity_fails(moc, client):
    moc.user_exists.return_value = False
    moc.identity_exists.return_value = False
    moc.create_identity.side_effect = ValueError("dummy error message")
    res = client.put("/users/test-user")
    assert res.status_code == 400


def test_create_moc_user_create_mapping_fails(moc, client):
    moc.user_exists.return_value = False
    moc.identity_exists.return_value = False
    moc.useridentitymapping_exists.return_value = False
    moc.create_useridentitymapping.side_effect = ValueError("dummy error message")
    res = client.put("/users/test-user")
    assert res.status_code == 400


def test_create_moc_user_create_all(moc, client):
    moc.user_exists.return_value = False
    moc.create_user.return_value = {}
    moc.identity_exists.return_value = False
    moc.create_identity.return_value = {}
    moc.useridentitymapping_exists.return_value = False
    moc.create_useridentitymapping.return_value = {}
    res = client.put("/users/test-user")
    assert res.status_code == 200
    moc.create_user.assert_called_with("test-user", "test-user")
    moc.create_identity.assert_called_with("test-user")
    moc.create_useridentitymapping.assert_called_with("test-user", "test-user")
    assert "user created" in res.json["msg"]


def test_delete_moc_user_delete_user_fails(moc, client):
    moc.user_exists.return_value = True
    moc.delete_user.side_effect = ValueError("dummy error message")
    res = client.delete("/users/test-user")
    assert res.status_code == 400


def test_delete_moc_user_delete_identity_fails(moc, client):
    moc.user_exists.return_value = True
    moc.identity_exists.return_value = True
    moc.delete_identity.side_effect = ValueError("dummy error message")
    res = client.delete("/users/test-user")
    assert res.status_code == 400


def test_delete_moc_user_delete_not_exists(moc, client):
    moc.user_exists.return_value = False
    moc.identity_exists.return_value = False
    res = client.delete("/users/test-user")
    assert res.status_code == 200


def test_delete_moc_user_delete_all(moc, client):
    moc.user_exists.return_value = True
    moc.delete_user.return_value = {}
    moc.identity_exists.return_value = True
    moc.delete_identity.return_value = {}
    res = client.delete("/users/test-user")
    assert res.status_code == 200
    assert "user deleted" in res.json["msg"]
