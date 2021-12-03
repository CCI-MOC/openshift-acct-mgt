#!/usr/bin/python3
# python3 -m pytest acct-mgt-test.py --amurl [acct_mgt_url] --user [username] --passwd [password]
#
# Note, to do this from apple OSX
#    1) convert the cert and key to a p12 file
#       via: openssl pkcs12 -export -in ./<client_cert> -inkey ./<client_key> -out client.p12
#       openssl pkcs12 -export -in ./acct-mgt-2.crt -inkey ./acct-mgt-2.key -out acct-mgt-2.p12
#
#    2) call curl with
#       curl -v -k -E ./client.p12:password http://url...
#
#    3) auth_opts can be of the following:
#
#          auth_opts = ["-E","./client_cert/acct-mgt-2.crt", "-key", "./client_cert/acct-mgt-2.key"]
#          auth_opts = ["-cert", r"acct-mgt-2",]
#
# Initial test to confirm that something is working
#    curl -kv https://acct-mgt.apps.cnv.massopen.cloud/projects/acct-mgt
#    curl -u <user>:<password> -kv https://acct-mgt.apps.cnv.massopen.cloud/projects/acct-mgt
#
#  -- testing with no authentication:
#     python3 -m pytest acct-mgt-test.py --amurl http://am2.apps.cnv.massopen.cloud
#
#  -- testing with basic authentication
#     python3 -m pytest acct-mgt-test.py --amurl https://acct-mgt.apps.cnv.massopen.cloud --basic "<admin>:<password>"
import subprocess
import re
import time
import json
import pprint
import pytest
import pytest_check as check


def get_pod_status(project, pod_name):
    result = subprocess.run(
        ["oc", "-n", project, "-o", "json", "get", "pod", pod_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
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
    p1 = re.compile(finished_pattern)
    done = False
    oc_array = oc_cmd.split(" ")
    matched_line = ""
    while time_out > 0 and not done:
        time.sleep(5)
        time_out = time_out - decrement
        result = subprocess.run(
            oc_array, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        lines = result.stdout.decode("utf-8").split("\n")
        cnt = 0
        for l in lines:
            if p1.match(l):
                matched_line = l
                done = True
    if p1.match(matched_line):
        return True
    return False


def user(user_name, op, success_pattern, auth_opts=[]):
    if op == "check":
        url_op = "GET"
    elif op == "add":
        url_op = "PUT"
    elif op == "del":
        url_op = "DELETE"

    # result = subprocess.run(
    #   ["curl", "-X", op, "-kv", "-E","./client_cert/acct-mgt-2.crt", "-key", "./client_cert/acct-mgt-2.key", url + "/users/" + user_name],
    #   ["curl", "-X", op, "-kv", "-cert", r"acct-mgt-2", url + "/users/" + user_name],
    #    stdout=subprocess.PIPE,
    #    stderr=subprocess.STDOUT,
    # )
    cmd = ["curl", "-X", op, "-kv"] + auth_opts + [url + "/users/" + user_name]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def compare_results(result, pattern):
    if result is not None:
        p1 = re.compile(pattern)
        lines = result.stdout.decode("utf-8").split("\n")
        cnt = 0
        for l in lines:
            # print("line ==> " + l)
            # print("patt --> " + pattern)
            if p1.match(l):
                return True
    return False


def oc_resource_exist(resource, kind, name, project=None):
    result = None
    if project is None:
        result = subprocess.run(
            ["oc", "-o", "json", "get", resource, name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    else:
        result = subprocess.run(
            ["oc", "-o", "json", "-n", project, "get", resource, name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    if result.returncode == 0:
        if result.stdout is not None:
            result_json = json.loads(result.stdout.decode("utf-8"))
            if result_json["kind"] == kind and result_json["metadata"]["name"] == name:
                return True
    return False


def ms_check_project(acct_mgt_url, project_name, auth_opts=[]):
    cmd = (
        ["curl", "-X", "GET", "-kv"]
        + auth_opts
        + [acct_mgt_url + "/projects/" + project_name]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    pprint.pprint(result)
    return compare_results(
        result, r'{"msg": "project exists \(' + project_name + r'\)"}'
    )


# expect this to be called with
#  project_uuid="1234-1234-1234-1234"
#  displayNameStr=None | '{"displayName":"project_name"}' | '{"funkyName":"project_name"}'
#
# examples:
#   curl -kv http://am2.apps.cnv.massopen.cloud/projects/test-001
#   curl -X PUT -kv http://am2.apps.cnv.massopen.cloud/projects/test-001
#
#
def ms_create_project(acct_mgt_url, project_uuid, displayNameStr, auth_opts=[]):
    cmd = ""
    if displayNameStr is None:
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
                displayNameStr,
            ]
            + auth_opts
            + [acct_mgt_url + "/projects/" + project_uuid]
        )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return compare_results(
        result, r'{"msg": "project created \(' + project_uuid + r'\)"}'
    )


def ms_delete_project(acct_mgt_url, project_name, auth_opts=[]):
    cmd = (
        ["curl", "-X", "DELETE", "-kv"]
        + auth_opts
        + [acct_mgt_url + "/projects/" + project_name]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return compare_results(
        result, r'{"msg": "project deleted \(' + project_name + r'\)"}'
    )


def ms_check_user(acct_mgt_url, user_name, auth_opts=[]):
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
    )
    return compare_results(result, r'{"msg": "user \(' + user_name + r'\) exists"}')


def ms_create_user(acct_mgt_url, user_name, auth_opts=[]):

    result = subprocess.run(
        ["curl", "-X", "PUT", "-kv"]
        + auth_opts
        + [acct_mgt_url + "/users/" + user_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return compare_results(result, r'{"msg": "user created \(' + user_name + r'\)"}')


def ms_delete_user(acct_mgt_url, user_name, auth_opts=[]):
    cmd = (
        ["curl", "-X", "DELETE", "-kv"]
        + auth_opts
        + [acct_mgt_url + "/users/" + user_name]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return compare_results(result, r'{"msg": "user deleted \(' + user_name + r'\)"}')


def ms_user_project_get_role(
    acct_mgt_url,
    user_name,
    project_name,
    role,
    success_pattern,
    auth_opts=[],
):
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
            + user_name
            + "/projects/"
            + project_name
            + "/roles/"
            + role
        ]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print("get role --> result: " + result.stdout.decode("utf-8") + "\n\n")
    return compare_results(result, success_pattern)


def ms_user_project_add_role(
    acct_mgt_url, user_name, project_name, role, success_pattern, auth_opts=[]
):
    cmd = (
        ["curl", "-X", "PUT", "-kv"]
        + auth_opts
        + [
            acct_mgt_url
            + "/users/"
            + user_name
            + "/projects/"
            + project_name
            + "/roles/"
            + role
        ]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print("add role --> result: " + result.stdout.decode("utf-8") + "\n\n")
    return compare_results(result, success_pattern)


def ms_user_project_remove_role(
    acct_mgt_url, user_name, project_name, role, success_pattern, auth_opts=[]
):
    cmd = (
        ["curl", "-X", "DELETE", "-kv"]
        + auth_opts
        + [
            acct_mgt_url
            + "/users/"
            + user_name
            + "/projects/"
            + project_name
            + "/roles/"
            + role
        ]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return compare_results(result, success_pattern)


def test_project(acct_mgt_url, auth_opts):
    result = 0
    # if(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
    #    print("Error: test_project failed as a project with a name of test-001 exists.  Please delete first and rerun the tests\n")
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
    #    When the "displayName" is not present, or the json doesn't exist, the displayName shall default to the project_uuid (first parameter)
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
    # if(oc_resource_exist("user", "test01",r'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01',r'Error from server (NotFound): users.user.openshift.io "test01" not found')):
    #    print("Error: test_user failed as a user with a name of test01 exists.  Please delete first and rerun the tests\n")
    #    assertTrue(False)

    check.is_false(
        ms_check_user(acct_mgt_url, "test01", auth_opts),
        "User test01 exists but it shouldn't exist at this point",
    )

    # test user creation
    # test01                    bfd6dab5-11f3-11ea-89a6-fa163e2bb38b                         sso_auth:test01
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
    for x in range(2, 6):
        if not oc_resource_exist("users", "User", "test0" + str(x)):
            check.is_true(
                ms_create_user(acct_mgt_url, "test0" + str(x), auth_opts),
                "Unable to create user " + "test0" + str(x),
            )
        check.is_true(
            oc_resource_exist("users", "User", "test0" + str(x)),
            "user test0" + str(x) + " not found",
        )

    # now bind an admin role to the user
    check.is_false(
        ms_user_project_get_role(
            acct_mgt_url,
            "test02",
            "test-002",
            "admin",
            r'{"msg": "user role exists \(test-002,test02,admin\)"}',
            auth_opts,
        )
    )
    check.is_true(
        ms_user_project_add_role(
            acct_mgt_url,
            "test02",
            "test-002",
            "admin",
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
            "test02",
            "test-002",
            "admin",
            r'{"msg": "user role exists \(test-002,test02,admin\)"}',
            auth_opts,
        )
    )

    check.is_true(
        ms_user_project_add_role(
            acct_mgt_url,
            "test02",
            "test-002",
            "admin",
            r'{"msg": "rolebinding already exists - unable to add \(test02,test-002,admin\)"}',
            auth_opts,
        ),
        "Added the same role to a user failed as it should",
    )

    check.is_true(
        ms_user_project_remove_role(
            acct_mgt_url,
            "test02",
            "test-002",
            "admin",
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
            "test02",
            "test-002",
            "admin",
            r'{"msg": "rolebinding does not exist - unable to delete \(test02,test-002,admin\)"}',
            auth_opts,
        ),
        "Unable to remove non-existing rolebinding",
    )

    # Clean up by removing the users and project (test-002)
    check.is_true(
        ms_delete_project(acct_mgt_url, "test-002", auth_opts) == True,
        "project (test-002) deleted",
    )
    for x in range(2, 6):
        if oc_resource_exist("users", "User", "test0" + str(x)):
            check.is_true(
                ms_delete_user(acct_mgt_url, "test0" + str(x), auth_opts) == True,
                "user " + "test0" + str(x) + "unable to be deleted",
            )


# def test_quota(self):
