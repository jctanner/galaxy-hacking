#!/bin/bash

cd docker.ux
docker build -t local/ux .
docker tag local/ux localhost:5000/local/ux
docker push localhost:5000/local/ux
