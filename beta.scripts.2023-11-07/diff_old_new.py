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
from namespace_utils import map_v3_namespace
from namespace_utils import generate_v3_namespace_from_attributes


GALAXY_TOKEN = os.environ.get('GALAXY_TOKEN')


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

    def wipe_server(self, baseurl):
        keys = sorted(list(self.cmap.keys()))
        keys = [x for x in keys if x.startswith(baseurl)]

        for key in keys:
            print(f'DELETE CACHE {key}')
            os.remove(self.cmap[key])
            self.cmap.pop(key, None)
            #import epdb; epdb.st()


def scrape_v3_namespaces(cacher, server=None):
    namespaces = []

    if server is None:
        baseurl = 'https://old-galaxy.ansible.com'
    else:
        baseurl = server

    next_page = f'{baseurl}/api/v3/namespaces/'
    while next_page:
        logger.info(next_page)
        ds = cacher.get(next_page)

        for ns in ds['data']:
            namespaces.append(ns)

        if not ds['links'].get('next'):
            break

        next_page = baseurl + ds['links']['next']

    return namespaces


def scrape_objects(object_name, cacher, api_version='v1', server=None):
    objects = []

    if server is None:
        baseurl = 'https://old-galaxy.ansible.com'
    else:
        baseurl = server

    next_page = f'{baseurl}/api/{api_version}/{object_name}/'
    while next_page:
        logger.info(next_page)
        ds = cacher.get(next_page)

        for obj in ds['results']:
            objects.append(obj)

        if not ds.get('next') and not ds.get('next_link'):
            break

        if ds.get('next_link'):
            next_page = baseurl + ds['next_link']
            continue

        next_page = ds['next']
        if 'http://' in next_page:
            next_page = next_page.replace('http://', 'https://')
        if not next_page.startswith(baseurl):
            next_page = baseurl + next_page

    return objects


def bind_provider(server, v1_id, v3_id):
    """Set the provider namespace on a legacy namespace."""

    # get the legacy namespace first ...
    legacy_url = server + f'/api/v1/namespaces/{v1_id}/'
    rr = requests.get(legacy_url)
    v1_data = rr.json()

    # don't change if already set
    if v1_data['summary_fields']['provider_namespaces']:
        return

    payload = {
        'id': v3_id
    }
    post_url = legacy_url + 'providers/'
    prr = requests.put(
        post_url,
        headers={'Authorization': f'token {GALAXY_TOKEN}'},
        json=payload
    )
    logger.info(f'\t\tprovider update status code: {prr.status_code}')
    #import epdb; epdb.st()


def compare_data(
    old_namespaces,
    new_namespaces,
    old_users=None,
    old_roles=None,
    old_collections=None,
    v3_namespaces=None,
    new_roles=None,
    server=None
):

    old_by_name = {}
    new_by_name = {}
    v3_by_name = {}

    # map out the downstream legacy namespace names as lowercase
    # so we can later check for duplication ...
    downstream_legacy_lowercase_namespace_name_map = {}

    old_users_by_username = {}
    for old_user in old_users:
        old_users_by_username[old_user['username']] = old_user

    for old_namespace in old_namespaces:
        old_by_name[old_namespace['name']] = old_namespace

    for new_namespace in new_namespaces:
        new_by_name[new_namespace['name']] = new_namespace

        lowercase_name = new_namespace['name'].lower()
        if lowercase_name not in downstream_legacy_lowercase_namespace_name_map:
            downstream_legacy_lowercase_namespace_name_map[lowercase_name] = []
        downstream_legacy_lowercase_namespace_name_map[lowercase_name].append(new_namespace['name'])

    for v3_ns in v3_namespaces:
        v3_by_name[v3_ns['name']] = v3_ns

    old_collection_namespaces = set()
    for old_collection in old_collections:
        old_collection_namespaces.add(old_collection['namespace']['name'])

    old_role_namespaces = set()
    for old_role in old_roles:
        old_role_namespaces.add(old_role['summary_fields']['namespace']['name'])

    missing_v1_namespaces = []
    missing_provider = []
    missing_owners = []

    old_names = sorted(list(old_by_name.keys()))
    for old_name in old_names:

        has_old_collections = old_name in old_collection_namespaces
        has_old_roles = old_name in old_role_namespaces
        has_old_content = has_old_collections or has_old_roles

        if old_name not in new_by_name:

            # we don't care if the namespace is missing if it doesn't have content ...
            if has_old_content:
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

    logger.info('')
    logger.info('==== STATS ====')
    logger.warning(f'legacy namespaces total: {len(new_namespaces)}')
    logger.warning(f'missing legacy namespaces: {len(missing_v1_namespaces)}')
    logger.warning(f'legacy namespaces w/ missing provider namespace: {len(missing_provider)}')
    logger.warning(f'legacy namespaces w/ missing owner(s): {len(missing_owners)}')

    logger.info('')
    logger.info('==== MISSING PROVIDERS ====')
    for nid,ns_name in enumerate(missing_provider):
        nsdata = new_by_name[ns_name]
        logger.info(f'{nid}. {ns_name}')

        gh_data = fetch_userdata_by_name(ns_name)
        github_id = gh_data.get('id')

        # is there a v3 namespace?
        v3_name = generate_v3_namespace_from_attributes(username=ns_name, github_id=github_id)
        v3_ns = v3_by_name.get(v3_name)
        if v3_ns:
            logger.info(f'\tfound v3: {v3_ns["name"]}')
            for owner in v3_ns['users']:
                logger.info(f'\t\towner: {owner["name"]}')

            bind_provider(server, new_by_name[ns_name]['id'], v3_ns['id'])
            continue

        logger.warning(f'\tno matching v3 namespace for {v3_name}')
            #import epdb; epdb.st()

    logger.info('')
    logger.info('==== MISSING LEGACY NAMESPACES ====')
    for nid,ns_name in enumerate(missing_v1_namespaces):
        logger.info(f'{nid}. {ns_name}')

        legacy_names = downstream_legacy_lowercase_namespace_name_map.get(ns_name.lower())
        if legacy_names:
            for ln in legacy_names:
                logger.info(f'\t similar legacy namespace: {ln}')

    import epdb; epdb.st()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--downstream',
        default='https://galaxy.ansible.com',
        help='the beta server'
    )
    parser.add_argument(
        '--refresh-downstream-cache',
        action='store_true'
    )
    args = parser.parse_args()

    # make cache
    cacher = Cacher()

    if args.refresh_downstream_cache:
        cacher.wipe_server(args.downstream)
        return
    # cacher.wipe_server('https://galaxy.ansible.com/api/v1/namespaces')

    # get all old roles
    upstream_roles = scrape_objects('roles', cacher)

    # get all old collections
    upstream_collections = scrape_objects('collections', cacher, api_version='v2')

    # get all new roles
    downstream_roles = scrape_objects('roles', cacher, server=args.downstream)

    # get all users from old ...
    upstream_users = scrape_objects('users', cacher)

    # get all v3 namespaces from new
    downstream_v3_namespaces = scrape_v3_namespaces(cacher, server=args.downstream)

    # get all namespaces from old
    # upstream_namespaces = scrape_namespaces(cacher)
    upstream_namespaces = scrape_objects('namespaces', cacher)

    # get all namespace from new
    downstream_legacy_namespaces = scrape_objects('namespaces', cacher, server=args.downstream)

    compare_data(
        upstream_namespaces,
        downstream_legacy_namespaces,
        old_users=upstream_users,
        old_roles=upstream_roles,
        old_collections=upstream_collections,
        v3_namespaces=downstream_v3_namespaces,
        new_roles=downstream_roles,
        server=args.downstream
    )
    #import epdb; epdb.st()


if __name__ == "__main__":
    main()
