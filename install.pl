#!/usr/bin/perl

use strict;

if($ARG[1]=='init')
    {
    system("oc create project acct-req");
    system("oc -n acct-rec create service account acct-req-sa")
    system("oc admin policy add-cluster-role-to-user system-admin -x acct-rec-sa")

    }