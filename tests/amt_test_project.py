""" Project  Test """

import pytest_check as check
import acct_mgt_test as amt


def test_project(acct_mgt_url, auth_opts):
    """This tests project existence/creation/deletion"""
    # if oc_resource_exist(
    #    "project",
    #    "test-001",
    #    "test-001[ \t]*test-001[ \t]",
    #    'Error from server (NotFound): namespaces "test-001" not found',
    # ):
    #    print(
    #        "Error: test_project failed as a project with a name of test-001 exists.  \n" +
    #        "Please delete first and rerun the tests\n"
    #    )
    #    assertTrue(False)

    # test if project doesn't exist
    check.is_false(
        amt.ms_check_project(acct_mgt_url, "test-001", auth_opts),
        "Project exists (test-001)",
    )

    # test project creation
    if not amt.oc_resource_exist("project", "Project", "test-001"):
        check.is_true(
            amt.ms_create_project(
                acct_mgt_url, "test-001", r'{"displayName":"test-001"}', auth_opts
            ),
            "Project (test-001) not created",
        )
        amt.wait_until_done(
            "oc get project test-001", r"test-001[ \t]+test-001[ \t]+Active"
        )
    check.is_true(
        amt.oc_resource_exist("project", "Project", "test-001"),
        "Project (test-001) not created",
    )
    check.is_true(
        amt.ms_check_project(acct_mgt_url, "test-001", auth_opts),
        "project test-001 was not found",
    )

    # test creation of a second project with the same name
    if amt.oc_resource_exist("project", "Project", "test-001"):
        check.is_false(
            amt.ms_create_project(
                acct_mgt_url, "test-001", r'{"displayName":"test-001"}', auth_opts
            ),
            "Project (test-001) was already created",
        )
    check.is_true(
        amt.oc_resource_exist("project", "Project", "test-001"),
        "Project test-001 was not found",
    )

    # test project deletion
    if amt.oc_resource_exist("project", "Project", "test-001"):
        check.is_true(
            amt.ms_delete_project(acct_mgt_url, "test-001", auth_opts),
            "Unable to delete project (test-001)",
        )
        # Wait until test-001 is terminated
        amt.wait_until_done(
            "oc get project test-001",
            r'Error from server (NotFound): namespaces "test-001" not found',
        )
    check.is_false(
        amt.oc_resource_exist("project", "Project", "test-001"),
        "Project test-001 exists and it shouldn't",
    )

    # test deleting a project that was deleted
    if not amt.oc_resource_exist("project", "Project", "test-001"):
        check.is_false(
            amt.ms_delete_project(acct_mgt_url, "test-001", auth_opts),
            "shouldn't be able to delete a non-existing project",
        )
    check.is_false(
        amt.oc_resource_exist("project", "Project", "test-001"),
        "Project test-001 exists and it should not",
    )

    # these tests are primarily done to ensure that the microserver doesn't crash
    #    When the "displayName" is not present, or the json doesn't exist, the displayName shall
    #    default to the project_uuid (first parameter)
    check.is_true(
        amt.ms_create_project(
            acct_mgt_url,
            "1234-1234-1234-1234",
            r'{"displayName":"test-001"}',
            auth_opts,
        ),
        "Project (1234-1234-1234-1234) not created",
    )
    amt.ms_delete_project(acct_mgt_url, "1234-1234-1234-1234", auth_opts)
    check.is_true(
        amt.ms_create_project(
            acct_mgt_url, "2234-1234-1234-1234", r'{"displaName":"test-001"}', auth_opts
        ),
        "Project (2234-1234-1234-1234) not created",
    )
    amt.ms_delete_project(acct_mgt_url, "2234-1234-1234-1234", auth_opts)
    check.is_true(
        amt.ms_create_project(acct_mgt_url, "3234-1234-1234-1234", r"{}", auth_opts),
        "Project (3234-1234-1234-1234) not created",
    )
    amt.ms_delete_project(acct_mgt_url, "3234-1234-1234-1234", auth_opts)
    check.is_true(
        amt.ms_create_project(acct_mgt_url, "4234-1234-1234-1234", None, auth_opts),
        "Project (4234-1234-1234-1234) not created",
    )
    amt.ms_delete_project(acct_mgt_url, "4234-1234-1234-1234", auth_opts)
