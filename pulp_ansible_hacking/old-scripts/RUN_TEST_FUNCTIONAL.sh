#!/bin/bash

#set -e

source venv/bin/activate
cd oci_env

# check if client has been generated ...
oci-env pulpcore-manager shell -c 'from pulpcore.client import pulp_ansible' > /tmp/client_check.txt
egrep -e ImportError -e ModuleNotFoundError /tmp/client_check.txt
RC=$?
if [[ $RC == 0 ]]; then
    echo "--------------------------------------------"
    echo "generating client"
    echo "--------------------------------------------"
    oci-env generate-client -i pulp_ansible
    #RC=$?
    #if [[ $RC != 0 ]]; then
    #    exit $RC
    #fi
fi

# check again ...
oci-env pulpcore-manager shell -c 'from pulpcore.client import pulp_ansible' > /tmp/client_check.txt
egrep -e ImportError -e ModuleNotFoundError /tmp/client_check.txt
RC=$?
if [[ $RC == 0 ]]; then
    echo "--------------------------------------------"
    echo "generating client again"
    echo "--------------------------------------------"
    oci-env generate-client -i pulp_ansible
    RC=$?
    if [[ $RC != 0 ]]; then
        exit $RC
    fi
fi

echo "--------------------------------------------"
echo "running tests"
echo "--------------------------------------------"
oci-env test -i -p pulp_ansible functional --exitfirst -v --disable-warnings --capture=no \
    -k 'test_collection_version_search' $@
