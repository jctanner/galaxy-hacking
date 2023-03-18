#!/bin/bash -x

set -e

if [[ ! -d ~/venv ]]; then
    virtualenv ~/venv
fi
source ~/venv/bin/activate
~/venv/bin/pip install docker pyyaml jinja2

cd /vagrant
./scripts/docker-killall
DELETE_ALL=1 ./scripts/docker-rmall
docker images | fgrep ci_build | awk '{print $3}' | xargs -I {} docker rmi {}

if [[ ! -d ~/.config ]]; then
    mkdir -p ~/.config
fi
rm -rf ~/.config/pulp

sudo rm -rf /tmp/ghacktion*
rm -f ~/.netrc
if [[ ! -d src ]]; then
    mkdir -p src
fi

sudo rm -f src/pulp_ansible/.github_env
sudo rm -rf src/pulp_ansible/.venv
sudo rm -rf /home/vagrant/ghacktion.venv

sudo rm -f src/pulp_ansible/.ci/ansible/Containerfile
sudo rm -rf src/pulp_ansible/.ci/ansible/settings
sudo rm -rf src/pulp_ansible/.ci/ansible/vars
sudo rm -rf src/pulp_ansible/.ci/assets/httpie/version_info.json
sudo rm -rf src/pulp_ansible/python-client-docs.tar
sudo rm -rf src/pulp_ansible/python-client.tar

# clean out the other checkouts or the CI will fail [not idempotent]
ls -1 src/ | fgrep -v pulp_ansible | xargs -I {} sudo rm -rf src/{}

if [[ ! -d src/pulp_ansible ]]; then
    git clone https://github.com/pulp/pulp_ansible src/pulp_ansible
fi

echo $(pwd)

#./ghacktion --local --repo=pulp/pulp_ansible --number=1062 run --file=ci.yml --job=test --noclean
#./ghacktion --local --repo=pulp/pulp_ansible --number=1067 run --file=ci.yml --job=test --noclean
./ghacktion/ghacktion.py --local --checkout=$(pwd)/src/pulp_ansible run --file=ci.yml --job=test --noclean
