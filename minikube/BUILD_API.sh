#!/bin/bash

cd docker
docker build -t local/api .
docker tag local/api localhost:5000/local/api
docker push localhost:5000/local/api
