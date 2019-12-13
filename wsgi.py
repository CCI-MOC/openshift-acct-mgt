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

@application.route("/users/<user_name>/projects/<project_name>/roles/<role>", methods=['GET','DELETE'])
def create_rolebindings(project_name, user_name, role):
    # role can be one of Admin, Member, Reader
    (token, openshift_url) = get_token_and_url()

    if(request.method == 'GET'):
        r = update_user_role_project(token, openshift_url, project_name, user_name, role,'add')
        return r
    elif(request.method == 'DELETE'):
        r = update_user_role_project(token, openshift_url, project_name, user_name, role,'del')
        return r
    return Response(
        response=json.dumps({"msg": "Method: '" + request.method + "' Not found"}),
        status=405,
        mimetype='application/json'
        )

@application.route("/projects/<project_name>", methods=['GET','DELETE'])
@application.route("/projects/<project_name>/owner/<user_name>", methods=['GET','DELETE'])
def create_project(project_name, user_name=None):
    (token, openshift_url) = get_token_and_url()
    if(request.method == 'GET'):
        # first check the project_name is a valid openshift project name
        suggested_project_name = cnvt_project_name(project_name)
        if(project_name != suggested_project_name):
            # future work, handel colisons by suggesting a different valid
            # project name
            return "{ \"status_code\": 400, \"msg\":\"ERROR: project name must match regex '[a-z0-9]([-a-z0-9]*[a-z0-9])?'\", \"suggested name\": \"" + suggested_project_name + "\"}", 422
        if(not exists_openshift_project(token, openshift_url, project_name)):
            r = create_openshift_project(
                token, openshift_url, project_name, user_name)
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
    elif(request.method=='DELETE'):
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
    return Response(
        response=json.dumps({"msg": "Method: '" + request.method + "' Not found"}),
        status=405,
        mimetype='application/json'
        )

@application.route("/users/<user_name>", methods=['GET','DELETE'])
@application.route("/users/<user_name>/fullname/<full_name>", methods=['GET','DELETE'])
@application.route("/users/<user_name>/fullname/<full_name>/<identity>/<id_user>", methods=['GET','DELETE'])
def user_management(user_name, full_name=None, id_provider="sso_auth", id_user=None):
    (token, openshift_url) = get_token_and_url()
    r=None

    if(request.method == 'GET'):
        user_exists = 0x00
        # use case if User doesn't exist, then create
        if(not exists_openshift_user(token, openshift_url, user_name)):
            r = create_openshift_user(
                token, openshift_url, user_name, full_name)
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
            r = create_openshift_identity(
                token, openshift_url, id_provider, id_user)
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
            r = create_openshift_useridentitymapping(
                token, openshift_url, user_name, id_provider, id_user)
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
        else:
            return Response(
                response=json.dumps({"msg": "user created (" + user_name + ")"}),
                status=200,
                mimetype='application/json'
                )


    elif(request.method == 'DELETE'):
        user_does_not_exist=0
         # use case if User exists then delete
        if(exists_openshift_user(token, openshift_url, user_name)):
            r = delete_openshift_user(
                token, openshift_url, user_name, full_name)
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
            r = delete_openshift_identity(
                token, openshift_url, id_provider, id_user)
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
        else:
            return Response(
                response=json.dumps({"msg": "user deleted (" + user_name + ")"}),
                status=200,
                mimetype='application/json'
                )
       
    return Response(
        response=json.dumps({"msg": "Method: '" + request.method + "' Not found"}),
        status=405,
        mimetype='application/json'
        )

@application.route("/users/<user_name>/projects/<project_name>/roles/<role>")
def map_project(user_name, project_name, role):
    # "oc login -u acct-mgt-sa"
    # "oc adm policy -n <project_name> add-role-to-user <role> <user_name>"
    return "{\"map\"}"

if __name__ == "__main__":
    application.run()
