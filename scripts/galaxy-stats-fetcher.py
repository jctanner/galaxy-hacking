#!/usr/bin/env python

import requests
import requests_cache
from logzero import logger
from pprint import pprint


class StatsMaker:

    def __init__(self):
        self.baseurl = 'https://galaxy.ansible.com'
        self.session = requests_cache.CachedSession('demo_cache')

    def get_namespaces(self):
        namespaces = []
        next_url = 'https://galaxy.ansible.com/api/v1/namespaces/'
        while next_url:
            rr = self.session.get(next_url)
            ds = rr.json()
            if ds['next_link'] is None:
                break
            next_url = self.baseurl + ds['next_link']
            import epdb; epdb.st()

        return namespaces

    def get_roles(self):
        roles = {}
        next_url = 'https://galaxy.ansible.com/api/v1/roles/'
        while next_url:
            logger.info(next_url)
            rr = self.session.get(next_url)
            ds = rr.json()
            for role in ds['results']:
                roles[(role['summary_fields']['namespace']['name'], role['name'])] = {
                    'downloads': role['download_count']
                }
            if ds['next_link'] is None:
                break
            next_url = self.baseurl + ds['next_link']

        return roles

    def get_collections(self):
        collections = {}
        next_url = 'https://galaxy.ansible.com/api/v2/collections/'
        while next_url:
            logger.info(next_url)
            rr = self.session.get(next_url)
            ds = rr.json()
            for collection in ds['results']:
                collections[(collection['namespace']['name'], collection['name'])] = {}
            if ds['next_link'] is None:
                break
            next_url = self.baseurl + ds['next_link']

        for ckey in collections.keys():
            size = self.get_collection_size(ckey[0], ckey[1])
            collections[ckey]['size'] = size
            downloads = self.get_collection_downloads(ckey[0], ckey[1])
            collections[ckey]['downloads'] = downloads

        return collections

    def get_collection_downloads(self, namespace, name):
        # https://galaxy.ansible.com/api/internal/ui/repos-and-collections/?namespace=community
        url = self.baseurl + f'/api/internal/ui/repos-and-collections/?namespace={namespace}&name={name}'
        logger.info(url)
        rr = self.session.get(url)
        ds = rr.json()
        # assert ds['collection']['count'] == 1
        if ds['collection']['count'] > 1:
            cols = ds['collection']['results']
            cols = [x for x in cols if x['namespace']['name'] == namespace and x['name'] == name]
            col = cols[0]
            count = col['download_count']
        else:
            count = ds['collection']['results'][0]['download_count']
        return count

    def get_collection_size(self, namespace, name):
        # https://galaxy.ansible.com/api/v2/collections/testing/k8s_demo_collection/versions/
        url = self.baseurl + f'/api/v2/collections/{namespace}/{name}/versions/'
        logger.info(url)
        rr = self.session.get(url)
        ds = rr.json()
        url2 = ds['results'][0]['href']
        rr2 = self.session.get(url2)
        ds2 = rr2.json()
        size = ds2['artifact']['size']
        return size

    def run(self):
        roles = self.get_roles()
        collections = self.get_collections()

        print('# top 10 collections by downloads')
        pprint(sorted(list(collections.items()), key=lambda x: x[1]['downloads'])[-10:])
        print('# top 10 collections by size')
        pprint(sorted(list(collections.items()), key=lambda x: x[1]['size'])[-10:])

        print('# top 10 roles by downloads')
        pprint(sorted(list(roles.items()), key=lambda x: x[1]['downloads'])[-10:])


def main():
    sm = StatsMaker()
    sm.run()


if __name__ == "__main__":
    main()
