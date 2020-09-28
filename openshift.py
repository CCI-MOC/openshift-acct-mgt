import kubernetes
import pprint
import logging
import requests
import json
import re
from flask import Flask, redirect, url_for, request, Response

import sys

# application = Flask(__name__)


class openshift:
    headers = None
    verify = False
    url = None

    def __init__(self, url, token, logger):
        self.set_token(token)
        self.set_url(url)
        self.logger = logger

    def set_token(self, token):
        self.headers = {
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def set_url(self, url):
        self.url = url

    def get_url(self):
        return self.url

    def cnvt_project_name(self, project_name):
        suggested_project_name = re.sub("^[^A-Za-z0-9]+", "", project_name)
        suggested_project_name = re.sub("[^A-Za-z0-9]+$", "", suggested_project_name)
        suggested_project_name = re.sub("[^A-Za-z0-9\-]+", "-", suggested_project_name)
        return suggested_project_name

    def get_request(self, url, debug=False):
        r = requests.get(url, headers=self.headers, verify=self.verify)
        if debug == True:
            self.logger.info("url: " + url)
            self.logger.info("g: " + str(r.status_code))
            self.logger.info("g: " + r.text)
        return r

    def del_request(self, url, payload, debug=False):
        if payload is None:
            r = requests.delete(url, headers=self.headers, verify=self.verify)
        else:
            r = requests.delete(
                url, headers=self.headers, data=json.dumps(payload), verify=self.verify
            )
        if debug == True:
            self.logger.info("url: " + url)
            if payload is not None:
                self.logger.info("payload:" + json.dumps(payload))
            self.logger.info("d: " + str(r.status_code))
            self.logger.info("d: " + r.text)
        return r

    def put_request(self, url, payload, debug=False):
        if payload is None:
            r = requests.put(url, headers=self.headers, verify=self.verify)
        else:
            r = requests.put(
                url, headers=self.headers, data=json.dumps(payload), verify=self.verify
            )
        if debug == True:
            self.logger.info("url: " + url)
            if payload is not None:
                self.logger.info("payload:" + json.dumps(payload))
            self.logger.info("pu: " + str(r.status_code))
            self.logger.info("pu: " + r.text)
        return r

    def post_request(self, url, payload, debug=False):
        r = requests.post(
            url, headers=self.headers, data=json.dumps(payload), verify=False
        )
        if debug == True:
            self.logger.info("url: " + url)
            self.logger.info("payload: " + json.dumps(payload))
            self.logger.info("po: " + str(r.status_code))
            self.logger.info("po: " + r.text)
        return r

    def user_rolebinding_exists(self, user, project_name, role):
        openshift_role = ""

        if role == "admin":
            openshift_role = "admin"
        elif role == "member":
            openshift_role = "edit"
        elif role == "reader":
            openshift_role = "view"
        else:
            return False

        r = self.get_rolebindings(project_name, openshift_role)
        if r.status_code == 200 or r.status_code == 201:
            role_binding = r.json()
            pprint.pprint(role_binding)
            if (
                "userNames" in role_binding.keys()
                and role_binding["userNames"] is not None
                and user in role_binding["userNames"]
            ):
                return True
        return False

    def get_all_moc_rolebindings(self, user, project_name):
        rolebindings = []
        for role in ["admin", "member", "view"]:
            if self.user_rolebinding_exists(user, project_name, role):
                role_bindings.push(role)
        if role_bindings.size() > 0:
            return Response(
                response=json.dumps(
                    {"msg": "role found", "rolebindings": rolebindings}
                ),
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps({"msg": "roles not found"}),
            status=404,
            mimetype="application/json",
        )

    def update_user_role_project(self, project_name, user, role, op):
        # The REST API 'create rolebindings' doesn't work the way that 'oc create rolebindings'
        # with the REST API,
        #     GET can be used to get the specific role from the project (or all roles)
        #     POST the role is bound to the project (and users)
        #     PUT is used to modify the rolebindings (add users or groups to the role)
        #     DELETE is used to remove the role (and all users) from the project
        #
        # Don't do anything incorrectly as the error messages are generic enough to be meaningless
        #
        # First check to see if there is a rolebinding on the project
        if op not in ["add", "del"]:
            return Response(
                response=json.dumps({"msg": "op is not in ('add' or 'del')"}),
                status=400,
                mimetype="application/json",
            )
        # add_openshift_role(token,self.get_url(),project_name, role)

        openshift_role = None
        if role == "admin":
            openshift_role = "admin"
        elif role == "member":
            openshift_role = "edit"
        elif role == "reader":
            openshift_role = "view"
        else:
            return Response(
                response=json.dumps(
                    {
                        "msg": "Error: Invalid role,  "
                        + role
                        + " is not one of 'admin', 'member' or 'reader'"
                    }
                ),
                status=400,
                mimetype="application/json",
            )

        r = self.get_rolebindings(project_name, openshift_role)
        # print("A: result: "+r.text)
        if not (r.status_code == 200 or r.status_code == 201):
            # try to create the roles for binding
            r = self.create_rolebindings(project_name, user, openshift_role)
            if r.status_code == 200 or r.status_code == 201:
                return Response(
                    response=json.dumps(
                        {
                            "msg": "rolebinding created ("
                            + user
                            + ","
                            + project_name
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
                        "msg": " unable to create rolebinding ("
                        + user
                        + ","
                        + project_name
                        + ","
                        + role
                        + ")"
                        + r.text
                    }
                ),
                status=400,
                mimetype="application/json",
            )

        # print("B: result: "+r.text)
        if r.status_code == 200 or r.status_code == 201:
            role_binding = r.json()
            if op == "add":
                self.logger.debug("role_binding: " + json.dumps(role_binding))
                self.logger.debug(
                    "role_binding['userNames']=" + str(role_binding["userNames"])
                )
                if role_binding["userNames"] is None:
                    role_binding["userNames"] = [user]
                else:
                    if user in role_binding["userNames"]:
                        return Response(
                            response=json.dumps(
                                {
                                    "msg": "rolebinding already exists - unable to add ("
                                    + user
                                    + ","
                                    + project_name
                                    + ","
                                    + role
                                    + ")"
                                }
                            ),
                            status=400,
                            mimetype="application/json",
                        )
                    role_binding["userNames"].append(user)
            elif op == "del":
                if (role_binding["userNames"] is None) or (
                    user not in role_binding["userNames"]
                ):
                    return Response(
                        response=json.dumps(
                            {
                                "msg": "rolebinding does not exist - unable to delete ("
                                + user
                                + ","
                                + project_name
                                + ","
                                + role
                                + ")"
                            }
                        ),
                        status=400,
                        mimetype="application/json",
                    )
                role_binding["userNames"].remove(user)
            else:
                return Response(
                    response=json.dumps(
                        {
                            "msg": "Invalid request ("
                            + user
                            + ","
                            + project_name
                            + ","
                            + role
                            + ","
                            + op
                            + ")"
                        }
                    ),
                    status=400,
                    mimetype="application/json",
                )

            # now add or remove the user
            r = self.update_rolebindings(project_name, openshift_role, role_binding)

            msg = "unknown message"
            if r.status_code == 200 or r.status_code == 201:
                if op == "add":
                    msg = "Added role to user on project"
                elif op == "del":
                    msg = "removed role from user on project"
                return Response(
                    response=json.dumps({"msg": msg}),
                    status=200,
                    mimetype="application/json",
                )
            if op == "add":
                msg = "unable to add role to user on project"
            elif op == "del":
                msg = "unable to remove role from user on project"
            return Response(
                response=json.dumps({"msg": msg}),
                status=400,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps(
                {
                    "msg": "rolebinding already exists ("
                    + user
                    + ","
                    + project_name
                    + ","
                    + role
                    + ")"
                }
            ),
            status=400,
            mimetype="application/json",
        )


class openshift_3_x(openshift):

    # member functions for projects
    def project_exists(self, project_name):
        url = "https://" + self.get_url() + "/oapi/v1/projects/" + project_name
        r = self.get_request(url, True)
        if r.status_code == 200 or r.status_code == 201:
            return True
        return False

    def create_project(self, project_name, display_name, user_name):
        # check project_name
        url = "https://" + self.get_url() + "/oapi/v1/projects"
        payload = {
            "kind": "Project",
            "apiVersion": "v1",
            "metadata": {
                "name": project_name,
                "annotations": {
                    "openshift.io/display-name": display_name,
                    "openshift.io/requester": user_name,
                },
            },
        }
        r = self.post_request(url, payload, True)
        return r

    def delete_project(self, project_name):
        # check project_name
        url = "https://" + self.get_url() + "/oapi/v1/projects/" + project_name
        r = self.del_request(url, True)
        return r

    # member functions for users
    def user_exists(self, user_name):
        url = "https://" + self.get_url() + "/oapi/v1/users/" + user_name
        r = self.get_request(url, True)
        if r.status_code == 200 or r.status_code == 201:
            return True
        return False

    def create_user(self, user_name, full_name):
        url = "https://" + self.get_url() + "/oapi/v1/users"
        payload = {
            "kind": "User",
            "apiVersion": "v1",
            "metadata": {"name": user_name},
            "fullName": full_name,
        }
        r = self.post_request(url, payload, True)
        return r

    def delete_user(self, user_name, full_name):
        url = "https://" + self.get_url() + "/oapi/v1/users/" + user_name
        r = self.del_request(url, None, True)
        return r

    # member functions for identities
    def identity_exists(self, id_provider, id_user):
        url = (
            "https://"
            + self.get_url()
            + "/oapi/v1/identities/"
            + id_provider
            + ":"
            + id_user
        )
        r = self.get_request(url, True)
        if r.status_code == 200 or r.status_code == 201:
            return True
        return False

    def create_identity(self, id_provider, id_user):
        url = "https://" + self.get_url() + "/oapi/v1/identities"
        payload = {
            "kind": "Identity",
            "apiVersion": "v1",
            "providerName": id_provider,
            "providerUserName": id_user,
        }
        r = self.post_request(url, payload, True)
        return r

    def delete_identity(self, id_provider, id_user):
        url = "https://" + self.get_url() + "/oapi/v1/identities"
        payload = {
            "kind": "DeleteOptions",
            "apiVersion": "v1",
            "providerName": id_provider,
            "providerUserName": id_user,
            "gracePeriodSeconds": 300,
        }
        r = self.del_request(url, payload, True)
        return r

    def useridentitymapping_exists(self, user_name, id_provider, id_user):
        url = (
            "https://"
            + self.get_url()
            + "/oapi/v1/useridentitymappings/"
            + id_provider
            + ":"
            + id_user
        )
        r = self.get_request(url, True)
        # it is probably not necessary to check the user name in the useridentity
        # mapping
        if r.status_code == 200 or r.status_code == 201:
            return True
        return False

    def create_useridentitymapping(self, user_name, id_provider, id_user):
        url = "https://" + self.get_url() + "/oapi/v1/useridentitymappings"
        payload = {
            "kind": "UserIdentityMapping",
            "apiVersion": "v1",
            "user": {"name": user_name},
            "identity": {"name": id_provider + ":" + id_user},
        }
        r = self.post_request(url, payload, True)
        return r

    # member functions to associate roles for users on projects
    # To check if a particular user has a rolebinding, get the complete
    # list of users that have that particular role on the project and
    # see if the user_name is in that list.
    #
    # This just returns the list
    def get_rolebindings(self, project_name, role):
        url = (
            "https://"
            + self.get_url()
            + "/oapi/v1/namespaces/"
            + project_name
            + "/rolebindings/"
            + role
        )
        r = self.get_request(url, True)
        self.logger.warning("get rolebindings: " + r.text)
        return r

    def list_rolebindings(self, project_name):
        url = (
            "https://"
            + self.get_url()
            + "/oapi/v1/namespaces/"
            + project_name
            + "/rolebindings"
        )
        r = self.get_request(url, True)
        return r

    def delete_rolebindings(self, project_name, user_name, role):
        payload = {
            "kind": "DeleteOptions",
            "apiVersion": "v1",
            "gracePeriodSeconds": "300",
        }
        r = self.del_request(url, payload, True)
        return r

    def create_rolebindings(self, project_name, user_name, role):
        url = (
            "https://"
            + self.get_url()
            + "/oapi/v1/namespaces/"
            + project_name
            + "/rolebindings"
        )  # /' + role
        payload = {
            "kind": "RoleBinding",
            "apiVersion": "v1",
            "metadata": {"name": role, "namespace": project_name},
            "groupNames": None,
            "userNames": [user_name],
            "roleRef": {"name": role},
        }
        r = self.post_request(url, payload, True)
        return r

    def update_rolebindings(self, project_name, role, rolebindings_json):
        url = (
            "https://"
            + self.get_url()
            + "/oapi/v1/namespaces/"
            + project_name
            + "/rolebindings/"
            + role
        )
        # need to eliminate some fields that might be there
        payload = {}
        for key in rolebindings_json:
            if key in ["kind", "apiVersion", "userNames", "groupNames", "roleRef"]:
                payload[key] = rolebindings_json[key]
        payload["metadata"] = {}
        self.logger.debug("payload -> 1: " + json.dumps(payload))
        for key in rolebindings_json["metadata"]:
            if key in ["name", "namespace"]:
                payload["metadata"][key] = rolebindings_json["metadata"][key]
        self.logger.debug("payload -> 2: " + json.dumps(payload))
        r = self.put_request(url, payload, True)
        return r


class openshift_4_x(openshift):

    # member functions for projects
    def project_exists(self, project_name):
        url = (
            "https://"
            + self.get_url()
            + "/apis/project.openshift.io/v1/projects/"
            + project_name
        )
        r = self.get_request(url, True)
        if r.status_code == 200 or r.status_code == 201:
            return True
        return False

    def create_project(self, project_name, display_name, user_name):
        # check project_name
        url = "https://" + self.get_url() + "/apis/project.openshift.io/v1/projects/"
        payload = {
            "kind": "Project",
            "apiVersion": "project.openshift.io/v1",
            "metadata": {
                "name": project_name,
                "annotations": {
                    "openshift.io/display-name": display_name,
                    "openshift.io/requester": user_name,
                },
            },
        }
        r = self.post_request(url, payload, True)
        return r

    def delete_project(self, project_name):
        # check project_name
        url = (
            "https://"
            + self.get_url()
            + "/apis/project.openshift.io/v1/projects/"
            + project_name
        )
        r = self.del_request(url, None, True)
        return r

    # member functions for users
    def user_exists(self, user_name):
        url = (
            "https://"
            + self.get_url()
            + "/apis/user.openshift.io/v1/users/"
            + user_name
        )
        r = self.get_request(url, True)
        if r.status_code == 200 or r.status_code == 201:
            return True
        return False

    def create_user(self, user_name, full_name):
        url = "https://" + self.get_url() + "/apis/user.openshift.io/v1/users"
        payload = {
            "kind": "User",
            "apiVersion": "user.openshift.io/v1",
            "metadata": {"name": user_name},
            "fullName": full_name,
        }
        r = self.post_request(url, payload, True)
        return r

    def delete_user(self, user_name):
        url = (
            "https://"
            + self.get_url()
            + "/apis/user.openshift.io/v1/users/"
            + user_name
        )
        r = self.del_request(url, None, True)
        return r

    # member functions for identities
    def identity_exists(self, id_provider, id_user):
        url = (
            "https://"
            + self.get_url()
            + "/apis/user.openshift.io/v1/identities/"
            + id_provider
            + ":"
            + id_user
        )
        r = self.get_request(url, True)
        if r.status_code == 200 or r.status_code == 201:
            return True
        return False

    def create_identity(self, id_provider, id_user):
        url = "https://" + self.get_url() + "/apis/user.openshift.io/v1/identities"
        payload = {
            "kind": "Identity",
            "apiVersion": "user.openshift.io/v1",
            "providerName": id_provider,
            "providerUserName": id_user,
        }
        r = self.post_request(url, payload, True)
        return r

    def delete_identity(self, id_provider, id_user):
        url = (
            "https://"
            + self.get_url()
            + "/apis/user.openshift.io/v1/identities/"
            + id_provider
            + ":"
            + id_user
        )
        payload = {
            "kind": "DeleteOptions",
            "apiVersion": "user.openshift.io/v1",
            "providerName": id_provider,
            "providerUserName": id_user,
            "gracePeriodSeconds": 300,
        }
        r = self.del_request(url, payload, True)
        return r

    def useridentitymapping_exists(self, user_name, id_provider, id_user):
        url = (
            "https://"
            + self.get_url()
            + "/apis/user.openshift.io/v1/useridentitymappings/"
            + id_provider
            + ":"
            + id_user
        )
        r = self.get_request(url, True)
        # it is probably not necessary to check the user name in the useridentity
        # mapping
        if r.status_code == 200 or r.status_code == 201:
            return True
        return False

    def create_useridentitymapping(self, user_name, id_provider, id_user):
        url = (
            "https://"
            + self.get_url()
            + "/apis/user.openshift.io/v1/useridentitymappings"
        )
        payload = {
            "kind": "UserIdentityMapping",
            "apiVersion": "user.openshift.io/v1",
            "user": {"name": user_name},
            "identity": {"name": id_provider + ":" + id_user},
        }
        r = self.post_request(url, payload, True)
        return r

    # member functions to associate roles for users on projects
    def get_rolebindings(self, project_name, role):
        url = (
            "https://"
            + self.get_url()
            + "/apis/authorization.openshift.io/v1/namespaces/"
            + project_name
            + "/rolebindings/"
            + role
        )
        r = self.get_request(url, True)
        self.logger.warning("get rolebindings: " + r.text)
        return r

    def list_rolebindings(self, project_name):
        url = (
            "https://"
            + self.get_url()
            + "/apis/authorization.openshift.io/v1/namespaces/"
            + project_name
            + "/rolebindings"
        )
        r = self.get_request(url, True)
        return r

    def delete_rolebindings(self, project_name, user_name, role):
        payload = {
            "kind": "DeleteOptions",
            "apiVersion": "authorization.openshift.io/v1",
            "gracePeriodSeconds": "300",
        }
        r = self.del_request(url, payload, True)
        return r

    def create_rolebindings(self, project_name, user_name, role):
        url = (
            "https://"
            + self.get_url()
            + "/apis/authorization.openshift.io/v1/namespaces/"
            + project_name
            + "/rolebindings"
        )  # /' + role
        payload = {
            "kind": "RoleBinding",
            "apiVersion": "authorization.openshift.io/v1",
            "metadata": {"name": role, "namespace": project_name},
            "groupNames": None,
            "userNames": [user_name],
            "roleRef": {"name": role},
        }
        r = self.post_request(url, payload, True)
        return r

    def update_rolebindings(self, project_name, role, rolebindings_json):
        url = (
            "https://"
            + self.get_url()
            + "/apis/authorization.openshift.io/v1/namespaces/"
            + project_name
            + "/rolebindings/"
            + role
        )
        # need to eliminate some fields that might be there
        payload = {}
        for key in rolebindings_json:
            if key in ["kind", "apiVersion", "userNames", "groupNames", "roleRef"]:
                payload[key] = rolebindings_json[key]
        payload["metadata"] = {}
        self.logger.debug("payload -> 1: " + json.dumps(payload))
        for key in rolebindings_json["metadata"]:
            if key in ["name", "namespace"]:
                payload["metadata"][key] = rolebindings_json["metadata"][key]
        self.logger.debug("payload -> 2: " + json.dumps(payload))
        r = self.put_request(url, payload, True)
        return r
