#!/bin/bash -x

WORKDIR=/tmp/$(ls -t /tmp | fgrep ghacktion | head -n1)
PULP_ANSIBLE_DIR=$WORKDIR/jctanner/pulp_ansible
#cd $PULP_ANSIBLE_DIR

cd src/pulp_ansible
source .venv/bin/activate
source .github_env

export PYTHONPATH=.:$(pwd)/../galaxy-importer 

.venv/bin/pip install epdb orionutils

.venv/bin/pytest \
    --capture=no \
    -v \
    -r sx \
    --color=yes \
    --pyargs pulp_ansible.tests.functional \
    -m "not parallel" \
    -k test_import_role
