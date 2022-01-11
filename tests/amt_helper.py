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
import pprint


def wait_until_lambda(lambdafunc, attempts=5, time_between_attemps=5):
    """
    This wait continue to try the lambdafunc up to n times
    """
    while attempts > 0 and not lambdafunc():
        attempts = attempts - 1
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


def oc_resource_exist(resource, kind, name, project=None) -> bool:
    """This uses oc to determine if an openshift resource exists"""
    cmd = ["oc", "-o", "json"]
    if project is not None:
        cmd = cmd + ["-n", project]
    cmd = cmd + ["get", resource]
    if name is not None:
        cmd = cmd + [name]
    pprint.pprint(cmd)
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode == 0 and result.stdout is not None:
        result_json = json.loads(result.stdout.decode("utf-8"))
        # This can return a list, so just look at the first item in the list
        if result_json["kind"] == "List":
            if len(result_json["items"]) == 0:
                return False
            result_json = result_json["items"][0]
        if result_json["kind"] == kind:
            if name is None:
                return True
            if result_json["metadata"]["name"] == name:
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
    return all(item is None for item in moc_quota.get("Quota", []))


def ms_get_moc_quota(acct_mgt_url, project_name, session) -> dict:
    """gets the moc quota specification (quota name mangled with scope) from the microserver"""
    resp = session.get(f"{acct_mgt_url}/projects/{project_name}/quota")
    moc_quota = resp.json()
    return moc_quota


def ms_put_moc_quota(acct_mgt_url, project_name, moc_quota_def, session):
    """The replaces the quota for the specific project - works even for the NULL Quota"""
    resp = session.put(
        f"{acct_mgt_url}/projects/{project_name}/quota", data=json.dumps(moc_quota_def)
    )
    if resp.status_code in [200, 201]:
        return True
    return False


def ms_del_moc_quota(acct_mgt_url, project_name, session):
    """
    This deletes all of the quota for the specified project

    From the OpenShift side this deletes all of the resourcequota objects on the openshift project
    """
    resp = session.delete(f"{acct_mgt_url}/projects/{project_name}/quota")
    if resp.status_code in [200, 201]:
        return True
    return False


# These functions are used to determine the quota multiplier based on
# the quota returned.
#
#               ((moc_quota from multiplier) - (moc_quota from multiplier 0))
#  multiplier = -------------------------------------------------------------
#               ((moc_quota from multiplier 1)-(moc_quota from multiplier 0)
#
# Could eventually test different units via logrithms
# to both handle the order of magnitude and conversion of base2 to base10


def remove_quota_units(moc_quota):
    """
    This just removes possible units from the quota values

    for example, 80Gi becomes 80

    This isn't a problem as we are assuming that the quotas are all the same unit
    in the
    """
    ret_quota = {}
    for quota, value in moc_quota.items():
        if isinstance(value, str):
            ret_quota[quota] = int("".join(filter(str.isdigit, value)))
        else:
            ret_quota[quota] = value
    return ret_quota


def are_all_quota_same_value(moc_quota, value):
    """returns true if any quota value is non-null

    expect to be used like:

    are_all_quota_same_value(moc_quota["Quota"], None)
        returns true if all values are None

    are_all_quota_same_value(moc_quota["Quota"], 2)
        returns true if all values are 2
    """
    for quota_value in moc_quota.values():
        if quota_value and quota_value != value:
            return False
    return True


def diff_moc_quota(moc_quota1, moc_quota2):
    """returns the difference moc_quota1 - moc_quota2

    expected to be used like

    dquota = diff_moc_quota(moc_quota1["Quota"],moc_quota2["Quota"])
    """
    diff_quota = {}
    for quota in moc_quota1:
        diff_quota[quota] = None
        if quota not in moc_quota2:
            moc_quota2[quota] = None
    for quota in moc_quota2:
        diff_quota[quota] = None
        if quota not in moc_quota1:
            moc_quota1[quota] = None
    for quota in diff_quota:
        if moc_quota1[quota] is None and moc_quota2[quota] is None:
            diff_quota[quota] = None
        elif moc_quota1[quota] is None and moc_quota2[quota] is not None:
            diff_quota[quota] = -moc_quota2[quota]
        elif moc_quota1[quota] is not None and moc_quota2[quota] is None:
            diff_quota[quota] = moc_quota1[quota]
        else:
            diff_quota[quota] = moc_quota1[quota] - moc_quota2[quota]
    return diff_quota


def div_moc_quota(moc_quota1, moc_quota2):
    """returns values ov moc_quota1 / moc_quota2"""
    div_quota = {}
    for quota in moc_quota1:
        div_quota[quota] = None
        if quota not in moc_quota2:
            moc_quota2[quota] = None
    for quota in moc_quota2:
        div_quota[quota] = None
        if quota not in moc_quota1:
            moc_quota1[quota] = None
    for quota in div_quota:
        if moc_quota1[quota] in [None, 0] or moc_quota2[quota] in [None, 0]:
            div_quota[quota] = None
        else:
            div_quota[quota] = moc_quota1[quota] / moc_quota2[quota]
    return div_quota
