#!/usr/bin/python3
"""
 This pytest module checks the results from a running openshift account management
 microserver using oc (openshift's kubectl equivalent).  This is done instead of mocking
 openshift, as openshift too frequently changes.

 General commandline format:

 python3 -m pytest amt_test*.py --amurl [acct_mgt_url] --user [username] --passwd [password]

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
     python3 -m pytest amt_test*.py --amurl http://acct-mgt..massopen.cloud

  -- testing with basic authentication
     python3 -m pytest amt_test*.py --amurl https://acct-mgt.massopen.cloud --basic "user:pass"
"""

import subprocess
import re
import time
import json
import pprint


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


#
def wait_while(project, pod_name, statuses, time_out=300):
    """
    This basically waits while a pod is in a set of statuses and possibly times out
    It is used to wait for openshift to do something with the pod, as in, deleting
    or starting a pod.

    pass in the following parameter:
       project:  the namespace of the pod
       pod_name: the name of the pod
       statuses: array of statuses


    """
    time_left = time_out
    time_interval = 5
    time.sleep(time_interval)
    status = get_pod_status(project, pod_name)
    while status in statuses and time_left > 0:
        time.sleep(time_interval)
        time_left = time_left - time_interval
        status = get_pod_status(project, pod_name)

    return status in statuses


def wait_until_done(oc_cmd, finished_pattern, attempts=30, decrement=5):
    """
    This wait while an oc command is running, looking for a pattern that
    indicates it is finished.
    """
    pattern = re.compile(finished_pattern)
    done = False
    oc_array = oc_cmd.split(" ")
    matched_line = ""
    while attempts > 0 and not done:
        time.sleep(5)
        attempts = attempts - decrement
        result = subprocess.run(
            oc_array,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        line_list = result.stdout.decode("utf-8").split("\n")
        for line in line_list:
            if pattern.match(line):
                matched_line = line
                done = True
    return pattern.match(matched_line)


def compare_results(result, pattern):
    """This compares the result of a subprocess (usually curl) call  with a pattern"""
    if result is not None:
        pattern = re.compile(pattern)
        line_array = result.stdout.decode("utf-8").split("\n")
        for line in line_array:
            if pattern.match(line):
                return True
    return False


def oc_resource_exist(resource, kind, name, project=None) -> bool:
    """This uses oc to determine if an openshift resource exists"""
    result = None
    cmd = ["oc", "-o", "json"]
    if project is not None:
        cmd = cmd + ["-n", project]
    cmd = cmd + ["get", resource]
    if name is not None:
        cmd = cmd + [name]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode == 0:
        if result.stdout is not None:
            result_json = json.loads(result.stdout.decode("utf-8"))
            if "items" in result_json:
                # if there is a list of items returned, pick the first one
                if len(result_json["items"]) == 0:
                    return False
                result_json = result_json["items"][0]
            if result_json["kind"] == kind:
                if name is None:
                    return True
                if result_json["metadata"]["name"] == name:
                    return True
    return False


def ms_check_project(acct_mgt_url, project_name, auth_opts=None):
    """Checks if the project exists using the microserver"""
    cmd = (
        ["curl", "-X", "GET", "-kv"]
        + auth_opts
        + [f"{acct_mgt_url}/projects/{project_name}"]
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


def ms_create_project(acct_mgt_url, project_name, display_name_str, auth_opts=None):
    """
    This creates a project (namespace) within openshift using the microserver

    expect this to be called with
    project_name="1234-1234-1234-1234"
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
            + [f"{acct_mgt_url}/projects/{project_name}"]
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
            + [f"{acct_mgt_url}/projects/{project_name}"]
        )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return compare_results(
        result, r'{"msg": "project created \(' + project_name + r'\)"}'
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
        + [f"{acct_mgt_url}/users/{user_name}"]
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
            f"{acct_mgt_url}/users/{role_info['user_name']}/projects/{role_info['project_name']}"
            + f"/roles/{role_info['role']}"
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
            f"{acct_mgt_url}/users/{role_info['user_name']}/projects/{role_info['project_name']}"
            + f"/roles/{role_info['role']}"
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
            f"{acct_mgt_url}/users/{role_info['user_name']}/projects/{role_info['project_name']}"
            + f"/roles/{role_info['role']}"
        ]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return compare_results(result, success_pattern)


def is_moc_quota_empty(moc_quota) -> bool:
    """This checks to see if an moc quota (name mangled) is empty"""
    return all(item is None for item in moc_quota.get("Quota", []))


def ms_get_moc_quota(acct_mgt_url, project_name, auth_opts=None) -> dict:
    """gets the moc quota specification (quota name mangled with scope) from the microserver"""
    cmd = (
        ["curl", "-X", "GET", "-kv"]
        + auth_opts
        + [f"{acct_mgt_url}/projects/{project_name}/quota"]
    )
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    moc_quota = {}
    if result.returncode == 0:
        line_array = result.stdout.decode("utf-8").split("\n")
        json_text = ""
        for line in line_array:
            if line[0] == "{":
                json_text = line
        moc_quota = json.loads(json_text)
    return moc_quota


def ms_put_moc_quota(acct_mgt_url, project_name, moc_quota_def, auth_opts=None):
    """The replaces the quota for the specific project - works even for the NULL Quota"""
    cmd = (
        ["curl", "-X", "PUT", "-kv", "-d", json.dumps(moc_quota_def)]
        + auth_opts
        + [f"{acct_mgt_url}/projects/{project_name}/quota"]
    )
    subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def ms_del_moc_quota(acct_mgt_url, project_name, auth_opts=None):
    """
    This deletes all of the quota for the specified project

    From the OpenShift side this deletes all of the resourcequota objects on the openshift project
    """
    cmd = (
        ["curl", "-X", "DELETE", "-kv"]
        + auth_opts
        + [f"{acct_mgt_url}/projects/{project_name}/quota"]
    )
    subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
