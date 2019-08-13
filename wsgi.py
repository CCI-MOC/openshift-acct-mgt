import kubernetes
from openshift.dynamic import DynamicClient
import pprint
import logging
import requests
import json
import re
from flask import Flask, redirect, url_for, request, Response

application = Flask(__name__)

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    application.logger.handlers = gunicorn_logger.handlers
    application.logger.setLevel(gunicorn_logger.level)


def get_user_token(kub_config_file, service_acct):
    with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as file:
        token = file.read()
        return token
    return ""


def get_token_and_url():
    token = get_user_token('/kube/config', 'moc-openshift-acct-req')
    openshift_url = "k-openshift.osh.massopen.cloud:8443"
    return (token, openshift_url)


def cnvt_project_name(project_name):
    suggested_project_name = re.sub('^[^A-Za-z0-9]+', '', project_name)
    suggested_project_name = re.sub(
        '[^A-Za-z0-9]+$', '', suggested_project_name)
    suggested_project_name = re.sub(
        '[^A-Za-z0-9\-]+', '-', suggested_project_name)
    return suggested_project_name


def exists_openshift_rolebindings(token, api_url, project_name, user_name, role):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json',
               'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' + \
          project_name + '/rolebindings/' + role
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("r: " + str(r.status_code) + "  " + user_name)
    application.logger.warning("r: " + r.text)
    if(r.status_code == 200 or r.status_code == 201):
        user_set = set(r.json["userNames"])
        if(user_name in user_set):
            return True
    return False


def delete_openshift_rolebindings(token, api_url, project_name, user_name, role):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json',
               'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' + project_name + '/rolebindings'
    payload = {
        "kind": "RoleBinding",
        "apiVersion": "v1",
        "metadata": {
            "name": role,
            "namespace": project_name
        },
        "groupNames": "null",
        "userNames": [user_name],
        "roleRef": {"name": role}
    }
    r = requests.delete(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r


def create_openshift_rolebindings(token, api_url, project_name, user_name, role):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' + project_name + '/rolebindings'
    payload = {
        "kind": "RoleBinding",
        "apiVersion": "v1",
        "metadata": {
            "name": role,
            "namespace": project_name
        },
        "groupNames": None,
        "userNames": [user_name],
        "roleRef": {"name": role}
    }
    r = requests.post(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("cr r: " + str(r.status_code))
    application.logger.warning("cr r: " + r.text)
    return r


@application.route("/users/<user_name>/projects/<project_name>/roles/<role>", methods=['GET','DELETE'])
def create_rolebindings(project_name, user_name, role):
    # role can be one of Admin, Member, Reader
    (token, openshift_url) = get_token_and_url()
    openshift_role = None
    if(role == "admin"):
        openshift_role = "admin"
    elif(role == "member"):
        openshift_role = "edit"
    elif(role == "reader"):
        openshift_role = "view"
    application.logger.warning("openshift_role " + openshift_role)
    if(openshift_role is not None):
        r = None
        if(request.method == 'GET'):
            if(not exists_openshift_rolebindings(token, openshift_url, project_name, user_name, openshift_role)):
                r = create_openshift_rolebindings(
                    token, openshift_url, project_name, user_name, openshift_role)
                if (r.status_code == 200 or r.status_code == 201):
                    return Response(
                        response=json.dumps({"msg":"Role binding created ("+user_name+","+project_name+","+role+")"}),
                        status=200,
                        mimetype='application/json'
                    )
                return Response(
                    response=json.dumps({"msg":"Unable to created role binding ("+user_name+","+project_name+","+role+")"}),
                    status=400,
                    mimetype='application/json'
                    )
            return Response(
                response=json.dumps({"msg":"Role binding currently exists ("+user_name+","+project_name+","+role+")"}),
                status=400,
                mimetype='application/json'
                )
        elif(request.method='DELETE'):
            if(exists_openshift_projectrole(token,api_url,project_name,user_name,role)):
                r=create_openshift_projectrole(token,api_url,project_name,username,role)
                if (r.status_code==200 or r.status_code1==201):
                    return Response(
                        response=json.dumps({"msg":"Role binding created ("+user_name+","+project_name+","+role+")"}),
                        status=200,
                        mimetype='application/json'
                        )
                return Response(
                    response=json.dumps({"msg":"Unable to delete role binding ("+user_name+","+project_name+","+role+")"}),
                    status=400,
                    mimetype='application/json'
                    )
            return Response(
                response=json.dumps({"msg":"Role binding currently does not exists ( ! "+user_name+","+project_name+","+role+")"}),
                status=400,
                mimetype='application/json'
                )
        return Response(
            response=json.dumps({"msg": "Method: '" + request.method + "' Not found"}),
            status=405,
            mimetype='application/json'
            )
    return Response(
        response=json.dumps({"msg": "Invalid parameters/syntax"}),
        status=400,
        mimetype='application/json'
        )        


def exists_openshift_project(token, api_url, project_name):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/projects/' + project_name
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False

#try just using the projet name
def delete_openshift_project(token, api_url, project_name, user_name):
    # check project_name
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/projects'
    payload = {"kind": "Project", "apiVersion": "v1", "metadata": {"name": project_name, "annotations": {
        "openshift.io/display-name": project_name, "openshift.io/requester": user_name}}}
    r = requests.delete(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r


def create_openshift_project(token, api_url, project_name, user_name):
    # check project_name
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/projects'
    payload = {"kind": "Project", "apiVersion": "v1", "metadata": {"name": project_name, "annotations": {
        "openshift.io/display-name": project_name, "openshift.io/requester": user_name}}}
    r = requests.post(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r


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
            if(r.status_code == 200 and r.status_code == 201):
                return Response(
                    response=json.dumps({"msg": "project created: " + project_name }),
                    status=200,
                    mimetype='application/json'
                    )
            return Response(
                response=json.dumps({"msg": "project unabled to be created: " + project_name }),
                status=400,
                mimetype='application/json'
                )
        return Response(
            response=json.dumps({"msg": "project currently exist: " + project_name }),
            status=400,
            mimetype='application/json'
            )
    elif(request.method=='DELETE'):

    return Response(
        response=json.dumps({"msg": "Method: '" + request.method + "' Not found"}),
        status=405,
        mimetype='application/json'
        )


def exists_openshift_user(token, api_url, user_name):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/users/' + user_name
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False


def create_openshift_user(token, api_url, user_name, full_name):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/users'
    payload = {"kind": "User", "apiVersion": "v1",
               "metadata": {"name": user_name}, "fullName": full_name}
    r = requests.post(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r

# try eliminating the full_name
def delete_openshift_user(token, api_url, user_name, full_name):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/users'
    payload = {"kind": "User", "apiVersion": "v1",
               "metadata": {"name": user_name}, "fullName": full_name}
    r = requests.delete(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r


def exists_openshift_identity(token, api_url, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/identities/' + id_provider + ':' + id_user
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False


def delete_openshift_identity(token, api_url, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/identities'
    payload = {"kind": "Identity", "apiVersion": "v1",
               "providerName": id_provider, "providerUserName": id_user}
    r = requests.delete(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r


def create_openshift_identity(token, api_url, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/identities'
    payload = {"kind": "Identity", "apiVersion": "v1",
               "providerName": id_provider, "providerUserName": id_user}
    r = requests.post(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r


def exists_openshift_useridentitymapping(token, api_url, user_name, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}

    url = 'https://' + api_url + '/oapi/v1/useridentitymappings/' + \
        id_provider + ':' + id_user
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    # it is probably not necessary to check the user name in the useridentity
    # mapping
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False


def create_openshift_useridentitymapping(token, api_url, user_name, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/useridentitymappings'
    payload = {"kind": "UserIdentityMapping", "apiVersion": "v1", "user": {
        "name": user_name}, "identity": {"name": id_provider + ":" + id_user}}
    r = requests.post(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r


@application.route("/users/<user_name>", methods=['GET','DELETE'])
@application.route("/users/<user_name>/fullname/<full_name>", methods=['GET','DELETE'])
@application.route("/users/<user_name>/fullname/<full_name>/<identity>/<id_user>", methods=['GET','DELETE'])
def create_user(user_name, full_name=None, id_provider="sso_auth", id_user=None):
    token = get_user_token('/kube/config', 'moc-openshift-acct-req')
    openshift_url = "k-openshift.osh.massopen.cloud:8443"
    r=None

    if(request.method == 'GET'):
        # use case if User doesn't exist, then create
        if(not exists_openshift_user(token, openshift_url, user_name)):
            r = create_openshift_user(
                token, openshift_url, user_name, full_name)
            if(r.status_code != 200 and r.status_code != 201):
                return Response(
                    response=json.dumps({"msg": "Unable to create User (" + user_name + ") 1"}),
                    status=400,
                    mimetype='application/json'
                    )
        if(id_user is None):
            id_user = user_name
        # if identity doesn't exist then create
        if(not exists_openshift_identity(token, openshift_url, id_provider, id_user)):
            r = create_openshift_identity(
                token, openshift_url, id_provider, id_user)
            if(r.status_code != 200 and r.status_code != 201):
                return Response(
                    response=json.dumps({"msg": "Unable to create identity (" + id_provider + ")"}),
                    status=400,
                    mimetype='application/json'
                    )
        # creates the useridenitymapping
        if(not exists_openshift_useridentitymapping(token, openshift_url, user_name, id_provider, id_user)):
            r = create_openshift_useridentitymapping(
                token, openshift_url, user_name, id_provider, id_user)
            if(r.status_code != 200 and r.status_code != 201):
                return Response(
                    response=json.dumps({"msg": "Unable to create user (" + user_name + ")"}),
                    status=400,
                    mimetype='application/json'
                    )
        return Response(
            response=json.dumps({"msg": "User Created (" + user_name + ")"}),
            status=200,
            mimetype='application/json'
            )
    elif(request.method == 'DELETE'):
         # use case if User exists then delete
        if(exists_openshift_user(token, openshift_url, user_name)):
            r = delete_openshift_user(
                token, openshift_url, user_name, full_name)
            if(r.status_code != 200 and r.status_code != 201):
                return Response(
                    response=json.dumps({"msg": "Unable to delete User (" + user_name + ") 1"}),
                    status=400,
                    mimetype='application/json'
                    )
        if(id_user is None):
            id_user = user_name
        # if identity doesn't exist then create
        if(exists_openshift_identity(token, openshift_url, id_provider, id_user)):
            r = delete_openshift_identity(
                token, openshift_url, id_provider, id_user)
            if(r.status_code != 200 and r.status_code != 201):
                return Response(
                    response=json.dumps({"msg": "Unable to delete identity (" + id_provider + ")"}),
                    status=400,
                    mimetype='application/json'
                    )
        # creates the useridenitymapping
        #if(not exists_openshift_useridentitymapping(token, openshift_url, user_name, id_provider, id_user)):
        #    r = create_openshift_useridentitymapping(
        #        token, openshift_url, user_name, id_provider, id_user)
        #    if(r.status_code != 200 and r.status_code != 201):
        #        return Response(
        #            response=json.dumps({"msg": "Unable to create user (" + user_name + ")"}),
        #            status=400,
        #            mimetype='application/json'
        #            )
        return Response(
            response=json.dumps({"msg": "User Deleted (" + user_name + ")"}),
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
    # "oc login -u acct-req-sa"
    # "oc adm policy -n <project_name> add-role-to-user <role> <user_name>"
    return "{\"map\"}"

if __name__ == "__main__":
    application.run()
