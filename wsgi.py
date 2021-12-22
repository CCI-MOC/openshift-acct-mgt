"""WSGI application for MOC openshift account management microservice"""

import logging
import json
import os
from flask import Flask, request, Response
from flask_httpauth import HTTPBasicAuth

import defaults
import kubeclient
import moc_openshift

ENVPREFIX = "ACCT_MGT_"


def env_config():
    """Get configuration values from environment variables.

    Look up all environment variables that start with ENVPREFIX (by default
    "ACCT_MGT_"), strip the prefix, and store them in a dictionary. Return the
    dictionary to the caller.
    """

    return {
        k[len(ENVPREFIX) :]: v for k, v in os.environ.items() if k.startswith(ENVPREFIX)
    }


def get_openshift(client, app):
    return moc_openshift.MocOpenShift4x(client, app)


# pylint: disable=too-many-statements,too-many-locals,redefined-outer-name
def create_app(**config):
    APP = Flask(__name__)
    AUTH = HTTPBasicAuth()

    APP.config.from_object(defaults)
    APP.config.from_mapping(config)

    # Allow unit tests to explicitly disable environment configuration
    if APP.config.get("DISABLE_ENV_CONFIG", False):
        APP.config.from_mapping(env_config())

    CLIENT = kubeclient.Client(
        baseurl=APP.config.get("OPENSHIFT_URL"),
        token=APP.config.get("AUTH_TOKEN"),
        verify=APP.config.get("CA_PATH"),
    )

    shift = get_openshift(CLIENT, APP)

    @AUTH.verify_password
    def verify_password(username, password):
        """Validates a username and password."""

        return (
            username == APP.config["ADMIN_USERNAME"]
            and password == APP.config["ADMIN_PASSWORD"]
        )

    @APP.route(
        "/users/<user_name>/projects/<project_name>/roles/<role>", methods=["GET"]
    )
    @AUTH.login_required
    def get_moc_rolebindings(project_name, user_name, role):
        # role can be one of Admin, Member, Reader
        if shift.user_rolebinding_exists(user_name, project_name, role):
            return Response(
                response=json.dumps(
                    {"msg": f"user role exists ({project_name},{user_name},{role})"}
                ),
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps(
                {"msg": f"user role does not exist ({project_name},{user_name},{role})"}
            ),
            status=404,
            mimetype="application/json",
        )

    @APP.route(
        "/users/<user_name>/projects/<project_name>/roles/<role>", methods=["PUT"]
    )
    @AUTH.login_required
    def create_moc_rolebindings(project_name, user_name, role):
        # role can be one of Admin, Member, Reader
        result = shift.update_user_role_project(project_name, user_name, role, "add")
        if result.status_code in (200, 201):
            return Response(
                response=result.response,
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=result.response,
            status=400,
            mimetype="application/json",
        )

    @APP.route(
        "/users/<user_name>/projects/<project_name>/roles/<role>", methods=["DELETE"]
    )
    @AUTH.login_required
    def delete_moc_rolebindings(project_name, user_name, role):
        # role can be one of Admin, Member, Reader
        result = shift.update_user_role_project(project_name, user_name, role, "del")
        if result.status_code in (200, 201):
            return Response(
                response=result.response,
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=result.response,
            status=400,
            mimetype="application/json",
        )

    @APP.route("/projects/<project_uuid>", methods=["GET"])
    @AUTH.login_required
    def get_moc_project(project_uuid):
        if shift.project_exists(project_uuid):
            return Response(
                response=json.dumps({"msg": f"project exists ({project_uuid})"}),
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps({"msg": f"project does not exist ({project_uuid})"}),
            status=400,
            mimetype="application/json",
        )

    @APP.route("/projects/<project_uuid>", methods=["PUT"])
    @APP.route("/projects/<project_uuid>/owner/<user_name>", methods=["PUT"])
    @AUTH.login_required
    def create_moc_project(project_uuid, user_name=None):
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
            if request.json:
                project_name = request.json.get("displayName", project_uuid)
                APP.logger.debug("create project json: %s", project_name)
            else:
                project_name = project_uuid
                APP.logger.debug("create project json: None")

            result = shift.create_project(project_uuid, project_name, user_name)
            if result.status_code in (200, 201):
                return Response(
                    response=json.dumps({"msg": f"project created ({project_uuid})"}),
                    status=200,
                    mimetype="application/json",
                )
            return Response(
                response=json.dumps(
                    {"msg": f"unable to create project ({project_uuid})"}
                ),
                status=400,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps({"msg": f"project already exists ({project_uuid})"}),
            status=400,
            mimetype="application/json",
        )

    @APP.route("/projects/<project_uuid>", methods=["DELETE"])
    @AUTH.login_required
    def delete_moc_project(project_uuid):
        if shift.project_exists(project_uuid):
            result = shift.delete_project(project_uuid)
            if result.status_code in (200, 201):
                return Response(
                    response=json.dumps({"msg": f"project deleted ({project_uuid})"}),
                    status=200,
                    mimetype="application/json",
                )
            return Response(
                response=json.dumps(
                    {"msg": f"unable to delete project ({project_uuid})"}
                ),
                status=400,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps({"msg": f"project does not exist ({project_uuid})"}),
            status=400,
            mimetype="application/json",
        )

    @APP.route("/users/<user_name>", methods=["GET"])
    @AUTH.login_required
    def get_moc_user(user_name):
        if shift.user_exists(user_name):
            return Response(
                response=json.dumps({"msg": f"user ({user_name}) exists"}),
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps({"msg": f"user ({user_name}) does not exist"}),
            status=400,
            mimetype="application/json",
        )

    @APP.route("/users/<user_name>", methods=["PUT"])
    @AUTH.login_required
    def create_moc_user(user_name):
        # these three values should be added to generalize this function
        # full_name    - the full name of the user as it is really convenient
        # id_provider  - this is in the yaml configuration for this project - needed in the past

        full_name = user_name
        id_user = user_name  # until we support different user names see above.

        user_exists = False
        # use case if User doesn't exist, then create
        if not shift.user_exists(user_name):
            result = shift.create_user(user_name, full_name)
            if result.status_code not in (200, 201):
                return Response(
                    response=json.dumps(
                        {"msg": f"unable to create openshift user ({user_name}) 1"}
                    ),
                    status=400,
                    mimetype="application/json",
                )
        else:
            user_exists = True

        identity_exists = False
        # if identity doesn't exist then create
        if not shift.identity_exists(id_user):
            result = shift.create_identity(id_user)
            if result.status_code not in (200, 201):
                return Response(
                    response=json.dumps({"msg": "unable to create openshift identity"}),
                    status=400,
                    mimetype="application/json",
                )
        else:
            identity_exists = True

        # creates the useridenitymapping
        user_identity_mapping_exists = False
        if not shift.useridentitymapping_exists(user_name, id_user):
            result = shift.create_useridentitymapping(user_name, id_user)
            if result.status_code not in (200, 201):
                return Response(
                    response=json.dumps(
                        {
                            "msg": f"unable to create openshift user identity mapping ({user_name})"
                        }
                    ),
                    status=400,
                    mimetype="application/json",
                )
        else:
            user_identity_mapping_exists = True

        if user_exists and identity_exists and user_identity_mapping_exists:
            return Response(
                response=json.dumps({"msg": f"user already exists ({user_name})"}),
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps({"msg": f"user created ({user_name})"}),
            status=200,
            mimetype="application/json",
        )

    @APP.route("/users/<user_name>", methods=["DELETE"])
    @AUTH.login_required
    def delete_moc_user(user_name):
        user_does_not_exist = 0
        # use case if User exists then delete
        if shift.user_exists(user_name):
            result = shift.delete_user(user_name)
            if result.status_code not in (200, 201):
                return Response(
                    response=json.dumps(
                        {"msg": f"unable to delete user ({user_name}) 1"}
                    ),
                    status=400,
                    mimetype="application/json",
                )
        else:
            user_does_not_exist = 0x01

        id_user = user_name

        if shift.identity_exists(id_user):
            result = shift.delete_identity(id_user)
            if result.status_code not in (200, 201):
                return Response(
                    response=json.dumps(
                        {"msg": f"unable to delete identity for ({id_user})"}
                    ),
                    status=400,
                    mimetype="application/json",
                )
        else:
            user_does_not_exist = user_does_not_exist | 0x02

        if user_does_not_exist == 3:
            return Response(
                response=json.dumps({"msg": f"user does not exist ({user_name})"}),
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps({"msg": f"user deleted ({user_name})"}),
            status=200,
            mimetype="application/json",
        )

    @APP.route("/projects/<project>/quota", methods=["GET"])
    @AUTH.login_required
    def get_quota(project):
        return Response(
            response=json.dumps(shift.get_moc_quota(project)),
            status=200,
            mimetype="application/json",
        )

    @APP.route("/projects/<project>/quota", methods=["PUT", "POST"])
    @AUTH.login_required
    def put_quota(project):
        moc_quota = request.get_json(force=True)
        return shift.replace_moc_quota(project, moc_quota)

    @APP.route("/projects/<project>/quota", methods=["DELETE"])
    @AUTH.login_required
    def delete_quota(project):
        return shift.delete_moc_quota(project)

    return APP


APP = create_app()

if __name__ == "__main__":
    APP.run()
else:
    APP.logger = logging.getLogger("gunicorn.error")
    # logger level INFO = 20 see (https://docs.python.org/3/library/logging.html#levels)
    APP.logger.setLevel(20)
