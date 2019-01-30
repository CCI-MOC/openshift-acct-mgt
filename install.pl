#!/usr/bin/perl

system("oc login");
system("oc new-project acct-req");
system("oc -n acct-req create sa acct-req-sa");
system("oc -n acct-req adm policy add-cluster-role-to-user cluster-admin system:serviceaccount:acct-req:acct-req-sa");
if(open(FP,"<oc serviceaccounts get-token acct-req-sa")) { $token=<FP>; }
system("oc login --token ".$token);
system("oc -n acct-req create secret generic kubecfg --from-file=/root/.kube/config");
#system(" oc -n acct-req new-app python:3.5~https://github.com/robbaronbu/openshift-acct-req.git");
system("oc new-app docker.io/robertbartlettbaron/openshift-acct-req:latest");

#Eventually we need to create a route
#oc create route edge \
#    --service=frontend \
#    --cert=${MASTER_CONFIG_DIR}/ca.crt \
#    --key=${MASTER_CONFIG_DIR}/ca.key \
#    --ca-cert=${MASTER_CONFIG_DIR}/ca.crt \
#    --hostname=www.example.com
