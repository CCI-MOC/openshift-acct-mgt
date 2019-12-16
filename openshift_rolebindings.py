import kubernetes
import pprint
import logging
import requests
import json
import re
from flask import Flask, redirect, url_for, request, Response

import sys

application = Flask(__name__)

# To check if a particular user has a rolebinding, get the complete
# list of users that have that particular role on the project and 
# see if the user_name is in that list.
#
# This just returns the list
def get_openshift_rolebindings(token, api_url, project_name, role):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json',
               'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' +  project_name + '/rolebindings/' + role
    r = requests.get(url, headers=headers, verify=False)
    application.logger.debug("r: "+r.text)
    return r

def list_openshift_rolebindings(token, api_url, project_name):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json',
               'Content-Type': 'application/json'}
    url = 'https://'+api_url+'/oapi/v1/namespaces/'+project_name+'/rolebindings'
    r = requests.get(url, headers=headers, verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("l: " + str(r.status_code))
    application.logger.debug("l: " + r.text)
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
    application.logger.debug("url: "+url)
    application.logger.debug("payload: "+json.dumps(payload))
    application.logger.debug("d: " + str(r.status_code))
    application.logger.debug("d: " + r.text)
    return r

def create_openshift_rolebindings(token, api_url, project_name, user_name, role):
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/json', 'Content-Type': 'application/json'}
    url = 'https://' + api_url + '/oapi/v1/namespaces/' + project_name + '/rolebindings' # /' + role
    payload = {
        "kind": "RoleBinding",
        "apiVersion": "v1",
        "metadata": {
            "name": role,
            "namespace": project_name
        },
        "groupNames": None,
        "userNames": [ user_name ],
        "roleRef": {"name": role}
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("payload: "+json.dumps(payload))
    application.logger.debug("crb r: " + str(r.status_code))
    application.logger.debug("crb r: " + r.text)
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
    application.logger.debug("payload -> 1: "+json.dumps(payload))
    for key in rolebindings_json["metadata"]:
        if key in ["name","namespace"]:
            payload["metadata"][key]=rolebindings_json["metadata"][key]
    application.logger.debug("payload -> 2: "+json.dumps(payload))
    r = requests.put(url, headers=headers, data=json.dumps(payload), verify=False)
    application.logger.debug("url: "+url)
    application.logger.debug("payload: "+json.dumps(payload))
    application.logger.debug("up r: " + str(r.status_code))
    application.logger.debug("up r: " + r.text)
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
    #add_openshift_role(token,api_url,project_name, role)

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
        
    r=get_openshift_rolebindings(token, api_url, project_name, openshift_role)
    #print("A: result: "+r.text)
    if(not (r.status_code==200 or r.status_code==201)):
        # try to create the roles for binding
        # can be more specific {"kind":"Status","apiVersion":"v1","metadata":{},"status":"Failure","message":"rolebindings \"admin\" not found","reason":"NotFound","details":{"name":"admin","kind":"rolebindings"},"code":404}
        r=create_openshift_rolebindings(token, api_url, project_name, user, openshift_role)
        if(r.status_code==200 or r.status_code==201):
            return Response(
                response=json.dumps({"msg":"rolebinding created ("+user+","+project_name+","+role+")"}),
                status=400,
                mimetype='application/json'
            )
        return Response(
                response=json.dumps({"msg":" unable to create rolebinding ("+user+","+project_name+","+role+")" + r.text }),
                status=400,
                mimetype='application/json'
            )

    #print("B: result: "+r.text)
    #r=create_openshift_rolebinding(token, api_url, project_name, role)
    if(r.status_code==200 or r.status_code==201):
        role_binding=r.json()
        if(op=='add'):
            application.logger.debug("role_binding: "+json.dumps(role_binding) )
            application.logger.debug("role_binding['userNames']=" + str(role_binding["userNames"]) )
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
        r = update_openshift_rolebindings(token, api_url, project_name, openshift_role, role_binding)

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
