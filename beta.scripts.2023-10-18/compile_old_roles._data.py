#!/usr/bin/env python

import os
import uuid
import argparse
import re
import subprocess

import json
import glob
import requests

from urllib.parse import urlparse, parse_qs
import logzero
from logzero import logger


class Cacher:
    def __init__(self, refresh=False):
        self.refresh = refresh
        self.cachedir = '.cache'
        if not os.path.exists(self.cachedir):
            os.makedirs(self.cachedir)

        self.cmap = {}
        cachefiles = glob.glob(f'{self.cachedir}/*.json')
        for cachefile in cachefiles:
            with open(cachefile, 'r') as f:
                ds = json.loads(f.read())
            self.cmap[ds['url']] = cachefile

        if self.refresh:

            by_baseurl = {}

            for url in self.cmap.keys():
                parsed_url = urlparse(url)
                baseurl = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                query_params = parse_qs(parsed_url.query)
                pagenumber = query_params.get('page', [None])[0]

                if pagenumber is None:
                    continue

                if baseurl not in by_baseurl:
                    by_baseurl[baseurl] = []

                by_baseurl[baseurl].append([int(pagenumber), url])

            for baseurl, pages in by_baseurl.items():
                pages = sorted(pages)
                logger.info(f'DELETE CACHE {pages[-1]}')
                cachekey = pages[-1][1]
                cachefile = self.cmap[cachekey]
                os.remove(cachefile)
                self.cmap.pop(cachekey)

        # bad keys?
        badkeys = [x for x in self.cmap.keys() if 'http://galaxy.ansible.com' in x]
        for badkey in badkeys:
            cachefile = self.cmap[badkey]
            os.remove(cachefile)
            self.cmap.pop(badkey)

    def clean(self, baseurl=None):
        keys = list(self.cmap.keys())
        for key in keys:
            if not key.startswith(baseurl):
                continue
            cachefile = self.cmap[key]
            logger.info(f'CLEAN {key} {cachefile}')
            os.remove(cachefile)
            self.cmap.pop(key)

    def store(self, url, data):
        fn = os.path.join(self.cachedir, str(uuid.uuid4()) + '.json')
        with open(fn, 'w') as f:
            f.write(json.dumps({'url': url, 'data': data}))
        self.cmap[url] = fn
        #import epdb; epdb.st()

    def get(self, url):

        if url in self.cmap:
            with open(self.cmap[url], 'r') as f:
                ds = json.loads(f.read())
            return ds['data']

        logger.info(f'fetch {url}')

        #import epdb; epdb.st()

        rr = requests.get(url)
        ds = rr.json()
        self.store(url, ds)
        return ds
    

def scrape_roles(cacher, server=None):

    roles = []

    #baseurl = 'https://galaxy.ansible.com'
    baseurl = server
    next_page = f'{baseurl}/api/v1/roles/'
    while next_page:
        logger.info(next_page)
        ds = cacher.get(next_page)

        for role in ds['results']:
            roles.append(role)

        if not ds.get('next') and not ds.get('next_link'):
            break

        if ds.get('next_link'):
            next_page = baseurl + ds['next_link']
            continue

        next_page = ds['next']
        if baseurl.startswith('https://') and next_page.startswith('http://'):
            next_page = next_page.replace('http://', 'https://', 1)
        if not next_page.startswith(baseurl):
            next_page = baseurl + next_page

    return roles


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--upstream',
        default='https://old-galaxy.ansible.com',
        help='the old server'
    )    
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--dest', required=True, help="data file to write")

    args = parser.parse_args()

    cacher = Cacher(refresh=args.refresh)

    # get all roles from old
    old = scrape_roles(cacher, server=args.upstream)

    with open(args.dest, 'w') as f:
        f.write(json.dumps(old, indent=2))

    #import epdb; epdb.st()