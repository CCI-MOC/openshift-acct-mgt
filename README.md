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

