#!/usr/bin/perl

# login to oc as cluster-admin

# see if openshift acme client is install 
# if it is not, install it
if(open(FP "oc get deployment.apps --all-namespaces |"))
    {
    my openshift_acme_installed=0;
    while($line=<FP>) { if($line~= /[ \t]openshift-acme[ \t]/ ) { openshift_acme_installed=1; }}
    if(openshift_acme_installed==0)
        {
        system("oc create -fhttps://raw.githubusercontent.com/tnozicka/openshift-acme/master/deploy/letsencrypt-live/cluster-wide/{clusterrole,serviceaccount,imagestream,deployment}.yaml");
        system("oc adm policy add-cluster-role-to-user openshift-acme -z openshift-acme");
        }
    }

# Install moc's acct-mgt microserver
system("oc new-project acct-mgt");
system("oc -n acct-req create sa acct-mgt-sa");
system("oc -n acct-req adm policy add-cluster-role-to-user cluster-admin system:serviceaccount:acct-req:acct-req-sa");
system("oc -n acct-req create template -f acct-req.yaml");
system("oc create route edge ".
       " --service=frontend ".
       " --hostname=acct-mgt.");
system("oc annotate route acct-mgt kubernetes.io/tls-acme:\"true\" ");