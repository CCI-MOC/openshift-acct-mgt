"""API wrapper for interacting with OpenShift authorization"""
import json
import re
import sys
import time

import kubernetes.dynamic.exceptions as kexc

from flask import Response

OPENSHIFT_ROLES = ["admin", "edit", "view"]

API_PROJECT = "project.openshift.io/v1"
API_USER = "user.openshift.io/v1"
API_RBAC = "rbac.authorization.k8s.io/v1"
API_CORE = "v1"

# pylint: disable=too-many-public-methods
class MocOpenShift4x:
    """API implementation for OpenShift 4.x"""

    @staticmethod
    def split_quota_name(moc_quota_name):
        name_array = moc_quota_name.split(":")
        if len(name_array[0]) == 0:
            scope = "Project"
        else:
            scope = name_array[0]
        quota_name = name_array[1]
        return (scope, quota_name)

    @staticmethod
    def cnvt_project_name(project_name):
        suggested_project_name = re.sub("^[^A-Za-z0-9]+", "", project_name)
        suggested_project_name = re.sub("[^A-Za-z0-9]+$", "", suggested_project_name)
        suggested_project_name = re.sub("[^A-Za-z0-9-]+", "-", suggested_project_name)
        return suggested_project_name

    def __init__(self, client, logger, config):
        self.client = client
        self.logger = logger
        self.id_provider = config["IDENTITY_PROVIDER"]
        self.quotafile = config["QUOTA_DEF_FILE"]
        self.limitfile = config["LIMIT_DEF_FILE"]
        self.apis = {}

        if not self.limitfile:
            self.logger.error("No default limit file provided.")
            sys.exit(1)

    def get_resource_api(self, api_version: str, kind: str):
        """Either return the cached resource api from self.apis, or fetch a
        new one, store it in self.apis, and return it."""
        k = f"{api_version}:{kind}"
        api = self.apis.setdefault(
            k, self.client.resources.get(api_version=api_version, kind=kind)
        )
        return api

    def useridentitymapping_exists(self, user_name, id_user):
        try:
            user = self.get_user(user_name)
        except kexc.NotFoundError:
            return False

        return any(
            identity == self.qualified_id_user(id_user)
            for identity in user.get("identities", [])
        )

    def user_rolebinding_exists(self, user_name, project_name, role):
        if role not in OPENSHIFT_ROLES:
            return False

        try:
            result = self.get_rolebindings(project_name, role)
        except kexc.NotFoundError:
            return False

        return any(
            (subject["kind"] == "User" and subject["name"] == user_name)
            for subject in result["subjects"]
        )

    def update_user_role_project(
        self, project_name, user, role, operation
    ):  # pylint: disable=too-many-return-statements,too-many-branches
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
        if operation not in ["add", "del"]:
            return Response(
                response=json.dumps({"msg": "operation is not in ('add' or 'del')"}),
                status=400,
                mimetype="application/json",
            )
        # add_openshift_role(token,self.get_url(),project_name, role)

        if role not in OPENSHIFT_ROLES:
            return Response(
                response=json.dumps(
                    {
                        "msg": f"Error: Invalid role, {role} is not one of 'admin', 'edit' or 'view'"
                    }
                ),
                status=400,
                mimetype="application/json",
            )

        result = self.get_rolebindings(project_name, role)
        if result.status_code not in (200, 201):
            if operation == "add":
                # try to create the roles for binding
                self.logger.info("Creating role bindings")
                result = self.create_rolebindings(project_name, user, role)
                if result.status_code in (200, 201):
                    return Response(
                        response=json.dumps(
                            {
                                "msg": f"rolebinding created ({user},{project_name},{role})"
                            }
                        ),
                        status=200,
                        mimetype="application/json",
                    )
                return Response(
                    response=json.dumps(
                        {
                            "msg": f"unable to create rolebinding ({user},{project_name},{role}){result.text}"
                        }
                    ),
                    status=400,
                    mimetype="application/json",
                )

            if operation == "del":
                # this is done for purely defensive reasons, shouldn't happen due to our current business
                self.logger.info(
                    "Warning: Attempt to delete from an newly created project - has the business logic changed"
                )
                return Response(
                    response=json.dumps(
                        {
                            "msg": f"unable to delete rolebinding ({user},{project_name},{role})"
                        }
                    ),
                    status=400,
                    mimetype="application/json",
                )

            # should never get here, but also done for purely defensive reasons
            self.logger.info("Error: unknown create operation")
            return Response(
                response=json.dumps(
                    {"msg": f"invalid request ({user},{project_name},{role})"}
                ),
                status=400,
                mimetype="application/json",
            )

        if result.status_code in (200, 201):
            role_binding = result.json()
            users_in_role = [
                u["name"]
                for u in role_binding.get("subjects", {})
                if u["kind"] == "User"
            ]

            if operation == "add":
                self.logger.debug("role_binding: " + json.dumps(role_binding))
                self.logger.debug(
                    "role_binding['subjects']=" + str(role_binding["subjects"])
                )
                if users_in_role is None:
                    role_binding["subjects"] = [{"user": user, "kind": "User"}]
                else:
                    if user in users_in_role:
                        return Response(
                            response=json.dumps(
                                {
                                    "msg": f"rolebinding already exists - unable to add ({user},{project_name},{role})"
                                }
                            ),
                            status=400,
                            mimetype="application/json",
                        )

                    users_in_role.append(user)
            elif operation == "del":
                if user not in users_in_role:
                    return Response(
                        response=json.dumps(
                            {
                                "msg": f"rolebinding does not exist - unable to delete ({user},{project_name},{role})"
                            }
                        ),
                        status=400,
                        mimetype="application/json",
                    )

                users_in_role.remove(user)
            else:
                self.logger.info("Error: unknown update operation")
                return Response(
                    response=json.dumps(
                        {
                            "msg": f"Invalid request ({user},{project_name},role,{operation})"
                        }
                    ),
                    status=400,
                    mimetype="application/json",
                )

            # now add or remove the user
            role_binding["subjects"] = [
                {"name": name, "kind": "User"} for name in users_in_role
            ]
            result = self.update_rolebindings(project_name, role_binding)

            msg = "unknown message"
            if result.status_code in (200, 201):
                if operation == "add":
                    msg = "Added role to user on project"
                elif operation == "del":
                    msg = "removed role from user on project"
                return Response(
                    response=json.dumps({"msg": msg}),
                    status=200,
                    mimetype="application/json",
                )
            if operation == "add":
                msg = "unable to add role to user on project"
            elif operation == "del":
                msg = "unable to remove role from user on project"
            return Response(
                response=json.dumps({"msg": msg}),
                status=400,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps(
                {"msg": f"rolebinding already exists ({user},{project_name},{role})"}
            ),
            status=400,
            mimetype="application/json",
        )

    def update_moc_quota(self, project_name, new_quota, patch=False):
        """This will update resourcequota objects in a project and create new ones based on the new_quota specification"""
        quota_def = self.get_quota_definitions()

        if patch:
            existing_quota = self.get_moc_quota_from_resourcequotas(project_name)
            for quota, value in existing_quota.items():
                quota_def[quota]["value"] = value

        for quota, value in new_quota["Quota"].items():
            quota_def[quota]["value"] = value

        self.logger.info(
            f"New Quota for project {project_name}: {json.dumps(new_quota, indent=2)}"
        )

        self.delete_moc_quota(project_name)
        self.create_shift_quotas(project_name, quota_def)

        return Response(
            response="MOC Quotas Updated",
            status=200,
            mimetype="application/json",
        )

    def get_quota_definitions(self):
        self.logger.info("reading quotas from %s", self.quotafile)
        with open(self.quotafile, "r") as file:
            quota = json.load(file)
        for k in quota:
            quota[k]["value"] = None

        return quota

    def get_limit_definitions(self):
        with open(self.limitfile, "r") as file:
            return json.load(file)

    def get_project(self, project_name):
        api = self.get_resource_api(API_PROJECT, "Project")
        return api.get(name=project_name).to_dict()

    def project_exists(self, project_name):
        try:
            self.get_project(project_name)
        except kexc.NotFoundError:
            return False
        return True

    def create_project(self, project_name, display_name, user_name, annotations=None):
        if annotations is None:
            annotations = {}
        else:
            annotations = dict(annotations)

        api = self.get_resource_api(API_PROJECT, "Project")

        annotations.update(
            {
                "openshift.io/display-name": display_name,
                "openshift.io/requester": user_name,
            }
        )
        labels = {
            "nerc.mghpcc.org/project": "true",
        }
        payload = {
            "metadata": {
                "name": project_name,
                "annotations": annotations,
                "labels": labels,
            },
        }
        res = api.create(body=payload).to_dict()
        self.create_limits(project_name)
        return res

    def delete_project(self, project_name):
        api = self.get_resource_api(API_PROJECT, "Project")
        return api.delete(name=project_name).to_dict()

    def get_user(self, user_name):
        api = self.get_resource_api(API_USER, "User")
        return api.get(name=user_name).to_dict()

    def user_exists(self, user_name):
        try:
            self.get_user(user_name)
        except kexc.NotFoundError:
            return False
        return True

    def create_user(self, user_name, full_name):
        api = self.get_resource_api(API_USER, "User")
        payload = {
            "metadata": {"name": user_name},
            "fullName": full_name,
        }
        return api.create(body=payload).to_dict()

    def delete_user(self, user_name):
        api = self.get_resource_api(API_USER, "User")
        return api.delete(name=user_name).to_dict()

    def qualified_id_user(self, id_user):
        return f"{self.id_provider}:{id_user}"

    def get_identity(self, id_user):
        api = self.get_resource_api(API_USER, "Identity")
        return api.get(name=self.qualified_id_user(id_user)).to_dict()

    def identity_exists(self, id_user):
        try:
            self.get_identity(id_user)
        except kexc.NotFoundError:
            return False
        return True

    def create_identity(self, id_user):
        api = self.get_resource_api(API_USER, "Identity")

        payload = {
            "providerName": self.id_provider,
            "providerUserName": id_user,
        }
        return api.create(body=payload).to_dict()

    def delete_identity(self, id_user):
        api = self.get_resource_api(API_USER, "Identity")
        return api.delete(name=self.qualified_id_user(id_user)).to_dict()

    def create_useridentitymapping(self, user_name, id_user):
        api = self.get_resource_api(API_USER, "UserIdentityMapping")
        payload = {
            "user": {"name": user_name},
            "identity": {"name": self.qualified_id_user(id_user)},
        }
        return api.create(body=payload).to_dict()

    # member functions to associate roles for users on projects
    def get_rolebindings(self, project_name, role):
        api = self.get_resource_api(API_RBAC, "RoleBinding")
        res = api.get(namespace=project_name, name=role).to_dict()

        # Ensure that rbd["subjects"] is a list (it can be None if the
        # rolebinding object had no subjects).
        if not res.get("subjects"):
            res["subjects"] = []

        return res

    def list_rolebindings(self, project_name):
        api = self.get_resource_api(API_RBAC, "RoleBinding")
        try:
            res = api.get(namespace=project_name).to_dict()
        except kexc.NotFoundError:
            return []

        return res["items"]

    def create_rolebindings(self, project_name, user_name, role):
        api = self.get_resource_api(API_RBAC, "RoleBinding")
        payload = {
            "metadata": {"name": role, "namespace": project_name},
            "subjects": [{"name": user_name, "kind": "User"}],
            "roleRef": {"name": role, "kind": "ClusterRole"},
        }
        return api.create(body=payload, namespace=project_name).to_dict()

    def update_rolebindings(self, project_name, rolebinding):
        api = self.get_resource_api(API_RBAC, "RoleBinding")
        return api.patch(body=rolebinding, namespace=project_name).to_dict()

    def get_moc_quota(self, project_name):
        quota_from_project = self.get_moc_quota_from_resourcequotas(project_name)

        quota = {}
        for quota_name, quota_value in quota_from_project.items():
            if quota_value:
                quota[quota_name] = quota_value

        quota_object = {
            "Version": "0.9",
            "Kind": "MocQuota",
            "ProjectName": project_name,
            "Quota": quota,
        }
        return quota_object

    def wait_for_quota_to_settle(self, project_name, resource_quota):
        """Wait for quota on resourcequotas to settle.

        When creating a new resourcequota that sets a quota on resourcequota objects, we need to
        wait for OpenShift to calculate the quota usage before we attempt to create any new
        resourcequota objects.
        """

        if "resourcequotas" in resource_quota["spec"]["hard"]:
            self.logger.info("waiting for resourcequota quota")

            api = self.get_resource_api(API_CORE, "ResourceQuota")
            while True:
                resp = api.get(
                    namespace=project_name, name=resource_quota["metadata"]["name"]
                ).to_dict()
                if "resourcequotas" in resp["status"].get("used", {}):
                    break
                time.sleep(0.1)

    def create_shift_quotas(self, project_name, quota_spec):
        quota_def = {}
        # separate the quota_spec by quota_scope
        for mangled_quota_name in quota_spec:
            (scope, quota_name) = self.split_quota_name(mangled_quota_name)
            if scope not in quota_def:
                quota_def[scope] = {}
            quota_def[scope][quota_name] = quota_spec[mangled_quota_name]

        for scope, quota_item in quota_def.items():
            resource_quota = {
                "metadata": {"name": f"{project_name.lower()}-{scope.lower()}"},
                "spec": {"hard": {}},
            }

            if scope != "Project":
                resource_quota["spec"]["scopes"] = [scope]

            resource_quota["spec"]["hard"] = {
                quota_name: quota_item[quota_name]["value"]
                for quota_name in quota_item
                if quota_item[quota_name]["value"] is not None
            }

            if resource_quota["spec"]["hard"]:
                api = self.get_resource_api(API_CORE, "ResourceQuota")
                res = api.create(namespace=project_name, body=resource_quota).to_dict()
                self.wait_for_quota_to_settle(project_name, res)

        return Response(
            response=json.dumps(
                {"msg": f"All quota from {project_name} successfully created"}
            ),
            status=200,
            mimetype="application/json",
        )

    def get_resourcequotas(self, project_name):
        """Returns a list of all of the resourcequota objects"""
        api = self.get_resource_api(API_CORE, "ResourceQuota")
        res = api.get(namespace=project_name).to_dict()

        return res["items"]

    def delete_resourcequota(self, project_name, resourcequota_name):
        """In an openshift namespace {project_name) delete a specified resourcequota"""
        api = self.get_resource_api(API_CORE, "ResourceQuota")
        return api.delete(namespace=project_name, name=resourcequota_name).to_dict()

    def delete_moc_quota(self, project_name):
        """deletes all resourcequotas from an openshift project"""
        resourcequotas = self.get_resourcequotas(project_name)
        for resourcequota in resourcequotas:
            self.delete_resourcequota(project_name, resourcequota["metadata"]["name"])

        return Response(
            response=json.dumps(
                {"msg": f"All quotas from {project_name} successfully deleted"}
            ),
            status=200,
            mimetype="application/json",
        )

    def get_moc_quota_from_resourcequotas(self, project_name):
        """This returns a dictionary suitable for merging in with the
        specification from Adjutant/ColdFront"""
        resourcequotas = self.get_resourcequotas(project_name)
        moc_quota = {}
        for rq in resourcequotas:
            rq_spec = rq["spec"]
            self.logger.info(
                f"processing resourcequota: {project_name}:{rq['metadata']['name']}"
            )
            scope_list = ["Project"]
            if "scopes" in rq_spec:
                scope_list = rq_spec["scopes"]
            if "hard" in rq_spec:
                for quota_name, quota_value in rq_spec["hard"].items():
                    for scope_item in scope_list:
                        if scope_item == "Project":
                            moc_quota_name = f":{quota_name}"
                        else:
                            moc_quota_name = f"{scope_item}:{quota_name}"
                        # Here we are just choosing an existing quota
                        # In the case of our service, there will be no conflicting
                        # quotas as it is setup by default.
                        if moc_quota_name not in moc_quota:
                            moc_quota[moc_quota_name] = quota_value
        return moc_quota

    def create_limits(self, project_name, limits=None):
        """
        project_name: project_name in which to create LimitRange
        limits: dictionary of limits to create, or None for default
        """
        api = self.get_resource_api(API_CORE, "LimitRange")

        payload = {
            "metadata": {"name": f"{project_name.lower()}-limits"},
            "spec": {"limits": limits or self.get_limit_definitions()},
        }
        return api.create(body=payload, namespace=project_name).to_dict()
