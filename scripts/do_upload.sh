#!/bin/bash

cd /home/jtanner/workspace/github/jctanner.redhat/galaxy-hacking

PYTHONPATH=. python cli/main.py namespaces create --name=ansible

PYTHONPATH=. python cli/main.py collections upload --filepath=artifacts/ansible-eda-1.4.2.tar.gz
