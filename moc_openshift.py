"""API wrapper for interacting with OpenShift authorization"""
# pylint: disable=too-many-public-methods
import abc
import pprint
import json
import re
import os
import time
import requests
from flask import Response


class MocOpenShift(metaclass=abc.ABCMeta):
    """API wrapper interface"""

    headers = None
    verify = False
    url = None

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

    @abc.abstractmethod
    def get_resourcequota_details(self, project_name) -> dict:
        return {}

    @staticmethod
    def get_identity_provider():
        return os.environ["ACCT_MGT_IDENTITY_PROVIDER"]

    @staticmethod
    def split_quota_name(moc_quota_name):
        name_array = moc_quota_name.split(":")
        if len(name_array[0]) == 0:
            scope = "Project"
        else:
            scope = name_array[0]
        quota_name = name_array[1]
        return (scope, quota_name)

    def __init__(self, url, token, logger):
        self.logger = logger
        self.set_token(token)
        self.set_url(url)

    def set_token(self, token):
        self.headers = {
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def set_url(self, url):
        if not url.startswith("http"):
            url = f"https://{url}"
        self.url = url

    def get_url(self):
        return self.url

    @staticmethod
    def cnvt_project_name(project_name):
        suggested_project_name = re.sub("^[^A-Za-z0-9]+", "", project_name)
        suggested_project_name = re.sub("[^A-Za-z0-9]+$", "", suggested_project_name)
        suggested_project_name = re.sub("[^A-Za-z0-9-]+", "-", suggested_project_name)
        return suggested_project_name

    def get_request(self, url, debug=False):
        if debug:
            self.logger.info(f"headers: {self.headers}")
            self.logger.info(f"url: {url}")
        result = requests.get(url, headers=self.headers, verify=self.verify)
        if debug:
            self.logger.info(f"g: {str(result.status_code)}")
            self.logger.info(f"g: {result.text}")
        return result

    def del_request(self, url, payload, debug=False):
        if payload is None:
            result = requests.delete(url, headers=self.headers, verify=self.verify)
        else:
            result = requests.delete(
                url, headers=self.headers, data=json.dumps(payload), verify=self.verify
            )
        if debug:
            self.logger.info("url: " + url)
            if payload is not None:
                self.logger.info(f"payload: {json.dumps(payload)}")
            self.logger.info(f"d: {str(result.status_code)}")
            self.logger.info(f"d: {result.text}")
        return result

    def put_request(self, url, payload, debug=False):
        if payload is None:
            result = requests.put(url, headers=self.headers, verify=self.verify)
        else:
            result = requests.put(
                url, headers=self.headers, data=json.dumps(payload), verify=self.verify
            )
        if debug:
            self.logger.info(f"url: {url}")
            if payload is not None:
                self.logger.info(f"payload: {json.dumps(payload)}")
            self.logger.info(f"pu: {str(result.status_code)}")
            self.logger.info(f"pu: {result.text}")
        return result

    def post_request(self, url, payload, debug=False):
        result = requests.post(
            url, headers=self.headers, data=json.dumps(payload), verify=False
        )
        if debug:
            self.logger.info(f"url: {url}")
            self.logger.info(f"payload: {json.dumps(payload)}")
            self.logger.info(f"po: {str(result.status_code)}")
            self.logger.info(f"po: {result.text}")
        return result

    def user_exists(self, user_name):
        result = self.get_user(user_name)
        if result.status_code in (200, 201):
            return True
        return False

    def useridentitymapping_exists(self, user_name, id_user):
        user = self.get_user(user_name)
        id_provider = self.get_identity_provider()
        if not (user.status_code in (200, 201)) and user["identities"]:
            id_str = f"{id_provider}:{id_user}"
            for identity in user["identities"]:
                if identity == id_str:
                    return True
        return False

    def user_rolebinding_exists(self, user_name, project_name, role):
        openshift_role = ""

        if role == "admin":
            openshift_role = "admin"
        elif role == "member":
            openshift_role = "edit"
        elif role == "reader":
            openshift_role = "view"
        else:
            return False

        result = self.get_rolebindings(project_name, openshift_role)
        if result.status_code in (200, 201):
            role_binding = result.json()
            self.logger.info(f"rolebinding result:\n{pprint.pformat(role_binding)}")
            if (
                "userNames" in role_binding.keys()
                and role_binding["userNames"] is not None
                and user_name in role_binding["userNames"]
            ):
                return True
        return False

    def get_all_moc_rolebindings(self, user, project_name):
        role_bindings = []
        for role in ["admin", "member", "reader"]:
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
                        "msg": f"Error: Invalid role, {role} is not one of 'admin', 'member' or 'reader'"
                    }
                ),
                status=400,
                mimetype="application/json",
            )

        result = self.get_rolebindings(project_name, openshift_role)
        if result.status_code not in (200, 201):
            if operation == "add":
                # try to create the roles for binding
                self.logger.info("Creating role bindings")
                result = self.create_rolebindings(project_name, user, openshift_role)
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
            if operation == "add":
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
                                    "msg": f"rolebinding already exists - unable to add ({user},{project_name},{role})"
                                }
                            ),
                            status=400,
                            mimetype="application/json",
                        )
                    role_binding["userNames"].append(user)
            elif operation == "del":
                if (role_binding["userNames"] is None) or (
                    user not in role_binding["userNames"]
                ):
                    return Response(
                        response=json.dumps(
                            {
                                "msg": f"rolebinding does not exist - unable to delete ({user},{project_name},{role})"
                            }
                        ),
                        status=400,
                        mimetype="application/json",
                    )
                role_binding["userNames"].remove(user)
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
            result = self.update_rolebindings(
                project_name, openshift_role, role_binding
            )

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

    def update_moc_quota(self, project_name, new_quota, replace=True):
        """This will delete all resourcequota objects in a project and create new ones based on the new_quota specification"""
        quota_def = self.get_quota_definitions()
        if "QuotaMultiplier" in new_quota["Quota"]:
            quota_multiplier = new_quota["Quota"]["QuotaMultiplier"]
            for quota in quota_def:
                quota_def[quota]["value"] = (
                    quota_def[quota]["coefficient"] * quota_multiplier
                    + quota_def[quota]["base"]
                )
                if "units" in quota_def[quota]:
                    quota_def[quota]["value"] = (
                        str(quota_def[quota]["value"]) + quota_def[quota]["units"]
                    )
        else:
            if replace is False:
                existing_quota = self.get_moc_quota_from_resourcequotas(project_name)
                pprint.pprint(existing_quota)
                for quota, value in existing_quota.items():
                    quota_def[quota]["value"] = value
            self.logger.info("new_quota")
            self.logger.info(pprint.pformat(new_quota))
            for quota, value in new_quota["Quota"].items():
                quota_def[quota]["value"] = value

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
            response="MOC Quotas Replaced",
            status=200,
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

    @staticmethod
    def get_quota_definitions():
        quota_def_file = os.getenv("ACCT_MGT_QUOTA_DEF_FILE")
        with open(quota_def_file, "r") as file:
            quota = json.loads(file.read())
        for k in quota:
            quota[k]["value"] = None
        return quota


class MocOpenShift4x(MocOpenShift):
    """API implementation for OpenShift 4.x"""

    # member functions for projects
    def project_exists(self, project_name):
        url = f"{self.get_url()}/apis/project.openshift.io/v1/projects/{project_name}"
        result = self.get_request(url, True)
        if result.status_code in (200, 201):
            return True
        return False

    def create_project(self, project_name, display_name, user_name):
        # check project_name
        url = f"{self.get_url()}/apis/project.openshift.io/v1/projects/"
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
        return self.post_request(url, payload, True)

    def delete_project(self, project_name):
        # check project_name
        url = f"{self.get_url()}/apis/project.openshift.io/v1/projects/{project_name}"
        return self.del_request(url, None, True)

    def get_user(self, user_name):
        url = f"{self.get_url()}/apis/user.openshift.io/v1/users/{user_name}"
        return self.get_request(url, True)

    # member functions for users
    def create_user(self, user_name, full_name):
        url = f"{self.get_url()}/apis/user.openshift.io/v1/users"
        payload = {
            "kind": "User",
            "apiVersion": "user.openshift.io/v1",
            "metadata": {"name": user_name},
            "fullName": full_name,
        }
        return self.post_request(url, payload, True)

    def delete_user(self, user_name):
        url = f"{self.get_url()}/apis/user.openshift.io/v1/users/{user_name}"
        return self.del_request(url, None, True)

    # member functions for identities
    def identity_exists(self, id_user):
        url = f"{self.get_url()}/apis/user.openshift.io/v1/identities/{self.get_identity_provider()}:{id_user}"
        result = self.get_request(url, True)
        if result.status_code in (200, 201):
            return True
        return False

    def create_identity(self, id_user):
        url = f"{self.get_url()}/apis/user.openshift.io/v1/identities"
        payload = {
            "kind": "Identity",
            "apiVersion": "user.openshift.io/v1",
            "providerName": self.get_identity_provider(),
            "providerUserName": id_user,
        }
        return self.post_request(url, payload, True)

    def delete_identity(self, id_user):
        url = f"{self.get_url()}/apis/user.openshift.io/v1/identities/{self.get_identity_provider()}:{id_user}"
        return self.del_request(url, None, True)

    def create_useridentitymapping(self, user_name, id_user):
        url = f"{self.get_url()}/apis/user.openshift.io/v1/useridentitymappings"
        payload = {
            "kind": "UserIdentityMapping",
            "apiVersion": "user.openshift.io/v1",
            "user": {"name": user_name},
            "identity": {"name": self.get_identity_provider() + ":" + id_user},
        }
        return self.post_request(url, payload, True)

    # member functions to associate roles for users on projects
    def get_rolebindings(self, project_name, role):
        url = f"{self.get_url()}/apis/authorization.openshift.io/v1/namespaces/{project_name}/rolebindings/{role}"
        result = self.get_request(url, True)
        self.logger.warning("get rolebindings: " + result.text)
        return result

    def list_rolebindings(self, project_name):
        url = f"{self.get_url()}/apis/authorization.openshift.io/v1/namespaces/{project_name}/rolebindings"
        result = self.get_request(url, True)
        return result

    def create_rolebindings(self, project_name, user_name, role):
        url = f"{self.get_url()}/apis/authorization.openshift.io/v1/namespaces/{project_name}/rolebindings"
        payload = {
            "kind": "RoleBinding",
            "apiVersion": "authorization.openshift.io/v1",
            "metadata": {"name": role, "namespace": project_name},
            "groupNames": None,
            "userNames": [user_name],
            "roleRef": {"name": role},
        }
        return self.post_request(url, payload, True)

    def update_rolebindings(self, project_name, role, rolebindings_json):
        url = f"{self.get_url()}/apis/authorization.openshift.io/v1/namespaces/{project_name}/rolebindings/{role}"
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
        return self.put_request(url, payload, True)

    def get_moc_quota(self, project_name):
        quota_def = self.get_quota_definitions()
        quota = {}
        for quota_name in quota_def:
            quota[quota_name] = quota_def[quota_name]["value"]
        quota_from_project = self.get_moc_quota_from_resourcequotas(project_name)
        for quota_name, quota_value in quota_from_project.items():
            quota[quota_name] = quota_value

        quota_object = {
            "Version": "0.9",
            "Kind": "MocQuota",
            "ProjectName": project_name,
            "Quota": quota,
        }
        return quota_object

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
                resource_quota_json["spec"]["scopes"] = []
                resource_quota_json["spec"]["scopes"].append(scope)
            non_null_quota_count = 0
            for quota_name in quota_item:
                if quota_item[quota_name]["value"] is not None:
                    non_null_quota_count += 1
                    resource_quota_json["spec"]["hard"][quota_name] = quota_item[
                        quota_name
                    ]["value"]
            if non_null_quota_count > 0:
                url = (
                    f"{self.get_url()}/api/v1/namespaces/{project_name}/resourcequotas"
                )
                resp = self.post_request(url, resource_quota_json, True)
                time.sleep(2)
                # This colapses 5 error codes to the most sever error and just contcatenates the 5 messages
                if resp.status_code in [200, 201]:
                    quota_create_msg = f"{quota_create_msg} Quota {project_name}/{quota_name} successfully created\n"
                else:
                    if resp.status_code > quota_create_status_code:
                        quota_create_status_code = resp.status_code
                    quota_create_msg = f"{quota_create_msg} Quota {project_name}/{quota_name} creation failed"
            # if the 5 calls were successful, we can be less verbose
            if quota_create_status_code in [200, 201]:
                quota_create_msg = f"All quota from {project_name} successfully created"
        return Response(
            response=quota_create_msg,
            status=quota_create_status_code,
            mimetype="application/json",
        )

    def get_resourcequota_details(self, project_name) -> dict:
        """Returns a list of resourcequota names in the spcified project"""
        url = f"{self.get_url()}/api/v1/namespaces/{project_name}/resourcequotas"
        rq_data = self.get_request(url, True).json()
        self.logger.info("get_resourcequota_details")
        self.logger.info(pprint.pformat(rq_data))
        rq_dict = {}
        if rq_data["kind"] == "ResourceQuotaList":
            for rq_info in rq_data["items"]:
                rq_dict[rq_info["metadata"]["name"]] = rq_info["spec"]
        return rq_dict

    def get_resourcequotas(self, project_name) -> list:
        """Returns a dictionary of all of the resourcequota objects"""
        url = f"{self.get_url()}/api/v1/namespaces/{project_name}/resourcequotas"
        rq_data = self.get_request(url, True).json()
        self.logger.info("get_resourcequotas")
        self.logger.info(pprint.pformat(rq_data))
        rq_list = []
        for rq_name in rq_data["items"]:
            rq_list.append(rq_name["metadata"]["name"])
        return rq_list

    def delete_resourcequota(self, project_name, resourcequota_name):
        """In an openshift namespace {project_name) delete a specified resourcequota"""
        url = f"{self.get_url()}/api/v1/namespaces/{project_name}/resourcequotas/{resourcequota_name}"
        return self.del_request(url, None, True)

    def delete_moc_quota(self, project_name):
        """deletes all resourcequotas from an openshift project"""
        resourcequota_list = self.get_resourcequotas(project_name)
        delete_msg = ""
        delete_status_code = 200
        for resourcequota in resourcequota_list:
            resp = self.delete_resourcequota(project_name, resourcequota)
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
