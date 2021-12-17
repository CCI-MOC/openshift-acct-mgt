#!/usr/bin/python3
"""
 This pytest module checks the results from a running openshift account management
 microserver using oc (openshift's kubectl equivalent).  This is done instead of mocking
 openshift, as openshift too frequently changes.
"""

import subprocess
import re
import time
import json


def wait_until_lambda(lambdafunc, num_tries=5, time_between_attemps=5):
    """
    This wait continue to try the lambdafunc up to n times
    """
    while num_tries > 0 and not lambdafunc():
        num_tries = num_tries - 1
        time.sleep(time_between_attemps)
    return lambdafunc()


def compare_results(result, pattern):
    """This compares the result of a subprocess (usually curl) call  with a pattern"""
    if result is not None:
        pattern = re.compile(pattern)
        line_array = result.stdout.decode("utf-8").split("\n")
        for line in line_array:
            if pattern.match(line):
                return True
    return False


def oc_resource_exist(resource, kind, name, project=None):
    """This uses oc to determine if an openshift resource exists"""
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
    if result.returncode == 0 and result.stdout is not None:
        result_json = json.loads(result.stdout.decode("utf-8"))
        if result_json["kind"] == kind and result_json["metadata"]["name"] == name:
            return True
    return False


def ms_check_project(acct_mgt_url, project_name, session):
    """Checks if the project exists using the microserver"""
    resp = session.get(f"{acct_mgt_url}/projects/{project_name}")

    if resp.status_code in [200, 201]:
        return True
    return False


def ms_create_project(acct_mgt_url, project_name, display_name, session):
    """
    This creates a project (namespace) within openshift using the microserver

    expect this to be called with
    project_name="1234-1234-1234-1234"
    displayName=None | [long project name ]

    examples:
        curl -kv http://am2.apps.cnv.massopen.cloud/projects/test-001
        curl -X PUT -kv http://am2.apps.cnv.massopen.cloud/projects/test-001
    """
    payload = {}
    if display_name is not None:
        payload = {"displayName": display_name}
    resp = session.put(
        f"{acct_mgt_url}/projects/{project_name}", data=json.dumps(payload)
    )
    if resp.status_code in [200, 201]:
        return True
    return False


def ms_delete_project(acct_mgt_url, project_name, session):
    """This deletes the specified project(namespace) using the microserver"""
    resp = session.delete(f"{acct_mgt_url}/projects/{project_name}")
    if resp.status_code in [200, 201]:
        return True
    return False


def ms_check_user(acct_mgt_url, user_name, session):
    """This checks if a user exists using the microserver"""
    resp = session.get(f"{acct_mgt_url}/users/{user_name}")

    if resp.status_code in [200, 201]:
        return True
    return False


def ms_create_user(acct_mgt_url, user_name, session):
    """Creates a user using the microserver"""
    resp = session.put(f"{acct_mgt_url}/users/{user_name}")
    if resp.status_code in [200, 201]:
        return True
    return False


def ms_delete_user(acct_mgt_url, user_name, session):
    """Deletes a user usering the microserver"""
    resp = session.delete(f"{acct_mgt_url}/users/{user_name}")
    if resp.status_code in [200, 201]:
        return True
    return False


def ms_user_project_get_role(
    acct_mgt_url,
    role_info,
    session,
):
    """Gets user roles from projects using the microserver"""
    resp = session.get(
        f"{acct_mgt_url}/users/{role_info['user_name']}/projects/{role_info['project_name']}/roles/{role_info['role']}"
    )

    if resp.status_code in [200, 201]:
        return True
    return False


def ms_user_project_add_role(acct_mgt_url, role_info, session):
    """adds user roles to a project using the microserver"""
    resp = session.put(
        f"{acct_mgt_url}/users/{role_info['user_name']}/projects/{role_info['project_name']}/roles/{role_info['role']}"
    )
    if resp.status_code in [200, 201]:
        return True
    return False


def ms_user_project_remove_role(acct_mgt_url, role_info, session):
    """removes user role from a project using the microserver"""
    resp = session.delete(
        f"{acct_mgt_url}/users/{role_info['user_name']}/projects/{role_info['project_name']}/roles/{role_info['role']}"
    )
    if resp.status_code in [200, 201]:
        return True
    return False


def is_moc_quota_empty(moc_quota) -> bool:
    """This checks to see if an moc quota (name mangled) is empty"""
    if "Quota" in moc_quota:
        for item in moc_quota["Quota"]:
            if moc_quota["Quota"][item] is not None:
                return False
    return True


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
