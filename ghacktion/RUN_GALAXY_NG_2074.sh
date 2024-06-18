#!/bin/bash

cd /vagrant
./ghacktion/ghacktion.py --repo=ansible/galaxy_ng --number=2074 --local run --noclean --file=ci.yml --job=test
