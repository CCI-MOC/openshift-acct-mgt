# pylint: disable=missing-module-docstring


def test_get_moc_rolebindings_exists(moc, client):
    moc.user_rolebinding_exists.return_value = True
    res = client.get("/users/test-user/projects/test-project/roles/admin")
    assert res.status_code == 200
    assert "user role exists" in res.json["msg"]


def test_get_moc_rolebindings_not_exists(moc, client):
    moc.user_rolebinding_exists.return_value = False
    res = client.get("/users/test-user/projects/test-project/roles/admin")
    assert res.status_code == 404
    assert "user role does not exist" in res.json["msg"]


def test_create_moc_rolebindings(moc, client):
    moc.add_user_to_role.return_value = {}
    res = client.put("/users/test-user/projects/test-project/roles/admin")
    assert res.status_code == 200


def test_create_moc_rolebindings_fails(moc, client):
    moc.add_user_to_role.side_effect = ValueError("dummy error")
    res = client.put("/users/test-user/projects/test-project/roles/admin")
    assert res.status_code == 400


def test_delete_moc_rolebindings_exists(moc, client):
    moc.remove_user_from_role.return_value = {}
    res = client.delete("/users/test-user/projects/test-project/roles/admin")
    assert res.status_code == 200


def test_delete_moc_rolebindings_fails(moc, client):
    moc.remove_user_from_role.side_effect = ValueError("dummy error")
    res = client.delete("/users/test-user/projects/test-project/roles/admin")
    assert res.status_code == 400
