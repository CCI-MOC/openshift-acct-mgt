import pprint
import json
import re
import requests
import time
from flask import Response


class MocOpenShift:
    headers = None
    verify = False
    url = None

    def __init__(self, url, namespace, token, logger):
        self.set_token(token)
        self.set_url(url)
        self.set_namespace(namespace)
        self.logger = logger

    def set_token(self, token):
        self.headers = {
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def set_url(self, url):
        self.url = "https://" + url

    def set_namespace(self, namespace):
        self.namespace = namespace

    def get_url(self):
        return self.url

    def cnvt_project_name(self, project_name):
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
            self.logger.info(f"url: " + url)
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
        if result.status_code == 200 or result.status_code == 201:
            return True
        return False

    def useridentitymapping_exists(self, user_name, id_provider, id_user):
        user = self.get_user(user_name)
        if (
            not (user.status_code == 200 or user.status_code == 201)
            and user["identities"]
        ):
            id_str = "{}:{}".format(id_provider, id_user)
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
        if result.status_code == 200 or result.status_code == 201:
            role_binding = result.json()
            pprint.pprint(role_binding)
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

    def update_user_role_project(self, project_name, user, role, operation):
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
        if not (result.status_code == 200 or result.status_code == 201):
            if operation == "add":
                # try to create the roles for binding
                self.logger.info("Creating role bindings")
                result = self.create_rolebindings(project_name, user, openshift_role)
                if result.status_code == 200 or result.status_code == 201:
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
            elif operation == "del":
                # this is done for purely defensive reasons, shouldn't happen due to our current business
                self.logger.info(
                    "Warning: Attempt to delete from an newly created project - has the business logic changed"
                )
                return Response(
                    response=json.dumps(
                        {
                            "msg": f"unable to delete rolebinding ({user},{project_name},{role}){result.text}"
                        }
                    ),
                    status=400,
                    mimetype="application/json",
                )
            else:
                # should never get here, but also done for purely defensive reasons
                self.logger.info("Error: unknown create operation")
                return Response(
                    response=json.dumps(
                        {
                            "msg": f"invalid request ({user},{project_name},{role}){result.text}"
                        }
                    ),
                    status=400,
                    mimetype="application/json",
                )

        if result.status_code == 200 or result.status_code == 201:
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
            if result.status_code == 200 or result.status_code == 201:
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

    def generate_quota_name(project_name, scope):
        return f"{project_name}-{scope}"

    def convert_to_quota_def(self, moc_quota_list):
        quota_def = dict()
        for k in moc_quota_list["QuotaList"]:
            # for each quota spec in the quotalist sort it
            keylist = k.split(":")
            if keylist[0] not in quota_def.keys():
                quota_def[keylist[0]] = {}
            if keylist[1] not in quota_def[keylist[0]].keys():
                quota_def[keylist[0]][keylist[1]] = {}
            if keylist[2] not in quota_def[keylist[0]][keylist[1]].keys():
                quota_def[keylist[0]][keylist[1]][keylist[2]] = moc_quota_list[
                    "QuotaList"
                ][k]
        return quota_def

    def convert_to_moc_quota_list(self, project_name, quota_def):
        moc_quota_list = {"Project": project_name, "QuotaList": {}}
        for scope in quota_def.keys():
            for kind in quota_def[scope].keys():
                for quota_name in quota_def[scope][kind].keys():
                    moc_quota_item = {
                        f'"{scope}:{kind}:{quota_name}"': quota_def[scope][kind][
                            quota_name
                        ]
                    }
                    moc_quota_list["QuotaList"].append(moc_quota_item)
        return moc_quota_list


class MocOpenShift3x(MocOpenShift):

    # member functions for projects
    def project_exists(self, project_name):
        url = f"{self.get_url()}/oapi/v1/projects/{project_name}"
        result = self.get_request(url, True)
        if result.status_code == 200 or result.status_code == 201:
            return True
        return False

    def create_project(self, project_name, display_name, user_name):
        # check project_name
        url = f"{self.get_url()}/oapi/v1/projects"
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
        return self.post_request(url, payload, True)

    def delete_project(self, project_name):
        # check project_name
        url = f"{self.get_url()}/oapi/v1/projects/{project_name}"
        return self.del_request(url, True)

    def get_user(self, user_name):
        url = f"{self.get_url()}/oapi/v1/users/{user_name}"
        return self.get_request(url, True)

    # member functions for users
    def create_user(self, user_name, full_name):
        url = f"{self.get_url()}/oapi/v1/users"
        payload = {
            "kind": "User",
            "apiVersion": "v1",
            "metadata": {"name": user_name},
            "fullName": full_name,
        }
        result = self.post_request(url, payload, True)
        return result

    def delete_user(self, user_name):
        url = f"{self.get_url()}/oapi/v1/users/{user_name}"
        return self.del_request(url, None, True)

    # member functions for identities
    def identity_exists(self, id_provider, id_user):
        url = f"{self.get_url()}/oapi/v1/identities/{id_provider}:{id_user}"
        result = self.get_request(url, True)
        if result.status_code == 200 or result.status_code == 201:
            return True
        return False

    def create_identity(self, id_provider, id_user):
        url = f"{self.get_url()}/oapi/v1/identities"
        payload = {
            "kind": "Identity",
            "apiVersion": "v1",
            "providerName": id_provider,
            "providerUserName": id_user,
        }
        return self.post_request(url, payload, True)

    def delete_identity(self, id_provider, id_user):
        url = f"{self.get_url()}/oapi/v1/identities"
        payload = {
            "kind": "DeleteOptions",
            "apiVersion": "v1",
            "providerName": id_provider,
            "providerUserName": id_user,
            "gracePeriodSeconds": 300,
        }
        return self.del_request(url, payload, True)

    def create_useridentitymapping(self, user_name, id_provider, id_user):
        url = f"{self.get_url()}/oapi/v1/useridentitymappings"
        payload = {
            "kind": "UserIdentityMapping",
            "apiVersion": "v1",
            "user": {"name": user_name},
            "identity": {"name": id_provider + ":" + id_user},
        }
        return self.post_request(url, payload, True)

    # member functions to associate roles for users on projects
    # To check if a particular user has a rolebinding, get the complete
    # list of users that have that particular role on the project and
    # see if the user_name is in that list.
    #
    # This just returns the list
    def get_rolebindings(self, project_name, role):
        url = f"{self.get_url()}/oapi/v1/namespaces/{project_name}/rolebindings/{role}"
        result = self.get_request(url, True)
        self.logger.info("get rolebindings: " + result.text)
        return result

    def list_rolebindings(self, project_name):
        url = f"{self.get_url()}/oapi/v1/namespaces/{project_name}/rolebindings"
        result = self.get_request(url, True)
        return result

    def create_rolebindings(self, project_name, user_name, role):
        url = f"{self.get_url()}/oapi/v1/namespaces/{project_name}/rolebindings"
        payload = {
            "kind": "RoleBinding",
            "apiVersion": "v1",
            "metadata": {"name": role, "namespace": project_name},
            "groupNames": None,
            "userNames": [user_name],
            "roleRef": {"name": role},
        }
        return self.post_request(url, payload, True)

    def update_rolebindings(self, project_name, role, rolebindings_json):
        url = f"{self.get_url()}/oapi/v1/namespaces/{project_name}/rolebindings/{role}"
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


class MocOpenShift4x(MocOpenShift):

    # member functions for projects
    def project_exists(self, project_name):
        url = f"{self.get_url()}/apis/project.openshift.io/v1/projects/{project_name}"
        result = self.get_request(url, True)
        if result.status_code == 200 or result.status_code == 201:
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
    def identity_exists(self, id_provider, id_user):
        url = f"{self.get_url()}/apis/user.openshift.io/v1/identities/{id_provider}:{id_user}"
        result = self.get_request(url, True)
        if result.status_code == 200 or result.status_code == 201:
            return True
        return False

    def create_identity(self, id_provider, id_user):
        url = f"{self.get_url()}/apis/user.openshift.io/v1/identities"
        payload = {
            "kind": "Identity",
            "apiVersion": "user.openshift.io/v1",
            "providerName": id_provider,
            "providerUserName": id_user,
        }
        return self.post_request(url, payload, True)

    def delete_identity(self, id_provider, id_user):
        url = f"{self.get_url()}/apis/user.openshift.io/v1/identities/{id_provider}:{id_user}"
        payload = {
            "kind": "DeleteOptions",
            "apiVersion": "user.openshift.io/v1",
            "providerName": id_provider,
            "providerUserName": id_user,
            "gracePeriodSeconds": 300,
        }
        return self.del_request(url, payload, True)

    def create_useridentitymapping(self, user_name, id_provider, id_user):
        url = f"{self.get_url()}/apis/user.openshift.io/v1/useridentitymappings"
        payload = {
            "kind": "UserIdentityMapping",
            "apiVersion": "user.openshift.io/v1",
            "user": {"name": user_name},
            "identity": {"name": id_provider + ":" + id_user},
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

    # member functions for quotas

    def get_configmap(self, configmap_name):
        url = f"{self.get_url()}/api/v1/namespaces/{self.namespace}/configmaps/{configmap_name}"
        data_section = self.get_request(url, True).json()["data"]
        return data_section

    def get_quota_definitions(self, configmap_name):
        # would want to do the following:
        #   quotas = json.loads(self.get_configmap_data(configmap_name)["json"])
        # But this has the unintended behavior of adding multiple layers of quotes as in
        #    ..."{\"json\":\"{  \\\":persistentvolumeclaims\\\":"...
        # This works for every key field in the embedded JSON - except for fields that contain a '-'
        # and the program throws an exception.
        #
        # However the following works
        quota_str = self.get_configmap(configmap_name)["json"]
        quota = json.loads(quota_str)
        # - Now on to our regularly scheduled program
        for k in quota:
            quota[k]["value"] = None

        # RBB Get the quotas from openshift ResourceQuotas
        # RBB url = f"{self.get_url()}/api/v1/namespaces/{project_name}/resourcequotas"
        # RBB resource_quotas=json.loads(self.get_request(url,True).json())

        # RBB Iterate through the resource quota objects adding value into the quotas

        return quota

    def get_moc_quota(self, project_name):
        quota_def = self.get_quota_definitions(
            "openshift-quota-definition", project_name
        )
        quota_def = self.add_in_quotas(project_name, quota_def)
        quota = dict()
        for k in quota_def:
            quota[k] = quota_def[k]["value"]

        quota_object = {
            "Version": "0.9",
            "Kind": "MocQuota",
            "ProjectName": project_name,
            "Quota": quota,
        }
        return quota_object

    def split_quota_name(self, moc_quota_name):
        name_array = moc_quota_name.split(":")
        if len(name_array[0]) == 0:
            scope = "Project"
        else:
            scope = name_array[0]
        quota_name = name_array[1]
        return (scope, quota_name)

    def create_shift_quotas(self, project_name, quota_spec):
        quota_def = dict()
        # separate the quota_spec by quota_scope
        for k in quota_spec:
            (scope, quota_name) = self.split_quota_name(k)
            if scope not in quota_def:
                quota_def[scope] = dict()
            quota_def[scope][quota_name] = quota_spec[k]
        # create the openshift quota resources
        for scope in quota_def:
            resource_quota_json = {
                "apiVersion": "v1",
                "kind": "ResourceQuota",
                "metadata": {"name": f"{project_name.lower()}-{scope.lower()}"},
                "spec": {"hard": {}},
            }
            if scope is not "Project":
                resource_quota_json["scopes"] = [scope]
            non_null_quota_count = 0
            for quota_name in quota_def[scope]:
                if quota_def[scope][quota_name] is not None:
                    non_null_quota_count += 1
                    resource_quota_json["spec"]["hard"][quota_name] = quota_def[scope][
                        quota_name
                    ]["value"]
            if non_null_quota_count > 0:
                url = (
                    f"{self.get_url()}/api/v1/namespaces/{project_name}/resourcequotas"
                )
                self.post_request(url, resource_quota_json, True)
                # RBB should check to see if the quota was created before here, but this is quick and easy!
                time.sleep(2)

    def replace_openshift_quota(self, project_name, new_quota):
        quota_def = self.get_quota_definitions("openshift-quota-definition")
        if "QuotaMultiplier" in new_quota["Quota"]:
            x = new_quota["Quota"]["QuotaMultiplier"]
            for quota in quota_def:
                quota_def[quota]["value"] = (
                    quota_def[quota]["coefficient"] * x + quota_def[quota]["base"]
                )
                if "units" in quota_def[quota]:
                    quota_def[quota]["value"] = (
                        str(quota_def[quota]["value"]) + quota_def[quota]["units"]
                    )

        # RBB  else:
        # RBB  need to overwrite the value in the quotadef with the ones from the new_quota

        # RBB self.delete_project_quotas(project_name)
        quota_def = self.create_shift_quotas(project_name, quota_def)
        return

    def update_openshift_quota(self, project_name, new_quota):
        url = f"{self.get_url()}/api/v1/namespaces/{project_name}/resourcequotas/{resource_name}"
        quota_configmap = self.get_quota_data("openshift-quota-definition")
        # RBB combine quota_configmap with the quota in the project

        return

    def delete_openshift_quota(self, project_name):
        url = f"{self.get_url()}/api/v1/namespaces/{project_name}/resourcequotas/{resource_name}"
        payload = {}
        return self.del_request(self, payload, True)
