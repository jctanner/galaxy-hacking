#!/usr/bin/env python

import os
import uuid
import argparse

import json
import glob
import requests

from urllib.parse import urlparse, parse_qs
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

    def get(self, url):

        if url in self.cmap:
            with open(self.cmap[url], 'r') as f:
                ds = json.loads(f.read())
            return ds['data']

        logger.info(f'fetch {url}')
        rr = requests.get(url)
        ds = rr.json()
        self.store(url, ds)
        return ds


class Score:

    _fixes = None
    _score = None

    def __init__(self, role_data, upstream_data):
        self.role_data = role_data
        self.upstream_data = upstream_data

        self.fixes = {}
        self._score = 0
        self.process()

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f'{self.role_data["id"]} {self.score}%'

    def __gt__(self, other):
        return self.score > other.score

    def __lt__(self, other):
        return self.score < other.score

    @property
    def score(self):
        return self._score

    def process(self):
        # namespace.name ...
        if self.role_data['summary_fields']['namespace']['name'] == self.upstream_data['summary_fields']['namespace']['name']:
            self._score += 10
        else:
            self.fixes['namespace.name'] = self.upstream_data['summary_fields']['namespace']['name']

        # name
        if self.role_data['name'] == self.upstream_data['name']:
            self._score += 10
        else:
            self.fixes['name'] = self.upstream_data['name']

        # github_user
        if self.role_data['github_user'] == self.upstream_data['github_user']:
            self._score += 10
        else:
            self.fixes['github_user'] = self.upstream_data['github_user']

        # github_repo
        if self.role_data['github_repo'] == self.upstream_data['github_repo']:
            self._score += 10
        else:
            self.fixes['github_repo'] = self.upstream_data['github_repo']

        # github_branch
        if self.role_data['github_branch'] == self.upstream_data['github_branch']:
            self._score += 10
        else:
            self.fixes['github_branch'] = self.upstream_data['github_branch']

        # repository name/original_name
        if self.role_data['summary_fields']['repository']['name'] == \
                self.upstream_data['summary_fields']['repository']['name']:
            self._score += 10
        else:
            self.fixes['repository.name'] = self.upstream_data['summary_fields']['repository']['name']
        if self.role_data['summary_fields']['repository']['original_name'] == \
                self.upstream_data['summary_fields']['repository']['original_name']:
            self._score += 10
        else:
            self.fixes['repository.original_name'] = self.upstream_data['summary_fields']['repository']['original_name']

        # versions ...
        #import epdb; epdb.st()



def scrape_old_roles(cacher):

    roles = []

    baseurl = 'https://old-galaxy.ansible.com'
    next_page = f'{baseurl}/api/v1/roles/'
    while next_page:
        logger.info(next_page)
        #rr = requests.get(next_page)
        ds = cacher.get(next_page)

        for role in ds['results']:
            roles.append(role)

        if not ds.get('next_link'):
            break
        next_page = baseurl + ds['next_link']

    return roles


def scrape_new_roles(cacher, server=None):

    roles = []

    #baseurl = 'https://galaxy.ansible.com'
    baseurl = server
    next_page = f'{baseurl}/api/v1/roles/'
    while next_page:
        logger.info(next_page)
        ds = cacher.get(next_page)

        for role in ds['results']:
            roles.append(role)

        if not ds.get('next'):
            break
        next_page = ds['next']

    return roles


def compare(old_roles, new_roles):

    old_by_id = dict((x['id'], x) for x in old_roles)
    new_by_id = dict((x['id'], x) for x in new_roles)

    new_by_uid = {}
    for x in new_roles:
        uid = x.get('upstream_id')
        if not uid:
            continue
        if uid not in new_by_uid:
            new_by_uid[uid] = []
        new_by_uid[uid].append(x['id'])

    to_ignore = set()
    to_fix = set()
    to_delete = set()

    for uid, role_ids in new_by_uid.items():

        if uid not in old_by_id:
            continue

        upstream = old_by_id[uid]
        roles = [new_by_id[x] for x in role_ids]

        scores = [Score(x, upstream) for x in roles]
        scores = sorted(scores, reverse=True)

        if scores[0].fixes:
            to_fix.add(scores[0])
        else:
            to_ignore.add(scores[0])

        for x in scores[1:]:
            to_delete.add(x)

    fixes = {}
    for tf in to_fix:
        for k,v in tf.fixes.items():
            if k not in fixes:
                fixes[k] = 0
            fixes[k] += 1

    ds = {
        'delete_role_ids': [x.role_data['id'] for x in to_delete],
    }
    for tf in to_fix:
        for k,v in tf.fixes.items():

            if k not in ds:
                ds[k] = []

            ds[k].append([tf.role_data['id'], v])


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--downstream',
        default='https://galaxy.ansible.com',
        help='the beta server'
    )
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--clean-downstream-cache', action='store_true')
    args = parser.parse_args()

    # make cache
    cacher = Cacher(refresh=args.refresh)
    if args.clean_downstream_cache:
        cacher.clean(baseurl=args.downstream)

    # get all roles from old
    old = scrape_old_roles(cacher)

    # get all roles from new
    new = scrape_new_roles(cacher, server=args.downstream)

    compare(old, new)
    #import epdb; epdb.st()


if __name__ == "__main__":
    main()
