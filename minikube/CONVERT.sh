#!/bin/bash

rm *.yaml

kompose convert -f ../docker-compose.yml

mv home-jtanner-workspace-github-jctanner-redhat-minikube-testing-postgres-env-configmap.yaml \
    postgres-env-configmap.yaml

sed -i.bak 's/home-jtanner-workspace-github-jctanner-redhat-minikube-testing-//g' *.yaml
rm *.bak


