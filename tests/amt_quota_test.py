""" tests adding quotas to projects """

import pytest_check as check
import amt_helper as amt


def test_quota(acct_mgt_url, session):
    """This tests quota support on the microserver"""
    # 1) Create a project
    project_name = "test-003"
    if not amt.oc_resource_exist("project", "Project", project_name):
        check.is_true(
            amt.ms_create_project(acct_mgt_url, project_name, None, session),
            f"Project ({project_name}) was unable to be created",
        )
    check.is_true(
        amt.oc_resource_exist("project", "Project", project_name),
        f"Project ({project_name}) does not exist",
    )

    # 2) Check to see that the quota is empty
    check.is_false(
        amt.oc_resource_exist("resourcequota", "ResourceQuota", None, project_name),
        "Error, unexpected quota as it should be empty",
    )

    # 3) Can we delete an empty quota?
    amt.ms_del_moc_quota(acct_mgt_url, project_name, session)
    # for now just endure that the service doesn't break
    # would like to test this like:
    # check.is_false(
    #     amt.ms_del_moc_quota(acct_mgt_url, project_name, session),
    #     "Error: Empty quota deleted",
    # )

    # 4) Create a quota using the QuotaMultiplier as adjutant/coldfront will initially do
    amt.ms_put_moc_quota(
        acct_mgt_url,
        project_name,
        {
            "Version": "0.9",
            "Kind": "MocQuota",
            "ProjectName": "rbb-test",
            "Quota": {"QuotaMultiplier": 1},
        },
        session,
    )
    check.is_true(
        amt.oc_resource_exist("resourcequota", "ResourceQuota", None, project_name),
        "quotas not there, but should be",
    )
    # cleanup after testing
    check.is_true(
        amt.ms_delete_project(acct_mgt_url, project_name, session) is True,
        "project (test-002) deleted",
    )
