#!/bin/bash

import glob
import datetime
import math
import statistics
import os
import json

import requests
from logzero import logger


def get_github_user_by_id(uid):
    fn = os.path.join('.cache/github_users/by_id', f'{uid}.json')
    with open(fn, 'r') as f:
        udata = json.loads(f.read())

    if udata.get('message') == 'Not Found':
        raise Exception('not found')

    return udata


def get_github_user_by_login(login):
    fn = os.path.join('.cache/github_users/by_name', f'{login}.json')
    with open(fn, 'r') as f:
        udata = json.loads(f.read())

    if udata.get('message') == 'Not Found':
        raise Exception('not found')

    return udata


def load_user_map():
    umap = {}
    filenames = glob.glob('.cache/github_users/by_id/*.json')
    for fn in filenames:
        with open(fn, 'r') as f:
            udata = json.loads(f.read())

        if udata.get('message') == 'Not Found':
            continue

        umap[udata['id']] = udata

    return umap


def main():

    cachedir = '.cache/galaxy_users'
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)

    baseurl = 'https://old-galaxy.ansible.com'
    next_url = baseurl + '/api/v1/users/'

    while next_url:
        logger.info(next_url)
        rr = requests.get(next_url)
        resp = rr.json()

        for udata in resp['results']:
            uid = udata['id']
            cfile = os.path.join(cachedir, str(uid) + '.json')
            logger.info(f'\t{cfile}')
            with open(cfile, 'w') as f:
                f.write(json.dumps(udata, indent=2, sort_keys=True))

        if not resp.get('next_link'):
            break

        next_url = baseurl + resp['next_link']


if __name__ == "__main__":
    main()
