#!/bin/bash

rm -rf ~/ghacktion.venv
rm -rf ~/.config

#./ghacktion.py --repo=ansible/galaxy_ng --number=1810 --local list --file=ci_oci-env-integration.yml 

#./ghacktion.py \
#        --repo=ansible/galaxy_ng \
#        --number=1810 \
#        --local \
#        run \
#            --noclean \
#            --file=ci_oci-env-integration.yml \
#            --job=integration \
#            --matrix_env='{"TEST_PROFILE": "certified-sync"}' \
#            --workdir=/home/runner/work

./ghacktion.py \
        --local \
        --repo=ansible/galaxy_ng \
        --checkout=/vagrant/src/galaxy_ng \
        run \
            --noclean \
            --file=ci_oci-env-integration.yml \
            --job=integration \
            --matrix_env='{"TEST_PROFILE": "certified-sync"}' \
            --workdir=/home/runner/work
