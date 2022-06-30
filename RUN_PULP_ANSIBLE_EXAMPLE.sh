#!/bin/bash

cd /vagrant
./scripts/docker-killall
./scripts/docker-rmall
rm -rf ~/.config/pulp
sudo rm -rf /tmp/ghacktion*
rm -f ~/.netrc


./ghacktion --local --repo=pulp/pulp_ansible --number=1062 run --file=ci.yml --job=test --noclean
#./ghacktion --local --repo=pulp/pulp_ansible --number=1067 run --file=ci.yml --job=test --noclean
