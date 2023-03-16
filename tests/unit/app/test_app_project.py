# pylint: disable=missing-module-docstring
import json

from acct_mgt.exceptions import ApiException


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
    assert "test-project" in res.json["msg"]


def test_create_moc_project_no_display_name(moc, client):
    moc.cnvt_project_name.return_value = "test-project"
    moc.project_exists.return_value = False
    moc.create_project.return_value = {}
    res = client.put("/projects/test-project")
    assert res.status_code == 200
    moc.create_project.assert_called_with(
        "test-project", "test-project", None, annotations={}
    )


def test_create_moc_project_with_display_name(moc, client):
    moc.cnvt_project_name.return_value = "test-project"
    moc.project_exists.return_value = False
    moc.create_project.return_value = {}
    res = client.put(
        "/projects/test-project",
        data=json.dumps({"displayName": "Test Project"}),
        content_type="application/json",
    )
    assert res.status_code == 200
    moc.create_project.assert_called_with(
        "test-project", "Test Project", None, annotations={}
    )


def test_create_moc_project_with_annotations(moc, client):
    moc.cnvt_project_name.return_value = "test-project"
    moc.project_exists.return_value = False
    moc.create_project.return_value = {}
    annotations = {"cf_pi": "1"}
    res = client.put(
        "/projects/test-project",
        data=json.dumps({"annotations": annotations}),
        content_type="application/json",
    )
    assert res.status_code == 200
    moc.create_project.assert_called_with(
        "test-project", "test-project", None, annotations=annotations
    )


def test_create_moc_project_exists(moc, client):
    moc.cnvt_project_name.return_value = "test-project"
    moc.project_exists.return_value = True
    res = client.put("/projects/test-project")
    assert res.status_code == 409
    assert "project already exists" in res.json["msg"]


def test_create_moc_project_fails(moc, client):
    moc.cnvt_project_name.return_value = "test-project"
    moc.project_exists.return_value = False
    moc.create_project.side_effect = ApiException("Error")
    res = client.put("/projects/test-project")
    assert res.status_code == 500
    assert "Error" in res.json["msg"]


def test_delete_moc_project_exists(moc, client):
    moc.project_exists.return_value = True
    moc.delete_project.return_value = {}
    res = client.delete("/projects/test-project")
    assert res.status_code == 200


def test_delete_moc_project_not_exists(moc, client):
    moc.project_exists.return_value = False
    res = client.delete("/projects/test-project")
    assert res.status_code == 200


def test_delete_moc_project_fails(moc, client):
    moc.project_exists.return_value = True
    moc.delete_project.side_effect = ValueError("dummy error message")
    res = client.delete("/projects/test-project")
    assert res.status_code == 400
