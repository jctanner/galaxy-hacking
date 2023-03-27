#!/bin/bash -x

set -e

if [[ $(whoami) != "runner" ]]; then
    echo "you must be the 'runner' user for pulp ci to work"
    exit 1
fi

if [[ ! -d ~/venv ]]; then
    virtualenv ~/venv
fi
source ~/venv/bin/activate
~/venv/bin/pip install docker pyyaml jinja2 epdb

cd /vagrant
./scripts/docker-killall
DELETE_ALL=1 ./scripts/docker-rmall
docker images | fgrep ci_build | awk '{print $3}' | xargs -I {} docker rmi {}

if [[ ! -d ~/.config ]]; then
    mkdir -p ~/.config
fi
sudo rm -rf ~/.config/pulp
sudo rm -rf ~/.config/pulp_smash
sudo chown -R $(whoami):$(whoami) ~/.config

sudo rm -rf /tmp/ghacktion*
rm -f ~/.netrc
if [[ ! -d src ]]; then
    mkdir -p src
fi

##############################################################################
# docker volume mounts screw with permissions so we need to get the source
# paths out of the vagrant share and owned by vagrant ..
##############################################################################

SRCPATH=~/src
sudo rm -rf $SRCPATH
mkdir -p $SRCPATH
cd $SRCPATH


#sudo rm -f src/pulp_ansible/.github_env
#sudo rm -rf src/pulp_ansible/.venv
sudo rm -rf ~/ghacktion.venv

#sudo rm -f src/pulp_ansible/.ci/ansible/Containerfile
#sudo rm -rf src/pulp_ansible/.ci/ansible/settings
#sudo rm -rf src/pulp_ansible/.ci/ansible/vars
#sudo rm -rf src/pulp_ansible/.ci/assets/httpie/version_info.json
#sudo rm -rf src/pulp_ansible/python-client-docs.tar
#sudo rm -rf src/pulp_ansible/python-client.tar

# clean out the other checkouts or the CI will fail [not idempotent]
#ls -1 src/ | fgrep -v pulp_ansible | xargs -I {} sudo rm -rf src/{}

if [[ ! -d $SRCPATH/pulp_ansible ]]; then
    # git clone https://github.com/pulp/pulp_ansible $SRCPATH/pulp_ansible
    if [[ -d /vagrant/src/pulp_ansible ]]; then
        cp -Rp /vagrant/src/pulp_ansible $SRCPATH/.
    fi
fi

echo $(pwd)


/vagrant/ghacktion/ghacktion.py \
    --local \
    --checkout=$SRCPATH/pulp_ansible \
    run \
        --file=ci.yml \
        --job=test \
        --matrix_env='{"TEST": "s3"}' \
        --noclean

