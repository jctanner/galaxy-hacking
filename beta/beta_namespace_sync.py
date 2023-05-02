#!/usr/bin/env python

import json
import os
import random
import re
import string

import requests
import requests_cache
from logzero import logger

# https://github.com/ansible/galaxy-importer/blob/master/galaxy_importer/constants.py#L45
NAME_REGEXP = re.compile(r"^(?!.*__)[a-z]+[0-9a-z_]*$")

UPSTREAM = "https://galaxy.ansible.com"
DOWNSTREAM = "http://localhost:5001"
DOWNSTREAM_USER = 'admin'
DOWNSTREAM_PASS = 'admin'
SESSION = requests_cache.CachedSession('demo_cache')


def get_upstream_namespaces():

    cache_file = 'data_namespaces.json'
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            namespaces = json.loads(f.read())
        return namespaces

    namespaces = {}

    pcount = 0
    next_url = UPSTREAM + '/api/v1/namespaces/?page_size=100'
    while next_url:
        pcount += 1
        logger.info(next_url)
        rr = SESSION.get(next_url)
        ds = rr.json()

        for res in ds['results']:
            namespaces[res['name']] = res

            owners = []

            # get the owners ...
            next_owners_url = UPSTREAM + res['related']['owners'] + '?page_size=100'
            while next_owners_url:
                logger.info(f'{pcount} {next_owners_url}')
                rr = SESSION.get(next_owners_url)
                ods = rr.json()
                for ores in ods['results']:
                    owners.append(ores)
                if not ods.get('next_link'):
                    break
                next_owners_url = UPSTREAM + ods['next_link']

            namespaces[res['name']]['owners'] = owners

        if not ds.get('next_link'):
            break

        next_url = UPSTREAM + ds['next_link']

    with open(cache_file, 'w') as f:
        f.write(json.dumps(namespaces))

    return namespaces


def create_downstream_namespaces(upstream_namespaces):

    users_to_sync = set()
    namespaces_to_sync = set()

    nskeys = sorted(upstream_namespaces.keys())
    for nskey in nskeys:
        ns = upstream_namespaces[nskey]

        # no point in creating namespaces that have no owners
        if not ns['owners']:
            continue

        # 1:1 username namespaces are autocreated during login or sync
        if len(ns['owners']) == 1 and ns['name'] == ns['owners'][0]['username']:
            continue

        # is this a valid namespace string?
        if not re.match(NAME_REGEXP, nskey):
            continue

        # is it long enough?
        if len(nskey) <= 2:
            continue

        for owner in ns['owners']:
            users_to_sync.add(owner['username'])

        namespaces_to_sync.add(nskey)

    create_downstream_users(users_to_sync)

    # make a list of current NSes
    current_namespaces = {}
    next_url = DOWNSTREAM + '/api/_ui/v1/namespaces/'
    while next_url:
        rr = requests.get(next_url, auth=(DOWNSTREAM_USER, DOWNSTREAM_PASS))
        ds = rr.json()

        for ns in ds['data']:
            current_namespaces[ns['name']] = ns

        if not ds['links'].get('next'):
            break

        next_url = DOWNSTREAM + ds['links']['next']

    # rbac ... ?
    #   https://github.com/ansible/galaxy_ng/blob/master/galaxy_ng/app/utils/rbac.py#L60-L62
    role_name = 'galaxy.collection_namespace_owner'
    rr = requests.get(
        DOWNSTREAM + f'/api/pulp/api/v3/roles/?name={role_name}',
        auth=(DOWNSTREAM_USER, DOWNSTREAM_PASS)
    )
    role_info = rr.json()['results'][0]

    # create or modify the namespaces
    namespaces_to_sync = sorted(list(namespaces_to_sync))
    total = len(namespaces_to_sync)
    for nscount,nskey in enumerate(namespaces_to_sync):

        logger.info(f'{total}|{nscount} checking owners for {nskey}')

        if nskey not in current_namespaces:
            logger.info(f'create {nskey} namespace')
            rr = requests.post(
                DOWNSTREAM + '/api/_ui/v1/namespaces/',
                json={'name': nskey, 'groups': []},
                auth=(DOWNSTREAM_USER, DOWNSTREAM_PASS)
            )
            current_namespaces[nskey] = rr.json()

        upstream_ns = upstream_namespaces[nskey]
        upstream_owners = [x['username'] for x in upstream_ns['summary_fields']['owners']]

        if 'pulp_href' not in current_namespaces[nskey]:
            import epdb; epdb.st()

        # rbac ... ?
        for uowner in upstream_owners:
            uinfo = get_downstream_user(uowner)
            userid = uinfo['id']
            logger.info(f'\tcheck current roles for {uowner}')
            rr = requests.get(DOWNSTREAM + f'/api/pulp/api/v3/users/{userid}/roles/', auth=(DOWNSTREAM_USER, DOWNSTREAM_PASS))
            res = rr.json()

            # check if the ns is bound to the user ...
            ns_href = current_namespaces[nskey]['pulp_href']
            matches = [x for x in res['results'] if x['role'] == role_name and x['content_object'] == ns_href]
            if not matches:
                logger.info(f'\tadd {role_name}+{nskey} to user:{uowner}')
                rr2 = requests.post(
                    DOWNSTREAM + f'/api/pulp/api/v3/users/{userid}/roles/',
                    json={'role': role_name, 'content_object': ns_href},
                    auth=(DOWNSTREAM_USER, DOWNSTREAM_PASS)
                )

        #import epdb; epdb.st()


def get_downstream_user(username):
    rr = requests.get(
        DOWNSTREAM + f'/api/_ui/v1/users/?username={username}',
        auth=(DOWNSTREAM_USER, DOWNSTREAM_PASS)
    )
    return rr.json()['data'][0]


def create_downstream_users(usernames):

    logger.info(f'verify {len(usernames)} usernames')

    # make a list of current users ...
    current_users = set()
    next_url = DOWNSTREAM + '/api/_ui/v1/users/?limit=100'
    while next_url:
        logger.info(next_url)
        rr = requests.get(next_url, auth=(DOWNSTREAM_USER, DOWNSTREAM_PASS))
        ds = rr.json()

        for user in ds['data']:
            current_users.add(user['username'])

        if not ds['links'].get('next'):
            break

        next_url = DOWNSTREAM + ds['links']['next']

    current_users = list(current_users)

    usernames = sorted(set(usernames))
    total = len(usernames)
    for idu, username in enumerate(usernames):

        if username in current_users:
            continue

        logger.info(f'create username[{total}|{idu}]: {username}')

        password = ''.join([random.choice(string.printable) for x in range(0, 12)])

        payload = {
            'username': username,
            'first_name': '',
            'last_name': '',
            'email': '',
            'group': '',
            'password': password,
            'description': ''
        }

        rr = requests.post(
            DOWNSTREAM + '/api/_ui/v1/users/',
            json=payload,
            auth=(DOWNSTREAM_USER, DOWNSTREAM_PASS)
        )
        assert rr.status_code == 201, rr.text


def main():
    upstream_namespaces = get_upstream_namespaces()
    create_downstream_namespaces(upstream_namespaces)


if __name__ == "__main__":
    main()
