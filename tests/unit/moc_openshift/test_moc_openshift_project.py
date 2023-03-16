# pylint: disable=missing-module-docstring
from unittest import mock

import kubernetes.dynamic.exceptions as kexc


def test_get_project(moc):
    fake_project = mock.Mock(spec=["to_dict"])
    fake_project.to_dict.return_value = {"project": "fake-project"}
    moc.client.resources.get.return_value.get.return_value = fake_project
    res = moc.get_project("fake-project")
    assert res == {"project": "fake-project"}


def test_project_exists(moc):
    fake_project = mock.Mock(spec=["to_dict"])
    moc.client.resources.get.return_value.get.return_value = fake_project
    assert moc.project_exists("fake-project")


def test_project_exists_not(moc):
    moc.client.resources.get.return_value.get.side_effect = kexc.NotFoundError(
        mock.Mock()
    )
    assert not moc.project_exists("fake-project")


@mock.patch("acct_mgt.moc_openshift.MocOpenShift4x.create_limits", mock.Mock())
def test_create_project(moc):
    moc.create_project("fake-project", "Fake Project", "fake-user")
    moc.client.resources.get.return_value.create.assert_called_with(
        body={
            "metadata": {
                "name": "fake-project",
                "annotations": {
                    "openshift.io/display-name": "Fake Project",
                    "openshift.io/requester": "fake-user",
                },
                "labels": {"nerc.mghpcc.org/project": "true"},
            }
        }
    )


def test_delete_project(moc):
    moc.delete_project("fake-project")
    moc.client.resources.get.return_value.delete.assert_called_with(name="fake-project")
