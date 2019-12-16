import kubernetes
import pprint
import logging
import requests
import json
import re
from flask import Flask, redirect, url_for, request, Response

import sys

from openshift_rolebindings import *
from openshift_project import *
from openshift_identity import *
from openshift_user import *

application = Flask(__name__)

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    application.logger.handlers = gunicorn_logger.handlers
    application.logger.setLevel(gunicorn_logger.level)


def get_user_token():
    with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as file:
        token = file.read()
        return token
    return ""

def get_token_and_url():
    token = get_user_token()
    #openshift_url = "https://192.168.64.17:8443"
    #openshift_url = "https://k-openshift.osh.massopen.cloud:8443"
    openshift_url = "s-openshift.osh.massopen.cloud:8443"
    #openshift_url = "sn001:8443"

    #the following 3 don't work
    #openshift_url = "https://127.30.0.1:443"
    #openshift_url = "https://127.30.0.1:8443"
    #openshift_url = "https://127.0.0.1:8443"
    return (token, openshift_url)

@application.route("/users/<user_name>/projects/<project_name>/roles/<role>", methods=['GET'])
def get_moc_rolebindings(project_name, user_name, role):
    # role can be one of Admin, Member, Reader
    (token, openshift_url) = get_token_and_url()
    get_openshift_rolebindings(token, api_url, project_name, role)
    if(exists_openshift_rolebindings(token, openshift_url, project_name, role)):
        return Response(
                response=json.dumps({"msg": "user role exists ("+project_name + "," + user_name + ","+ role + ")"}),
                status=202,
                mimetype='application/json'
            )
    return Response(
            response=json.dumps({"msg": "user role does not exists ("+project_name + "," + user_name + ","+ role + ")"}),
            status=400,
            mimetype='application/json'
        )    

@application.route("/users/<user_name>/projects/<project_name>/roles/<role>", methods=['PUT'])
def create_moc_rolebindings(project_name, user_name, role):
    # role can be one of Admin, Member, Reader
    (token, openshift_url) = get_token_and_url()
    r = update_user_role_project(token, openshift_url, project_name, user_name, role,'add') 
    return r
 

@application.route("/users/<user_name>/projects/<project_name>/roles/<role>", methods=['DELETE'])
def delete_moc_rolebindings(project_name, user_name, role):
    # role can be one of Admin, Member, Reader
    (token, openshift_url) = get_token_and_url()
    r = update_user_role_project(token, openshift_url, project_name, user_name, role,'del')
    return r

@application.route("/projects/<project_name>", methods=['GET'])
@application.route("/projects/<project_name>/owner/<user_name>", methods=['GET'])
def get_moc_project(project_name, user_name=None):
    (token, openshift_url) = get_token_and_url()
    if(exists_openshift_project(token, openshift_url, project_name)):
        return Response(
            response=json.dumps({"msg": "project exists (" + project_name + ")"}),
            status=202,
            mimetype='application/json'
            )
    return Response(
        response=json.dumps({"msg": "project does not exist (" + project_name + ")"}),
        status=400,
        mimetype='application/json'
        )                 

@application.route("/projects/<project_name>", methods=['PUT'])
@application.route("/projects/<project_name>/owner/<user_name>", methods=['PUT'])
def create_moc_project(project_name, user_name=None):
    (token, openshift_url) = get_token_and_url()
    # first check the project_name is a valid openshift project name
    suggested_project_name = cnvt_project_name(project_name)
    if(project_name != suggested_project_name):
        # future work, handel colisons by suggesting a different valid
        # project name
        return Response(
            response=json.dumps({"msg":"ERROR: project name must match regex '[a-z0-9]([-a-z0-9]*[a-z0-9])?'", "suggested name": suggested_project_name }),
            status=400,
            mimetype='application/json'
            )
    if(not exists_openshift_project(token, openshift_url, project_name)):
        r = create_openshift_project(token, openshift_url, project_name, user_name)
        if(r.status_code == 200 or r.status_code == 201):
            return Response(
                response=json.dumps({"msg": "project created (" + project_name +")" }),
                status=200,
                mimetype='application/json'
                )
        return Response(
            response=json.dumps({"msg": "project unabled to be created (" + project_name +")" }),
            status=400,
            mimetype='application/json'
            )
    return Response(
        response=json.dumps({"msg": "project currently exist (" + project_name +")" }),
        status=400,
        mimetype='application/json'
        )

@application.route("/projects/<project_name>", methods=['DELETE'])
@application.route("/projects/<project_name>/owner/<user_name>", methods=['DELETE'])
def delete_moc_project(project_name, user_name=None):
    (token, openshift_url) = get_token_and_url()
    if(exists_openshift_project(token, openshift_url, project_name)):
        r = delete_openshift_project(
            token, openshift_url, project_name, user_name)
        if(r.status_code == 200 or r.status_code == 201):
            return Response(
                response=json.dumps({"msg": "project deleted (" + project_name +")" }),
                status=200,
                mimetype='application/json'
               )
        return Response(
            response=json.dumps({"msg": "project unabled to be deleted (" + project_name +")" }),
            status=400,
            mimetype='application/json'
            )
    return Response(
        response=json.dumps({"msg": "unable to delete, project does not exist(" + project_name +")" }),
        status=400,
        mimetype='application/json'
        )
 
@application.route("/users/<user_name>", methods=['GET'])
def get_moc_user(user_name, full_name=None, id_provider="sso_auth", id_user=None):
    (token, openshift_url) = get_token_and_url()
    r=None
    if(exists_openshift_user(token, openshift_url, user_name)):
        return Response(
            response=json.dumps({"msg": "User (" + user_name + ") exists"}),
            status=202,
            mimetype='application/json'
            )
    return Response(
            response=json.dumps({"msg": "User (" + user_name + ") does not exist"}),
            status=400,
            mimetype='application/json'
            )       

@application.route("/users/<user_name>", methods=['PUT'])
def create_moc_user(user_name, full_name=None, id_provider="sso_auth", id_user=None):
    (token, openshift_url) = get_token_and_url()
    r=None
    # full name in payload
    user_exists = 0x00
    # use case if User doesn't exist, then create
    if(not exists_openshift_user(token, openshift_url, user_name)):
        r = create_openshift_user(token, openshift_url, user_name, full_name)
        if(r.status_code != 200 and r.status_code != 201):
            return Response(
                response=json.dumps({"msg": "unable to create openshift User (" + user_name + ") 1"}),
                status=400,
                mimetype='application/json'
                )
    else:
        user_exists = user_exists | 0x01

    if(id_user is None):
        id_user = user_name

    # if identity doesn't exist then create
    if(not exists_openshift_identity(token, openshift_url, id_provider, id_user)):
        r = create_openshift_identity(token, openshift_url, id_provider, id_user)
        if(r.status_code != 200 and r.status_code != 201):
            return Response(
                response=json.dumps({"msg": "unable to create openshift identity (" + id_provider + ")"}),
                status=400,
                mimetype='application/json'
                )
    else:
        user_exists = user_exists | 0x02
    # creates the useridenitymapping
    if(not exists_openshift_useridentitymapping(token, openshift_url, user_name, id_provider, id_user)):
        r = create_openshift_useridentitymapping(token, openshift_url, user_name, id_provider, id_user)
        if(r.status_code != 200 and r.status_code != 201):
            return Response(
                response=json.dumps({"msg": "unable to create openshift user identity mapping (" + user_name + ")"}),
                status=400,
                mimetype='application/json'
                )
    else:
        user_exists = user_exists | 0x04

    if(user_exists==7):
        return Response(
            response=json.dumps({"msg": "user currently exists (" + user_name + ")"}),
            status=200,
            mimetype='application/json'
            )
    return Response(
        response=json.dumps({"msg": "user created (" + user_name + ")"}),
        status=200,
        mimetype='application/json'
        )

@application.route("/users/<user_name>", methods=['DELETE'])
def delete_moc_user(user_name, full_name=None, id_provider="sso_auth", id_user=None):
    (token, openshift_url) = get_token_and_url()
    r=None
    user_does_not_exist=0
    # use case if User exists then delete
    if(exists_openshift_user(token, openshift_url, user_name)):
        r = delete_openshift_user(token, openshift_url, user_name, full_name)
        if(r.status_code != 200 and r.status_code != 201):
            return Response(
                response=json.dumps({"msg": "unable to delete User (" + user_name + ") 1"}),
                status=400,
                mimetype='application/json'
                )
    else:
        user_does_not_exist = 0x01

    if(id_user is None):
        id_user = user_name
    # if identity doesn't exist then create
    if(exists_openshift_identity(token, openshift_url, id_provider, id_user)):
        r = delete_openshift_identity(token, openshift_url, id_provider, id_user)
        if(r.status_code != 200 and r.status_code != 201):
            return Response(
                response=json.dumps({"msg": "unable to delete identity (" + id_provider + ")"}),
                status=400,
                mimetype='application/json'
                )
    else:
        user_does_not_exist =  user_does_not_exist | 0x02

    if(user_does_not_exist==3):
        return Response(
            response=json.dumps({"msg": "user does not currently exist (" + user_name + ")"}),
            status=200,
            mimetype='application/json'
            )
    return Response(
        response=json.dumps({"msg": "user deleted (" + user_name + ")"}),
        status=200,
        mimetype='application/json'
        )     


if __name__ == "__main__":
    application.run()
