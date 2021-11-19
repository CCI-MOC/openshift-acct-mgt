import logging
import json
import os
from flask import Flask, request, Response
from flask_httpauth import HTTPBasicAuth
import moc_openshift

APP = Flask(__name__)
AUTH = HTTPBasicAuth()

if __name__ != "__main__":
    APP.logger = logging.getLogger("gunicorn.error")
    # logger level INFO = 20 see (https://docs.python.org/3/library/logging.html#levels)
    APP.logger.setLevel(20)


class MocOpenShiftSingleton:
    class __MocOSInt:
        def __init__(self, version, url, logger):
            with open(
                "/var/run/secrets/kubernetes.io/serviceaccount/token", "r"
            ) as file:
                token = file.read()
                # if version == "3":
                #    self.shift = moc_openshift.MocOpenShift3x(url, token, logger)
                #    APP.logger.info("using Openshift ver 3")
                # else:
                self.shift = moc_openshift.MocOpenShift4x(url, token, logger)
                APP.logger.info("using Openshift ver 4")

    openshift_instance = None

    def __init__(self, version, url, logger):
        if not MocOpenShiftSingleton.openshift_instance:
            MocOpenShiftSingleton.openshift_instance = MocOpenShiftSingleton.__MocOSInt(
                version, url, logger
            )

    def get_openshift(self):
        return self.openshift_instance.shift


def get_openshift():
    version = os.environ["OPENSHIFT_VERSION"]
    url = os.environ["OPENSHIFT_URL"]
    shift = MocOpenShiftSingleton(version, url, APP.logger).get_openshift()
    return shift


@AUTH.verify_password
def verify_password(username, password):
    with open("/app/auth/users", "r") as my_file:
        user_str = my_file.read()
    if user_str:
        user = user_str.split(" ", 1)
        if username == user[0] and password == user[1]:
            return username
    return None


@APP.route("/users/<user_name>/projects/<project_name>/roles/<role>", methods=["GET"])
@AUTH.login_required
def get_moc_rolebindings(project_name, user_name, role):
    # role can be one of Admin, Member, Reader
    shift = get_openshift()
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
            {"msg": f"user role does not exists ({project_name},{user_name},{role})"}
        ),
        status=404,
        mimetype="application/json",
    )


@APP.route("/users/<user_name>/projects/<project_name>/roles/<role>", methods=["PUT"])
@AUTH.login_required
def create_moc_rolebindings(project_name, user_name, role):
    # role can be one of Admin, Member, Reader
    shift = get_openshift()
    result = shift.update_user_role_project(project_name, user_name, role, "add")
    if result.status_code == 200 or result.status_code == 201:
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
    shift = get_openshift()
    result = shift.update_user_role_project(project_name, user_name, role, "del")
    if result.status_code == 200 or result.status_code == 201:
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
    shift = get_openshift()
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
            APP.logger.debug("create project json: " + project_name)
        else:
            APP.logger.debug("create project json: None")

        result = shift.create_project(project_uuid, project_name, user_name)
        if result.status_code == 200 or result.status_code == 201:
            return Response(
                response=json.dumps({"msg": f"project created ({project_uuid})"}),
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps(
                {"msg": f"project unabled to be created ({project_uuid})"}
            ),
            status=400,
            mimetype="application/json",
        )
    return Response(
        response=json.dumps({"msg": f"project currently exist ({project_uuid})"}),
        status=400,
        mimetype="application/json",
    )


@APP.route("/projects/<project_uuid>", methods=["DELETE"])
@AUTH.login_required
def delete_moc_project(project_uuid):
    shift = get_openshift()
    if shift.project_exists(project_uuid):
        result = shift.delete_project(project_uuid)
        if result.status_code == 200 or result.status_code == 201:
            return Response(
                response=json.dumps({"msg": f"project deleted ({project_uuid})"}),
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps(
                {"msg": f"project unabled to be deleted ({project_uuid})"}
            ),
            status=400,
            mimetype="application/json",
        )
    return Response(
        response=json.dumps(
            {"msg": f"unable to delete, project does not exist ({project_uuid})"}
        ),
        status=400,
        mimetype="application/json",
    )


@APP.route("/users/<user_name>", methods=["GET"])
@AUTH.login_required
def get_moc_user(user_name):
    shift = get_openshift()
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
    # full_name    - the full name of the user as it is really convenient to confirm who the account belongs to
    # id_provider  - the id provider (was sso_auth, now is moc-sso)
    # id_user      - the user name associated with the id provider.  can be used to map muliple sso users to a an account as people don't always remember which sso account they are logged in as
    # id_provider = "moc-sso"
    id_provider = "developer"
    full_name = user_name
    id_user = user_name  # until we support different user names see above.

    shift = get_openshift()
    user_exists = False
    # use case if User doesn't exist, then create
    if not shift.user_exists(user_name):
        result = shift.create_user(user_name, full_name)
        if result.status_code != 200 and result.status_code != 201:
            return Response(
                response=json.dumps(
                    {f"msg": "unable to create openshift user ({user_name}) 1"}
                ),
                status=400,
                mimetype="application/json",
            )
    else:
        user_exists = True

    identity_exists = False
    # if identity doesn't exist then create
    if not shift.identity_exists(id_provider, id_user):
        result = shift.create_identity(id_provider, id_user)
        if result.status_code != 200 and result.status_code != 201:
            return Response(
                response=json.dumps(
                    {"msg": f"unable to create openshift identity ({id_provider})"}
                ),
                status=400,
                mimetype="application/json",
            )
    else:
        identity_exists = True

    # creates the useridenitymapping
    user_identity_mapping_exists = False
    if not shift.useridentitymapping_exists(user_name, id_provider, id_user):
        result = shift.create_useridentitymapping(user_name, id_provider, id_user)
        if result.status_code != 200 and result.status_code != 201:
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
            response=json.dumps({"msg": f"user currently exists ({user_name})"}),
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
    shift = get_openshift()
    user_does_not_exist = 0
    # use case if User exists then delete
    if shift.user_exists(user_name):
        result = shift.delete_user(user_name)
        if result.status_code != 200 and result.status_code != 201:
            return Response(
                response=json.dumps({"msg": f"unable to delete User ({user_name}) 1"}),
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
        result = shift.delete_identity(id_provider, id_user)
        if result.status_code != 200 and result.status_code != 201:
            return Response(
                response=json.dumps(
                    {"msg": f"unable to delete identity ({id_provider})"}
                ),
                status=400,
                mimetype="application/json",
            )
    else:
        user_does_not_exist = user_does_not_exist | 0x02

    if user_does_not_exist == 3:
        return Response(
            response=json.dumps(
                {"msg": f"user does not currently exist ({user_name})"}
            ),
            status=200,
            mimetype="application/json",
        )
    return Response(
        response=json.dumps({"msg": f"user deleted ({user_name})"}),
        status=200,
        mimetype="application/json",
    )


if __name__ == "__main__":
    APP.run()


@APP.route("/projects/<project>/quota", methods=["GET"])
@AUTH.login_required
def list_moc_quota(project):
    shift = get_openshift()
    return shift.get_moc_quota(project)


@APP.route("/projects/<project>/quota", methods=["POST"])
@AUTH.login_required
def put_moc_quota(project):
    shift = get_openshift()
    quota_def = request.json
    return shift.get_moc_quota(project, quota_def)


@APP.route("/projects/<project>/quota", methods=["DELETE"])
@AUTH.login_required
def delete_quota(project):
    shift = get_openshift()
    return shift.delete_moc_quota(project)
