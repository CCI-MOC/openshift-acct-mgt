import kubernetes
import pprint
import logging
import requests
import json
import re
from flask import Flask, redirect, url_for, request, Response

import sys

application = Flask(__name__)

def exists_openshift_identity(token, api_url, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/identities/' + id_provider + ':' + id_user
    r = requests.get(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("r: " + str(r.status_code))
    application.logger.debug("r: " + r.text)
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False


def delete_openshift_identity(token, api_url, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/identities'
    payload = {"kind": "DeleteOptions", "apiVersion": "v1",
               "providerName": id_provider, "providerUserName": id_user, "gracePeriodSeconds":"300" }
    r = requests.delete(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("payload: "+json.dumps(payload))
    application.logger.debug("d os ident: " + str(r.status_code))
    application.logger.debug("d os ident: " + r.text)
    return r
    
def create_openshift_identity(token, api_url, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/identities'
    payload = {"kind": "Identity", "apiVersion": "v1",
               "providerName": id_provider, "providerUserName": id_user}
    r = requests.post(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("r: " + str(r.status_code))
    application.logger.debug("r: " + r.text)
    return r


def exists_openshift_useridentitymapping(token, api_url, user_name, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}

    url = 'https://' + api_url + '/oapi/v1/useridentitymappings/' + \
        id_provider + ':' + id_user
    r = requests.get(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("r: " + str(r.status_code))
    application.logger.debug("r: " + r.text)
    # it is probably not necessary to check the user name in the useridentity
    # mapping
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False


def create_openshift_useridentitymapping(token, api_url, user_name, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/useridentitymappings'
    payload = {"kind": "UserIdentityMapping", "apiVersion": "v1", "user": {
        "name": user_name}, "identity": {"name": id_provider + ":" + id_user}}
    r = requests.post(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("payload: "+json.dumps(payload))
    application.logger.debug("r: " + str(r.status_code))
    application.logger.debug("r: " + r.text)
    return r
