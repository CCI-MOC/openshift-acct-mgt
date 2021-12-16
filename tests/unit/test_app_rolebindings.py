# pylint: disable=missing-module-docstring
from .conftest import fake_200_response, fake_400_response


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
    moc.update_user_role_project.return_value = fake_200_response
    res = client.put("/users/test-user/projects/test-project/roles/admin")
    assert res.status_code == 200
    moc.update_user_role_project.assert_called_with(
        "test-project", "test-user", "admin", "add"
    )
    assert b"it worked" in res.data


def test_create_moc_rolebindings_fails(moc, client):
    moc.update_user_role_project.return_value = fake_400_response
    res = client.put("/users/test-user/projects/test-project/roles/admin")
    assert res.status_code == 400
    assert b"it failed" in res.data


def test_delete_moc_rolebindings_exists(moc, client):
    moc.update_user_role_project.return_value = fake_200_response
    res = client.delete("/users/test-user/projects/test-project/roles/admin")
    assert res.status_code == 200
    moc.update_user_role_project.assert_called_with(
        "test-project", "test-user", "admin", "del"
    )
    assert b"it worked" in res.data


def test_delete_moc_rolebindings_fails(moc, client):
    moc.update_user_role_project.return_value = fake_400_response
    res = client.delete("/users/test-user/projects/test-project/roles/admin")
    assert res.status_code == 400
    assert b"it failed" in res.data
