#!/usr/bin/env python

import json
import logging
import os
import re
import requests
import requests_cache


logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s')


# https://github.com/ansible/galaxy-importer/blob/master/galaxy_importer/constants.py#L45
NAME_REGEXP = re.compile(r"^(?!.*__)[a-z]+[0-9a-z_]*$")
DOWNSTREAM_BASEURL = 'https://galaxy-ng-beta.tannerjc.net'


if not os.path.exists('/tmp/downstream'):
    os.makedirs('/tmp/downstream')

def create_downstream_user(username):

    logging.info(f'check {username}')

    fn = os.path.join('/tmp/downstream', f'user.{username}')
    if os.path.exists(fn):
        return

    '''
    search_url = DOWNSTREAM_BASEURL + f'/api/_ui/v1/users/?username={username}'
    rr = requests.get(search_url, verify=False, auth=('admin', 'admin'))
    ds = rr.json()
    if ds['meta']['count'] > 0:
        with open(fn, 'w') as f:
            f.write('')
        return
    '''

    logging.info(f'create {username}')
    url = DOWNSTREAM_BASEURL + f'/api/_ui/v1/users/'
    rr2 = requests.post(url, verify=False, auth=('admin', 'admin'), json={'username': username})
    # assert rr2.status_code == 201

    with open(fn, 'w') as f:
        f.write('')


def main():

    with open('data.json', 'r') as f:
        ds = json.loads(f.read())

    for idu, username in enumerate(ds['usernames']):
        logging.info(f'{len(ds["usernames"])} | {idu}')
        create_downstream_user(username)

    import epdb; epdb.st()


if __name__ == "__main__":
    main()
