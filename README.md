# openshift-acct-mgt

Simple microserver that implements a REST API to manage users, projects,
project ResourceQuotas, and role assignments on OpenShift 4.X clusters.

The created users are assigned an identity and an identity mapping.

The endpoint is protected using HTTP Basic Auth. 


## API Description

    1) Create a user.

        a) API call:

            get [cluster url]/users/<user-name>

        b) Equivalent command line commands:

            oc create user <user-name>
            oc create identity <idp>:<user-name>
            oc useridentitymapping <idp>:<user-name> <user-name>
    
    2) Create a project.

        a) API call:

            get [cluster url]/projects/<project-name>

        b) Equivalent command line commands:

        oc create project <project-name>

    3) Add a user to a project with a given role. In OpenShift, these roles are 'admin', 'edit', 'view' respectively.

        a) API call:

            get [cluster url]/users/<user-name>/projects/<project-name>/roles/<admin|edit|view>

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
        
            delete [cluster url]/users/<user-name>/projects/<project-name>/roles/<admin|edit|view>

        b) Equivalent command line commands:
    
            oc adm policy -n <project-name> rm-role-from-user <admin|edit|view> <user-name>

## Configuration Options
The following configuration options are accepted

* **ACCT_MGT_ADMIN_USERNAME**
  * **Description**: Expected username through HTTP Basic Auth when receiving API requests.
  * **Required**: No
  * **Default**: admin
* **ACCT_MGT_ADMIN_PASSWORD**
  * **Description**: Expected password through HTTP Basic Auth when receiving API requests.
  * **Required**: Yes
* **ACCT_MGT_IDENTITY_PROVIDER**
  * **Description**: Identity provider to create the UserIdentityMapping. As configured on OpenShift.
  * **Required**: Yes
* **ACCT_MGT_AUTH_TOKEN**
  * **Description**: Authentication token for the OpenShift cluster. Only required when not running directly on the cluster.
  * **Required**: No
* **ACCT_MGT_OPENSHIFT_URL**
  * **Description**: URL of the OpenShift API. Only required when not running directly on the cluster.
  * **Required**: No
* **ACCT_MGT_QUOTA_DEF_FILE**
  * **Description**: Path to the JSON file containing the quota definition. See example in `k8s/base/quotas/json`.
  * **Required**: No (The file is required)
  * **Default**: quotas.json

## Build
The recommended method to build and test changes is using Microshift.
Running `./ci/setup.sh` is going to deploy a Microshift container
and build and deploy the application using the k8s manifests on
`k8s`.

```bash
./ci/setup.sh
```

## Running Tests
To run the tests (both functional tests and unit tests), make sure to have an
environment with the necessary dependencies installed.

The recommended solution is to create a new virtual environment:

```shell
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt -r test-requirements.txt
```

### Running Functional Tests
Functional tests require a working OpenShift cluster. We do not recommend
running them on a production cluster as they do not perform cleanup.

If you have followed the steps in the Build section, running functional
tests is as easy as running the following commands. 

```bash
./ci/run_functional_tests.sh
```

### Running Unit tests
To run the unit tests and produce a coverage report (found in `htmlcov/index.html`):

```shell
pytest tests/unit -v --cov=acct_mgt --cov-report=term
```

## Running the service locally

It is possible to run the application outside an OpenShift cluster.

You will need to make sure you are authenticated to OpenShift (when
run locally, we use `oc whoami -t` to get an authentication token).

The following environment variables need to be set:

```
OPENSHIFT_URL=$(oc whoami --show-server)
ACCT_MGT_IDENTITY_PROVIDER=developer
ACCT_MGT_ADMIN_PASSWORD=pass
```

Then start the server up with:

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
