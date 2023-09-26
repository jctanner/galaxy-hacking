#!/bin/bash

set -e

# get rid of the binary
if [ -f /usr/local/bin/docker-compose ]; then
    sudo rm -f /usr/local/bin/docker-compose
fi

if [ ! -d ~/bin ]; then
    mkdir ~/bin
fi

if [ ! -f ~/bin/docker-compose ]; then
    cp /vagrant/scripts/docker-compose ~/bin/.
    chmod +x ~/bin/docker-compose
fi

if [ ! -f ~/bin/docker-killall ]; then
    cp /vagrant/scripts/docker-killall ~/bin/.
    chmod +x ~/bin/docker-killall
fi

if [ ! -f ~/bin/docker-rmall ]; then
    cp /vagrant/scripts/docker-rmall ~/bin/.
    chmod +x ~/bin/docker-rmall
fi

cd /home/vagrant

if [ ! -d ~/src ]; then
    mkdir ~/src
fi

if [ ! -d ~/src/oci_env ]; then
    git clone https://github.com/pulp/oci_env ~/src/oci_env
fi

if [ ! -d ~/src/venv ]; then
    python3 -m venv ~/src/venv
fi
source ~/src/venv/bin/activate
cd ~/src/oci_env
pip install -e client

cd /home/vagrant

export GH_TEARDOWN=0
export GH_FLAGS="-v --capture=no --exitfirst -k test_cross_repository_search"
export OCI_DEBUG=1
export OCI_VERBOSE=1

COUNTER=0

while true; do

    let COUNTER=COUNTER+1
    echo "#######################################################################"
    echo "${COUNTER}"
    echo "#######################################################################"

    docker-killall
    DELETE_ALL=1 docker-rmall

    cd /home/vagrant

    sudo rm -rf /home/vagrant/src/galaxy_ng
    rsync -avz /vagrant/src/galaxy_ng /home/vagrant/src/.

    sudo rm -rf /home/vagrant/src/oci_env
    rsync -avz /vagrant/src/oci_env /home/vagrant/src/.
    cd /home/vagrant/src/oci_env
    pip install -e client

    cd /home/vagrant/src/galaxy_ng
    
    #make gh-action/insights
    make gh-action/community
    #make oci/standalone
    RC=$?
    if [[ $RC != 0 ]]; then
        exit $RC
    fi
    #exit $RC
done
