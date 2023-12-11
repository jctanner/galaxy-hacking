import os
import json
import gzip

import requests


# LOAD THE CACHE
with gzip.open('galaxy_namespaces.json.gz', 'rt') as gzipped_file:
    NAMESPACE_CACHE = json.load(gzipped_file)
IDS = list(NAMESPACE_CACHE['by_id'].keys())
for ID in IDS:
    newid = int(ID)
    NAMESPACE_CACHE['by_id'][newid] = NAMESPACE_CACHE['by_id'][ID]
    NAMESPACE_CACHE['by_id'].pop(ID)

with gzip.open('galaxy_users.json.gz', 'rt') as gzipped_file:
    USER_CACHE = json.load(gzipped_file)
IDS = list(USER_CACHE['by_id'].keys())
for ID in IDS:
    newid = int(ID)
    USER_CACHE['by_id'][newid] = USER_CACHE['by_id'][ID]
    USER_CACHE['by_id'].pop(ID)


def get_namespace_by_name(name):

    if name in NAMESPACE_CACHE['by_name']:
        return {
            'count': 1,
            'results': [NAMESPACE_CACHE['by_name'][name]]
        }

    safe_name = name.replace('/', '__SLASH__')

    cdir = '.cache/galaxy_namespaces'
    cfile = os.path.join(cdir, safe_name + '.json')
    if not os.path.exists(cdir):
        os.makedirs(cdir)
    if os.path.exists(cfile):
        with open(cfile, 'r') as f:
            ndata = json.loads(f.read())
        return ndata

    url = f'https://old-galaxy.ansible.com/api/v1/namespaces/?name={name}'
    rr = requests.get(url)
    ds = rr.json()

    with open(cfile, 'w') as f:
        f.write(json.dumps(ds))

    return ds



def get_user_detail(user_id):

    if user_id in USER_CACHE['by_id']:
        return USER_CACHE['by_id'][user_id]

    cdir = '.cache/galaxy_users'
    cfile = os.path.join(cdir, str(user_id) + '.json')
    if not os.path.exists(cdir):
        os.makedirs(cdir)
    if os.path.exists(cfile):
        with open(cfile, 'r') as f:
            udata = json.loads(f.read())
        return udata

    url = f'https://old-galaxy.ansible.com/api/v1/users/{user_id}/'
    rr = requests.get(url)
    ds = rr.json()

    with open(cfile, 'w') as f:
        f.write(json.dumps(ds))

    return ds


def get_old_owners(names):
    for name in names:

        ds = get_namespace_by_name(name)
        if not ds['results']:
            continue

        ds = ds['results'][0]

        owners = ds['summary_fields']['owners']

        # fill in the github ids ...
        for idx, x in enumerate(owners):
            udata = get_user_detail(x['id'])
            owners[idx].update(udata)

        return (name, owners)

    return (None, [])
