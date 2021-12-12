""" tests adding roles to users on projects """

import pytest_check as check
import acct_mgt_test as amt

def test_project_user_role(acct_mgt_url, auth_opts):
    """This tests project role existence/creation/update/deletion"""
    # Create a project
    if not amt.oc_resource_exist("project", "Project", "test-002"):
        check.is_true(
            amt.ms_create_project(
                acct_mgt_url, "test-002", '{"displayName":"test-002"}', auth_opts
            ),
            "Project (test-002) was unable to be created",
        )
    check.is_true(
        amt.oc_resource_exist("project", "Project", "test-002"),
        "Project (test-002) does not exist",
    )

    # Create some users test02 - test-05
    for user_number in range(2, 6):
        if not amt.oc_resource_exist("users", "User", "test0" + str(user_number)):
            check.is_true(
                amt.ms_create_user(acct_mgt_url, "test0" + str(user_number), auth_opts),
                "Unable to create user " + "test0" + str(user_number),
            )
        check.is_true(
            amt.oc_resource_exist("users", "User", "test0" + str(user_number)),
            "user test0" + str(user_number) + " not found",
        )

    # now bind an admin role to the user
    role_info = {"user_name": "test02", "project_name": "test-002", "role": "admin"}
    check.is_false(
        amt.ms_user_project_get_role(
            acct_mgt_url,
            role_info,
            r'{"msg": "user role exists \(test-002,test02,admin\)"}',
            auth_opts,
        )
    )
    check.is_true(
        amt.ms_user_project_add_role(
            acct_mgt_url,
            role_info,
            r'{"msg": "rolebinding created \(test02,test-002,admin\)"}',
            auth_opts,
        ),
        "Role unable to be added",
    )

    # should write a oc command to check this, but for rolebindings
    # this cannot be done in the same way as for users and projects
    # for now, rely on the microserver.
    check.is_true(
        amt.ms_user_project_get_role(
            acct_mgt_url,
            role_info,
            r'{"msg": "user role exists \(test-002,test02,admin\)"}',
            auth_opts,
        )
    )

    check.is_true(
        amt.ms_user_project_add_role(
            acct_mgt_url,
            role_info,
            r'{"msg": "rolebinding already exists - unable to add \(test02,test-002,admin\)"}',
            auth_opts,
        ),
        "Added the same role to a user failed as it should",
    )

    check.is_true(
        amt.ms_user_project_remove_role(
            acct_mgt_url,
            role_info,
            r'{"msg": "removed role from user on project"}',
            auth_opts,
        ),
        "Removed rolebinding successful",
    )
    # Should write an oc command to check if a role was added to a user for a project.
    # however this is not easy based on the current way this is reported by oc so for
    # now just use the microserver
    check.is_true(
        amt.ms_user_project_remove_role(
            acct_mgt_url,
            role_info,
            r'{"msg": "rolebinding does not exist - unable to delete \(test02,test-002,admin\)"}',
            auth_opts,
        ),
        "Unable to remove non-existing rolebinding",
    )

    # Clean up by removing the users and project (test-002)
    check.is_true(
        amt.ms_delete_project(acct_mgt_url, "test-002", auth_opts) is True,
        "project (test-002) deleted",
    )
    for user_number in range(2, 6):
        if amt.oc_resource_exist("users", "User", "test0" + str(user_number)):
            check.is_true(
                amt.ms_delete_user(acct_mgt_url, "test0" + str(user_number), auth_opts)
                is True,
                "user " + "test0" + str(user_number) + "unable to be deleted",
            )
