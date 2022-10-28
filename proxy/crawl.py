#!/usr/bin/env python

import datetime
import requests


perfmap = {}


def paginate(next_url):
    base_url = 'http://localhost:8080'
    while next_url:
        print(next_url)
        t1 = datetime.datetime.now()
        rr = requests.get(next_url)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        perfmap[next_url] = delta

        if rr.status_code != 200:
            parts = next_url.split('=')
            pagenum = int(parts[1]) + 1
            next_url = parts[0] + '=' + str(pagenum)
            continue

        ds = rr.json()
        if not ds.get('next_link'):
            break
        next_url = base_url + ds['next_link']


def main():

    base_url = 'http://localhost:8080'

    roles = []

    next_url = base_url + '/api/v1/roles'
    while next_url:
        print(next_url)
        t1 = datetime.datetime.now()
        rr = requests.get(next_url)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        perfmap[next_url] = delta
        print(delta)

        if rr.status_code != 200:
            parts = next_url.split('=')
            pagenum = int(parts[1]) + 1
            next_url = parts[0] + '=' + str(pagenum)
            continue

        ds = rr.json()
        if not ds.get('next_link'):
            break
        next_url = base_url + ds['next_link']
        roles.extend(ds['results'])

    # iterate each role ...
    for idr,role in enumerate(roles):
        role_url = base_url + role['url']
        print(f'{len(roles)}|{idr} {role_url}')
        t1 = datetime.datetime.now()
        rr2 = requests.get(role_url)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        perfmap[role_url] = delta

        ds2 = rr2.json()
        paginate(base_url + role['url'] + 'versions/')

    import epdb; epdb.st()


if __name__ == "__main__":
    main()
