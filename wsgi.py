import kubernetes
from openshift.dynamic import DynamicClient
import pprint
import logging
from flask import Flask

application = Flask(__name__)

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    application.logger.handlers = gunicorn_logger.handlers
    application.logger.setLevel(gunicorn_logger.level)

@application.route("/projects/<project_name>")
def create_project(project_name):
    # "oc login -u acct-req-sa"
    k8s_client = kubernetes.config.new_client_from_config()
    dyn_client = DynamicClient(k8s_client)

    # This is a standard Kubernetes definition for a Service
    service = "{ }" 
        #+ "\"kind\": \"Service\","
        #+ "\"apiVersion\": \"v1\","
        #+ "\"metadata\": {"
        #+     "\"name\": \"my-service\""
        #+ "},"
        #+ "\"spec\": {"
        #+     "\"selector\": {"
        #+         "\"app\": \"MyApp\""
        #+     "},"
        #+ "\"ports\": [{"
        #+     "\"protocol\": \"TCP\","
        #+     "\"port\": 8080,"
        #+     "\"targetPort\": 9376,"
        #+     "}]"
        #+"}"
        #+"}"
    resp = v1_services.create(body=service, namespace='acct-req')
    # "oc create project <project_name>"
    return "{\"create project\"}"

@application.route("/users/<user_name>")
@application.route("/users/<user_name>/fullname/<full_name>")
@application.route("/users/<user_name>/fullname/<full_name>/<identity>/<id_name>")
def create_user(user_name, full_name=null, identity="SSO_AUTH", id_name=null):
    # "oc login -u acct-req-sa"
    # "oc create user <user_name>"
    # "oc create identity <identity_provider>:<user_name from identity provider>"
    # "oc create useridentitymapping <identity_provider>:<user_name from identity provider> <user_name>"
    #pp = pprint.PrettyPrinter(indent=4)
    #k8s_client = kubernetes.config.new_client_from_config()
    #dyn_client = DynamicClient(k8s_client)
    #v1_users = dyn_client.resources.get(api_version='v1', kind='User')
    #application.logger.warning("Users: " + pp.pformat(v1_users));
    #user = "{\"apiVersion\":\"v1\",\"kind\":\"User\":\"" + user_name + "\",\"identities\":[\"keystone_auth:robbaron@bu.edu\"],\"groups\":null,\"metadata\":{\"name\":\"test\"}}"
    #     #  { "apiVersion": "user.openshift.io/v1", "groups": null, "identities": [ "keystone_auth:robbaron@bu.edu" ], "kind": "User", "metadata": { "name": "test" } }
    application.logger.warning("Users2: " + user);
    resp = v1_users.create(body=user)
    token = get_user_token('/kube/config','moc-openshift-acct-req')
    url='https://k-openshift.osh.massopen.cloud:8443/oapi/v1";
    headers={'Authorizations': 'Bearer '+token }
    payload={ 
        "apiVersion":"v1",
        "kind":"User": user_name,
        "groups":null,
        "metadata":
            {
            "name":full_name
            }
 
        }
    json = requests.get(url, headers=headers, data=json.dumps(payload), verify=false)
    return "{\"create user\"}"

@application.route("/users/<user_name>/projects/<project_name>/roles/<role>")
def map_project(user_name,project_name,role):
    # "oc login -u acct-req-sa"
    # "oc adm policy -n <project_name> add-role-to-user <role> <user_name>"
    return "{\"map\"}"

if __name__ == "__main__":
    application.run()
