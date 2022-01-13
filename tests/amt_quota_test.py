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
            "Quota": {"QuotaMultiplier": 0},
        },
        session,
    )
    moc_quota_0 = amt.ms_get_moc_quota(acct_mgt_url, project_name, session)
    moc_quota_0 = amt.remove_quota_units(moc_quota_0["Quota"])

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
    moc_quota_1 = amt.ms_get_moc_quota(acct_mgt_url, project_name, session)
    moc_quota_1 = amt.remove_quota_units(moc_quota_1["Quota"])

    amt.ms_put_moc_quota(
        acct_mgt_url,
        project_name,
        {
            "Version": "0.9",
            "Kind": "MocQuota",
            "ProjectName": "rbb-test",
            "Quota": {"QuotaMultiplier": 3},
        },
        session,
    )
    moc_quota_3 = amt.ms_get_moc_quota(acct_mgt_url, project_name, session)
    moc_quota_3 = amt.remove_quota_units(moc_quota_3["Quota"])

    slope = amt.div_moc_quota(
        amt.diff_moc_quota(moc_quota_3, moc_quota_0),
        amt.diff_moc_quota(moc_quota_1, moc_quota_0),
    )
    check.is_true(
        amt.are_all_quota_same_value(slope, 3),
        "The slope is not consistent, QuotaMultiplier doesnt work",
    )

    # test setting a specific quota
    amt.ms_del_moc_quota(acct_mgt_url, project_name, session)

    quota1 = {
        "Version": "0.9",
        "Kind": "MocQuota",
        "ProjectName": "rbb-test",
        "Quota": {":resourcequotas": 5, "BestEffort:pods": 2},
    }

    amt.ms_put_moc_quota(
        acct_mgt_url,
        project_name,
        quota1,
        session,
    )

    ret_quota = amt.ms_get_moc_quota(acct_mgt_url, project_name, session)
    quota1 = amt.remove_quota_units(quota1["Quota"])
    ret_quota = amt.remove_quota_units(ret_quota["Quota"])
    check.is_true(
        amt.are_all_quota_same_value(amt.diff_moc_quota(quota1, ret_quota), 0),
        "Quotas Don't match, but they should",
    )

    # modifying the above quota
    quota1 = {
        "Version": "0.9",
        "Kind": "MocQuota",
        "ProjectName": "rbb-test",
        "Quota": {":resourcequotas": None},
    }

    amt.ms_patch_moc_quota(
        acct_mgt_url,
        project_name,
        quota1,
        session,
    )

    ret_quota = amt.ms_get_moc_quota(acct_mgt_url, project_name, session)

    expected_quota = {
        "Version": "0.9",
        "Kind": "MocQuota",
        "ProjectName": "rbb-test",
        "Quota": {"BestEffort:pods": 2},        
    }
    ret_quota = amt.remove_quota_units(ret_quota["Quota"])
    expected_quota = amt.remove_quota_units(expected_quota["Quota"])
    check.is_true(
        amt.are_all_quota_same_value(amt.diff_moc_quota(ret_quota, ret_quota), 0),
        "Quotas Don't match, but they should",
    )
    # cleanup after testing
    check.is_true(
        amt.ms_delete_project(acct_mgt_url, project_name, session) is True,
        "project (test-002) deleted",
    )
