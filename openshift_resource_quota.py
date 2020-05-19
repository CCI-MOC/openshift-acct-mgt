import kubernetes
import pprint
import logging
import requests
import json
import re
from flask import Flask, redirect, url_for, request, Response

import sys

application = Flask(__name__)



def exists_openshift_resource_quota(token,api_url,project_name,resource_name):
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/api/v1/namespaces/' + project_name + '/resourcequotas/'+resource_name
    r = requests.get(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("cr p: " + str(r.status_code))
    application.logger.debug("cr p: " + r.text)
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False


def create_openshift_resource_quota(token, api_url, project_name,resource_name,cpu_limit, memory_limit):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/api/v1/namespaces/' + project_name + '/resourcequotas'
    quota_def = {
      "kind": "ResourceQuota",
      "apiVersion": "v1",
      "metadata": {
        "name": resource_name
      },
      "spec": {
        "hard": {
          "limits.cpu": cpu_limit,
          "limits.memory": memory_limit,
          "pods": "5",
          "requests.cpu": "1",
          "requests.memory": "1Gi"
        }
      }
    }
    r = requests.post(url, headers=headers, data=json.dumps(quota_def), verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("payload: "+json.dumps(quota_def))
    application.logger.debug("cr r: " + str(r.status_code))
    application.logger.debug("cr r: " + r.text)
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False


def update_openshift_resource_quota(token,api_url,project_name,resource_name):
    headers = {'Authorization': 'Bearer ' + token,'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/api/v1/namespaces/' + project_name + '/resourcequotas/'+ resource_name
    r = requests.get(url, headers=headers, verify=False)
    #if(r.status_code == 200 or r.status_code == 201):
    with open(update_quota.json, 'r') as f:
    	quota = json.load(f)
    r = requests.post(url, headers=headers, data=json.dumps(quota), verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("payload: "+json.dumps(payload))
    application.logger.debug("cr r: " + str(r.status_code))
    application.logger.debug("cr r: " + r.text)
    return r

def get_openshift_resource_quota(token,api_url,project_name,resource_name):
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/api/v1/namespaces/' + project_name + '/resourcequotas/'+resource_name
    r = requests.get(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("cr p: " + str(r.status_code))
    application.logger.debug("cr p: " + r.text)
    return r
#    if(r.status_code == 200 or r.status_code == 201):
#	       return r
#    return False


def delete_openshift_resource_quota(token,api_url,project_name,resource_name):
    headers = {'Authorization': 'Bearer ' + token,'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/api/v1/namespaces/' + project_name + '/resourcequotas/'+ resource_name
    r = requests.delete(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("cr p: " + str(r.status_code))
    application.logger.debug("cr p: " + r.text)
    return r


def deleteAll_openshift_resource_quota(token,api_url,project_name):
    headers = {'Authorization': 'Bearer ' + token,'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/api/v1/namespaces/' + project_name + '/resourcequotas'
    r = requests.delete(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("cr p: " + str(r.status_code))
    application.logger.debug("cr p: " + r.text)
    return r
