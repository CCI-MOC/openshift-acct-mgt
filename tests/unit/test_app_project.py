# pylint: disable=missing-module-docstring
import json

from .conftest import fake_200_response, fake_400_response


def test_get_moc_project_exists(moc, client):
    moc.project_exists.return_value = True
    res = client.get("/projects/test-project")
    assert res.status_code == 200
    assert "project exists" in res.json["msg"]


def test_get_moc_project_fails(moc, client):
    moc.project_exists.return_value = False
    res = client.get("/projects/test-project")
    assert res.status_code == 400
    assert "project does not exist" in res.json["msg"]


def test_create_moc_project_bad_name(moc, client):
    moc.cnvt_project_name.return_value = "test-project"
    res = client.put("/projects/Test%20Project")
    assert res.status_code == 400
    assert "project name must match regex" in res.json["msg"]
    assert res.json["suggested name"] == "test-project"


def test_create_moc_project_no_display_name(moc, client):
    moc.cnvt_project_name.return_value = "test-project"
    moc.project_exists.return_value = False
    moc.create_project.return_value = fake_200_response
    res = client.put("/projects/test-project")
    assert res.status_code == 200
    moc.create_project.assert_called_with("test-project", "test-project", None)


def test_create_moc_project_with_display_name(moc, client):
    moc.cnvt_project_name.return_value = "test-project"
    moc.project_exists.return_value = False
    moc.create_project.return_value = fake_200_response
    res = client.put(
        "/projects/test-project",
        data=json.dumps({"displayName": "Test Project"}),
        content_type="application/json",
    )
    assert res.status_code == 200
    moc.create_project.assert_called_with("test-project", "Test Project", None)


def test_create_moc_project_exists(moc, client):
    moc.cnvt_project_name.return_value = "test-project"
    moc.project_exists.return_value = True
    res = client.put("/projects/test-project")
    assert res.status_code == 400
    assert "project already exists" in res.json["msg"]


def test_create_moc_project_fails(moc, client):
    moc.cnvt_project_name.return_value = "test-project"
    moc.project_exists.return_value = False
    moc.create_project.return_value = fake_400_response
    res = client.put("/projects/test-project")
    assert res.status_code == 400
    assert "unable to create project" in res.json["msg"]


def test_delete_moc_project_exists(moc, client):
    moc.project_exists.return_value = True
    moc.delete_project.return_value = fake_200_response
    res = client.delete("/projects/test-proejct")
    assert res.status_code == 200


def test_delete_moc_project_not_exists(moc, client):
    moc.project_exists.return_value = False
    moc.delete_project.return_value = fake_400_response
    res = client.delete("/projects/test-proejct")
    assert res.status_code == 400
    assert "project does not exist" in res.json["msg"]


def test_delete_moc_project_fails(moc, client):
    moc.project_exists.return_value = True
    moc.delete_project.return_value = fake_400_response
    res = client.delete("/projects/test-proejct")
    assert res.status_code == 400
    assert "unable to delete project" in res.json["msg"]
