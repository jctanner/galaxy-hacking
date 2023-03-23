#!/bin/bash

docker cp wisdom_dumper.py galaxy_ng_api_1:/tmp/.
docker exec -it galaxy_ng_api_1 /bin/bash -c 'pulpcore-manager shell < /tmp/wisdom_dumper.py' | tee -a test.out
