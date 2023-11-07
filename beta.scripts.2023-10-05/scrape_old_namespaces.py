#!/bin/bash

import glob
import datetime
import math
import statistics
import os
import json

from galaxy import upstream_namespace_iterator


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

    cachedir = os.path.join('.cache', 'namespaces')
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)

    fns = glob.glob(f'{cachedir}/*.json')
    cached_namespaces = [os.path.basename(x).replace('.json', '') for x in fns]

    mapped_users_by_id = load_user_map()

    durations = []
    count = 0

    last_page = None
    if os.path.exists('/tmp/last_page.json'):
        with open('/tmp/last_page.json', 'r') as f:
            pdata = json.loads(f.read())
            if pdata['page'] > 2:
                last_page = pdata['page'] - 1

    kwargs = {
        'use_cache': True,
        'start_page': last_page,
        #'skip_names': cached_namespaces
    }

    for pagenum, total, namespace_details in upstream_namespace_iterator(**kwargs):

        with open('/tmp/last_page.json', 'w') as f:
            f.write(json.dumps({'page': pagenum}))

        namespace_name = namespace_details['name']
        eta = None
        if durations and len(durations) > 3:
            eta = statistics.mean(durations) * (total - count)
            #import epdb; epdb.st()

        t0 = datetime.datetime.now()
        count += 1

        print(f'({total}|{count}) [{eta}s] {namespace_name}')

        #namespace_name = namespace_details['name']
        if '/' in namespace_name:
            continue
            #import epdb; epdb.st()
        cfn = os.path.join(cachedir, namespace_details['name'] + '.json')
        if os.path.exists(cfn):
            print(f'\tfound in cache ...')
            continue

        '''
        eta = None
        if durations and len(durations) > 3:
            eta = statistics.mean(durations) * (total - count)
            #import epdb; epdb.st()

        t0 = datetime.datetime.now()
        count += 1

        print(f'({total}|{count}) [{eta}s] {namespace_name}')
        '''

        ldata = {
            'namespace': namespace_name,
            'owners': []
        }

        for owner_details in namespace_details['summary_fields']['owners']:

            galaxy_username = owner_details['username']
            galaxy_github_id = owner_details['github_id']
            this_owner = {
                'galaxy_username': galaxy_username,
                'galaxy_github_id': galaxy_github_id,
                'github_login': None
            }

            print(f'\t{galaxy_username}:{galaxy_github_id}')

            if galaxy_github_id is None:
                print(f'\t\tlookup by user ...')
                try:
                    github_user_details = get_github_user_by_login(galaxy_username)
                except:
                    print(f'\t\t{galaxy_username} not found')
                    ldata['owners'].append(this_owner)
                    continue
            elif galaxy_github_id not in mapped_users_by_id:
                print(f'\t\tlookup by github id ...')
                try:
                    github_user_details = get_github_user_by_id(galaxy_github_id)
                except:
                    print(f'\t\t{galaxy_username} {galaxy_github_id} not found')
                    ldata['owners'].append(this_owner)
                    continue
                mapped_users_by_id[galaxy_github_id] = github_user_details
            else:
                github_user_details = mapped_users_by_id[galaxy_github_id]

            github_login = github_user_details['login']

            if galaxy_username != github_login:
                print(f'\t\t{galaxy_username} => {github_login}')

            this_owner['github_login'] = github_login
            ldata['owners'].append(this_owner)

        tN = datetime.datetime.now()
        tD = (tN - t0).total_seconds()
        durations.append(tD)

        with open(cfn, 'w') as f:
            f.write(json.dumps(ldata, indent=2))


if __name__ == "__main__":
    main()
