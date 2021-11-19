#!/usr/bin/python3

# To run:
#    1) login as cluster admin
#        oc login -u [cluster-admin account] -
import subprocess
import sys
import re
import time
import json
import pprint


def usage_msg():
    print(
        """
        Purpose:
        
        To build and deploy an administrative microservice to automate some administrative activities

        Usage: 

        build.py [project] [service] [openshift's app url] [openshift's api url] [openshift_version] [docker_file] [docker_image] [opt username] [opt password]

        Examples:
api.crc.testing
        build.py "acct-mgt-2" "acct-mgt" s-apps.osh.massopen.cloud "s-openshift.osh.massopen.cloud:8443" "3.11" "Dockerfile.x86" "docker.io/robertbartlettbaron/acct-mgt.x86:latest"
        build.py "acct-mgt" "acct-mgt" k-apps.osh.massopen.cloud "k-openshift.osh.massopen.cloud:8443" "3.11" "Dockerfile.x86" "docker.io/robertbartlettbaron/acct-mgt.x86:latest" <username> <password>
        build.py "acct-mgt" "acct-mgt" "apps.cnv.massopen.cloud" "api.cnv.massopen.cloud:6443" "4.5" "Dockerfile.x86" "docker.io/robertbartlettbaron/acct-mgt.x86:latest" <username> <password>
    """
    )


def get_pod_status(project, pod_name):
    result = subprocess.run(
        ["oc", "-n", project, "-o", "json", "get", "pod", pod_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode == 0:
        result_json = json.loads(result.stdout.decode("utf-8"))
        print(result_json["status"]["phase"])
        return result_json["status"]["phase"]
    print("None")
    return None


# pass in the following parameter:
#   project,pod_name: identify the pod
#   statuses: the array of statuses to wait for
def wait_while(project, pod_name, statuses, time_out=300):
    time_left = time_out
    time_interval = 5
    time.sleep(time_interval)
    status = get_pod_status(project, pod_name)
    while status in statuses and time_left > 0:
        time.sleep(time_interval)
        time_left = time_left - time_interval
        status = get_pod_status(project, pod_name)

    if status in statuses:
        return False
    return True


def build_docker_image(docker_file, image_name):
    subprocess.run(["docker", "build", "-f", docker_file, "-t", image_name, "."])
    subprocess.run(["docker", "push", image_name])


def oc_rollout_dc(project, dc_name):
    result = subprocess.run(
        ["oc", "-n", project, "-o", "json", "rollout", "latest", dc_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode == 0:
        result_json = json.loads(result.stdout.decode("utf-8"))
        dc_pod_name = (
            result_json["metadata"]["name"]
            + "-"
            + str(result_json["status"]["latestVersion"])
            + "-deploy"
        )
        return wait_while(
            project, dc_pod_name, ["ContainerCreation", "Pending", "Running"]
        )
    return False


def oc_service_account_exists(project, service_account):
    result = subprocess.run(
        ["oc", "-o", "json", "-n", project, "get", "sa", service_account],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode == 0:
        result_json = json.loads(result.stdout.decode("utf-8"))
        if (
            result_json["kind"] == "ServiceAccount"
            and result_json["metadata"]["name"] == service_account
        ):
            return True
    return False


def oc_sa_role_exists(project, service_account, cluster_role):
    result = subprocess.run(
        ["oc", "-o", "json", "get", "clusterrolebindings"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode == 0:
        result_json = json.loads(result.stdout.decode("utf-8"))
        for item in result_json["items"]:
            if (
                item["kind"] == "ClusterRoleBinding"
                and item["roleRef"]["name"] == cluster_role
            ):
                for sub in item["subjects"]:
                    if (
                        sub["kind"] == "ServiceAccount"
                        and sub["namespace"] == project
                        and sub["name"] == service_account
                    ):
                        return True
    return False


def oc_create_service_account(project, service_account, cluster_role):
    if not oc_service_account_exists(project, service_account):
        result = subprocess.run(
            ["oc", "-o", "json", "-n", project, "create", "sa", service_account],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    # short circuit this as a work-a-round
    # TODO: fix oc_sa_role_exists
    if True or not oc_sa_role_exists(project, service_account, cluster_role):
        # oc adm policy add-cluster-role-to-user cluster-admin -n acct-mgt-2 -z acct-mgt-2-sa
        result = subprocess.run(
            [
                "oc",
                "-o",
                "json",
                "-n",
                project,
                "adm",
                "policy",
                r"add-cluster-role-to-user",
                cluster_role,
                "-z",
                service_account,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )


def oc_project_exists(project):
    result = subprocess.run(
        ["oc", "-o", "json", "get", "project", project],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode == 0:
        result_json = json.loads(result.stdout.decode("utf-8"))
        if (
            result_json["kind"] == "Project"
            and result_json["metadata"]["name"] == project
        ):
            return True
    return False


def oc_create_project(project):
    subprocess.run(["oc", "new-project", project])


def oc_service_exists(project, service):
    result = subprocess.run(
        ["oc", "-n", project, "-o", "json", "get", "service", service],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode == 0:
        result_json = json.loads(result.stdout.decode("utf-8"))
        if (
            result_json["kind"] == "Service"
            and result_json["metadata"]["name"] == service
        ):
            return True
    return False


def oc_dc_exists(project, dc):
    result = subprocess.run(
        ["oc", r"-n", project, "-o", "json", "get", "dc", dc],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode == 0:
        result_json = json.loads(result.stdout.decode("utf-8"))
        if (
            result_json["kind"] == "DeploymentConfig"
            and result_json["metadata"]["name"] == dc
        ):
            return True
    return False


def get_dc_def(openshift_url, openshift_version, project, docker_image, configmap_name):
    dc = ""
    if (
        openshift_url is not None
        and len(openshift_url) > 0
        and project is not None
        and len(project) > 0
        and docker_image is not None
        and len(docker_image) > 0
    ):
        dc = {
            "apiVersion": "v1",
            "kind": "DeploymentConfig",
            "metadata": {"name": project, "labels": {"app": project}},
            "spec": {
                "replicas": 1,
                "selector": {"app": project, "deploymentconfig": project},
                "strategy": {
                    "activeDeadlineSeconds": 21600,
                    "rollingParams": {
                        "intervalSeconds": 1,
                        "maxSurge": "25%",
                        "maxUnavailable": "25%",
                        "timeoutSeconds": 600,
                        "updatePeriodSeconds": 1,
                    },
                    "type": "Rolling",
                },
                "template": {
                    "metadata": {
                        "labels": {"app": project, "deploymentconfig": project}
                    },
                    "spec": {
                        "serviceAccountName": project + "-sa",
                        "automountServiceAccountToken": True,
                        "containers": [
                            {
                                "env": [
                                    {"name": "OPENSHIFT_URL", "value": openshift_url},
                                    {
                                        "name": "OPENSHIFT_VERSION",
                                        "value": openshift_version,
                                    },
                                ],
                                "image": docker_image,
                                "imagePullPolicy": "Always",
                                "name": project,
                                "resources": {
                                    "limits": {"memory": "1024Mi", "cpu": "2000m"},
                                    "requests": {"memory": "150Mi", "cpu": "250m"},
                                },
                                "volumeMounts": [
                                    {
                                        "mountPath": "/app/auth",
                                        "name": "admin-pass",
                                        "readOnly": True,
                                    },
                                ],
                                "ports": [{"containerPort": 8080, "protocol": "TCP"}],
                            }
                        ],
                        "dnsPolicy": "ClusterFirst",
                        "restartPolicy": "Always",
                        "terminationGracePeriodSeconds": 30,
                        "volumes": [
                            {
                                "name": "admin-pass",
                                "configMap": {
                                    "name": configmap_name,
                                    "items": [{"key": "user-data", "path": "users"}],
                                },
                            }
                        ],
                    },
                    "paramters": [
                        {
                            "name": "OPENSHIFT_URL",
                            "displayName": "OpenShift URL",
                            "description": "The OpenShift Master URL - because openshift pods don't know their master",
                            "required": True,
                            "value": openshift_url,
                        },
                        {
                            "name": "OPENSHIFT_VERSION",
                            "displayName": "OpenShift URL",
                            "description": "The OpenShift Master URL - because openshift pods don't know their master",
                            "required": True,
                            "value": openshift_version,
                        },
                    ],
                },
                "test": False,
                "triggers": [{"type": "ConfigChange"}],
            },
        }
    return json.dumps(dc)


# apiVersion: v1
# imagePullSecrets:
# - name: acct-mgt-2-sa-dockercfg-vm58v
# kind: ServiceAccount
# metadata:
#  creationTimestamp: 2020-06-30T15:53:47Z
#  name: acct-mgt-2-sa
#  namespace: acct-mgt-2
#  resourceVersion: "7721457"
#  selfLink: /api/v1/namespaces/acct-mgt-2/serviceaccounts/acct-mgt-2-sa
#  uid: e20d40a3-bae9-11ea-9ff6-fa163eb966c2
# secrets:
# - name: acct-mgt-2-sa-token-6jtcp
# - name: acct-mgt-2-sa-dockercfg-vm58v


def oc_create_dc(
    openshift_url, openshift_version, project, docker_image, configmap_name
):
    proc = subprocess.Popen(
        ["oc", "create", "-f", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
    )
    dc = get_dc_def(
        openshift_url, openshift_version, project, docker_image, configmap_name
    )
    print(dc)
    proc.communicate(dc.encode())


def get_svc_def(project, service, port=8080):
    svc = ""
    if project is not None and len(project) > 0 and port is not None:
        svc = {
            "kind": "Service",
            "apiVersion": "v1",
            "metadata": {"name": service, "namespace": project},
            "spec": {
                "ports": [
                    {
                        "name": "8080-tcp",
                        "protocol": "TCP",
                        "port": 8080,
                        "targetPort": port,
                    }
                ],
                "type": "ClusterIP",
                "selector": {"app": project, "deploymentconfig": project},
            },
        }
    return json.dumps(svc)


def oc_create_service(project, port=8080):
    proc = subprocess.Popen(
        ["oc", "-n", project, "create", "-f", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
    )
    json_str = get_svc_def(project, port)
    print("\n\n")
    print(json_str.encode())
    print("\n\n")
    proc.communicate(json_str.encode())


def oc_route_exists(project, route, host_subdomain):
    result = subprocess.run(
        ["oc", "-n", project, "-o", "json", "get", "route", route],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode == 0:
        result_json = json.loads(result.stdout.decode("utf-8"))
        if (
            result_json["kind"] == "Project"
            and result_json["metadata"]["name"] == route
        ):
            return True
    return False


def get_route_def(project, route, app_url, service):
    route = {
        "apiVersion": "route.openshift.io/v1",
        "kind": "Route",
        "metadata": {
            "name": route,
            "namespace": project,
            "labels": {"app": project},
        },
        "spec": {
            "host": route + "." + app_url,
            "port": {"targetPort": "8080-tcp"},  # defined in the service !!!
            "tls": {"termination": "edge"},
            "to": {"kind": "Service", "name": service, "weight": 100},
        },
    }
    return json.dumps(route)


def oc_create_route(project, route, app_url, service):
    proc = subprocess.Popen(
        ["oc", "create", "-f", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
    )
    r = get_route_def(project, route, app_url, service)
    print("\n\n")
    print(r.encode())
    print("\n\n")
    proc.communicate(r.encode())


def get_pass_configmap(project, cm_name, username, password):
    configmap = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": cm_name,
            "namespace": project,
            "labels": {"app": project},
        },
        "data": {"user-data": username + " " + password},
    }
    return json.dumps(configmap)


def oc_create_cm_pass(project, cm_name, username, password):
    proc = subprocess.Popen(
        ["oc", "create", "-f", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
    )
    cm = get_pass_configmap(project, cm_name, username, password)
    print("\n\n")
    print(cm.encode())
    print("\n\n")
    proc.communicate(cm.encode())


def create_objects(
    openshift_url,
    openshift_version,
    app_url,
    project,
    service,
    docker_image,
    username,
    password,
):
    if not oc_project_exists(project):
        oc_create_project(project)
    if not oc_service_account_exists(project, project + "-sa") or not oc_sa_role_exists(
        project, project + "-sa", "cluster-admin"
    ):
        oc_create_service_account(project, project + "-sa", "cluster-admin")
    if not oc_service_exists(project, service):
        oc_create_service(project, service)
    if not oc_route_exists(project, project, app_url):
        oc_create_route(project, project, app_url, project)
    cm_name = "admin-pass"
    # if oc_cm_pass_exists(project, cm_name):
    #    oc_delete_configmap(project, cm_name)
    oc_create_cm_pass(project, cm_name, username, password)

    if not oc_dc_exists(project, project):
        oc_create_dc(openshift_url, openshift_version, project, docker_image, cm_name)
    else:
        oc_rollout_dc(project, project)


def main():
    # TODO: make the commandline interface more reasonable
    #      1) doing a docker build should be optional
    #      2) generating all of the certificates should be optional
    if len(sys.argv) in [8, 10]:
        project = str(sys.argv[1])
        service = str(sys.argv[2])
        app_url = str(sys.argv[3])
        openshift_url = str(sys.argv[4])
        openshift_version = str(sys.argv[5])
        docker_file = str(sys.argv[6])
        docker_image = str(sys.argv[7])
        username = ""
        password = ""
        if len(sys.argv) == 10:
            username = str(sys.argv[8])
            password = str(sys.argv[9])
        if not oc_project_exists(project):
            oc_create_project(project)
        #build_docker_image(docker_file, docker_image)

        if not oc_project_exists(project):
            oc_create_project(project)

        create_objects(
            openshift_url,
            openshift_version,
            app_url,
            project,
            service,
            docker_image,
            username,
            password,
        )
    elif len(sys.argv) == 3:
        docker_file = str(sys.argv[1])
        docker_image = str(sys.argv[2])
        build_docker_image(docker_file, docker_image)
    else:
        print(len(sys.argv))
        usage_msg()


main()
