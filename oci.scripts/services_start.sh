#!/bin/bash

# pulpcore-api pulpcore-content pulpcore-worker@1
SERVICES=$(s6-rc -a list)
SERVICES="pulpcore-api
pulpcore-content
pulpcore-worker"
echo "$SERVICES" | xargs -I {} s6-rc -u change {}
