#!/usr/bin/env python

import json
import logging
import re
import requests
import requests_cache


logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s')


# https://github.com/ansible/galaxy-importer/blob/master/galaxy_importer/constants.py#L45
NAME_REGEXP = re.compile(r"^(?!.*__)[a-z]+[0-9a-z_]*$")

DOWNSTREAM_BASEURL = 'https://galaxy-ng-beta.tannerjc.net'


def get_upstream_roles():
    roles = []

    session = requests_cache.CachedSession('upstream_cache')
    next_url = 'https://galaxy.ansible.com/api/v1/roles/'
    while next_url:
        logging.info(next_url)
        rr = session.get(next_url)
        try:
            ds = rr.json()
        except requests.exceptions.JSONDecodeError:
            pagenum = int(next_url.split('=')[1]) + 1
            next_url = 'https://galaxy.ansible.com/api/v1/roles/?page=' + str(pagenum)
            continue

        results = ds['results']
        roles.extend(results)
        next_url = ds['next']
        if next_url:
            next_url = 'https://galaxy.ansible.com/api/v1' + next_url

    return roles


def get_upstream_collections():
    collections = []

    session = requests_cache.CachedSession('upstream_cache')
    next_url = 'https://galaxy.ansible.com/api/v2/collections/'
    while next_url:
        logging.info(next_url)
        rr = session.get(next_url)
        ds = rr.json()
        results = ds['results']

        for idc, collection in enumerate(results):
            logging.info(collection['namespace']['href'])
            ns_rr = session.get(collection['namespace']['href'])
            results[idc]['namespace'] = ns_rr.json()

        collections.extend(results)
        next_url = ds['next']
        if next_url:
            next_url = 'https://galaxy.ansible.com' + next_url

    return collections


def collections_to_namespaces(collections):
    namespaces = {}
    for collection in collections:
        ns = collection['namespace']['name']
        if ns not in namespaces:
            namespaces[ns] = collection['namespace']
    return namespaces


def roles_to_namespaces(roles):
    namespaces = {}
    for role in roles:
        ns = role['summary_fields']['namespace']
        ns_name = ns['name']
        if ns_name not in namespaces:
            namespaces[ns_name] = ns
    return namespaces


def get_upstream_namespaces(limit=None, get_content=True):

    namespaces = []

    session = requests_cache.CachedSession('upstream_cache')
    next_url = 'https://galaxy.ansible.com/api/v1/namespaces'
    count = 0
    while next_url:
        count += 1
        logging.info(next_url)
        rr = session.get(next_url)
        ds = rr.json()

        results = ds['results']

        if get_content:
            for ids, ns in enumerate(results):
                content = []
                next_content_url = 'https://galaxy.ansible.com' + ns['related']['content']
                while next_content_url:
                    logging.info(next_content_url)
                    crr = session.get(next_content_url)
                    try:
                        cds = crr.json()
                    except requests.exceptions.JSONDecodeError:
                        if '?' not in next_content_url:
                            break
                        import epdb; epdb.st()
                    content.extend(cds['results'])

                    next_content_url = cds['next_link']
                    if next_content_url:
                        next_content_url = 'https://galaxy.ansible.com' + next_content_url

                results[ids]['content'] = content
                #if content:
                #    import epdb; epdb.st()

        namespaces.extend(results)

        next_url = ds.get('next')
        if next_url:
            next_url = 'https://galaxy.ansible.com/api/v1' + next_url
        if limit and len(namespaces) >= limit:
            break

    return namespaces


def namespaces_to_userlist(namespaces):
    users = {}
    for ns in namespaces:
        for owner in ns['summary_fields']['owners']:
            username = owner['username']
            if username not in users:
                users[username] = {
                    'info': owner,
                    'namespaces': set()
                }
            users[username]['namespaces'].add(ns['name'])
    return users


def namespaces_to_owner_names(namespaces):
    owners = {}
    for ns in namespaces:
        owners[ns['name']] = \
            [x['username'] for x in ns['summary_fields']['owners']]
    return owners


def namespaces_to_map(namespaces):
    nsmap = {}
    for namespace in namespaces:
        nsmap[namespace['name']] = namespace
    return nsmap


def create_downstream_user(userinfo):
    username = userinfo['info']['username']
    search_url = DOWNSTREAM_BASEURL + f'/api/_ui/v1/users/?username={username}'
    rr = requests.get(search_url, verify=False, auth=('admin', 'admin'))
    ds = rr.json()
    if ds['meta']['count'] > 0:
        return

    logging.info(f'create {username}')
    url = DOWNSTREAM_BASEURL + f'/api/_ui/v1/users/'
    rr2 = requests.post(url, verify=False, auth=('admin', 'admin'), json={'username': username})
    assert rr2.status_code == 201


def main():

    #upstream_namespaces = get_upstream_namespaces(limit=100)
    upstream_namespaces = get_upstream_namespaces(get_content=False)
    upstream_namespace_map = namespaces_to_map(upstream_namespaces)

    #upstream_users = namespaces_to_userlist(upstream_namespaces)
    #upstream_owners = namespaces_to_owner_names(upstream_namespaces)

    upstream_roles = get_upstream_roles()
    upstream_role_namespaces = roles_to_namespaces(upstream_roles)

    upstream_collections = get_upstream_collections()
    upstream_collection_namespaces = collections_to_namespaces(upstream_collections)

    #upstream_collection_owners = namespaces_to_owner_names(upstream_collection_namespaces.values())
    #upstream_collection_users = namespaces_to_userlist(upstream_collection_namespaces.values())

    all_namespace_names = sorted(set(
        list(upstream_role_namespaces.keys())
        + list(upstream_collection_namespaces.keys())
        + [x['name'] for x in upstream_namespaces]
    ))

    namespaces_collections_only = [
        x for x in all_namespace_names
        if x in upstream_collection_namespaces and x not in upstream_role_namespaces
    ]
    namespaces_roles_only = [
        x for x in all_namespace_names
        if x not in upstream_collection_namespaces and x in upstream_role_namespaces
    ]
    namespaces_roles_and_collections = [
        x for x in all_namespace_names
        if x in upstream_collection_namespaces and x in upstream_role_namespaces
    ]
    namespaces_roles_or_collections = [
        x for x in all_namespace_names
        if x in upstream_collection_namespaces or x in upstream_role_namespaces
    ]
    namespaces_no_content = [
        x for x in all_namespace_names
        if x not in upstream_collection_namespaces and x not in upstream_role_namespaces
    ]

    # check downstream users
    has_content = [x for x in upstream_namespaces if x['name'] in namespaces_roles_or_collections]
    #content_owners = namespaces_to_owner_names(has_content)
    content_owners = namespaces_to_userlist(has_content)

    '''
    for username, userinfo in content_owners.items():
        create_downstream_user(userinfo)
    import epdb; epdb.st()

    # check downstream role owners
    for ns in namespaces_roles_or_collections:
        namespace = upstream_namespace_map[ns]
        import epdb; epdb.st()
    '''

    ds = {
        'usernames': sorted(set(list(content_owners.keys()))),
        'namespaces': [
            {
                'name': x['name'],
                'has_roles': x['name'] in upstream_role_namespaces,
                'has_collections': x['name'] in upstream_collection_namespaces,
                'owners': [y['username'] for y in x['summary_fields']['owners']]
            }
            for x in upstream_namespaces if x['name'] in namespaces_roles_or_collections]
    }
    with open('data.json', 'w') as f:
        f.write(json.dumps(ds, indent=2))
    #import epdb; epdb.st()



if __name__ == "__main__":
    main()
