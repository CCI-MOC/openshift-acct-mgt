#!/usr/bin/perl

use strict;
use warnings;
use Test::More;
use Test::Cmd;

#
#  To use:
#  
#      1) deploy the acct-mgt microsver on an openshift instance
#      2) point a local oc to a cluster-admin on that openshift instance
#      3) call this script with:
#          [script name] -m acct-mgmt.apps.openshift.com
#

use time;

sub oc_cmd
    {
    my $action=shift;
    my $type=shift;
    my $item=shift;
    my @rv

    if( open(FP,"oc "$action." ".$type." user ".$item." |"))
        {
        @rv=<FP>;
        }   
    return @rv
    }

sub oc_exists
    {
    my $type=shift
    my $item=shift;
    my @lines=oc_cmd("get",$type,$username);
    foreach $l in (@lines) { if($l=~/^$username/) {return 1;} return 0;}
    }

sub oc_user_exists { my $user_name=shift; return oc_exists("user",$username); }    
sub oc_delete_user { my $username=shift;  oc_cmd("delete","user",$username); }
sub oc_identity_exists { my $identity=shift; return oc_exists("identity",$identity); }
sub oc_delete_identity { my $username=shift; oc_cmd("delete","identity",$identity); }
sub oc_project_exists( my $project=shift; return oc_exists("project",$project); )
sub oc_delete_project { my $project=shift; oc_cmd("delete","project",$project); }

sub username_exists
    {
    my $username=shift;

    if( open(FP,"oc get user ".$username." |"))
        {
        while(my $line=<FP>)
            {
            if($line=~ /^$username/)
                {
                return 1;
                }
            }
        }
    return 0
    }

# assume that this works - it is only to be used if 
# the microserver doesn't work.
sub oc_delete_username
    {
    my $username=shift;

    if( open(FP,"oc delete user ".$username." |"))
        {
        while(my $line=<FP>) { }
        return 1
        }
    return 0;
    }

sub gen_username
    {
    return "test_".time(NULL);
    }

sub create_user
    {
    my $microserver_url=shift;
    my $username=shift;

    system("curl get -kv https://".$microserver_url."/users/".$username);
    }

sub delete_user
    {
    my $microserver_url=shift;
    my $username=shift;

    system("curl delete -kv https://".$microserver_url."/users/".$username);
    }

sub test_create_and_delete_user
    {
    my $microsever=shift;
    my $username=shift;

    if(username_exists($username)==0)
        {
        create_user($microserver,$username)
        if(oc_username_exists($username)==1)
            {
            delete_user($microserver,$username);
            if(oc_username_exists==0)
                {
                return 1
                }
            else
                {
                oc_userdelete($username);
                }
            }
        else
            {
            printf("Unable to create User")
            }
        }
    return 0;
    }

test_create_user("acc-req.k-apps.osh.openshift.massopen.cloud",gen_username());

# Basic methodology
# Construct and absurd name
# if the absurd name for the resource doesn't exit
#    create/delete the resource using the micro server on openshift
#    check that the resource exists/does not exist using oc
# clean up using oc (if necessary)



# log in with oc


# test 1
# Create User
#    find user test-n
#    if no user test-n exists
#        create test-n
#        check with oc that test-n exists
#        delete test-n
#        check with oc that test-n does not exists

# test 2
# Create identity
#    find if identity sso_auth::test-n exists
#    if no
#        create identity sso_auth::test-n
#        check
#        delete "
#        check 

# test 3
# Create User and identity
# clean up

# test 4
# create project
# cleanup

#test 5
# create user and identity 
# create project
# create role
# clean up