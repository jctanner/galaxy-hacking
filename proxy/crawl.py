#!/usr/bin/env python


import requests


def paginate(next_url):
    base_url = 'http://localhost:8080'
    while next_url:
        print(next_url)
        rr = requests.get(next_url)
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
    next_url = base_url + '/api/v1/roles'
    while next_url:
        print(next_url)
        rr = requests.get(next_url)
        if rr.status_code != 200:
            parts = next_url.split('=')
            pagenum = int(parts[1]) + 1
            next_url = parts[0] + '=' + str(pagenum)
            continue
        ds = rr.json()
        if not ds.get('next_link'):
            break
        next_url = base_url + ds['next_link']

        # iterate each role ...
        for role in ds['results']:
            role_url = base_url + role['url']
            print(role_url)
            rr2 = requests.get(role_url)
            ds2 = rr2.json()
            paginate(base_url + role['url'] + 'versions/')

    import epdb; epdb.st()


if __name__ == "__main__":
    main()
