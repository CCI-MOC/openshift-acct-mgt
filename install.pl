#!/usr/bin/perl

system("oc login");
system("oc new-project acct-req");
system("oc -n acct-req create sa acct-req-sa");
system("oc -n acct-req adm policy add-cluster-role-to-user cluster-admin system:serviceaccount:acct-req:acct-req-sa");
if(open(FP,"<oc serviceaccounts get-token acct-req-sa")) { $token=<FP>; }
system("oc login --token ".$token);
system("oc -n acct-req create secret generic kubecfg --from-file=/root/.kube/config");
system(" oc -n acct-req new-app python:2.7~https://github.com/robbaronbu/openshift-acct-req.git");
