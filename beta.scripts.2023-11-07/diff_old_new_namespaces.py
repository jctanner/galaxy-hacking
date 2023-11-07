#!/usr/bin/env python

import os
import uuid
import argparse

import json
import glob
import requests

from logzero import logger

from github_lib import fetch_userdata_by_id
from github_lib import fetch_userdata_by_name


class Cacher:
    def __init__(self):
        self.cachedir = '.cache'
        if not os.path.exists(self.cachedir):
            os.makedirs(self.cachedir)

        self.cmap = {}
        cachefiles = glob.glob(f'{self.cachedir}/*.json')
        for cachefile in cachefiles:
            with open(cachefile, 'r') as f:
                ds = json.loads(f.read())
            self.cmap[ds['url']] = cachefile

    def store(self, url, data):
        fn = os.path.join(self.cachedir, str(uuid.uuid4()) + '.json')
        with open(fn, 'w') as f:
            f.write(json.dumps({'url': url, 'data': data}))
        self.cmap[url] = fn

    def get(self, url):

        if url in self.cmap:
            with open(self.cmap[url], 'r') as f:
                ds = json.loads(f.read())
            return ds['data']

        rr = requests.get(url)
        ds = rr.json()
        self.store(url, ds)
        return ds



def scrape_namespaces(cacher, server=None):

    namespaces = []

    if server is None:
        baseurl = 'https://old-galaxy.ansible.com'
    else:
        baseurl = server

    next_page = f'{baseurl}/api/v1/namespaces/'
    while next_page:
        logger.info(next_page)
        ds = cacher.get(next_page)

        for namespace in ds['results']:
            namespaces.append(namespace)

        if not ds.get('next') and not ds.get('next_link'):
            break

        if ds.get('next_link'):
            next_page = baseurl + ds['next_link']
            continue

        next_page = ds['next']
        #import epdb; epdb.st()

    return namespaces


def scrape_users(cacher, server=None):
    users = []

    if server is None:
        baseurl = 'https://old-galaxy.ansible.com'
    else:
        baseurl = server

    next_page = f'{baseurl}/api/v1/users/'
    while next_page:
        logger.info(next_page)
        ds = cacher.get(next_page)

        for user in ds['results']:
            users.append(user)

        if not ds.get('next') and not ds.get('next_link'):
            break

        if ds.get('next_link'):
            next_page = baseurl + ds['next_link']
            continue

        next_page = ds['next']
        #import epdb; epdb.st()

    return users


def compare_namespaces(old_namespaces, new_namespaces, old_users=None):

    old_by_name = {}
    new_by_name = {}

    old_users_by_username = {}
    for old_user in old_users:
        old_users_by_username[old_user['username']] = old_user

    for old_namespace in old_namespaces:
        old_by_name[old_namespace['name']] = old_namespace

    for new_namespace in new_namespaces:
        new_by_name[new_namespace['name']] = new_namespace

    missing_v1_namespaces = []
    missing_provider = []
    missing_owners = []

    old_names = sorted(list(old_by_name.keys()))
    for old_name in old_names:
        if old_name not in new_by_name:
            missing_v1_namespaces.append(old_name)
            continue

        old_ns = old_by_name.get(old_name)
        new_ns = new_by_name.get(old_name)

        if not new_ns['summary_fields']['provider_namespaces']:
            missing_provider.append(old_name)
            continue

        if not old_ns['summary_fields']['owners']:
            continue

        old_owners = [x['username'] for x in old_ns['summary_fields']['owners']]
        new_owners = [x['username'] for x in new_ns['summary_fields']['owners']]

        if sorted(old_owners) == sorted(new_owners):
            continue

        _missing_owners = []
        for old_owner in old_owners:
            if old_owner not in new_owners:

                old_owner_data = old_users_by_username[old_owner]
                old_owner_gh_id = old_owner_data['github_id']
                old_owner_gh_data = fetch_userdata_by_id(old_owner_gh_id)
                if old_owner_gh_data:
                    old_owner_gh_login_current = old_owner_gh_data['login']
                else:
                    old_owner_gh_login_current = None

                # if they changed their username and the new username is an owner,
                # they're not missing ...
                if old_owner_gh_login_current and old_owner_gh_login_current in new_owners:
                    continue

                _missing_owners.append(old_owner)

        if not _missing_owners:
            continue

        missing_owners.append(old_name)
        #import epdb; epdb.st()

    print(f'legacy namespaces w/ missing provider namespace: {len(missing_provider)}')
    print(f'legacy namespaces w/ missing owner(s): {len(missing_owners)}')

    import epdb; epdb.st()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--downstream',
        default='https://galaxy.ansible.com',
        help='the beta server'
    )
    args = parser.parse_args()

    # make cache
    cacher = Cacher()

    # get all users from old ...
    old_users = scrape_users(cacher)

    # get all roles from old
    old = scrape_namespaces(cacher)

    # get all roles from new
    new = scrape_namespaces(cacher, server=args.downstream)

    compare_namespaces(old, new, old_users=old_users)
    #import epdb; epdb.st()


if __name__ == "__main__":
    main()
