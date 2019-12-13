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

# Don't use this one.
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

# A more general wait
def wait_until_done(oc_cmd, finished_pattern, time_out=30, decrement=5):
    p1=re.compile(finished_pattern)
    p2=re.compile("Running")
    done=False
    oc_array=oc_cmd.split(" ")
    matched_line=""
    while time_out>0 and not done:
        time.sleep(5)
        time_out=time_out-decrement
        result=subprocess.run(oc_array,stdout=subprocess.PIPE,stderr=subprocess.STDOUT) 
        lines=result.stdout.decode('utf-8').split('\n')
        cnt = 0
        for l in lines:
            if(p1.match(l)):
                matched_line=l
                done=True
    if(p1.match(matched_line)):
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

def oc_resource_exist(resource, name, true_pattern, false_pattern, project=None):
    result=None
    if(project is None):
        result=subprocess.run(['oc', 'get', resource, name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    else:
        result=subprocess.run(['oc', '-n', project, 'get', resource, name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    #print("\nresult: \n\n"+result.stdout.decode('utf-8'))
    #print("\nT pattern: "+true_pattern)
    #print("\nF pattern: "+false_pattern)
    if(compare_results(result,true_pattern)):
        return True
    if(compare_results(result,false_pattern)):
        return False
    return False

def ms_create_project(project_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","GET","-kv",microserver_url+"/projects/"+project_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    # {"msg": "project created \(test\-001\)"}
    if(compare_results(result,'{"msg": "project created \('+project_name+'\)"}')):
        return True
    return False

def ms_delete_project(project_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","DELETE","-kv",microserver_url+"/projects/"+project_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    # {"msg": "project deleted (test-001)"}
    if(compare_results(result,'{"msg": "project deleted \('+project_name+'\)"}')):
        return True
    return False



def ms_create_user(user_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","GET","-kv",microserver_url+"/users/"+user_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    # {"msg": "user created (test01)"}
    if(compare_results(result,'{"msg": "user created \('+user_name+'\)"}')):
        return True
    return False

def ms_delete_user(user_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","DELETE","-kv",microserver_url+"/users/"+user_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    #print("result: "+result.stdout.decode('utf-8') +"\n\n")
    if(compare_results(result,'{"msg": "user deleted \('+user_name+'\)"}')):
        return True
    return False


def ms_user_project_add_role(user_name, project_name, role, success_pattern):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","GET","-kv",microserver_url+"/users/"+user_name+"/projects/"+project_name+"/roles/"+role],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print("--> result: "+result.stdout.decode('utf-8') +"\n\n")
    if(compare_results(result,success_pattern)):
        return True
    return False

def ms_user_project_remove_role(user_name, project_name, role, success_pattern):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","DELETE","-kv",microserver_url+"/users/"+user_name+"/projects/"+project_name+"/roles/"+role],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print("--> result: "+result.stdout.decode('utf-8') +"\n\n")
    if(compare_results(result,success_pattern)):
        return True
    return False

def check_result(test,result):
    if(test):
        return result
    return result+1
    
class TestStringMethods(unittest.TestCase):

    def test_project(self):
        result=0

        if(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
            print("Error: test_project failed as a project with a name of test-001 exists.  Please delete first and rerun the tests\n")
            self.assertTrue(False)

        # test project creation
        if(not oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
            ms_create_project('test-001')
            if( not wait_until_done('oc get project test-001', 'test-001[ \t]+test-001[ \t]+Active') ):
                print("Create Project Failed")
        result=check_result(oc_resource_exist("project", "test-001",'test-001[ \t]+test-001[ \t]+Active','Error from server (NotFound): namespaces "test-001" not found'),result)
        print("A: "+str(result))
        
        # test creation of a second project with the same name
        if(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
            if( ms_create_project('test-001') ):
                print("Create Project succeed where it should have failed")
        result=check_result(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found'),result)
        print("B: "+str(result))
        
        # test project deletion
        if(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
            ms_delete_project('test-001')
            # Wait until test-001 is terminated
            if(not wait_until_done('oc get project test-001', 'Error from server \(NotFound\): namespaces "test-001" not found') ):
                print("delete project failed to delete project")
        result=check_result(not oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found'),result)
        print("c: "+str(result))
        
        # test deleting a project that was deleted
        if(not oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
            if( ms_delete_project('test-001') ):
                print("delete project succeeded where it should have failed")
        result=check_result(not oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found'),result)
        print("D: "+str(result))
        
        self.assertTrue(result==0)

    def test_user(self):
        if(oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found')):
            print("Error: test_user failed as a user with a name of test01 exists.  Please delete first and rerun the tests\n")
            self.assertTrue(False)

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
        self.assertFalse(oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found'))

        # test deleting a user that was deleted
        if(not oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found')):
            self.assertFalse(ms_delete_user('test01'))
        self.assertFalse(oc_resource_exist("user", "test01",'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01','Error from server (NotFound): users.user.openshift.io "test01" not found'))

    #def test_user_adv(self):

    def test_project_user_role(self):
        # Create a project
        if(not oc_resource_exist("project", "test-002",'test-002[ \t]*test-002[ \t]','Error from server (NotFound): namespaces "test-002" not found')):
            self.assertTrue(ms_create_project('test-002'))
        self.assertTrue(oc_resource_exist("project", "test-002",'test-002[ \t]*test-002[ \t]','Error from server (NotFound): namespaces "test-002" not found'))

        # Create some users test02 - test-05
        for x in range(2,6):
            if(not oc_resource_exist("user", "test0"+str(x),'test0'+str(x)+'[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test0'+str(x),'Error from server (NotFound): users.user.openshift.io "test0'+str(x)+'" not found')):
                self.assertTrue(ms_create_user('test0'+str(x)))
            self.assertTrue(oc_resource_exist("user", 'test0'+str(x),'test0'+str(x)+'[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test0'+str(x),'Error from server (NotFound): users.user.openshift.io "test0'+str(x)+'" not found'))

        # now bind an admin role to the user
        self.assertTrue(ms_user_project_add_role("test02", "test-002", 'admin', '{"msg": "rolebinding created \(test02,test-002,admin\)"}'))
        self.assertTrue(oc_resource_exist("rolebindings", 'admin', '^admin[ \t]*/admin[ \t]*test02','',"test-002"))

        self.assertTrue(ms_user_project_add_role("test02", "test-002", 'admin', '{"msg": "rolebinding already exists - unable to add \(test02,test-002,admin\)"}'))

        self.assertTrue(ms_user_project_remove_role("test02", "test-002", 'admin', '{"msg": "removed role from user on project"}'))
        self.assertFalse(oc_resource_exist("rolebindings", 'admin', '^admin[ \t]*/admin[ \t]*test02','',"test-002"))

        self.assertTrue(ms_user_project_remove_role("test02", "test-002", 'admin', '{"msg": "rolebinding does not exist - unable to delete \(test02,test-002,admin\)"}'))

        ms_delete_project('test-002')

        for x in range(2,6):
            if(oc_resource_exist("user", "test0"+str(x),'test0'+str(x)+'[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test0'+str(x),'Error from server (NotFound): users.user.openshift.io "test0'+str(x)+'" not found')):
                ms_delete_user('test0'+str(x))
    #def test_quota(self):


if __name__ == '__main__':
    unittest.main()
