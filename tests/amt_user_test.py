""" test user functionality """

import pytest_check as check
import amt_helper as amt


def test_user(acct_mgt_url, auth_opts):
    """This tests user (and user identity) existence/creation/deletion"""
    # if oc_resource_exist(
    #    "user",
    #    "test01",
    #    r"test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01",
    #    r'Error from server (NotFound): users.user.openshift.io "test01" not found',
    # ):
    #    print(
    #        "Error: test_user failed as a user with a name of test01 exists.\n" +
    #        "Please delete first and rerun the tests\n"
    #    )
    #    assertTrue(False)

    check.is_false(
        amt.ms_check_user(acct_mgt_url, "test01", auth_opts),
        "User test01 exists but it shouldn't exist at this point",
    )

    # test user creation
    # test01      bfd6dab5-11f3-11ea-89a6-fa163e2bb38b      sso_auth:test01
    if not amt.oc_resource_exist("users", "User", "test01"):
        check.is_true(
            amt.ms_create_user(acct_mgt_url, "test01", auth_opts),
            "unable to create test01",
        )

    check.is_true(
        amt.oc_resource_exist("users", "User", "test01"),
        "user test01 doesn't exist",
    )
    check.is_true(
        amt.ms_check_user(acct_mgt_url, "test01", auth_opts),
        "User test01 doesn't exist but it should",
    )

    # test creation of a second user with the same name
    if amt.oc_resource_exist("users", "User", "test01"):
        check.is_false(
            amt.ms_create_user(acct_mgt_url, "test01", auth_opts),
            "Should have failed to create a second user with the username of test01",
        )
    check.is_true(
        amt.oc_resource_exist("users", "User", "test01"),
        "user test01 doesn't exist",
    )

    # test user deletion
    if amt.oc_resource_exist("users", "User", "test01"):
        check.is_true(
            amt.ms_delete_user(acct_mgt_url, "test01", auth_opts),
            "user test01 deleted",
        )
    check.is_false(
        amt.oc_resource_exist("users", "User", "test01"),
        "user test01 not found",
    )

    # test deleting a user that was deleted
    if not amt.oc_resource_exist("users", "User", "test01"):
        check.is_false(
            amt.ms_delete_user(acct_mgt_url, "test01", auth_opts),
            "shouldn't be able to delete non-existing user test01",
        )
    check.is_false(
        amt.oc_resource_exist("users", "User", "test01"),
        "user test01 not found",
    )
    check.is_false(
        amt.ms_check_user(acct_mgt_url, "test01", auth_opts),
        "User test01 exists but it shouldn't exist at this point",
    )
