#!/usr/bin/env python

import requests
import os

def main():

    token = os.environ.get('HUB_TOKEN')
    username = os.environ.get('HUB_USERNAME')
    password = os.environ.get('HUB_PASSWORD')
    upstream_baseurl = os.environ.get(
        'GALAXY_UPSTREAM_BASEURL',
        'https://galaxy.ansible.com'
    )
    baseurl = upstream_baseurl + '/api/v1/roles/'
    downstream_baseurl = os.environ.get(
        'GALAXY_DOWNSTREAM_BASEURL',
        'https://beta-galaxy-dev.ansible.com'
    )
    sync_url = downstream_baseurl + '/api/v1/sync/'

    kwargs = {
        'json': {'baseurl': baseurl},
    }
    if token:
        headers = {'Authorization': f'token {token}'}
        kwargs['headers'] = headers
    elif username and password:
        kwargs['auth'] = (username, password)

    rr = requests.post(sync_url, **kwargs)
    ds = rr.json()


if __name__ == "__main__":
    main()
