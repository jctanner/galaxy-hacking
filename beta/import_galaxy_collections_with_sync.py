#!/usr/bin/env python

import copy
import datetime
import glob
import json
import os
import statistics
import string
import subprocess
import sys
import time

import yaml
import requests
import requests_cache

from pprint import pprint
from logzero import logger

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_upstream_collection_list(baseurl=None):

    nexturl = baseurl + '/api/v2/collections/'

    if not os.path.exists('.data'):
        os.makedirs('.data')

    # always start fresh on the last page ...
    cachefiles = glob.glob('.data/collections_page_*.json')
    cachefiles = [(int(x.split('_')[-1].replace('.json', '')), x) for x in cachefiles]
    cachefiles = sorted(cachefiles)
    if cachefiles:
        os.remove(cachefiles[-1][1])

    results = []

    page_index = 0
    while nexturl:

        if not nexturl.startswith('http'):
            nexturl = baseurl.rstrip('/') + '/' + nexturl.lstrip('/')

        print(nexturl)
        if 'page=' in nexturl:
            page_index = int(nexturl.split('=')[-1])

        cf = os.path.join('.data', f'collections_page_{str(page_index)}.json')
        print(cf)

        if not os.path.exists(cf):
            rr = requests.get(nexturl)
            ds = rr.json()
            print(f'write {cf}')
            with open(cf, 'w') as f:
                f.write(json.dumps(ds))
        else:
            print(f'read {cf}')
            with open(cf, 'r') as f:
                ds = json.loads(f.read())

        results.extend(ds['results'])
        if ds.get('next_link'):
            nexturl = ds.get('next_link')
        else:
            nexturl = None

    return results


def get_collection_versions(cname, nexturl, baseurl=None):

    if not os.path.exists('.data'):
        os.makedirs('.data')

    results = []
    page_index = 0
    while nexturl:

        if not nexturl.startswith('http'):
            nexturl = baseurl.rstrip('/') + '/' + nexturl.lstrip('/')

        print(nexturl)
        if 'page=' in nexturl:
            page_index = int(nexturl.split('=')[-1])

        cf = os.path.join('.data', f'collections_versions_{cname}_page_{str(page_index)}.json')
        print(cf)

        if not os.path.exists(cf):
            rr = requests.get(nexturl)
            ds = rr.json()
            print(f'write {cf}')
            with open(cf, 'w') as f:
                f.write(json.dumps(ds))
        else:
            print(f'read {cf}')
            with open(cf, 'r') as f:
                ds = json.loads(f.read())

        results.extend(ds['results'])
        if ds.get('next'):
            #import epdb; epdb.st()
            nexturl = ds.get('next')
        else:
            nexturl = None

    return results


def generate_sync_requirements(cmap, baseurl):
    reqs ={'collections': []}
    keys = sorted(list(cmap.keys()))
    for key in keys:
        versions = cmap[key][::-1]
        for version in versions:
            ds = {
                'name': '.'.join(key),
                'version': version['version'],
                'source': f'{baseurl}/'
            }
            reqs['collections'].append(ds)
    return reqs



def main():

    token = os.environ.get('HUB_TOKEN')
    username = os.environ.get('HUB_USERNAME')
    password = os.environ.get('HUB_PASSWORD')

    upstream_baseurl = os.environ.get(
        'GALAXY_UPSTREAM_BASEURL',
        'https://galaxy.ansible.com'
    )
    downstream_baseurl = os.environ.get(
        'GALAXY_DOWNSTREAM_BASEURL',
        'https://beta-galaxy-dev.ansible.com'
    )
    sync_config_url = downstream_baseurl + '/api/content/published/v3/sync/config/'
    get_href_url = downstream_baseurl + '/api/pulp/api/v3/repositories/ansible/ansible/?name=published'
    if token:
        r_href = requests.get(get_href_url, headers={'Authorization': f'token {token}'}, verify=False)
    else:
        r_href = requests.get(get_href_url, auth=(username, password), verify=False)
    pulp_href = json.loads(r_href.content)['results'][0]['pulp_href']
    repo_url = downstream_baseurl + pulp_href
    sync_url = repo_url + 'sync/'
    api = 'api'

    upstream_collections = get_upstream_collection_list(baseurl=upstream_baseurl)

    cmap = {}
    for ds in upstream_collections:
        key = (ds['namespace']['name'], ds['name'])
        cname = '_'.join(key)
        cversions = get_collection_versions(
            cname,
            ds['versions_url'],
            baseurl=upstream_baseurl
        )
        cmap[key] = cversions

    greqs = generate_sync_requirements(cmap, upstream_baseurl)
    collections = greqs["collections"]
    total_collections = len(collections)
    chunk_size = int(os.environ.get(
        'CHUNK_SIZE',
        '100'
    ))
    total_chunks = (total_collections // chunk_size) + 1

    for chunk in range(1, total_chunks + 1):
        while True:
            if token:
                rr4 = requests.get(repo_url, headers={'Authorization': f'token {token}'}, verify=False)
            else:
                rr4 = requests.get(repo_url, auth=(username, password), verify=False)
            sync_state = json.loads(rr4.content)['last_sync_task']['state']
            if sync_state != "running" and sync_state != "waiting":
                break
            time.sleep(10)

        start = (chunk - 1) * chunk_size
        end = min(start + chunk_size, total_collections)
        output_file = f"galaxy_requirements_{chunk}.yml"

        greqs_string = yaml.safe_dump({"collections": collections[start:end]})

        print('')
        print('*' * 50)
        print('get sync config')
        print('*' * 50)
        if token:
            rr1 = requests.get(sync_config_url, headers={'Authorization': f'token {token}'}, verify=False)
        else:
            rr1 = requests.get(sync_config_url, auth=(username, password), verify=False)
        assert rr1.status_code == 200
        cfg = rr1.json()

        print('')
        print('*' * 50)
        print('generated new config ' + str(chunk) + ' of ' + str(total_chunks))
        print('*' * 50)
        cfg['url'] = upstream_baseurl.rstrip('/') + '/api/'
        cfg['requirements_file'] = greqs_string
        with open(output_file, 'w') as f:
            f.write(greqs_string)
        #sys.exit(0)
        print(cfg)

        # set the config
        print('')
        print('*' * 50)
        print('set new config ' + str(chunk) + ' of ' + str(total_chunks))
        print('*' * 50)
        if token:
            rr2 = requests.put(
                sync_config_url,
                headers={'Authorization': f'token {token}'},
                json=cfg,
                verify=False
            )
        else:
            rr2 = requests.put(
                sync_config_url,
                auth=(username, password),
                json=cfg,
                verify=False
            )
        print(rr2)
        assert rr2.status_code == 200

        # start the sync
        print('*' * 50)
        print('start sync ' + str(chunk) + ' of ' + str(total_chunks))
        print('*' * 50)
        if token:
            rr3 = requests.post(sync_url, headers={'Authorization': f'token {token}'}, json={}, verify=False)
        else:
            rr3 = requests.post(sync_url, auth=(username, password), json={}, verify=False)
        print(rr3)
        # {'task': '9e8129f6-e547-4142-bb95-22e520e3156f'}
        assert rr3.status_code == 202


if __name__ == "__main__":
    main()
