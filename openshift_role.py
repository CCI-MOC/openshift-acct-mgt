# This is not currently being used, but I am keeping it around as I may need it

import kubernetes
import pprint
import logging
import requests
import json
import re
from flask import Flask, redirect, url_for, request, Response

import sys

application = Flask(__name__)

def get_openshift_role(token, api_url, project_name, role=None):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' + project_name + '/roles'
    if(role is not None):
        url = 'https://' + api_url + '/oapi/v1/namespaces/' + project_name + '/roles/' + role
    r = requests.get(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("gr r: " + str(r.status_code))
    application.logger.debug("gr r: " + r.text)
    return r


def create_openshift_role(token, api_url, project_name, role):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' + project_name + '/roles'
    payload = {
        "kind": "Role",
        "apiVersion": "v1",
        "metadata": {
            "name": role,
            "namespace": project_name
        },
        "name": role,
        "namespace": project_name
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("payload: "+json.dumps(payload))
    application.logger.debug("cr r: " + str(r.status_code))
    application.logger.debug("cr r: " + r.text)
    return r

def add_openshift_role(token,api_url,project_name,role):
    r=get_openshift_role(token, api_url, project_name)
    r=create_openshift_role(token, api_url, project_name, role)
    print("3: roles: "+r.text)

    return r

