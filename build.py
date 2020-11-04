#!/usr/bin/python3

import subprocess
import sys
import re
import json
import time

def wait_until_container_is_ready():
    p1=re.compile("pod")
    p2=re.compile("Running")
    done=False
    matched_line=""
    while not done:
        time.sleep(5)
        result=subprocess.run(['oc','-n','acct-mgt-2','get','all'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        lines=result.stdout.decode('utf-8').split('\n')
        cnt = 0
        for l in lines:
            if(p1.match(l)):
                matched_line=l
                cnt = cnt + 1
        print("cnt = " + str(cnt))
        if(cnt==1):
            done=True
    if(p2.match(matched_line)):
        return True
    return False

def build_and_deploy(docker_image):
    subprocess.run(['docker','build','-f','Dockerfile.x86','-t',docker_image,'.'])
    subprocess.run(['docker','push',docker_image])
    subprocess.run(['oc','-n','acct-mgt-2','rollout','latest','acct-mgt-2'])
    result=subprocess.run(['oc','get','all'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return True

def compare_results(result, pattern):
    if(result is not None):
        p1=re.compile(pattern)
        lines=result.stdout.decode('utf-8').split('\n')
        cnt = 0
        for l in lines:
            if(p1.match(l)):
                return True
    return False

def oc_service_account_exists(project, service_account):
    # TODO check privledge
    result=subprocess.run(['oc', '-n', project, 'get', 'sa', service_account],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if(compare_results(result,r'^'+service_account)):
        return True
    return False


def oc_create_service_account(project, service_account, privledge):
    subprocess.run(['oc', r'-n', project, 'create', 'sa',service_account])
    subprocess.run(['oc', 'adm', 'policy', r'add-cluster-role-to-user', privledge, r'system:serviceaccount:' + project + r':' + service_account])
    return True


def oc_project_exists(project):
    result=subprocess.run(['oc', 'get', 'project', project],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if(compare_results(result,r'^'+project)):
        return True
    return False


def oc_create_project(project):
    subprocess.run(['oc','new-project',project])
    return True


def oc_route_exists(project,route,host_subdomain):
    result=subprocess.run(['oc', r'-n',project, 'get', 'route', route],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if(compare_results(result,r'^'+route)):
        return True
    return False

def oc_create_route(project,route,host_subdomain,service):
    subprocess.run(['oc', r'-n',project, 'create', 'route', 'edge', r'--service=' + service, r'--hostname='+route+'.'+host_subdomain])
    subprocess.run(['oc', r'-n',project, 'annotate', 'route',route, r'kubernetes.io/tls-acme=true'])
    return True

def oc_dc_exists(project,dc):
    result=subprocess.run(['oc', r'-n',project, 'get', 'dc', dc],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if(compare_results(result,r'^'+dc)):
        return True
    return False


def get_dc_def(openshift_url,microserver_url,project,docker_image):
    dc=""
    if(openshift_url is not None and len(openshift_url)>0 and
       microserver_url is not None and len(microserver_url)>0 and
       project is not None and len(project)>0 and
       docker_image is not None and len(docker_image)>0):
        dc='apiVersion: v1\n' \
        +'kind: DeploymentConfig\n' \
        +'metadata: \n' \
        +'  name: '+ project +'\n' \
        +'  labels:\n' \
        +'    app: '+ project +'\n' \
        +'spec:\n' \
        +'  replicas: 1\n' \
        +'  selector:\n' \
        +'    app: '+project+'\n' \
        +'    deploymentconfig: '+project+'\n' \
        +'  strategy:\n' \
        +'    activeDeadlineSeconds: 21600\n' \
        +'    rollingParams:\n' \
        +'      intervalSeconds: 1\n' \
        +'      maxSurge: 25%\n' \
        +'      maxUnavailable: 25%\n' \
        +'      timeoutSeconds: 600\n' \
        +'      updatePeriodSeconds: 1\n' \
        +'    type: Rolling\n' \
        +'  template:\n' \
        +'    metadata:\n' \
        +'      labels:\n' \
        +'        app: '+project+'\n' \
        +'        deploymentconfig: '+project+'\n' \
        +'    spec:\n' \
        +'      serviceAccountName: '+project+'-sa\n' \
        +'      automountServiceAccountToken: True\n' \
        +'      containers:\n' \
        +'      - env:\n' \
        +'        - name: openshift_url\n' \
        +'          value: '+openshift_url+'\n' \
        +'        image: '+docker_image+'\n' \
        +'        imagePullPolicy: Always\n' \
        +'        name: '+project+'\n' \
        +'        resources:\n' \
        +'          limits:\n' \
        +'            memory: 1024Mi\n' \
        +'            cpu: 2000m\n' \
        +'          requests:\n' \
        +'            memory: 150Mi\n' \
        +'            cpu: 250m\n' \
        +'        #terminationMessagePath: /dev/termination-log\n' \
        +'      dnsPolicy: ClusterFirst\n' \
        +'      restartPolicy: Always\n' \
        +'      terminationGracePeriodSeconds: 30\n' \
        +'    paramters:\n' \
        +'    - name: "openshifturl"\n' \
        +'      displayName: "OpenShift URL"\n' \
        +'      description: "The OpenShift Master URL - because openshift pods don\'t know their master"\n' \
        +'      required: true"\n' \
        +'      value: ' + openshift_url + '\n' \
        +'  test: False\n' \
        +'  triggers:\n' \
        +'  - type: ConfigChange\n'
    return dc

def oc_create_dc(openshift_url,microserver_url,project,docker_image):
    proc=subprocess.Popen(['oc','create','-f','-'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,stdin=subprocess.PIPE)
    proc.communicate(get_dc_def(openshift_url,microserver_url,project,docker_image).encode())
    return 1

def oc_service_exists(project,service):
    result=subprocess.run(['oc', r'-n',project, 'get', 'service', service],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if(compare_results(result,r'^'+service)):
        return True
    return False

#apiVersion: v1
#kind: Service
#metadata:
#  creationTimestamp: 2019-09-26T13:47:48Z
#  labels:
#    app: acct-mgt
#  name: acct-mgt
#  namespace: acct-mgt
#  resourceVersion: "879306"
#  selfLink: /api/v1/namespaces/acct-mgt/services/acct-mgt
#  uid: 39b978e4-e064-11e9-9cfd-fa163e2bb38b
#spec:
#  clusterIP: 172.30.195.49
#  externalIPs:
#  - 172.29.230.64
#  externalTrafficPolicy: Cluster
#  ports:
#  - nodePort: 30002
#    port: 8080
#    protocol: TCP
#    targetPort: 8080
#  selector:
#    app: acct-mgt
#    deploymentconfig: acct-mgt
#  sessionAffinity: None
#  type: LoadBalancer
#status:
#  loadBalancer:
#    ingress:
#    - ip: 172.29.230.64


def get_svc_def(project,service,port=8080):
    svc=""
    if(project is not None and len(project)>0 and port is not None):
        svc='{ "kind": "Service",' \
            + '"apiVersion": "v1",' \
            + '"metadata":' \
            +  '{ "name": "'+service+'",' \
            +    '"namespace":"'+project+'" },' \
            +    '"spec": { ' \
            +      '"ports": [ ' \
            +          '{ "protocol": "TCP", "port": '+str(port)+', "targetPort": '+str(port)+' }' \
            +      '], '\
            +    '"type":"LoadBalancer",' \
            +    '"externalTrafficPolicy": "Cluster",' \
            +    '"selector":{'\
            +        '"app":"'+project+'",'\
            +        '"deploymentconfig": "'+project+'" }' \
            +   '} }'
    return svc

def oc_create_service(project,port=8080):
    proc=subprocess.Popen(['oc','-n',project,'create','-f','-'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,stdin=subprocess.PIPE)
    json_str=get_svc_def(project,port)
    print("service json: "+json_str)
    proc.communicate(json_str.encode())
    #printing stdout doesn't seem to work.
    #print()
    return 1

def build_and_deploy2(openshift_url, project,microserver_url,host_subdomain,docker_image):
    #subprocess.run(['docker','build','-f','Dockerfile.x86','-t','docker.io/robertbartlettbaron/'+project+'.x86','.'])
    #subprocess.run(['docker','push','docker.io/robertbartlettbaron/'+project+'.x86'])
    if(not oc_project_exists(project)):
        oc_create_project(project)
    if(not oc_service_account_exists(project, project+"-sa")):
        oc_create_service_account(project, project+"-sa", "cluster-admin")
    if(not oc_dc_exists(project,project)):
        oc_create_dc(openshift_url,microserver_url,project,docker_image)
    if(not oc_service_exists(project,project)):
        oc_create_service(project,project)
    if(not oc_route_exists(project, project,host_subdomain)):
        oc_create_route(project,project,host_subdomain,project)


    #subprocess.run(['oc','-n','acct-mgt','rollout','latest',project])
    #result=subprocess.run(['oc','get','all'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    #return wait_until_container_is_ready()

def main():
    # export MICROSERVER_URL=https://acct-req.k-apps.osh.massopen.cloud
    # export MICROSERVER_URL=https://acct-mgt-acct-mgt.s-apps.osh.massopen.cloud
    microserver_url='https://acct-mgt-acct-mgt.s-apps.osh.massopen.cloud'
    project="acct-mgt-test-3"
    openshift_url="s-openshift.osh.massopen.cloud:8443"
    #openshift_url="192.168.42.52:8443"
    host_subdomain="s-apps.osh.massopen.cloud"
    docker_image="docker.io/surbhi0129/acct-mgt"
    docker_version=":latest"
    build_and_deploy(docker_image)
    build_and_deploy2(openshift_url, project, microserver_url, host_subdomain,docker_image+docker_version)

main()

