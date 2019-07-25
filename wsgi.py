import kubernetes
from openshift.dynamic import DynamicClient
import pprint
import logging
import requests
import json
import re
from flask import Flask, redirect, url_for, request

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
    token = get_user_token('/kube/config','moc-openshift-acct-req')
    openshift_url="k-openshift.osh.massopen.cloud:8443"
    return (token,openshift_url)

# I broke this out into find_openshift_... and create_openshift_... because there may be type specific logic 
# inserted into each function.

#export TOKEN=`cat /var/run/secrets/kubernetes.io/serviceaccount/token`
#export ENDPOINT=k-openshift.osh.massopen.cloud:8443
#lists all projects
#curl -k -X GET -H "Authorization: Bearer $TOKEN" -H 'Accept: application/json' -H 'Content-Type: application/json' https://$ENDPOINT/oapi/v1/projects
#lists one project
#curl -k -X GET -H "Authorization: Bearer $TOKEN" -H 'Accept: application/json' -H 'Content-Type: application/json' https://$ENDPOINT/oapi/v1/projects/t001
#{
#  "kind": "Project",
#  "apiVersion": "v1",
#  "metadata": {
#    "name": "t001",
#    "selfLink": "/oapi/v1/projects/t001",
#    "uid": "0b8cca14-201a-11e9-b42b-fa163e917d49",
#    "resourceVersion": "215424",
#    "creationTimestamp": "2019-01-24T20:53:04Z",
#    "annotations": {
#      "alm-manager": "operator-lifecycle-manager.olm-operator",
#      "openshift.io/description": "",
#      "openshift.io/display-name": "",
#      "openshift.io/requester": "robbaron@bu.edu",
#      "openshift.io/sa.scc.mcs": "s0:c17,c4",
#      "openshift.io/sa.scc.supplemental-groups": "1000280000/10000",
#      "openshift.io/sa.scc.uid-range": "1000280000/10000"
#    }
#  },
#  "spec": {
#    "finalizers": [
#      "kubernetes"
#    ]
#  },
#  "status": {
#    "phase": "Active"
#  }
#}
# note regex for name is '[a-z0-9]([-a-z0-9]*[a-z0-9])?'
#curl -k \
#    -X POST \
#    -d @- \
#    -H "Authorization: Bearer $TOKEN" \
#    -H 'Accept: application/json' \
#    -H 'Content-Type: application/json' \
#    https://$ENDPOINT/oapi/v1/projects <<'EOF'
#{
#  "kind": "Project",
#  "apiVersion": "v1",
#  "metadata": {"name": "test1", "annotations": { "openshift.io/display-name": "", "openshift.io/requester": "robbaron@bu.edu" } }
#}
#EOF
def cnvt_project_name( project_name ):
    suggested_project_name=re.sub('^[^A-Za-z0-9]+','',project_name)
    suggested_project_name=re.sub('[^A-Za-z0-9]+$','',suggested_project_name)
    suggested_project_name=re.sub('[^A-Za-z0-9\-]+','-',suggested_project_name)
    return suggested_project_name

#curl -k -X GET -H "Authorization: Bearer $TOKEN" -H 'Accept: application/json' -H 'Content-Type: application/json' https://$ENPOINT/oapi/v1/rolebindings/t001
#{
##  "kind": "Status",
#  "apiVersion": "v1",
#  "metadata": {
#
#  },
#  "status": "Failure",
#  "message": "the server could not find the requested resource",
#  "reason": "NotFound",
#  "details": {
#
#  },
#  "code": 404
#}sh-4.2$ curl -k -X GET -H "Authorization: Bearer $TOKEN" -H 'Accept: application/json' -H 'Content-Type: application/json' https://$ENPOINT/oapi/v1/rolebindings/t002
#{
#  "kind": "Status",
#  "apiVersion": "v1",
#  "metadata": {
#
#  },
##  "status": "Failure",
##  "message": "the server could not find the requested resource",
##  "reason": "NotFound",
##  "details": {
##
##  },
##  "code": 404
##}sh-4.2$ curl -k -X GET -H "Authorization: Bearer $TOKEN" -H 'Accept: application/json' -H 'Content-Type: application/json' https://$ENPOINT/oapi/v1/namespaces/t001/rolebindings/
##{
##  "kind": "RoleBindingList",
##  "apiVersion": "v1",
##  "metadata": {
##    "selfLink": "/oapi/v1/namespaces/t001/rolebindings/",
##    "resourceVersion": "52171529"
##  },
##  "items": [
##    {
##      "metadata": {
##        "name": "admin",
##        "namespace": "t001",
##        "selfLink": "/oapi/v1/namespaces/t001/rolebindings/admin",
##        "uid": "0b99d36b-201a-11e9-b42b-fa163e917d49",
##        "resourceVersion": "52667",
#        "creationTimestamp": "2019-01-24T20:53:04Z"
#      },
#      "userNames": [
#        "robbaron@bu.edu"
#      ],
#      "groupNames": null,
#      "subjects": [
#        {
#          "kind": "User",
#          "name": "robbaron@bu.edu"
#        }
#      ],
#      "roleRef": {
#        "name": "admin"
#      }
#    },
#    {
#      "metadata": {
#        "name": "system:deployers",
#        "namespace": "t001",
#        "selfLink": "/oapi/v1/namespaces/t001/rolebindings/system%3Adeployers",
#        "uid": "0b974e41-201a-11e9-b42b-fa163e917d49",
#        "resourceVersion": "52664",
#        "creationTimestamp": "2019-01-24T20:53:04Z",
#        "annotations": {
#          "openshift.io/description": "Allows deploymentconfigs in this namespace to rollout pods in this namespace.  It is auto-managed by a controller; remove subjects to disable."
#        }
#      },
#      "userNames": [
#        "system:serviceaccount:t001:deployer"
#      ],
#      "groupNames": null,
#      "subjects": [
#        {
#          "kind": "ServiceAccount",
#          "namespace": "t001",
#          "name": "deployer"
#        }
#      ],
#      "roleRef": {
#        "name": "system:deployer"
#      }
#    },
#    {
#      "metadata": {
#        "name": "system:image-builders",
#        "namespace": "t001",
#        "selfLink": "/oapi/v1/namespaces/t001/rolebindings/system%3Aimage-builders",
#        "uid": "0b94ba83-201a-11e9-b42b-fa163e917d49",
#        "resourceVersion": "52661",
#        "creationTimestamp": "2019-01-24T20:53:04Z",
#        "annotations": {
#          "openshift.io/description": "Allows builds in this namespace to push images to this namespace.  It is auto-managed by a controller; remove subjects to disable."
#        }
#      },
#      "userNames": [
#        "system:serviceaccount:t001:builder"
#      ],
#      "groupNames": null,
#      "subjects": [
#        {
#          "kind": "ServiceAccount",
#          "namespace": "t001",
#          "name": "builder"
#        }
#      ],
#      "roleRef": {
#        "name": "system:image-builder"
#      }
#    },
#    {
#      "metadata": {
#        "name": "system:image-pullers",
#        "namespace": "t001",
#        "selfLink": "/oapi/v1/namespaces/t001/rolebindings/system%3Aimage-pullers",
#        "uid": "0b8fbafa-201a-11e9-b42b-fa163e917d49",
#        "resourceVersion": "52658",
#        "creationTimestamp": "2019-01-24T20:53:04Z",
#        "annotations": {
#          "openshift.io/description": "Allows all pods in this namespace to pull images from this namespace.  It is auto-managed by a controller; remove subjects to disable."
#        }
#      },
#      "userNames": null,
#      "groupNames": [
#        "system:serviceaccounts:t001"
#      ],
#      "subjects": [
#        {
#          "kind": "SystemGroup",
#          "name": "system:serviceaccounts:t001"
#        }
#      ],
#      "roleRef": {
#        "name": "system:image-puller"
#      }
#    }
#  ]
#}
#
#curl -k -X GET -H "Authorization: Bearer $TOKEN" -H 'Accept: application/json' -H 'Content-Type: application/json' https://$ENPOINT/oapi/v1/namespaces/t001/rolebindings/admin
#{
#  "kind": "RoleBinding",
#  "apiVersion": "v1",
#  "metadata": {
#    "name": "admin",
#    "namespace": "t001",
#    "selfLink": "/oapi/v1/namespaces/t001/rolebindings/admin",
#    "uid": "0b99d36b-201a-11e9-b42b-fa163e917d49",
#    "resourceVersion": "52667",
#    "creationTimestamp": "2019-01-24T20:53:04Z"
#  },
#  "userNames": [
#    "robbaron@bu.edu"
#  ],
#  "groupNames": null,
#  "subjects": [
#    {
#      "kind": "User",
#      "name": "robbaron@bu.edu"
#    }
#  ],
#  "roleRef": {
#    "name": "admin"
#  }
#}
# export TOKEN=`cat /var/run/secrets/kubernetes.io/serviceaccount/token`
# export ENDPOINT=k-openshift.osh.massopen.cloud:8443
# 
# curl -k \
#     -X POST \
#     -d @- \
#     -H "Authorization: Bearer $TOKEN" \
#     -H 'Accept: application/json' \
#     -H 'Content-Type: application/json' \
#     https://$ENDPOINT/oapi/v1/namespaces/test8/rolebindings <<'EOF'
# {
#   "kind": "RoleBinding",
#   "apiVersion": "v1",
#   "metadata": {
#     "name": "admin",
#     "namespace": "test8"
#   },
#   "groupNames": null,
#   "userNames": [
#     "robbaron@bu.edu"
#   ],
#   "roleRef": {
#     "name": "admin"
#   }
# }
# EOF


def exists_openshift_rolebindings(token, api_url, project_name,user_name,role):
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
    url='https://'+api_url+'/oapi/v1/namespaces/'+project_name+'/rolebindings/'+role
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("r: " + str(r.status_code) + "  " + user_name)
    application.logger.warning("r: " + r.text)
    if(r.status_code==200 or r.status_code==201):
        user_set=set(r.json["userNames"])
        if(user_name in user_set):
            return True
    return False

def delete_openshift_rolebindings(token,api_url,project_name,user_name,role):
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
    url='https://'+api_url+'/oapi/v1/namespaces/'+project_name+'/rolebindings'
    payload={ "kind": "RoleBinding", "apiVersion": "v1","metadata": {"name": role, "namespace": project_name }, "groupNames": "null", "userNames": [user_name ], "roleRef": { "name": role } }
    r = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    if (r.status_code==200 or r.status_code==201):
        return "{\"status_code\":\"200\", \"msg\":\""+role+" role deleted from user "+user_name+" in project "+project_name+" \"}"
    return r

def create_openshift_rolebindings(token, api_url, project_name, user_name, role):
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
    url='https://'+api_url+'/oapi/v1/namespaces/'+project_name+'/rolebindings'
    payload={ "kind": "RoleBinding", "apiVersion": "v1","metadata": {"name": role, "namespace": project_name }, "groupNames": None, "userNames": [user_name ], "roleRef": { "name": role } }
    r = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
    application.logger.warning("cr r: " + str(r.status_code))
    application.logger.warning("cr r: " + r.text)
    return r


@application.route("/users/<user_name>/projects/<project_name>/roles/<role>", methods = ['GET'])
def create_rolebindings(project_name,user_name,role):
    # role can be one of Admin, Member, Reader
    (token,openshift_url)=get_token_and_url()
    openshift_role=None
    if(role=="admin"):
        openshift_role="admin"
    elif(role=="member"):
        openshift_role="edit"
    elif(role=="reader"):
        openshift_role="view"
    application.logger.warning("openshift_role " + openshift_role)
    if(openshift_role!=None):
        r=None
        if(request.method=='GET'):
            if(not exists_openshift_rolebindings(token,openshift_url,project_name,user_name,openshift_role)):
                r=create_openshift_rolebindings(token,openshift_url,project_name,user_name,openshift_role)
                if (r.status_code==200 or r.status_code==201):
                    return "{\"status_code\":\"200\", \"msg\":\"role created\"}"
                return " rolebindings unable to be set: "+r.text+" "+str(r.status_code)
            return "{\"status_code\":\"409\", \"msg\":\"msg: role already present\"}"            
        #if(request.method='DELETE'):
        #    if(exists_openshift_projectrole(token,api_url,project_name,user_name,role)):
        #        r=create_openshift_projectrole(token,api_url,project_name,username,role)
        #        if (r.status_code!=200 or r.status_code1=201):
        #            return r
        #    return "{\"status_code\":\"200\", \"msg\":\"role deleted\"}"
    return "{\"status_code\"=\"400\"}"
    


def exists_openshift_project(token, api_url, project_name):
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
    url='https://'+api_url+'/oapi/v1/projects/'+project_name
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    if(r.status_code==200 or r.status_code==201):
        return True
    return False


def create_openshift_project(token, api_url, project_name, user_name):
    # check project_name
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
    url='https://'+api_url+'/oapi/v1/projects'
    payload={ "kind": "Project", "apiVersion":"v1", "metadata": { "name": project_name, "annotations": { "openshift.io/display-name": project_name, "openshift.io/requester": user_name } } }
    r = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r


@application.route("/projects/<project_name>", methods = ['GET'])
@application.route("/projects/<project_name>/owner/<user_name>", methods = ['GET'])
def create_project(project_name,user_name=None):
    (token,openshift_url)=get_token_and_url()
    if(request.method=='GET'):
        #first check the project_name is a valid openshift project name
        suggested_project_name=cnvt_project_name(project_name)
        if(project_name!=suggested_project_name):
            # future work, handel colisons by suggesting a different valid project name
            return "{ \"status_code\": 400, \"msg\":\"ERROR: project name must match regex '[a-z0-9]([-a-z0-9]*[a-z0-9])?'\", \"suggested name\": \""+suggested_project_name+"\"}",422
        if(not exists_openshift_project(token,openshift_url,project_name) ):
            r=create_openshift_project(token,openshift_url,project_name,user_name)
            if(r.status_code==200 and r.status_code==201):
                return "\"status_code\": \"200\", \"msg\":\"project created\" }"
            return r.text + str(r.status_code)
        return "{\"status_code\": \"409\", \"msg\": \"project currently exist: "+project_name+"\"}"
    return "{\"status_code\": \"405\", \"msg\": \"Method: '"+request.method+"' Not found\" }"

def exists_openshift_user(token, api_url, user_name):
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
    url='https://'+api_url+'/oapi/v1/users/'+user_name
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    if(r.status_code==200 or r.status_code==201):
        return True
    return False

def create_openshift_user(token, api_url, user_name, full_name):
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
    url='https://'+api_url+'/oapi/v1/users'
    payload={ "kind": "User", "apiVersion":"v1", "metadata": { "name": user_name }, "fullName": full_name }
    r = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r

def exists_openshift_identity(token, api_url, id_provider, id_user):
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
    url='https://'+api_url+'/oapi/v1/identities/'+id_provider+':' + id_user
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    if(r.status_code==200 or r.status_code==201):
        return True
    return False

def create_openshift_identity(token, api_url, id_provider, id_user):
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
    url='https://'+api_url+'/oapi/v1/identities'
    payload={ "kind": "Identity", "apiVersion":"v1",   "providerName": id_provider, "providerUserName": id_user }
    r = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r

def exists_openshift_useridentitymapping(token, api_url, user_name, id_provider, id_user):
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
 
    url='https://'+api_url+'/oapi/v1/useridentitymappings/'+id_provider+':' + id_user
    r = requests.get(url, headers=headers, verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    # it is probably not necessary to check the user name in the useridentity mapping
    if(r.status_code==200 or r.status_code==201):
        return True
    return False

def create_openshift_useridentitymapping(token, api_url, user_name, id_provider, id_user):
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
    url='https://'+api_url+'/oapi/v1/useridentitymappings'
    payload={ "kind": "UserIdentityMapping", "apiVersion":"v1", "user": {"name": user_name }, "identity": {"name": id_provider + ":" + id_user } }
    r = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
    application.logger.warning("r: " + str(r.status_code))
    application.logger.warning("r: " + r.text)
    return r

@application.route("/users/<user_name>", methods = ['GET'])
@application.route("/users/<user_name>/fullname/<full_name>", methods = ['GET'])
@application.route("/users/<user_name>/fullname/<full_name>/<identity>/<id_user>", methods = ['GET'])
def create_user(user_name, full_name=None, id_provider="sso_auth", id_user=None):
    token = get_user_token('/kube/config','moc-openshift-acct-req')
    openshift_url="k-openshift.osh.massopen.cloud:8443"
    headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json', 'Content-Type': 'application/json' }
    r=None

    if(request.method=='GET'):
        #use case if User doesn't exist, then create
        if(not exists_openshift_user(token,openshift_url,user_name)):
            r=create_openshift_user(token,openshift_url,user_name,full_name)
            if(r.status_code!=200 and r.status_code!=201):
                return r.text + str(r.status_code)
        if( id_user is None):
            id_user=user_name
        #if identity doesn't exist then create
        if(not exists_openshift_identity(token,openshift_url,id_provider,id_user)):
            r=create_openshift_identity(token,openshift_url,id_provider,id_user)
            if(r.status_code!=200 and r.status_code!=201):
                return r.text + str(r.status_code)
        #creates the useridenitymapping   
        if(not exists_openshift_useridentitymapping(token,openshift_url,user_name,id_provider,id_user)):
            r=create_openshift_useridentitymapping(token,openshift_url,user_name,id_provider,id_user)
            if(r.status_code!=200 and r.status_code!=201):
                return r.text + str(r.status_code)
        return "{\"status_code\": \"200\", \"msg\": \"Created User:"+user_name+" with identity: "+id_provider+":"+id_user+" \"}",200
    return "{\"status_code\": \"405\", \"msg\": \"Method: '"+request.method+"' Not found\" }",405

@application.route("/users/<user_name>/projects/<project_name>/roles/<role>")
def map_project(user_name,project_name,role):
    # "oc login -u acct-req-sa"
    # "oc adm policy -n <project_name> add-role-to-user <role> <user_name>"
    return "{\"map\"}"

if __name__ == "__main__":
    application.run()
