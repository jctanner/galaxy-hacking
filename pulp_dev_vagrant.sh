#!/bin/bash

# https://github.com/ansible/galaxy_ng/wiki/Using-the-Vagrant-Dev-Environment


set -e
set -x


REPOSPECS="pulp::pulp_installer jctanner:pulp:pulp_ansible pulp::pulp_container jctanner:ansible:galaxy_ng jctanner:pulp:pulpcore jctanner:ansible:galaxy-importer jctanner:ansible:ansible-hub-ui"

if [ -d dev ]; then
    rm -rf dev
fi
mkdir -p dev
TOPDIR=$(pwd)
cd dev
DEVDIR=$(pwd)

for REPOSPEC in $REPOSPECS; do

    DOWNSTREAM=$(echo $REPOSPEC | cut -d\: -f1)
    UPSTREAM=$(echo $REPOSPEC | cut -d\: -f2)
    REPO=$(echo $REPOSPEC | cut -d\: -f3)
    if [[ -z $UPSTREAM ]]; then
        UPSTREAM=$DOWNSTREAM
    fi

    CLONE_URL="https://github.com/${DOWNSTREAM}/${REPO}"
    if [[ "$DOWNSTREAM" == "jctanner" ]]; then
        CLONE_URL="git@github.com:${DOWNSTREAM}/${REPO}"
    fi
    UPSTREAM_URL="https://github.com/${UPSTREAM}/${REPO}"

    echo ""
    echo $DOWNSTREAM
    echo $UPSTREAM
    echo $REPO
    echo $CLONE_URL

    cd $DEVDIR
    git clone $CLONE_URL
    cd $REPO
    git fetch -a

    if [[ $DOWNSTREAM != $UPSTREAM ]]; then
        git remote add upstream $UPSTREAM_URL
        git fetch upstream
        #git pull --rebase upstream 

        PRIMARY_BRANCH=$(git remote show upstream | sed -n '/HEAD branch/s/.*: //p')
        echo "PBRANCH: ${PRIMARY_BRANCH}"
        CURRENT_BRANCH=$(git branch | awk '{print $2}')
        if [[ $CURRENT_BRANCH != $PRIMARY_BRANCH ]]; then
            git checkout origin/$PRIMARY_BRANCH
        fi
        git pull --rebase upstream $PRIMARY_BRANCH
    fi

done

cd $DEVDIR/pulp_installer

# 3.11 does not work on F35 because of https://github.com/theforeman/forklift/issues/1362
# git checkout 3.11
git submodule update --init
cp $TOPDIR/local.dev-config.yml .
