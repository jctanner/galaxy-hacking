#!/usr/bin/env python

import requests
import json


def main():

    baseurl = 'https://galaxy.ansible.com'
    next_url = baseurl + '/api/v1/imports/?order_by=-created'
    while next_url:
        rr = requests.get(next_url)
        ds = rr.json()

        for task in ds['results']:
            sf = task['summary_fields']
            tds = {
                'id': task['id'],
                #'created': task['created'],
                'user': sf['request_username'],
                'github_user': sf['github_user'],
                'github_repo': sf['github_repo'],
                'github_ref': sf['github_reference'],
                'role_name': sf['alternate_role_name'],
            }
            print(json.dumps(tds))
            #import epdb; epdb.st()

        if not ds.get('next'):
            break

        next_url = ds['next']
        #import epdb; epdb.st()


if __name__ == "__main__":
    main()
