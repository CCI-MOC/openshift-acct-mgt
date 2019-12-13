import kubernetes
import pprint
import logging
import requests
import json
import re
from flask import Flask, redirect, url_for, request, Response

import sys

application = Flask(__name__)

def exists_openshift_user(token, api_url, user_name):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/users/' + user_name
    r = requests.get(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    #application.logger.debug("payload: "+payload)
    application.logger.debug("exists os user: " + str(r.status_code))
    application.logger.debug("exists os user: " + r.text)
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False


def create_openshift_user(token, api_url, user_name, full_name):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/users'
    payload = {"kind": "User", "apiVersion": "v1",
               "metadata": {"name": user_name}, "fullName": full_name}
    r = requests.post(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("payload: "+json.dumps(payload))
    application.logger.debug("r: " + str(r.status_code))
    application.logger.debug("r: " + r.text)
    return r

def delete_openshift_user(token, api_url, user_name, full_name):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/users/' + user_name
    r = requests.delete(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("d os user: " + str(r.status_code))
    application.logger.debug("d os user: " + r.text)
    return r
