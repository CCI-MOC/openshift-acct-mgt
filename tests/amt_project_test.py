""" Project  Test """

import pytest_check as check
import amt_helper as amt


def test_project(acct_mgt_url, session):
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
        amt.ms_check_project(acct_mgt_url, "test-001", session),
        "Project exists (test-001)",
    )

    # test project creation
    if not amt.oc_resource_exist("project", "Project", "test-001"):
        check.is_true(
            amt.ms_create_project(acct_mgt_url, "test-001", "test-001", session),
            "Project (test-001) not created",
        )
        check.is_true(
            amt.wait_until_lambda(
                lambda: amt.oc_resource_exist("project", "Project", "test-001")
            ),
            "ms_create_project call failed to create 'test-001')",
        )

    # test creation of a second project with the same name
    if amt.oc_resource_exist("project", "Project", "test-001"):
        check.is_false(
            amt.ms_create_project(acct_mgt_url, "test-001", "test-001", session),
            "Project (test-001) was already created",
        )
    check.is_true(
        amt.oc_resource_exist("project", "Project", "test-001"),
        "Project test-001 was not found",
    )

    # test project deletion
    if amt.oc_resource_exist("project", "Project", "test-001"):
        check.is_true(
            amt.ms_delete_project(acct_mgt_url, "test-001", session),
            "Unable to delete project (test-001)",
        )
        # Wait until test-001 is removed
        check.is_true(
            amt.wait_until_lambda(
                lambda: amt.oc_resource_exist("project", "Project", "test-001") is False
            ),
            "ms_delete_project call failed to delete'test-001')",
        )
    check.is_false(
        amt.oc_resource_exist("project", "Project", "test-001"),
        "Project test-001 exists and it shouldn't",
    )

    # test deleting a project that was deleted
    if not amt.oc_resource_exist("project", "Project", "test-001"):
        check.is_false(
            amt.ms_delete_project(acct_mgt_url, "test-001", session),
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
            "test-001",
            session,
        ),
        "Project (1234-1234-1234-1234) not created",
    )
    amt.ms_delete_project(acct_mgt_url, "1234-1234-1234-1234", session)
    check.is_true(
        amt.ms_create_project(acct_mgt_url, "2234-1234-1234-1234", "test-001", session),
        "Project (2234-1234-1234-1234) not created",
    )
    amt.ms_delete_project(acct_mgt_url, "2234-1234-1234-1234", session)
    check.is_true(
        amt.ms_create_project(acct_mgt_url, "3234-1234-1234-1234", None, session),
        "Project (3234-1234-1234-1234) not created",
    )
    amt.ms_delete_project(acct_mgt_url, "3234-1234-1234-1234", session)
    check.is_true(
        amt.ms_create_project(acct_mgt_url, "4234-1234-1234-1234", None, session),
        "Project (4234-1234-1234-1234) not created",
    )
    amt.ms_delete_project(acct_mgt_url, "4234-1234-1234-1234", session)
