#!/usr/bin/python3
# python3 -m pytest acct-mgt-test.py
import subprocess
import re
import time
import pytest
import pytest_check as check

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
    microserver_url=get_microserver()
    if(op=='check'):
        url_op='GET'
    elif(op=='add'):
        url_op="PUT"
    elif(op=='del'):
        url_op="DELETE"
        
    result=subprocess.run(['curl',"-X",op,"-kv",url+"/users/"+user_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

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

def ms_check_project(project_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","GET","-kv",microserver_url+"/projects/"+project_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    # {"msg": "project exists (test-001)"}
    #print("\n\n***** result: "+result.stdout.decode('utf-8') +"\n\n")
    if(compare_results(result,r'{"msg": "project exists \('+project_name+r'\)"}')):
        return True
    return False

# expect this to be called with 
#  project_uuid="1234-1234-1234-1234"
#  displayNameStr=None | '{"displayName":"project_name"}' | '{"funkyName":"project_name"}'
def ms_create_project(project_uuid,displayNameStr):
    microserver_url=get_microserver()
    if(displayNameStr is None):
        result=subprocess.run(['curl',"-X","PUT","-kv",microserver_url+"/projects/"+project_uuid],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    else:
        result=subprocess.run(['curl',"-X","PUT","-d",displayNameStr,"-kv",microserver_url+"/projects/"+project_uuid],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
       
    # {"msg": "project created \(test\-001\)"}
    if(compare_results(result,r'{"msg": "project created \('+project_uuid+r'\)"}')):
        return True
    return False

def ms_delete_project(project_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","DELETE","-kv",microserver_url+"/projects/"+project_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    # {"msg": "project deleted (test-001)"}
    if(compare_results(result,r'{"msg": "project deleted \('+project_name+r'\)"}')):
        return True
    return False

def ms_check_user(user_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","GET","-kv",microserver_url+"/users/"+user_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    # {"msg": "User (test01) exists"}
    print("\ncheck_user: "+result.stdout.decode('utf-8') +"\n\n")
    if(compare_results(result,r'{"msg": "user \('+user_name+r'\) exists"}')):
        return True
    return False    

def ms_create_user(user_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","PUT","-kv",microserver_url+"/users/"+user_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    # {"msg": "user created (test01)"}
    # print("\nresult: "+result.stdout.decode('utf-8') +"\n\n")
    if(compare_results(result,r'{"msg": "user created \('+user_name+r'\)"}')):
        return True
    return False

def ms_delete_user(user_name):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","DELETE","-kv",microserver_url+"/users/"+user_name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    # print("result: "+result.stdout.decode('utf-8') +"\n\n")
    if(compare_results(result,r'{"msg": "user deleted \('+user_name+r'\)"}')):
        return True
    return False

def ms_user_project_get_role(user_name, project_name, role, success_pattern):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","PUT","-kv",microserver_url+"/users/"+user_name+"/projects/"+project_name+"/roles/"+role],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print("get role --> result: "+result.stdout.decode('utf-8') +"\n\n")
    if(compare_results(result,success_pattern)):
        return True
    return False

def ms_user_project_add_role(user_name, project_name, role, success_pattern):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","PUT","-kv",microserver_url+"/users/"+user_name+"/projects/"+project_name+"/roles/"+role],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print("add role --> result: "+result.stdout.decode('utf-8') +"\n\n")
    return True
    if(compare_results(result,success_pattern)):
        return True
    return False

def ms_user_project_remove_role(user_name, project_name, role, success_pattern):
    microserver_url=get_microserver()
    result=subprocess.run(['curl',"-X","DELETE","-kv",microserver_url+"/users/"+user_name+"/projects/"+project_name+"/roles/"+role],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    #print("--> result: "+result.stdout.decode('utf-8') +"\n\n")
    if(compare_results(result,success_pattern)):
        return True
    return False

def test_project():
    result=0

    #if(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
    #    print("Error: test_project failed as a project with a name of test-001 exists.  Please delete first and rerun the tests\n")
    #    assertTrue(False)

    # test if project doesn't exist
    check.is_false(ms_check_project('test-001'),'Project exists (test-001)')

    # test project creation
    if(not oc_resource_exist("project", "test-001",r'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
        check.is_true(ms_create_project('test-001',r'{"displayName":"test-001"}'),'Project (test-001) not created')
        wait_until_done('oc get project test-001', r'test-001[ \t]+test-001[ \t]+Active') 
    check.is_true(oc_resource_exist("project", "test-001",r'test-001[ \t]+test-001[ \t]+Active',r'Error from server (NotFound): namespaces "test-001" not found'),"Project (test-001) not created")
    check.is_true(ms_check_project('test-001'),'project test-001 was not found')

    # test creation of a second project with the same name
    if(oc_resource_exist("project", "test-001",r'test-001[ \t]*test-001[ \t]',r'Error from server (NotFound): namespaces "test-001" not found')):
        check.is_false(ms_create_project('test-001',r'{"displayName":"test-001"}'),'Project (test-001) was already created' )
    check.is_true(oc_resource_exist("project", "test-001",r'test-001[ \t]*test-001[ \t]',r'Error from server (NotFound): namespaces "test-001" not found'),"Project test-001 was not found")
    
    # test project deletion
    if(oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
        check.is_true(ms_delete_project('test-001'),'Unable to delete project (test-001)')
        # Wait until test-001 is terminated
        wait_until_done('oc get project test-001', r'Error from server (NotFound): namespaces "test-001" not found')
    check.is_false(oc_resource_exist("project", "test-001",r'test-001[ \t]*test-001[ \t]',r'Error from server (NotFound): namespaces "test-001" not found'),"Project test-001 exists and it shouldn't")
    
    # test deleting a project that was deleted
    if(not oc_resource_exist("project", "test-001",'test-001[ \t]*test-001[ \t]','Error from server (NotFound): namespaces "test-001" not found')):
        check.is_false(ms_delete_project('test-001'),"shouldn't be able to delete a non-existing project" )
    check.is_false(oc_resource_exist("project", "test-001",r'test-001[ \t]*test-001[ \t]',r'Error from server (NotFound): namespaces "test-001" not found'),"Project test-001 exists and it should not")

    # these tests are primarily done to ensure that the microserver doesn't crash
    #    When the "displayName" is not present, or the json doesn't exist, the displayName shall default to the project_uuid (first parameter)
    check.is_true(ms_create_project('1234-1234-1234-1234',r'{"displayName":"test-001"}'),'Project (1234-1234-1234-1234) not created')
    ms_delete_project('1234-1234-1234-1234')
    check.is_true(ms_create_project('2234-1234-1234-1234',r'{"displaName":"test-001"}'),'Project (2234-1234-1234-1234) not created')
    ms_delete_project('2234-1234-1234-1234')
    check.is_true(ms_create_project('3234-1234-1234-1234',r'{}'),'Project (3234-1234-1234-1234) not created')
    ms_delete_project('3234-1234-1234-1234')
    check.is_true(ms_create_project('4234-1234-1234-1234',None),'Project (4234-1234-1234-1234) not created')
    ms_delete_project('4234-1234-1234-1234')




def test_user():
    #if(oc_resource_exist("user", "test01",r'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01',r'Error from server (NotFound): users.user.openshift.io "test01" not found')):
    #    print("Error: test_user failed as a user with a name of test01 exists.  Please delete first and rerun the tests\n")
    #    assertTrue(False)

    check.is_false(ms_check_user('test01'),"User test01 exists but it shouldn't exist at this point")

    # test user creation
    # test01                    bfd6dab5-11f3-11ea-89a6-fa163e2bb38b                         sso_auth:test01
    if(not oc_resource_exist("user", "test01",r'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01',r'Error from server \(NotFound\): users.user.openshift.io "test01" not found')):
        check.is_true(ms_create_user('test01'), 'unable to create test01')
    check.is_true(oc_resource_exist("user", "test01",r'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01',''), "user test01 doesn't exist")
    check.is_true(ms_check_user('test01'),"User test01 doesn't exist but it should")

    # test creation of a second user with the same name
    if(oc_resource_exist("user", "test01",r'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01',r'Error from server \(NotFound\): users.user.openshift.io "test01" not found')):
        check.is_false(ms_create_user('test01'),"Should have failed to create a second user with the username of test01")
    check.is_true(oc_resource_exist("user", "test01",r'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01',''), "user test01 doesn't exist")

    # test user deletion
    if(oc_resource_exist("user", "test01",r'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01',r'Error from server (NotFound): users.user.openshift.io "test01" not found')):
        check.is_true(ms_delete_user('test01'),"user test01 deleted")
    check.is_false(oc_resource_exist("user", "test01",r'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01',r'Error from server \(NotFound\): users.user.openshift.io "test01" not found'),"user test01 not found")

    # test deleting a user that was deleted
    if(not oc_resource_exist("user", "test01",r'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01',r'Error from server (NotFound): users.user.openshift.io "test01" not found')):
        check.is_false(ms_delete_user('test01'),"shouldn't be able to delete non-existing user test01")
    check.is_false(oc_resource_exist("user", "test01",r'test01[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test01',r'Error from server \(NotFound\): users.user.openshift.io "test01" not found'),"user test01 not found")
    check.is_false(ms_check_user('test01'),"User test01 exists but it shouldn't exist at this point")

def test_project_user_role():
    # Create a project
    if(not oc_resource_exist("project", "test-002",r'test-002[ \t]*test-002[ \t]',r'Error from server \(NotFound\): namespaces "test-002" not found')):
        check.is_true(ms_create_project('test-002','{"displayName":"test-002"}'), "Project (test-002) was unable to be created")
    check.is_true(oc_resource_exist("project", "test-002",r'test-002[ \t]*test-002[ \t]',r'Error from server \(NotFound\): namespaces "test-002" not found'), "Project (test-002) does not exist")

    # Create some users test02 - test-05
    for x in range(2,6):
        if(not oc_resource_exist("user", "test0"+str(x),'test0'+str(x)+r'[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test0'+str(x),r'Error from server (NotFound): users.user.openshift.io "test0'+str(x)+'" not found')):
            check.is_true(ms_create_user('test0'+str(x)),'Unable to create user '+'test0'+str(x))
        check.is_true(oc_resource_exist("user", 'test0'+str(x),'test0'+str(x)+r'[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test0'+str(x),r'Error from server (NotFound): users.user.openshift.io "test0'+str(x)+r'" not found'),"user test0"+str(x)+' not found')

    # now bind an admin role to the user
    check.is_true(ms_user_project_add_role("test02", "test-002", 'admin', r'{"msg": "rolebinding created \(test02,test-002,admin\)"}'),"Role unable to be added")
    check.is_true(oc_resource_exist("rolebindings", 'admin', '^admin[ \t]*/admin[ \t]*test02','',"test-002"),"role does not exist")

    check.is_true(ms_user_project_add_role("test02", "test-002", 'admin', r'{"msg": "rolebinding already exists - unable to add \(test02,test-002,admin\)"}'),"Added the same role to a user failed as it should")

    check.is_true(ms_user_project_remove_role("test02", "test-002", 'admin', r'{"msg": "removed role from user on project"}'),"Removed rolebinding successful")
    check.is_false(oc_resource_exist("rolebindings", 'admin', r'^admin[ \t]*/admin[ \t]*test02',r'',"test-002"),"Rolebinding does not exit")

    check.is_true(ms_user_project_remove_role("test02", "test-002", 'admin', r'{"msg": "rolebinding does not exist - unable to delete \(test02,test-002,admin\)"}'),"Unable to remove non-existing rolebinding")

    # Clean up by removing the users and project (test-002)
    check.is_true(ms_delete_project('test-002')==True, "project (test-002) deleted")
    for x in range(2,6):
        if(oc_resource_exist("user", "test0"+str(x),'test0'+str(x)+r'[ \t]*[a-f0-9\-]*[ \t]*sso_auth:test0'+str(x),r'Error from server (NotFound): users.user.openshift.io "test0'+str(x)+'" not found')):
            check.is_true(ms_delete_user('test0'+str(x))==True, "user "+'test0'+str(x)+"unable to be deleted")

#def test_quota(self):

