import kubernetes
import pprint
import logging
import requests
import json
import re
import os
from flask import Flask, redirect, url_for, request, Response
#from flask_restful import reqparse

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
    openshift_url = os.environ["openshift_url"]
    return (token, openshift_url)

@application.route("/users/<user_name>/projects/<project_name>/roles/<role>", methods=['GET'])
def get_moc_rolebindings(project_name, user_name, role):
    # role can be one of Admin, Member, Reader
    (token, openshift_url) = get_token_and_url()
    if(exists_user_rolebinding(token, openshift_url, user_name, project_name, role)):
        return Response(
                response=json.dumps({"msg": "user role exists ("+project_name + "," + user_name + ","+ role + ")"}),
                status=200,
                mimetype='application/json'
            )
    return Response(
            response=json.dumps({"msg": "user role does not exists ("+project_name + "," + user_name + ","+ role + ")"}),
            status=404,
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

@application.route("/projects/<project_uuid>", methods=['GET'])
@application.route("/projects/<project_uuid>/owner/<user_name>", methods=['GET'])
def get_moc_project(project_uuid, user_name=None):
    (token, openshift_url) = get_token_and_url()
    if(exists_openshift_project(token, openshift_url, project_uuid)):
        return Response(
            response=json.dumps({"msg": "project exists (" + project_uuid + ")"}),
            status=200,
            mimetype='application/json'
            )
    return Response(
        response=json.dumps({"msg": "project does not exist (" + project_uuid + ")"}),
        status=400,
        mimetype='application/json'
        )                 

@application.route("/projects/<project_uuid>", methods=['PUT'])
@application.route("/projects/<project_uuid>/owner/<user_name>", methods=['PUT'])
def create_moc_project(project_uuid, user_name=None):
    (token, openshift_url) = get_token_and_url()
    # first check the project_name is a valid openshift project name
    suggested_project_name = cnvt_project_name(project_uuid)
    if(project_uuid != suggested_project_name):
        # future work, handel colisons by suggesting a different valid
        # project name
        return Response(
            response=json.dumps({"msg":"ERROR: project name must match regex '[a-z0-9]([-a-z0-9]*[a-z0-9])?'", "suggested name": suggested_project_name }),
            status=400,
            mimetype='application/json'
            )
    if(not exists_openshift_project(token, openshift_url, project_uuid)):
        project_name=project_uuid
        if("Content-Length" in request.headers):
            req_json=request.get_json(force=True)
            if("displayName" in req_json):
                project_name=req_json["displayName"]
            application.logger.debug("create project json: "+project_name)
        else:
            application.logger.debug("create project json: None")

        r = create_openshift_project(token, openshift_url, project_uuid, project_name, user_name)
        if(r.status_code == 200 or r.status_code == 201):
            return Response(
                response=json.dumps({"msg": "project created (" + project_uuid +")" }),
                status=200,
                mimetype='application/json'
                )
        return Response(
            response=json.dumps({"msg": "project unabled to be created (" + project_uuid +")" }),
            status=400,
            mimetype='application/json'
            )
    return Response(
        response=json.dumps({"msg": "project currently exist (" + project_uuid +")" }),
        status=400,
        mimetype='application/json'
        )

@application.route("/projects/<project_uuid>", methods=['DELETE'])
@application.route("/projects/<project_uuid>/owner/<user_name>", methods=['DELETE'])
def delete_moc_project(project_uuid, user_name=None):
    (token, openshift_url) = get_token_and_url()
    if(exists_openshift_project(token, openshift_url, project_uuid)):
        r = delete_openshift_project( token, openshift_url, project_uuid, user_name)
        if(r.status_code == 200 or r.status_code == 201):
            return Response(
                response=json.dumps({"msg": "project deleted (" + project_uuid +")" }),
                status=200,
                mimetype='application/json'
               )
        return Response(
            response=json.dumps({"msg": "project unabled to be deleted (" + project_uuid +")" }),
            status=400,
            mimetype='application/json'
            )
    return Response(
        response=json.dumps({"msg": "unable to delete, project does not exist(" + project_uuid +")" }),
        status=400,
        mimetype='application/json'
        )

@application.route("/users/<user_name>", methods=['GET'])
def get_moc_user(user_name, full_name=None, id_provider="sso_auth", id_user=None):
    (token, openshift_url) = get_token_and_url()
    r=None
    if(exists_openshift_user(token, openshift_url, user_name)):
        return Response(
            response=json.dumps({"msg": "user (" + user_name + ") exists"}),
            status=200,
            mimetype='application/json'
            )
    return Response(
            response=json.dumps({"msg": "user (" + user_name + ") does not exist"}),
            status=400,
            mimetype='application/json'
            )       

@application.route("/users/<user_name>", methods=['PUT'])
def create_moc_user(user_name, full_name=None, id_provider="sso_auth", id_user=None):
    token, openshift_url = get_token_and_url()

    # A user in OpenShift is composed of 3 parts: user, identity, and identitymapping.
    user_exists = exists_openshift_user(token, openshift_url, user_name)
    if not user_exists:
        r = create_openshift_user(token, openshift_url, user_name, full_name)

        if r.status_code not in [200, 201]:
            return Response(
                response=json.dumps({"msg": "unable to create openshift user (" + user_name + ") 1"}),
                status=400,
                mimetype='application/json'
                )

    if id_user is None:
        id_user = user_name

    identity_exists = exists_openshift_identity(token, openshift_url, id_provider, id_user)
    if not identity_exists:
        r = create_openshift_identity(token, openshift_url, id_provider, id_user)

        if r.status_code not in [200, 201]:
            return Response(
                response=json.dumps({"msg": "unable to create openshift identity (" + id_provider + ")"}),
                status=400,
                mimetype='application/json'
                )

    mapping_exists = exists_openshift_useridentitymapping(token, openshift_url, user_name, id_provider, id_user)
    if not mapping_exists:
        r = create_openshift_useridentitymapping(token, openshift_url, user_name, id_provider, id_user)

        if r.status_code not in [200, 201]:
            return Response(
                response=json.dumps({"msg": "unable to create openshift user identity mapping (" + user_name + ")"}),
                status=400,
                mimetype='application/json'
                )

    if user_exists and identity_exists and mapping_exists:
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
    token, openshift_url = get_token_and_url()

    user_exists = exists_openshift_user(token, openshift_url, user_name)
    if user_exists:
        r = delete_openshift_user(token, openshift_url, user_name, full_name)
        if r.status_code not in [200, 201]:
            return Response(
                response=json.dumps({"msg": "unable to delete User (" + user_name + ") 1"}),
                status=400,
                mimetype='application/json'
                )

    if id_user is None:
        id_user = user_name

    identity_exists = exists_openshift_identity(token, openshift_url, id_provider, id_user)
    if identity_exists:
        r = delete_openshift_identity(token, openshift_url, id_provider, id_user)

        if r.status_code not in [200, 201]:
            return Response(
                response=json.dumps({"msg": "unable to delete identity (" + id_provider + ")"}),
                status=400,
                mimetype='application/json'
                )

    if not user_exists and not identity_exists:
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
