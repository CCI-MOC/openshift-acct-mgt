import kubernetes
import pprint
import logging
import requests
import json
import re
from flask import Flask, redirect, url_for, request, Response

import sys

application = Flask(__name__)

def cnvt_project_name(project_name):
    suggested_project_name = re.sub('^[^A-Za-z0-9]+', '', project_name)
    suggested_project_name = re.sub(
        '[^A-Za-z0-9]+$', '', suggested_project_name)
    suggested_project_name = re.sub(
        '[^A-Za-z0-9\-]+', '-', suggested_project_name)
    return suggested_project_name

def exists_openshift_project(token, api_url, project_name):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/projects/' + project_name
    r = requests.get(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("r: " + str(r.status_code))
    application.logger.debug("r: " + r.text)
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False

#try just using the projet name
def delete_openshift_project(token, api_url, project_name, user_name):
    # check project_name
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/projects/' + project_name
    r = requests.delete(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("r: " + str(r.status_code))
    application.logger.debug("r: " + r.text)
    return r


def create_openshift_project(token, api_url, project_uuid, project_name, user_name):
    # check project_name
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/projects'
    payload = {"kind": "Project", "apiVersion": "v1", "metadata": {"name": project_uuid, "annotations": {
        "openshift.io/display-name": project_name, "openshift.io/requester": user_name}}}
    r = requests.post(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("payload: "+json.dumps(payload))
    application.logger.debug("r: " + str(r.status_code))
    application.logger.debug("r: " + r.text)
    return r
