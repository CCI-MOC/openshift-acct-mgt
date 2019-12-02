#!/usr/bin/python3
import subprocess
import re
import time

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
    subprocess.run(['docker','build','-f','Dockerfile.x86','-t','docker.io/robertbartlettbaron/acct-mgt.x86','.'])
    subprocess.run(['docker','push','docker.io/robertbartlettbaron/acct-mgt.x86'])
    subprocess.run(['oc','rollout','latest','acct-mgt'])
    result=subprocess.run(['oc','get','all'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT) 
    return wait_until_container_is_ready()

def main():
    # export MICROSERVER_URL=https://acct-req.k-apps.osh.massopen.cloud 
    # export MICROSERVER_URL=https://acct-mgt-acct-mgt.s-apps.osh.massopen.cloud
    microserver_url='https://acct-mgt-acct-mgt.s-apps.osh.massopen.cloud'
    build_and_deploy()

main()
