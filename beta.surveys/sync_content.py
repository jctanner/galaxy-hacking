#!/usr/bin/env python

import json
import requests
import subprocess


def sync_roles():
    with open('old_role_surveys.json', 'r') as f:
        rows = json.loads(f.read())

    fqrns = set()
    for row in rows:
        fqrn = (row['ns_name'], row['repo_name'])
        fqrns.add(fqrn)
    fqrns = sorted(fqrns)

    rmap = {}

    baseurl = 'http://localhost:5001'
    next_page = baseurl + '/api/v1/roles/'
    while next_page:
        rr = requests.get(next_page)
        ds = rr.json()
        for role in ds['results']:
            fqrn = (role['summary_fields']['namespace']['name'], role['name'])
            rmap[fqrn] = role

        if not ds.get('next'):
            break
        next_page = ds['next']

    for idf,fqrn in enumerate(fqrns):
        print(f'{idf} {fqrn}')
        if fqrn in rmap:
            continue
        ns_name = fqrn[0]
        name = fqrn[1]
        cmd = f'pulpcore-manager sync-galaxy-roles --github_user={ns_name} --role_name={name}'
        pid = subprocess.run(cmd, shell=True)

    #import epdb; epdb.st()

def sync_collections():
    with open('old_collection_surveys.json', 'r') as f:
        rows = json.loads(f.read())

    fqcns = set()
    for row in rows:
        fqcn = (row['namespace'], row['name'])
        fqcns.add(fqcn)
    fqcns = sorted(fqcns)

    cmap = {}
    baseurl = 'http://localhost:5001'
    next_page = baseurl + '/api/v3/collections/'
    while next_page:
        print(next_page)
        rr = requests.get(next_page)
        ds = rr.json()
        for col in ds['data']:
            fqcn = (col['namespace'], col['name'])
            cmap[fqcn] = col

        if not ds['links'].get('next'):
            break

        next_page = baseurl + ds['links']['next']

    import epdb; epdb.st()

    for idc,fqcn in enumerate(fqcns):
        print(f'{idc} {fqcn}')
        if fqcn in cmap:
            continue

        namespace = fqcn[0]
        name = fqcn[1]

        cmd = [
            'pulpcore-manager sync-galaxy-collections',
            f'--namespace={namespace}',
            f'--name={name}',
            f'--remote=community',
            f'--repository=published',
            '--latest'
        ]
        pid = subprocess.run(' '.join(cmd), shell=True)

    import epdb; epdb.st()


def main():
    #sync_roles()
    sync_collections()
    import epdb; epdb.st()



if __name__ == "__main__":
    main()
