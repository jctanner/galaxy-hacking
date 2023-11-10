#!/usr/bin/env python

import json
import os
import requests

from pprint import pprint

from github_lib import fetch_userdata_by_id


def main():

    GALAXY_TOKEN = os.environ.get('GALAXY_TOKEN')

    with open('data.json', 'r') as f:
        rows = json.loads(f.read())

    for row in rows:

        print('')
        print('-' * 50)
        pprint(row)
        print('')

        # get the github user data ...
        gid = int(row['uid'])
        gdata = fetch_userdata_by_id(gid)

        real_login = gdata['login']
        print(f'{gid} == {real_login}')
        print('')

        v1_name = row['legacy_ns']
        bad_v3_name = row['v3_ns']
        correct_v3_name = row['v3_ns'][:-1]

        owners = {}

        lns_rr = requests.get(f'https://galaxy.ansible.com/api/v1/namespaces/?name={v1_name}')
        lns_data = lns_rr.json()['results'][0]
        print(f'v1:{v1_name} owners ...')
        for owner in lns_data['summary_fields']['owners']:
            print('\t' + owner['username'])
            owners[owner['username']] = owner['id']

        bns_rr = requests.get(f'https://galaxy.ansible.com/api/v3/namespaces/?name={correct_v3_name}')
        bns_data = bns_rr.json()['data'][0]
        print(f'v3:{bad_v3_name} owners ...')
        for owner in bns_data['users']:
            print('\t' + owner['name'])
            owners[owner['name']] = owner['id']

        cns_rr = requests.get(f'https://galaxy.ansible.com/api/v3/namespaces/?name={correct_v3_name}')
        cns_data = cns_rr.json()['data'][0]
        print(f'v3:{correct_v3_name} owners ...')
        for owner in cns_data['users']:
            print('\t' + owner['name'])
            owners[owner['name']] = owner['id']


        # set the provider namespace ...
        v1_id = lns_data['id']
        cns_id = cns_data['id']

        v1_owners_url = f'https://galaxy.ansible.com/api/v1/namespaces/{v1_id}/owners/'
        v1_provider_url = f'https://galaxy.ansible.com/api/v1/namespaces/{v1_id}/providers/'

        # add ALL owners to the correct namespace ...
        owners_payload = {'owners': [{'id': x} for x in owners.values()]}
        orr = requests.put(
            v1_owners_url,
            headers={'Authorization': f'token {GALAXY_TOKEN}'},
            json=owners_payload
        )
        assert orr.status_code == 200

        # set the provider namespace ...
        print(v1_provider_url)
        provider_payload = {'id': cns_id}
        prr = requests.put(
            v1_provider_url,
            headers={'Authorization': f'token {GALAXY_TOKEN}'},
            json=provider_payload
        )
        assert prr.status_code == 200
        #import epdb; epdb.st()


if __name__ == "__main__":
    main()
