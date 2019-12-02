#!/usr/bin/python3
import subprocess
import re
import time
import unittest

def get_microserver():
    # export MICROSERVER_URL=https://acct-req.k-apps.osh.massopen.cloud 
    # export MICROSERVER_URL=https://acct-mgt-acct-mgt.s-apps.osh.massopen.cloud
    microserver_url='https://acct-mgt-acct-mgt.s-apps.osh.massopen.cloud'
    return microserver_url;

def wait_until_container_is_ready():
    p1=re.compile("pod")
    p2=re.compile("Running")
    done=False
    matched_line=""
    while not done:
        time.sleep(5)
        result=subprocess.run(['oc','get','all'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT) 
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

def build_and_deploy():
    subprocess.run(['docker','build','-f','Dockerfile.x86','-t','docker.io/robertbartlettbaron/acct-mgt.x86','.'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    subprocess.run(['docker','push','docker.io/robertbartlettbaron/acct-mgt.x86'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    subprocess.run(['oc','rollout','latest','acct-mgt'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    result=subprocess.run(['oc','get','all'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT) 
    return wait_until_container_is_ready()

def user(user_name, op, success_pattern):
    microserver_url=get_microserver();
    if(op=='add'):
        url_op="GET"
    elif(op=='del'):
        url_op="DELETE"
        
    result=subprocess.run(['curl',"-X","GET","-kv",url+"/users/"+user_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    result=subprocess.run(['oc', 'get', 'user', user_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

def compare_results(result, pattern):
    if(result is not None):
        p1=re.compile(pattern)
        lines=result.stdout.decode('utf-8').split('\n')
        cnt = 0
        for l in lines:
            if(p1.match(l)):
                return True
    return False

def oc_resource_exist(resource, name, true_pattern, false_pattern):
    result=subprocess.run(['oc', 'get', resource, name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if(compare_results(result,true_pattern)):
        return True
    if(compare_results(result,false_pattern)):
        return False
    return False

def ms_create_project(project_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","GET","-kv",microserver_url+"/projects/"+project_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    #print("result: "+result.stdout.decode('utf-8') +"\n\n")
    # {"msg": "project created \(test\-001\)"}
    if(compare_results(result,'{"msg": "project created \('+project_name+'\)"}')):
        return True
    return False

def ms_delete_project(project_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","DELETE","-kv",microserver_url+"/projects/"+project_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    #print("result: "+result.stdout.decode('utf-8') +"\n\n")
    # {"msg": "project deleted (test-001)"}
    if(compare_results(result,'{"msg": "project deleted \('+project_name+'\)"}')):
        return True
    return False

def ms_project_user_role(project_name, user_name, role, success_pattern):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","GET","-kv",microserver_url+"/projects/"+project_name+"/users/"+user_name+"/roles/"+role],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if(compare_results(result,"{\"msg\": \"user created \("+user_name+"\)\" }")):
        return True
    return False

def ms_create_user(user_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","GET","-kv",microserver_url+"/users/"+user_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print("result: "+result.stdout.decode('utf-8') +"\n\n")
    # {"msg": "user created (test01)"}
    if(compare_results(result,'{"msg": "user created \('+user_name+'\)"}')):
        return True
    return False

def ms_delete_user(user_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","DELETE","-kv",microserver_url+"/users/"+user_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print("result: "+result.stdout.decode('utf-8') +"\n\n")
    if(compare_results(result,"{\"msg\": \"user deleted \("+user_name+"\)\"}")):
        return True
    return False

class TestStringMethods(unittest.TestCase):

    def test_project(self):
        #if(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
        #    print("Error: test_project failed as a project with a name of test-001 exists.  Please delete first and rerun the tests\n")
        #    self.assertTrue(False)

        # test project creation
        if(not oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
            self.assertTrue(ms_create_project('test-001'))
        self.assertTrue(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found'))

        # test creation of a second project with the same name
        if(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
            self.assertFalse(ms_create_project('test-001'))
        self.assertTrue(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found'))

        # test project deletion
        if(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
            self.assertTrue(ms_delete_project('test-001'))
        self.assertTrue(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found'))

        # test deleting a project that was deleted
        if(not oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
            self.assertTrue(ms_create_project('test-001'))
        self.assertTrue(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found'))

    def test_user(self):
        # test user creation
        # test01                    bfd6dab5-11f3-11ea-89a6-fa163e2bb38b                         sso_auth:test01
        if(not oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found')):
            self.assertTrue(ms_create_user('test01'))
        self.assertTrue(oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found'))

        # test creation of a second user with the same name
        if(oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found')):
            self.assertFalse(ms_create_user('test01'))
        self.assertTrue(oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found'))

        # test user deletion
        if(oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found')):
            self.assertTrue(ms_delete_user('test01'))
        self.assertTrue(oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found'))

        # test deleting a user that was deleted
        if(not oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found')):
            self.assertTrue(ms_create_user('test01'))
        self.assertTrue(oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found'))


    #def test_project_user_role(self):
    #def test_quota(self):


if __name__ == '__main__':
    unittest.main()
