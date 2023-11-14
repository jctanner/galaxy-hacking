#!/bin/bash

# pulpcore-api pulpcore-content pulpcore-worker@1
SERVICES=$(s6-rc -a list | grep -E ^pulp)
echo "$SERVICES" | xargs -I {} s6-rc -d change {}
