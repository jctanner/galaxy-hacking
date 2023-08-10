#!/usr/bin/env python

import argparse
import os
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('namespace')
    parser.add_argument('--token', default=os.environ.get('BETA_TOKEN'))
    args = parser.parse_args()

    if not args.token:
        raise Exception('export BETA_TOKEN or use --token=')

    baseurl = 'https://beta-galaxy-stage.ansible.com'
    next_url = (
        baseurl
        + '/api/v3/plugin/ansible/search/collection-versions/'
        + f'?is_highest=true&namespace={args.namespace}&offset=0&order_by=name'
    )
    while next_url:
        rr = requests.get(next_url)
        ds = rr.json()
        for collection_summary in ds['data']:
            namespace = collection_summary['collection_version']['namespace']
            name = collection_summary['collection_version']['name']
            if namespace != args.namespace:
                continue

            print(f'{namespace}.{name}')
            url = baseurl + f'/api/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/'
            #crr = requests.get(url)
            drr = requests.delete(
                url,
                headers={'Authorizaton': f'token {args.token}'}
            )
            print(f'\t{drr.status_code}')

        if not ds['links']['next']:
            break
        next_url = baseurl + ds['links']['next']



if __name__ == "__main__":
    main()
