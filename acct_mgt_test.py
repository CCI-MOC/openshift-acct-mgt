#!/usr/bin/python3
"""
 This pytest module checks the results from a running openshift account management
 microserver using oc (openshift's kubectl equivalent).  This is done instead of mocking
 openshift, as openshift too frequently changes.

 General commandline format:

 python3 -m pytest acct-mgt-test.py --amurl [acct_mgt_url] --user [username] --passwd [password]

 Note, to do this from apple OSX
    1) convert the cert and key to a p12 file
       via: openssl pkcs12 -export -in ./<client_cert> -inkey ./<client_key> -out client.p12
       openssl pkcs12 -export -in ./acct-mgt-2.crt -inkey ./acct-mgt-2.key -out acct-mgt-2.p12

    2) call curl with
       curl -v -kv -E ./client.p12:password http://url...

    3) auth_opts can be of the following:

          auth_opts = ["-E","./client_cert/acct-mgt-2.crt", "-key", "./client_cert/acct-mgt-2.key"]
          auth_opts = ["-cert", r"acct-mgt-2",]

 Initial test to confirm that something is working
    curl -kv https://acct-mgt.apps.cnv.massopen.cloud/projects/acct-mgt
    curl -u <user>:<password> -kv https://acct-mgt.apps.cnv.massopen.cloud/projects/acct-mgt

  -- testing with no authentication:
     python3 -m pytest acct-mgt-test.py --amurl http://am2.apps.cnv.massopen.cloud

  -- testing with basic authentication
     python3 -m pytest acct-mgt-test.py --amurl https://acct-mgt.massopen.cloud --basic "user:pass"
"""

import subprocess
import re
import time
import json
import pprint

# import pytest
import pytest_check as check


def get_pod_status(project, pod_name):
    """This gets the specified pod status from openshift"""
    result = subprocess.run(
        ["oc", "-n", project, "-o", "json", "get", "pod", pod_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode == 0:
        result_json = json.loads(result.stdout.decode("utf-8"))
        print(result_json["status"]["phase"])
        return result_json["status"]["phase"]
    print("None")
    return None


# pass in the following parameter:
#   project,pod_name: identify the pod
#   statuses: the array of statuses to wait for
def wait_while(project, pod_name, statuses, time_out=300):
    """
    This basically waits while a pod is in a set of statuses and possibly times out
    It is used to wait for openshift to do something with the pod, as in, deleting
    or starting a pod.
    """
    time_left = time_out
    time_interval = 5
    time.sleep(time_interval)
    status = get_pod_status(project, pod_name)
    while status in statuses and time_left > 0:
        time.sleep(time_interval)
        time_left = time_left - time_interval
        status = get_pod_status(project, pod_name)

    if status in statuses:
        return False
    return True


def wait_until_done(oc_cmd, finished_pattern, time_out=30, decrement=5):
    """
    This wait while an oc command is running, looking for a pattern that
    indicates it is finished.
    """
    pattern1 = re.compile(finished_pattern)
    done = False
    oc_array = oc_cmd.split(" ")
    matched_line = ""
    while time_out > 0 and not done:
        time.sleep(5)
        time_out = time_out - decrement
        result = subprocess.run(
            oc_array,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        line_list = result.stdout.decode("utf-8").split("\n")
        for line in line_list:
            if pattern1.match(line):
                matched_line = line
                done = True
    if pattern1.match(matched_line):
        return True
    return False


def compare_results(result, pattern):
    """This compares the result of a subprocess (usually curl) call  with a pattern"""
    if result is not None:
        pattern1 = re.compile(pattern)
        line_array = result.stdout.decode("utf-8").split("\n")
        for line in line_array:
            if pattern1.match(line):
                return True
    return False


def oc_resource_exist(resource, kind, name, project=None):
    """This uses oc to determin if an openshift resource exists"""
    result = None
    if project is None:
        result = subprocess.run(
            ["oc", "-o", "json", "get", resource, name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    else:
        result = subprocess.run(
            ["oc", "-o", "json", "-n", project, "get", resource, name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode == 0:
        if result.stdout is not None:
            result_json = json.loads(result.stdout.decode("utf-8"))
            if result_json["kind"] == kind and result_json["metadata"]["name"] == name:
                return True
    return False


def ms_check_project(acct_mgt_url, project_name, auth_opts=None):
    """Checks if the project exists using the microserver"""
    cmd = (
        ["curl", "-X", "GET", "-kv"]
        + auth_opts
        + [acct_mgt_url + "/projects/" + project_name]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    pprint.pprint(result)
    return compare_results(
        result, r'{"msg": "project exists \(' + project_name + r'\)"}'
    )


def ms_create_project(acct_mgt_url, project_uuid, display_name_str, auth_opts=None):
    """s
    This creates a project (namespace) within openshift using the microserver

    expect this to be called with
    project_uuid="1234-1234-1234-1234"
    displayNameStr=None | '{"displayName":"project_name"}' | '{"funkyName":"project_name"}'

    examples:
        curl -kv http://am2.apps.cnv.massopen.cloud/projects/test-001
        curl -X PUT -kv http://am2.apps.cnv.massopen.cloud/projects/test-001
    """
    cmd = ""
    if display_name_str is None:
        cmd = (
            [
                "curl",
                "-X",
                "PUT",
                "-kv",
            ]
            + auth_opts
            + [acct_mgt_url + "/projects/" + project_uuid]
        )
    else:
        cmd = (
            [
                "curl",
                "-X",
                "PUT",
                "-kv",
                "-d",
                display_name_str,
            ]
            + auth_opts
            + [acct_mgt_url + "/projects/" + project_uuid]
        )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return compare_results(
        result, r'{"msg": "project created \(' + project_uuid + r'\)"}'
    )


def ms_delete_project(acct_mgt_url, project_name, auth_opts=None):
    """This deletes the specified project(namespace) using the microserver"""
    cmd = (
        ["curl", "-X", "DELETE", "-kv"]
        + auth_opts
        + [acct_mgt_url + "/projects/" + project_name]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return compare_results(
        result, r'{"msg": "project deleted \(' + project_name + r'\)"}'
    )


def ms_check_user(acct_mgt_url, user_name, auth_opts=None):
    """This checks if a user exists using the microserver"""
    cmd = (
        [
            "curl",
            "-X",
            "GET",
            "-kv",
        ]
        + auth_opts
        + [acct_mgt_url + "/users/" + user_name]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return compare_results(result, r'{"msg": "user \(' + user_name + r'\) exists"}')


def ms_create_user(acct_mgt_url, user_name, auth_opts=None):
    """Creates a user using the microserver"""
    result = subprocess.run(
        ["curl", "-X", "PUT", "-kv"]
        + auth_opts
        + [acct_mgt_url + "/users/" + user_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return compare_results(result, r'{"msg": "user created \(' + user_name + r'\)"}')


def ms_delete_user(acct_mgt_url, user_name, auth_opts=None):
    """Deletes a user usering the microserver"""
    cmd = (
        ["curl", "-X", "DELETE", "-kv"]
        + auth_opts
        + [acct_mgt_url + "/users/" + user_name]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return compare_results(result, r'{"msg": "user deleted \(' + user_name + r'\)"}')


def ms_user_project_get_role(
    acct_mgt_url,
    role_info,
    success_pattern,
    auth_opts=None,
):
    """Gets user roles from projects using the microserver"""
    cmd = (
        [
            "curl",
            "-X",
            "GET",
            "-kv",
        ]
        + auth_opts
        + [
            acct_mgt_url
            + "/users/"
            + role_info["user_name"]
            + "/projects/"
            + role_info["project_name"]
            + "/roles/"
            + role_info["role"]
        ]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print("get role --> result: " + result.stdout.decode("utf-8") + "\n\n")
    return compare_results(result, success_pattern)


def ms_user_project_add_role(acct_mgt_url, role_info, success_pattern, auth_opts=None):
    """adds user roles to a project using the microserver"""
    cmd = (
        ["curl", "-X", "PUT", "-kv"]
        + auth_opts
        + [
            acct_mgt_url
            + "/users/"
            + role_info["user_name"]
            + "/projects/"
            + role_info["project_name"]
            + "/roles/"
            + role_info["role"]
        ]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print("add role --> result: " + result.stdout.decode("utf-8") + "\n\n")
    return compare_results(result, success_pattern)


def ms_user_project_remove_role(
    acct_mgt_url, role_info, success_pattern, auth_opts=None
):
    """removes user role from a project using the microserver"""
    cmd = (
        ["curl", "-X", "DELETE", "-kv"]
        + auth_opts
        + [
            acct_mgt_url
            + "/users/"
            + role_info["user_name"]
            + "/projects/"
            + role_info["project_name"]
            + "/roles/"
            + role_info["role"]
        ]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return compare_results(result, success_pattern)


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
        ms_check_project(acct_mgt_url, "test-001", auth_opts),
        "Project exists (test-001)",
    )

    # test project creation
    if not oc_resource_exist("project", "Project", "test-001"):
        check.is_true(
            ms_create_project(
                acct_mgt_url, "test-001", r'{"displayName":"test-001"}', auth_opts
            ),
            "Project (test-001) not created",
        )
        wait_until_done(
            "oc get project test-001", r"test-001[ \t]+test-001[ \t]+Active"
        )
    check.is_true(
        oc_resource_exist("project", "Project", "test-001"),
        "Project (test-001) not created",
    )
    check.is_true(
        ms_check_project(acct_mgt_url, "test-001", auth_opts),
        "project test-001 was not found",
    )

    # test creation of a second project with the same name
    if oc_resource_exist("project", "Project", "test-001"):
        check.is_false(
            ms_create_project(
                acct_mgt_url, "test-001", r'{"displayName":"test-001"}', auth_opts
            ),
            "Project (test-001) was already created",
        )
    check.is_true(
        oc_resource_exist("project", "Project", "test-001"),
        "Project test-001 was not found",
    )

    # test project deletion
    if oc_resource_exist("project", "Project", "test-001"):
        check.is_true(
            ms_delete_project(acct_mgt_url, "test-001", auth_opts),
            "Unable to delete project (test-001)",
        )
        # Wait until test-001 is terminated
        wait_until_done(
            "oc get project test-001",
            r'Error from server (NotFound): namespaces "test-001" not found',
        )
    check.is_false(
        oc_resource_exist("project", "Project", "test-001"),
        "Project test-001 exists and it shouldn't",
    )

    # test deleting a project that was deleted
    if not oc_resource_exist("project", "Project", "test-001"):
        check.is_false(
            ms_delete_project(acct_mgt_url, "test-001", auth_opts),
            "shouldn't be able to delete a non-existing project",
        )
    check.is_false(
        oc_resource_exist("project", "Project", "test-001"),
        "Project test-001 exists and it should not",
    )

    # these tests are primarily done to ensure that the microserver doesn't crash
    #    When the "displayName" is not present, or the json doesn't exist, the displayName shall
    #    default to the project_uuid (first parameter)
    check.is_true(
        ms_create_project(
            acct_mgt_url,
            "1234-1234-1234-1234",
            r'{"displayName":"test-001"}',
            auth_opts,
        ),
        "Project (1234-1234-1234-1234) not created",
    )
    ms_delete_project(acct_mgt_url, "1234-1234-1234-1234", auth_opts)
    check.is_true(
        ms_create_project(
            acct_mgt_url, "2234-1234-1234-1234", r'{"displaName":"test-001"}', auth_opts
        ),
        "Project (2234-1234-1234-1234) not created",
    )
    ms_delete_project(acct_mgt_url, "2234-1234-1234-1234", auth_opts)
    check.is_true(
        ms_create_project(acct_mgt_url, "3234-1234-1234-1234", r"{}", auth_opts),
        "Project (3234-1234-1234-1234) not created",
    )
    ms_delete_project(acct_mgt_url, "3234-1234-1234-1234", auth_opts)
    check.is_true(
        ms_create_project(acct_mgt_url, "4234-1234-1234-1234", None, auth_opts),
        "Project (4234-1234-1234-1234) not created",
    )
    ms_delete_project(acct_mgt_url, "4234-1234-1234-1234", auth_opts)


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
        ms_check_user(acct_mgt_url, "test01", auth_opts),
        "User test01 exists but it shouldn't exist at this point",
    )

    # test user creation
    # test01      bfd6dab5-11f3-11ea-89a6-fa163e2bb38b      sso_auth:test01
    if not oc_resource_exist("users", "User", "test01"):
        check.is_true(
            ms_create_user(acct_mgt_url, "test01", auth_opts),
            "unable to create test01",
        )

    check.is_true(
        oc_resource_exist("users", "User", "test01"),
        "user test01 doesn't exist",
    )
    check.is_true(
        ms_check_user(acct_mgt_url, "test01", auth_opts),
        "User test01 doesn't exist but it should",
    )

    # test creation of a second user with the same name
    if oc_resource_exist("users", "User", "test01"):
        check.is_false(
            ms_create_user(acct_mgt_url, "test01", auth_opts),
            "Should have failed to create a second user with the username of test01",
        )
    check.is_true(
        oc_resource_exist("users", "User", "test01"),
        "user test01 doesn't exist",
    )

    # test user deletion
    if oc_resource_exist("users", "User", "test01"):
        check.is_true(
            ms_delete_user(acct_mgt_url, "test01", auth_opts),
            "user test01 deleted",
        )
    check.is_false(
        oc_resource_exist("users", "User", "test01"),
        "user test01 not found",
    )

    # test deleting a user that was deleted
    if not oc_resource_exist("users", "User", "test01"):
        check.is_false(
            ms_delete_user(acct_mgt_url, "test01", auth_opts),
            "shouldn't be able to delete non-existing user test01",
        )
    check.is_false(
        oc_resource_exist("users", "User", "test01"),
        "user test01 not found",
    )
    check.is_false(
        ms_check_user(acct_mgt_url, "test01", auth_opts),
        "User test01 exists but it shouldn't exist at this point",
    )


def test_project_user_role(acct_mgt_url, auth_opts):
    """This tests project role existence/creation/update/deletion"""
    # Create a project
    if not oc_resource_exist("project", "Project", "test-002"):
        check.is_true(
            ms_create_project(
                acct_mgt_url, "test-002", '{"displayName":"test-002"}', auth_opts
            ),
            "Project (test-002) was unable to be created",
        )
    check.is_true(
        oc_resource_exist("project", "Project", "test-002"),
        "Project (test-002) does not exist",
    )

    # Create some users test02 - test-05
    for user_number in range(2, 6):
        if not oc_resource_exist("users", "User", "test0" + str(user_number)):
            check.is_true(
                ms_create_user(acct_mgt_url, "test0" + str(user_number), auth_opts),
                "Unable to create user " + "test0" + str(user_number),
            )
        check.is_true(
            oc_resource_exist("users", "User", "test0" + str(user_number)),
            "user test0" + str(user_number) + " not found",
        )

    # now bind an admin role to the user
    role_info = {"user_name": "test02", "project_name": "test-002", "role": "admin"}
    check.is_false(
        ms_user_project_get_role(
            acct_mgt_url,
            role_info,
            r'{"msg": "user role exists \(test-002,test02,admin\)"}',
            auth_opts,
        )
    )
    check.is_true(
        ms_user_project_add_role(
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
        ms_user_project_get_role(
            acct_mgt_url,
            role_info,
            r'{"msg": "user role exists \(test-002,test02,admin\)"}',
            auth_opts,
        )
    )

    check.is_true(
        ms_user_project_add_role(
            acct_mgt_url,
            role_info,
            r'{"msg": "rolebinding already exists - unable to add \(test02,test-002,admin\)"}',
            auth_opts,
        ),
        "Added the same role to a user failed as it should",
    )

    check.is_true(
        ms_user_project_remove_role(
            acct_mgt_url,
            role_info,
            r'{"msg": "removed role from user on project"}',
            auth_opts,
        ),
        "Removed rolebinding successful",
    )
    # TODO: write an oc command to check if a role was added to a user for a project.
    #       Not trivial based on the current way this is reported by oc
    check.is_true(
        ms_user_project_remove_role(
            acct_mgt_url,
            role_info,
            r'{"msg": "rolebinding does not exist - unable to delete \(test02,test-002,admin\)"}',
            auth_opts,
        ),
        "Unable to remove non-existing rolebinding",
    )

    # Clean up by removing the users and project (test-002)
    check.is_true(
        ms_delete_project(acct_mgt_url, "test-002", auth_opts) is True,
        "project (test-002) deleted",
    )
    for user_number in range(2, 6):
        if oc_resource_exist("users", "User", "test0" + str(user_number)):
            check.is_true(
                ms_delete_user(acct_mgt_url, "test0" + str(user_number), auth_opts)
                is True,
                "user " + "test0" + str(user_number) + "unable to be deleted",
            )
