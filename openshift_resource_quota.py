import kubernetes
import pprint
import logging
import requests
import json
import re
from flask import Flask, redirect, url_for, request, Response

import sys

application = Flask(__name__)


def create_openshift_resource_quota(token,api_url,project_name)
	headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/api/v1/namespaces/' + project_name + '/resourcequotas/'
    with open(compute_resource.json) as file:
    	quota = json.load(file)
    r = requests.post(url, headers=headers, data=json.dumps(quota), verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("quota: "+json.dumps(quota))
    application.logger.debug("cr r: " + str(r.status_code))
    application.logger.debug("cr r: " + r.text)
    return r

def update_openshift_resource_quota(token,api_url,project_name,resource_name)
	headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/api/v1/namespaces/' + project_name + '/resourcequotas/'+ resource_name
    r = requests.get(url, headers=headers, verify=False)
    if(r.status_code == 200 or r.status_code == 201):
    	with open(update_quota.json) as file:
    	quota = json.load(file)    
    	p = requests.post(url, headers=headers, data=json.dumps(quota), verify=False)
    	application.logger.debug("url: "+url)
    	application.logger.debug("quota: "+json.dumps(quota))
    	application.logger.debug("cr p: " + str(p.status_code))
    	application.logger.debug("cr p: " + p.text)
    	return p

def delete_openshift_resource_quota(token,api_url,project_name,resource_name)
	headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/api/v1/namespaces/' + project_name + '/resourcequotas/'+ resource_name
    r = requests.delete(url, headers=headers, verify=False)
    	application.logger.debug("url: "+url)
    	application.logger.debug("quota: "+json.dumps(quota))
    	application.logger.debug("cr p: " + str(r.status_code))
    	application.logger.debug("cr p: " + r.text)
    	return r

def deleteAll_openshift_resource_quota(token,api_url,project_name)
	headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/api/v1/namespaces/' + project_name + '/resourcequotas/'
    r = requests.delete(url, headers=headers, verify=False)
    	application.logger.debug("url: "+url)
    	application.logger.debug("quota: "+json.dumps(quota))
    	application.logger.debug("cr p: " + str(r.status_code))
    	application.logger.debug("cr p: " + r.text)
    	return r

def getAll_openshift_resource_quota(token,api_url,project_name)
	headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/api/v1/namespaces/' + project_name + '/resourcequotas/'
    r = requests.get(url, headers=headers, verify=False)
    	application.logger.debug("url: "+url)
    	application.logger.debug("quota: "+json.dumps(quota))
    	application.logger.debug("cr p: " + str(r.status_code))
    	application.logger.debug("cr p: " + r.text)
	if(r.status_code == 200 or r.status_code == 201):
		return r
	return False


    return False



