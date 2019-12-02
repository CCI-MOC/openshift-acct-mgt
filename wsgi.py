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


def get_user_token():
    with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as file:
        token = file.read()
        return token
    return ""


def get_token_and_url():
    token = get_user_token()
    #openshift_url = "https://192.168.64.17:8443"
    #openshift_url = "https://k-openshift.osh.massopen.cloud:8443"
    openshift_url = "s-openshift.osh.massopen.cloud:8443"
    #openshift_url = "sn001:8443"

    #the following 3 don't work
    #openshift_url = "https://127.30.0.1:443"
    #openshift_url = "https://127.30.0.1:8443"
    #openshift_url = "https://127.0.0.1:8443"
    return (token, openshift_url)


def cnvt_project_name(project_name):
    suggested_project_name = re.sub('^[^A-Za-z0-9]+', '', project_name)
    suggested_project_name = re.sub(
        '[^A-Za-z0-9]+$', '', suggested_project_name)
    suggested_project_name = re.sub(
        '[^A-Za-z0-9\-]+', '-', suggested_project_name)
    return suggested_project_name


def exists_openshift_rolebindings(token, api_url, project_name, role):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json',
               'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' +  project_name + '/rolebindings/' + role
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("url: "+url)
    application.logger.warning("r: " + str(r.status_code) + "  " + user_name)
    application.logger.warning("r: " + r.text)
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False

def get_openshift_rolebindings(token, api_url, project_name, role):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json',
               'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' +  project_name + '/rolebindings/' + role
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("r: "+r.text)
    return r

def list_openshift_rolebindings(token, api_url, project_name):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json',
               'Content-Type': 'application/json'}
    url = 'https://'+api_url+'/oapi/v1/namespaces/'+project_name+'/rolebindings'
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("url: "+url)
    application.logger.warning("l: " + str(r.status_code))
    application.logger.warning("l: " + r.text)
    return r


def delete_openshift_rolebindings(token, api_url, project_name, user_name, role):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json',
               'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' + project_name + '/rolebindings/' + role
    payload =     {
        "kind": "DeleteOptions", 
        "apiVersion": "v1",
        "gracePeriodSeconds":"300" 
    }

    r = requests.delete(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("url: "+url)
    application.logger.warning("payload: "+json.dumps(payload))
    application.logger.warning("d: " + str(r.status_code))
    application.logger.warning("d: " + r.text)
    return r


def create_openshift_rolebindings(token, api_url, project_name, role):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' + project_name + '/rolebindings/' + role
    payload = {
        "kind": "RoleBinding",
        "apiVersion": "v1",
        "metadata": {
            "name": role,
            "namespace": project_name
        },
        "groupNames": None,
        "userNames": [],
        "roleRef": {"name": role}
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
    application.logger.warning("url: "+url)
    application.logger.warning("payload: "+json.dumps(payload))
    application.logger.warning("cr r: " + str(r.status_code))
    application.logger.warning("cr r: " + r.text)
    return r

def update_openshift_rolebindings(token,api_url,project_name,role,rolebindings_json):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' + project_name + '/rolebindings/' + role
    # need to eliminate some fields that might be there
    payload={}
    for key in rolebindings_json:
        if key in ["kind","apiVersion","userNames","groupNames","roleRef"]:
            payload[key]=rolebindings_json[key]
    payload['metadata']={}
    application.logger.warning("payload -> 1: "+json.dumps(payload))
    for key in rolebindings_json["metadata"]:
        if key in ["name","namespace"]:
            payload["metadata"][key]=rolebindings_json["metadata"][key]
    application.logger.warning("payload -> 2: "+json.dumps(payload))
    r = requests.put(url, headers=headers, data=json.dumps(payload), verify=False)
    application.logger.warning("url: "+url)
    application.logger.warning("payload: "+json.dumps(payload))
    application.logger.warning("up r: " + str(r.status_code))
    application.logger.warning("up r: " + r.text)
    return r

def update_user_role_project(token, api_url, project_name, user, role, op):
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
    if(op not in ['add','del']):
       return Response(
            response=json.dumps({"msg":"op is not in ('add' or 'del')"}),
            status=400,
            mimetype='application/json'
        ) 
    r=get_openshift_rolebindings(token, api_url, project_name, role)
    #r=create_openshift_rolebinding(token, api_url, project_name, role)
    if(r.status_code==200 or r.status_code==201):
        role_binding=r.json()
        if(op=='add'):
            application.logger.warning("role_binding: "+json.dumps(role_binding) )
            application.logger.warning("role_binding['userNames']=" + str(role_binding["userNames"]) )
            if(role_binding['userNames'] is None):
                role_binding['userNames']=[user]
            else:
                if(user in role_binding["userNames"]):
                    return Response(
                        response=json.dumps({"msg":"rolebinding already exists - unable to add ("+user+","+project_name+","+role+")"}),
                        status=400,
                        mimetype='application/json'
                    )
                role_binding["userNames"].append(user)
        elif(op=='del'):
            if((role_binding['userNames'] is None) or (user not in role_binding["userNames"]) ):
                return Response(
                    response=json.dumps({"msg":"rolebinding does not exist - unable to delete ("+user+","+project_name+","+role+")"}),
                    status=400,
                    mimetype='application/json'
                )
            role_binding["userNames"].remove(user)                
        else:
            return Response(
                        response=json.dumps({"msg":"Invalid request ("+user+","+project_name+","+role+","+op+")"}),
                        status=400,
                        mimetype='application/json'
                    )

        # now add or remove the user
        r = update_openshift_rolebindings(token, api_url, project_name, role, role_binding)

        msg="unknown message"
        if(r.status_code==200 or r.status_code==201):
            if(op=='add'):
                msg="Added role to user on project"
            elif(op=='del'):
                msg="removed role from user on project"
            return Response(
                response=json.dumps({"msg": msg}),
                status=200,
                mimetype='application/json'
            ) 
        if(op == 'add'):
            msg="unable to add role to user on project"
        elif(op == 'del'):
            msg="unable to remove role from user on project"
        return Response(
            response=json.dumps({"msg":msg}),
            status=400,
            mimetype='application/json'
        ) 
    return Response(
        response=json.dumps({"msg":"rolebinding already exists ("+user+","+project_name+","+role+")"}),
        status=400,
        mimetype='application/json'
        )

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
    else:
        return Response( 
            response=json.dumps({"msg":"Error: Invalid role,  "+role+" is not one of 'admin', 'member' or 'reader'"}),
            status=400,
            mimetype='application/json'
        )
    application.logger.warning("openshift_role " + openshift_role)
    if(openshift_role is not None):
        r = None
        if(request.method == 'GET'):
            r = update_user_role_project(token, openshift_url, project_name, user_name, openshift_role,'add')
            return r
        elif(request.method == 'DELETE'):
            r = update_user_role_project(token, openshift_url, project_name, user_name, openshift_role,'del')
            return r
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
    application.logger.warning("url: "+url)
    #application.logger.warning("payload: "+payload)
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
    url = 'https://' + api_url + '/oapi/v1/projects/' + project_name
    #payload = {"kind": "Project", "apiVersion": "v1", "metadata": {"name": project_name, "annotations": {
    #    "openshift.io/display-name": project_name, "openshift.io/requester": user_name}}}
    r = requests.delete(url, headers=headers, verify=False)
    #                  data=json.dumps(payload), verify=False)
    application.logger.warning("url: "+url)
    #application.logger.warning("payload: "+json.dumps(payload))
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
    application.logger.warning("url: "+url)
    application.logger.warning("payload: "+json.dumps(payload))
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
            if(r.status_code == 200 or r.status_code == 201):
                return Response(
                    response=json.dumps({"msg": "project created (" + project_name +")" }),
                    status=200,
                    mimetype='application/json'
                    )
            return Response(
                response=json.dumps({"msg": "project unabled to be created (" + project_name +")" }),
                status=400,
                mimetype='application/json'
                )
        return Response(
            response=json.dumps({"msg": "project currently exist (" + project_name +")" }),
            status=400,
            mimetype='application/json'
            )
    elif(request.method=='DELETE'):
        if(exists_openshift_project(token, openshift_url, project_name)):
            r = delete_openshift_project(
                token, openshift_url, project_name, user_name)
            if(r.status_code == 200 or r.status_code == 201):
                return Response(
                    response=json.dumps({"msg": "project deleted (" + project_name +")" }),
                    status=200,
                    mimetype='application/json'
                    )
            return Response(
                response=json.dumps({"msg": "project unabled to be deleted (" + project_name +")" }),
                status=400,
                mimetype='application/json'
                )
        return Response(
            response=json.dumps({"msg": "unable to delete, project does not exist(" + project_name +")" }),
            status=400,
            mimetype='application/json'
            )
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
    application.logger.warning("url: "+url)
    #application.logger.warning("payload: "+payload)
    application.logger.warning("exists os user: " + str(r.status_code))
    application.logger.warning("exists os user: " + r.text)
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
    application.logger.warning("url: "+url)
    application.logger.warning("payload: "+json.dumps(payload))
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r

# try eliminating the full_name
def delete_openshift_user(token, api_url, user_name, full_name):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/users/' + user_name
    #payload = {"kind": "User", "apiVersion": "v1",
    #           "metadata": {"name": user_name}, "fullName": full_name}
    r = requests.delete(url, headers=headers, verify=False)
    #                  data=json.dumps(payload), verify=False)
    application.logger.warning("url: "+url)
    #application.logger.warning("payload: "+payload)
    application.logger.warning("d os user: " + str(r.status_code))
    application.logger.warning("d os user: " + r.text)
    return r


def exists_openshift_identity(token, api_url, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/identities/' + id_provider + ':' + id_user
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("url: "+url)
    #application.logger.warning("payload: "+payload)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    if(r.status_code == 200 or r.status_code == 201):
        return True
    return False


def delete_openshift_identity(token, api_url, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/identities'
    payload = {"kind": "DeleteOptions", "apiVersion": "v1",
               "providerName": id_provider, "providerUserName": id_user, "gracePeriodSeconds":"300" }
    r = requests.delete(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("url: "+url)
    application.logger.warning("payload: "+json.dumps(payload))
    application.logger.warning("d os ident: " + str(r.status_code))
    application.logger.warning("d os ident: " + r.text)
    return r


def create_openshift_identity(token, api_url, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/identities'
    payload = {"kind": "Identity", "apiVersion": "v1",
               "providerName": id_provider, "providerUserName": id_user}
    r = requests.post(url, headers=headers,
                      data=json.dumps(payload), verify=False)
    application.logger.warning("url: "+url)
    #application.logger.warning("payload: "+json.dumps(payload))
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r


def exists_openshift_useridentitymapping(token, api_url, user_name, id_provider, id_user):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}

    url = 'https://' + api_url + '/oapi/v1/useridentitymappings/' + \
        id_provider + ':' + id_user
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("url: "+url)
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
    application.logger.warning("url: "+url)
    application.logger.warning("payload: "+json.dumps(payload))
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r


@application.route("/users/<user_name>", methods=['GET','DELETE'])
@application.route("/users/<user_name>/fullname/<full_name>", methods=['GET','DELETE'])
@application.route("/users/<user_name>/fullname/<full_name>/<identity>/<id_user>", methods=['GET','DELETE'])
def user_management(user_name, full_name=None, id_provider="sso_auth", id_user=None):
    (token, openshift_url) = get_token_and_url()
    r=None

    if(request.method == 'GET'):
        user_exists = 0x00
        # use case if User doesn't exist, then create
        if(not exists_openshift_user(token, openshift_url, user_name)):
            r = create_openshift_user(
                token, openshift_url, user_name, full_name)
            if(r.status_code != 200 and r.status_code != 201):
                return Response(
                    response=json.dumps({"msg": "unable to create openshift User (" + user_name + ") 1"}),
                    status=400,
                    mimetype='application/json'
                    )
        else:
            user_exists = user_exists | 0x01

        if(id_user is None):
            id_user = user_name

        # if identity doesn't exist then create
        if(not exists_openshift_identity(token, openshift_url, id_provider, id_user)):
            r = create_openshift_identity(
                token, openshift_url, id_provider, id_user)
            if(r.status_code != 200 and r.status_code != 201):
                return Response(
                    response=json.dumps({"msg": "unable to create openshift identity (" + id_provider + ")"}),
                    status=400,
                    mimetype='application/json'
                    )
        else:
            user_exists = user_exists | 0x02

        # creates the useridenitymapping
        if(not exists_openshift_useridentitymapping(token, openshift_url, user_name, id_provider, id_user)):
            r = create_openshift_useridentitymapping(
                token, openshift_url, user_name, id_provider, id_user)
            if(r.status_code != 200 and r.status_code != 201):
                return Response(
                    response=json.dumps({"msg": "unable to create openshift user identity mapping (" + user_name + ")"}),
                    status=400,
                    mimetype='application/json'
                    )
        else:
            user_exists = user_exists | 0x04

        if(user_exists==7):
            return Response(
                response=json.dumps({"msg": "user currently exists (" + user_name + ")"}),
                status=200,
                mimetype='application/json'
                )
        else:
            return Response(
                response=json.dumps({"msg": "user created (" + user_name + ")"}),
                status=200,
                mimetype='application/json'
                )


    elif(request.method == 'DELETE'):
        user_does_not_exist=0
         # use case if User exists then delete
        if(exists_openshift_user(token, openshift_url, user_name)):
            r = delete_openshift_user(
                token, openshift_url, user_name, full_name)
            if(r.status_code != 200 and r.status_code != 201):
                return Response(
                    response=json.dumps({"msg": "unable to delete User (" + user_name + ") 1"}),
                    status=400,
                    mimetype='application/json'
                    )
        else:
            user_does_not_exist = 0x01

        if(id_user is None):
            id_user = user_name
        # if identity doesn't exist then create
        if(exists_openshift_identity(token, openshift_url, id_provider, id_user)):
            r = delete_openshift_identity(
                token, openshift_url, id_provider, id_user)
            if(r.status_code != 200 and r.status_code != 201):
                return Response(
                    response=json.dumps({"msg": "unable to delete identity (" + id_provider + ")"}),
                    status=400,
                    mimetype='application/json'
                    )
        else:
            user_does_not_exist =  user_does_not_exist | 0x02

        if(user_does_not_exist==3):
            return Response(
                response=json.dumps({"msg": "user does not currently exist (" + user_name + ")"}),
                status=200,
                mimetype='application/json'
                )
        else:
            return Response(
                response=json.dumps({"msg": "user deleted (" + user_name + ")"}),
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
    # "oc login -u acct-mgt-sa"
    # "oc adm policy -n <project_name> add-role-to-user <role> <user_name>"
    return "{\"map\"}"

if __name__ == "__main__":
    application.run()
