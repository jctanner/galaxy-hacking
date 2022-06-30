#!/bin/bash

set -e

cd /vagrant
./scripts/docker-killall
#./scripts/docker-rmall
docker images | fgrep ci_build | awk '{print $3}' | xargs -I {} docker rmi {}
rm -rf ~/.config/pulp
sudo rm -rf /tmp/ghacktion*
rm -f ~/.netrc
sudo rm -f src/pulp_ansible/.github_env
sudo rm -rf src/pulp_ansible/.venv

sudo rm -f src/pulp_ansible/.ci/ansible/Containerfile
sudo rm -rf src/pulp_ansible/.ci/ansible/settings
sudo rm -rf src/pulp_ansible/.ci/ansible/vars
sudo rm -rf src/pulp_ansible/.ci/assets/httpie/version_info.json
sudo rm -rf src/pulp_ansible/python-client-docs.tar
sudo rm -rf src/pulp_ansible/python-client.tar

# clean out the other checkouts or the CI will fail [not idempotent]
ls -1 src/ | fgrep -v pulp_ansible | xargs -I {} sudo rm -rf src/{}

#./ghacktion --local --repo=pulp/pulp_ansible --number=1062 run --file=ci.yml --job=test --noclean
#./ghacktion --local --repo=pulp/pulp_ansible --number=1067 run --file=ci.yml --job=test --noclean
./ghacktion --local --checkout=$(pwd)/src/pulp_ansible run --file=ci.yml --job=test --noclean
