"""API wrapper for interacting with OpenShift authorization"""
# pylint: disable=too-many-public-methods
import abc
import pprint
import json
import re
import time

from flask import Response

from . import exceptions

OPENSHIFT_ROLES = ["admin", "edit", "view"]


class MocOpenShift(metaclass=abc.ABCMeta):
    """API wrapper interface"""

    @abc.abstractmethod
    def get_user(self, user_name):
        return

    @abc.abstractmethod
    def get_rolebindings(self, project_name, role):
        return

    @abc.abstractmethod
    def create_rolebindings(self, project_name, user_name, role):
        return

    @abc.abstractmethod
    def update_rolebindings(self, project_name, role, rolebindings_json):
        return

    @abc.abstractmethod
    def delete_moc_quota(self, project_name):
        return

    @abc.abstractmethod
    def create_shift_quotas(self, project_name, quota_spec):
        return

    @staticmethod
    def split_quota_name(moc_quota_name):
        name_array = moc_quota_name.split(":")
        if len(name_array[0]) == 0:
            scope = "Project"
        else:
            scope = name_array[0]
        quota_name = name_array[1]
        return (scope, quota_name)

    def __init__(self, client, app):
        self.client = client
        self.app = app
        self.logger = app.logger
        self.id_provider = app.config["IDENTITY_PROVIDER"]
        self.quotafile = app.config["QUOTA_DEF_FILE"]

    @staticmethod
    def cnvt_project_name(project_name):
        suggested_project_name = re.sub("^[^A-Za-z0-9]+", "", project_name)
        suggested_project_name = re.sub("[^A-Za-z0-9]+$", "", suggested_project_name)
        suggested_project_name = re.sub("[^A-Za-z0-9-]+", "-", suggested_project_name)
        return suggested_project_name

    def user_exists(self, user_name):
        result = self.get_user(user_name)
        if result.status_code in (200, 201):
            return True
        return False

    def useridentitymapping_exists(self, user_name, id_user):
        user = self.get_user(user_name)
        id_provider = self.id_provider
        if not (user.status_code in (200, 201)) and user["identities"]:
            id_str = f"{id_provider}:{id_user}"
            for identity in user["identities"]:
                if identity == id_str:
                    return True
        return False

    def user_rolebinding_exists(self, user_name, project_name, role):
        if role not in OPENSHIFT_ROLES:
            return False

        result = self.get_rolebindings(project_name, role)
        if result.status_code in (200, 201):
            role_binding = result.json()
            self.logger.info(f"rolebinding result:\n{pprint.pformat(role_binding)}")
            users_in_role = [
                u["name"]
                for u in role_binding.get("subjects", {})
                if u["kind"] == "User"
            ]
            return user_name in users_in_role
        return False

    def get_all_moc_rolebindings(self, user, project_name):
        role_bindings = []
        for role in OPENSHIFT_ROLES:
            if self.user_rolebinding_exists(user, project_name, role):
                role_bindings.append(role)
        if role_bindings:
            return Response(
                response=json.dumps(
                    {"msg": "role found", "rolebindings": role_bindings}
                ),
                status=200,
                mimetype="application/json",
            )
        return Response(
            response=json.dumps({"msg": "roles not found"}),
            status=404,
            mimetype="application/json",
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
            result = self.update_rolebindings(project_name, role, role_binding)

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
            f"New Quota for project {project_name}: {pprint.pformat(new_quota)}"
        )

        delete_resp = self.delete_moc_quota(project_name)
        if delete_resp.status_code not in [200, 201]:
            return Response(
                response="Unable to delete current quotas in {project_name}\n {delete_resp.status}",
                status=delete_resp.status_code,
                mimetype="application/json",
            )
        create_resp = self.create_shift_quotas(project_name, quota_def)
        if create_resp.status_code not in [200, 201]:
            return Response(
                response="Unable to define Quotas",
                status=400,
                mimetype="application/json",
            )
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

    @abc.abstractmethod
    def get_resourcequota_details(self, project_name) -> dict:
        pass

    @abc.abstractmethod
    def get_moc_quota_from_resourcequotas(self, project_name) -> dict:
        pass


class MocOpenShift4x(MocOpenShift):
    """API implementation for OpenShift 4.x"""

    # member functions for projects
    def project_exists(self, project_name):
        url = f"/apis/project.openshift.io/v1/projects/{project_name}"
        result = self.client.get(url)
        if result.status_code in (200, 201):
            return True
        return False

    def create_project(self, project_name, display_name, user_name, annotations=None):
        # check project_name
        if annotations is None:
            annotations = {}
        else:
            annotations = dict(annotations)
        url = "/apis/project.openshift.io/v1/projects/"
        annotations["openshift.io/display-name"] = display_name
        annotations["openshift.io/requester"] = user_name
        payload = {
            "kind": "Project",
            "apiVersion": "project.openshift.io/v1",
            "metadata": {"name": project_name, "annotations": annotations},
        }
        r = self.client.post(url, json=payload)
        if r.status_code not in [200, 201]:
            raise exceptions.ApiException(f"unable to create project ({project_name})")
        return r

    def delete_project(self, project_name):
        # check project_name
        url = f"/apis/project.openshift.io/v1/projects/{project_name}"
        return self.client.delete(url)

    def get_user(self, user_name):
        url = f"/apis/user.openshift.io/v1/users/{user_name}"
        return self.client.get(url)

    # member functions for users
    def create_user(self, user_name, full_name):
        url = "/apis/user.openshift.io/v1/users"
        payload = {
            "kind": "User",
            "apiVersion": "user.openshift.io/v1",
            "metadata": {"name": user_name},
            "fullName": full_name,
        }
        return self.client.post(url, json=payload)

    def delete_user(self, user_name):
        url = f"/apis/user.openshift.io/v1/users/{user_name}"
        return self.client.delete(url)

    # member functions for identities
    def identity_exists(self, id_user):
        url = f"/apis/user.openshift.io/v1/identities/{self.id_provider}:{id_user}"
        result = self.client.get(url)
        if result.status_code in (200, 201):
            return True
        return False

    def create_identity(self, id_user):
        url = "/apis/user.openshift.io/v1/identities"
        payload = {
            "kind": "Identity",
            "apiVersion": "user.openshift.io/v1",
            "providerName": self.id_provider,
            "providerUserName": id_user,
        }
        return self.client.post(url, json=payload)

    def delete_identity(self, id_user):
        url = f"/apis/user.openshift.io/v1/identities/{self.id_provider}:{id_user}"
        return self.client.delete(url)

    def create_useridentitymapping(self, user_name, id_user):
        url = "/apis/user.openshift.io/v1/useridentitymappings"
        payload = {
            "kind": "UserIdentityMapping",
            "apiVersion": "user.openshift.io/v1",
            "user": {"name": user_name},
            "identity": {"name": self.id_provider + ":" + id_user},
        }
        return self.client.post(url, json=payload)

    # member functions to associate roles for users on projects
    def get_rolebindings(self, project_name, role):
        url = f"/apis/rbac.authorization.k8s.io/v1/namespaces/{project_name}/rolebindings/{role}"
        result = self.client.get(url)
        self.logger.warning("get rolebindings: " + result.text)
        return result

    def list_rolebindings(self, project_name):
        url = (
            f"/apis/rbac.authorization.k8s.io/v1/namespaces/{project_name}/rolebindings"
        )
        result = self.client.get(url)
        return result

    def create_rolebindings(self, project_name, user_name, role):
        url = (
            f"/apis/rbac.authorization.k8s.io/v1/namespaces/{project_name}/rolebindings"
        )
        payload = {
            "kind": "RoleBinding",
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "metadata": {"name": role, "namespace": project_name},
            "subjects": [{"name": user_name, "kind": "User"}],
            "roleRef": {"name": role, "kind": "ClusterRole"},
        }
        return self.client.post(url, json=payload)

    def update_rolebindings(self, project_name, role, rolebindings_json):
        url = f"/apis/rbac.authorization.k8s.io/v1/namespaces/{project_name}/rolebindings/{role}"
        # need to eliminate some fields that might be there
        payload = {}
        for key in rolebindings_json:
            if key in ["kind", "apiVersion", "subjects", "roleRef"]:
                payload[key] = rolebindings_json[key]
        payload["metadata"] = {}
        self.logger.debug("payload -> 1: " + json.dumps(payload))
        for key in rolebindings_json["metadata"]:
            if key in ["name", "namespace"]:
                payload["metadata"][key] = rolebindings_json["metadata"][key]
        self.logger.debug("payload -> 2: " + json.dumps(payload))
        return self.client.put(url, json=payload)

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

    def wait_for_quota_to_settle(self, project_name, resource_quota_json):
        """Wait for quota on resourcequotas to settle.

        When creating a new resourcequota that sets a quota on resourcequota objects, we need to
        wait for OpenShift to calculate the quota usage before we attempt to create any new
        resourcequota objects.
        """

        if "resourcequotas" in resource_quota_json["spec"]["hard"]:
            self.logger.info("waiting for resourcequota quota")
            url = f"/api/v1/namespaces/{project_name}/resourcequotas/{resource_quota_json['metadata']['name']}"
            while True:
                resp = self.client.get(url)
                if "resourcequotas" in resp.json()["status"].get("used", {}):
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
        # create the openshift quota resources
        quota_create_status_code = 200
        quota_create_msg = ""
        for scope, quota_item in quota_def.items():
            resource_quota_json = {
                "apiVersion": "v1",
                "kind": "ResourceQuota",
                "metadata": {"name": f"{project_name.lower()}-{scope.lower()}"},
                "spec": {"hard": {}},
            }
            if scope != "Project":
                resource_quota_json["spec"]["scopes"] = [scope]
            non_null_quota_count = 0
            for quota_name in quota_item:
                if quota_item[quota_name]["value"] is not None:
                    non_null_quota_count += 1
                    resource_quota_json["spec"]["hard"][quota_name] = quota_item[
                        quota_name
                    ]["value"]
            if non_null_quota_count > 0:
                url = f"/api/v1/namespaces/{project_name}/resourcequotas"
                resp = self.client.post(url, json=resource_quota_json)
                # This colapses 5 error codes to the most sever error and just contcatenates the 5 messages
                if resp.status_code in [200, 201]:
                    self.wait_for_quota_to_settle(project_name, resource_quota_json)
                    quota_create_msg = f"{quota_create_msg} Quota {project_name}/{quota_name} successfully created\n"
                else:
                    if resp.status_code > quota_create_status_code:
                        quota_create_status_code = resp.status_code
                    self.logger.error(
                        f"Quota creation for {project_name} with error: {str(resp.json())}"
                    )
                    quota_create_msg = f"{quota_create_msg} Quota {project_name}/{quota_name} creation failed"
            # if the 5 calls were successful, we can be less verbose
            if quota_create_status_code in [200, 201]:
                quota_create_msg = f"All quota from {project_name} successfully created"
        return Response(
            response=quota_create_msg,
            status=quota_create_status_code,
            mimetype="application/json",
        )

    def get_resourcequotas(self, project_name) -> list:
        """Returns a dictionary of all of the resourcequota objects"""
        url = f"/api/v1/namespaces/{project_name}/resourcequotas"
        rq_data = self.client.get(url).json()
        self.logger.info(pprint.pformat(rq_data))
        rq_list = []
        for rq_name in rq_data["items"]:
            rq_list.append(rq_name["metadata"]["name"])
        return rq_list

    def delete_quota(self, project_name, resourcequota_name):
        """In an openshift namespace {project_name) delete a specified resourcequota"""
        url = f"/api/v1/namespaces/{project_name}/resourcequotas/{resourcequota_name}"
        return self.client.delete(url)

    def delete_moc_quota(self, project_name):
        """deletes all resourcequotas from an openshift project"""
        resourcequota_list = self.get_resourcequotas(project_name)
        delete_msg = ""
        delete_status_code = 200
        for resourcequota in resourcequota_list:
            resp = self.delete_quota(project_name, resourcequota)
            # This colapses 5 error codes to the most sever error and just contcatenates the 5 messages
            if resp.status_code in [200, 201]:
                delete_msg = f"{delete_msg} Quota {project_name}/{resourcequota} successfully deleted\n"
            else:
                if resp.status_code > delete_status_code:
                    delete_status_code = resp.status_code
                delete_msg = (
                    f"{delete_msg} Quota {project_name}/{resourcequota} deletion failed"
                )
        # if the 5 calls were successful, we can be less verbose
        if delete_status_code in [200, 201]:
            delete_msg = f"All quota from {project_name} successfully deleted"
        return Response(
            response=delete_msg,
            status=delete_status_code,
            mimetype="application/json",
        )

    def get_moc_quota_from_resourcequotas(self, project_name) -> dict:
        """This returns a dictionary suitable for merging in with the specification from Adjutant/ColdFront"""
        rq_data = self.get_resourcequota_details(project_name)
        # url = f"{self.get_url()}/api/v1/namespaces/{project_name}/resourcequotas"
        # rq_data = self.get_request(url, True)
        moc_quota = {}
        for rq_name, rq_spec in rq_data.items():
            self.logger.info(f"processing resourcequota: {project_name}:{rq_name}")
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
        self.logger.info("get moc_quota_from_resourceQuotas")
        self.logger.info(pprint.pformat(moc_quota))
        return moc_quota

    def get_resourcequota_details(self, project_name) -> dict:
        """Returns a list of resourcequota names in the spcified project"""
        url = f"/api/v1/namespaces/{project_name}/resourcequotas"
        rq_data = self.client.get(url).json()
        self.logger.info(f"get_resourcequota_details: {pprint.pformat(rq_data)}")

        rq_dict = {}
        if rq_data["kind"] == "ResourceQuotaList":
            for rq_info in rq_data["items"]:
                rq_dict[rq_info["metadata"]["name"]] = rq_info["spec"]
        return rq_dict
