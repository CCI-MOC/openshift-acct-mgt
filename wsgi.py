import kubernetes
import pprint
import logging
import requests
import json
import re
import os
from flask import Flask, redirect, url_for, request, Response
from flask_httpauth import HTTPBasicAuth

# from flask_restful import reqparse

import sys

from openshift import *

application = Flask(__name__)
auth = HTTPBasicAuth()

if __name__ != "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    application.logger.handlers = gunicorn_logger.handlers
    application.logger.setLevel(gunicorn_logger.level)


def get_openshift():
    version = os.environ["OPENSHIFT_VERSION"]
    url = os.environ["OPENSHIFT_URL"]
    with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as file:
        token = file.read()
        if version == '3':
            shift = openshift_3_x(url, token, application.logger)
            application.logger.info("using Openshift ver 3")
        else:
            shift = openshift_4_x(url, token, application.logger)
            application.logger.info("using Openshift ver 4")
        return shift
    application.logger.info("Unable to open service account token file, shift not initialized")


@auth.verify_password
def verify_password(username, password):
    with open("/app/auth/users", "r") as f:
        user_str = f.read()
    if(user_str is not None and user_str.len() > 0):
        user = user_str.split(" ", 1)
        if username == user[0] and password == user[1]:
            return username


@application.route(
    "/users/<user_name>/projects/<project_name>/roles/<role>", methods=["GET"]
)
@auth.login_required
def get_moc_rolebindings(project_name, user_name, role):
    # role can be one of Admin, Member, Reader
    shift = get_openshift()
    if shift.user_rolebinding_exists(user_name, project_name, role):
        return Response(
            response=json.dumps(
                {
                    "msg": "user role exists ("
                    + project_name
                    + ","
                    + user_name
                    + ","
                    + role
                    + ")"
                }
            ),
            status=200,
            mimetype="application/json",
        )
    return Response(
        response=json.dumps(
            {
                "msg": "user role does not exists ("
                + project_name
                + ","
                + user_name
                + ","
                + role
                + ")"
            }
        ),
        status=404,
        mimetype="application/json",
    )


@application.route(
    "/users/<user_name>/projects/<project_name>/roles/<role>", methods=["PUT"]
)
@auth.login_required
def create_moc_rolebindings(project_name, user_name, role):
    # role can be one of Admin, Member, Reader
    shift = get_openshift()
    r = shift.update_user_role_project(project_name, user_name, role, "add")
    return r


@application.route(
    "/users/<user_name>/projects/<project_name>/roles/<role>", methods=["DELETE"]
)
@auth.login_required
def delete_moc_rolebindings(project_name, user_name, role):
    # role can be one of Admin, Member, Reader
    shift = get_openshift()
    r = shift.update_user_role_project(project_name, user_name, role, "del")
    return r


@application.route("/projects/<project_uuid>", methods=["GET"])
@application.route("/projects/<project_uuid>/owner/<user_name>", methods=["GET"])
@auth.login_required
def get_moc_project(project_uuid, user_name=None):
    shift = get_openshift()
    if shift.project_exists(project_uuid):
        return Response(
            response=json.dumps({"msg": "project exists (" + project_uuid + ")"}),
            status=200,
            mimetype="application/json",
        )
    return Response(
        response=json.dumps({"msg": "project does not exist (" + project_uuid + ")"}),
        status=400,
        mimetype="application/json",
    )


@application.route("/projects/<project_uuid>", methods=["PUT"])
@application.route("/projects/<project_uuid>/owner/<user_name>", methods=["PUT"])
@auth.login_required
def create_moc_project(project_uuid, user_name=None):
    shift = get_openshift()
    # first check the project_name is a valid openshift project name
    suggested_project_name = shift.cnvt_project_name(project_uuid)
    if project_uuid != suggested_project_name:
        # future work, handel colisons by suggesting a different valid
        # project name
        return Response(
            response=json.dumps(
                {
                    "msg": "ERROR: project name must match regex '[a-z0-9]([-a-z0-9]*[a-z0-9])?'",
                    "suggested name": suggested_project_name,
                }
            ),
            status=400,
            mimetype="application/json",
        )
    if not shift.project_exists(project_uuid):
        project_name = project_uuid
        if "Content-Length" in request.headers:
            req_json = request.get_json(force=True)
            if "displayName" in req_json:
                project_name = req_json["displayName"]
            application.logger.debug("create project json: " + project_name)
        else:
            application.logger.debug("create project json: None")

        r = shift.create_project(project_uuid, project_name, user_name)
        if r.status_code == 200 or r.status_code == 201:
            return Response(
                response=json.dumps({"msg": "project created (" + project_uuid + ")"}),
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps(
                {"msg": "project unabled to be created (" + project_uuid + ")"}
            ),
            status=400,
            mimetype="application/json",
        )
    return Response(
        response=json.dumps({"msg": "project currently exist (" + project_uuid + ")"}),
        status=400,
        mimetype="application/json",
    )


@application.route("/projects/<project_uuid>", methods=["DELETE"])
@auth.login_required
def delete_moc_project(project_uuid):
    shift = get_openshift()
    if shift.project_exists(project_uuid):
        r = shift.delete_project(project_uuid)
        if r.status_code == 200 or r.status_code == 201:
            return Response(
                response=json.dumps({"msg": "project deleted (" + project_uuid + ")"}),
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps(
                {"msg": "project unabled to be deleted (" + project_uuid + ")"}
            ),
            status=400,
            mimetype="application/json",
        )
    return Response(
        response=json.dumps(
            {"msg": "unable to delete, project does not exist(" + project_uuid + ")"}
        ),
        status=400,
        mimetype="application/json",
    )


@application.route("/users/<user_name>", methods=["GET"])
@auth.login_required
def get_moc_user(user_name, full_name=None, id_provider="moc-sso", id_user=None):
    shift = get_openshift()
    r = None
    if shift.user_exists(user_name):
        return Response(
            response=json.dumps({"msg": "user (" + user_name + ") exists"}),
            status=200,
            mimetype="application/json",
        )
    return Response(
        response=json.dumps({"msg": "user (" + user_name + ") does not exist"}),
        status=400,
        mimetype="application/json",
    )


@application.route("/users/<user_name>", methods=["PUT"])
@auth.login_required
def create_moc_user(user_name, full_name=None, id_provider="moc-sso", id_user=None):
    shift = get_openshift()
    r = None
    # full name in payload
    user_exists = False
    # use case if User doesn't exist, then create
    if not shift.user_exists(user_name):
        r = shift.create_user(user_name, full_name)
        if r.status_code != 200 and r.status_code != 201:
            return Response(
                response=json.dumps(
                    {"msg": "unable to create openshift user (" + user_name + ") 1"}
                ),
                status=400,
                mimetype="application/json",
            )
    else:
        user_exists = True

    if id_user is None:
        id_user = user_name

    identity_exists = False
    # if identity doesn't exist then create
    if not shift.identity_exists(id_provider, id_user):
        r = shift.create_identity(id_provider, id_user)
        if r.status_code != 200 and r.status_code != 201:
            return Response(
                response=json.dumps(
                    {"msg": "unable to create openshift identity (" + id_provider + ")"}
                ),
                status=400,
                mimetype="application/json",
            )
    else:
        identity_exists = True

    # creates the useridenitymapping
    user_identity_mapping_exists = False
    if not shift.useridentitymapping_exists(user_name, id_provider, id_user):
        r = shift.create_useridentitymapping(user_name, id_provider, id_user)
        if r.status_code != 200 and r.status_code != 201:
            return Response(
                response=json.dumps(
                    {
                        "msg": "unable to create openshift user identity mapping ("
                        + user_name
                        + ")"
                    }
                ),
                status=400,
                mimetype="application/json",
            )
    else:
        user_identity_mapping_exists = True

    if user_exists and identity_exists and user_identity_mapping_exists:
        return Response(
            response=json.dumps({"msg": "user currently exists (" + user_name + ")"}),
            status=200,
            mimetype="application/json",
        )
    return Response(
        response=json.dumps({"msg": "user created (" + user_name + ")"}),
        status=200,
        mimetype="application/json",
    )


@application.route("/users/<user_name>", methods=["DELETE"])
@auth.login_required
def delete_moc_user(user_name):
    shift = get_openshift()
    r = None
    user_does_not_exist = 0
    # use case if User exists then delete
    if shift.user_exists(user_name):
        r = shift.delete_user(user_name)
        if r.status_code != 200 and r.status_code != 201:
            return Response(
                response=json.dumps(
                    {"msg": "unable to delete User (" + user_name + ") 1"}
                ),
                status=400,
                mimetype="application/json",
            )
    else:
        user_does_not_exist = 0x01

    # This is the specific business case for the MOC sort of
    # TODO: generalize this in the next version.
    #    1) get the list of identities associated with the user
    #    2) delete each one (as well as doing this part first)
    id_user = user_name
    id_provider = "sso_auth"

    if shift.identity_exists(id_provider, id_user):
        r = shift.delete_identity(id_provider, id_user)
        if r.status_code != 200 and r.status_code != 201:
            return Response(
                response=json.dumps(
                    {"msg": "unable to delete identity (" + id_provider + ")"}
                ),
                status=400,
                mimetype="application/json",
            )
    else:
        user_does_not_exist = user_does_not_exist | 0x02

    if user_does_not_exist == 3:
        return Response(
            response=json.dumps(
                {"msg": "user does not currently exist (" + user_name + ")"}
            ),
            status=200,
            mimetype="application/json",
        )
    return Response(
        response=json.dumps({"msg": "user deleted (" + user_name + ")"}),
        status=200,
        mimetype="application/json",
    )


if __name__ == "__main__":
    application.run()
