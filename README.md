This is a simple microserver that implements a REST API to manage users and projects on the MOC's
OpenShift clusters.

It implements the following functions:

    1) Create a user.

        a) API call:

            get [cluster url]/users/<user-name>

        b) Equivalent command line commands:

            oc create user <user-name>
            oc create identity sso_auth:<user-name>
            oc useridentitymapping sso_auth:<user-name> <user-name>
    
    2) Create a project.

        a) API call:

            get [cluster url]/projects/<project-name>

        b) Equivalent command line commands:

        oc create project <project-name>

    3) Add a user to a project with a given role.  Here the role may be one of 'admin', 'member' or 'reader'.  In OpenShift, these roles are 'admin', 'edit', 'view' respectively.

        a) API call:

            get [cluster url]/users/<user-name>/projects/<project-name>/roles/<admin|member|reader>

        b) Equivalent command line commands:

        oc adm policy -n <project-name> add-role-to-user <admin|edit|view> <user-name>

    4) Delete a user.

        a) API call:

            delete [cluster url]/users/<user-name>

        b) Equivalent command line commands:

            oc delete user <user-name>
            oc delete identity sso_auth:<user-name>

    5) Delete a project.

        a) API call:
    
            delete [cluster url]/projects/<project-name>

        b) Equivalent command line commands:

            oc delete project <project-name>

    6) Remove a role from a user within a project.  Role her is the same as the roles defined in 'Add a user to a project with a role'.

        a) API call:
        
            delete [cluster url]/users/<user-name>/projects/<project-name>/roles/<admin|member|reader>   
        b) Equivalent command line commands:
    
            oc adm policy -n <project-name> rm-role-from-user <admin|edit|view> <user-name>

How to test:
    1.1) testing with minishift
    1.1.1) start minishift with the following commands

minishift start
eval $(minishift docker-env
oc login -u system:admin
oc adm policy add-cluster-role-to-user cluster-admin developer"
oc login -u developer
docker login -u developer -p developer 172.30.1.1:5000

## Running the unit tests

Before running the unit tests, make sure you have installed all the
test dependencies defined in `test-requirements.txt`.

To run the unit tests and produce a coverage report:

```
pytest tests/unit
```

This will place a coverage report in `htmlcov/index.html`.

## Running the service locally

You will need to make sure you are authenticated to OpenShift (when
run locally, we use `oc whoami -t` to get an authentication token).

You will need to set the following environment variables:

```
OPENSHIFT_URL=$(oc whoami --show-server)
ACCT_MGT_IDENTITY_PROVIDER=developer
ACCT_MGT_ADMIN_PASSWORD=pass
```

Then start the server up like this:

```
ACCT_MGT_AUTH_TOKEN=$(oc whoami -t) \
flask run -p 8080
```

Or alternately:

```
ACCT_MGT_AUTH_TOKEN=$(oc whoami -t) \
gunicorn -b 127.0.0.1:8080 -c config.py wsgi:APP
```

This will expose the microservice on http://127.0.0.1:8080. You can
access it like this:

```
$ curl -u admin:pass  http://localhost:8080/users/test-user
{"msg": "user (test-user) does not exist"}
```
