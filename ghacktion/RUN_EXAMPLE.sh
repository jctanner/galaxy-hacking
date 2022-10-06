#!/bin/bash

cd /vagrant
./ghacktion --repo=ansible/galaxy_ng --number=1247 --local run --noclean --file=ci.yml --job=test
