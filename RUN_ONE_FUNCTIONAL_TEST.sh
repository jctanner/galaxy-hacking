#!/bin/bash -x

WORKDIR=/tmp/$(ls -t /tmp | fgrep ghacktion | head -n1)
PULP_ANSIBLE_DIR=$WORKDIR/pulp/pulp_ansible
cd $PULP_ANSIBLE_DIR
source .venv/bin/activate

export PYTHONPATH=$PULP_ANSIBLE_DIR:$PULP_ANSIBLE_DIR/../galaxy-importer 

.venv/bin/pip install epdb orionutils

.venv/bin/pytest \
    --capture=no \
    -v \
    -r sx \
    --color=yes \
    --pyargs pulp_ansible.tests.functional \
    -m "not parallel" \
    -k test_import_role
