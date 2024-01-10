#!/bin/bash

cd docker.proxy
docker build -t local/proxy .
docker tag local/proxy localhost:5000/local/proxy
docker push localhost:5000/local/proxy
