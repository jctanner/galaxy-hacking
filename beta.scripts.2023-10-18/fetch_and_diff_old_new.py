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


GITHUB_USERNAME_REGEXP = re.compile(r"^[a-zA-Z\d](?:[a-zA-Z\d]|-(?=[a-zA-Z\d])){0,38}$")
LEGACY_ROLE_NAME_REGEXP = re.compile("^[a-zA-Z0-9_-]{1,55}$")
LEGACY_NAMESPACE_REGEXP = re.compile("^([a-zA-Z0-9.]+[-_]?)+$")


def get_nested_value(d, key_string):
    keys = key_string.split('.')
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
        else:
            raise KeyError(f"Key {key} not found or not a dictionary.")
    return d


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


class Score:

    _fixes = None
    _score = None

    def __init__(self, role_data, upstream_data):
        self.role_data = role_data
        self.upstream_data = upstream_data

        self.fixes = {}
        self._score = 100
        self.process()

    @property
    def fqn(self):
        ns = self.role_data['summary_fields']['namespace']['name']
        name = self.role_data['name']
        return ns + '.' + name

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f'{self.role_data["id"]} {self.fqn} {self.score}%'

    def __gt__(self, other):
        return self.score > other.score

    def __lt__(self, other):
        return self.score < other.score

    @property
    def score(self):
        return self._score

    def process(self):

        weight = 10
        to_inspect = [
            ['summary_fields.namespace.name', weight * 2],
            'summary_fields.repository.name',
            'summary_fields.repository.original_name',
            'name',
            'github_user',
            'github_repo',
            'github_branch',
        ]
 
        for key in to_inspect:

            this_key = key
            this_weight = weight
            if isinstance(key, list):
                this_key = key[0]
                this_weight = key[1]
                #import epdb; epdb.st()

            upstream_val = get_nested_value(self.upstream_data, this_key)
            downstream_val = get_nested_value(self.role_data, this_key)
            if downstream_val != upstream_val:
                self._score -= this_weight
                self.fixes[this_key] = [downstream_val, upstream_val]


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


def get_missing_tags(sorted_scores):

    # merge all tags from all dupes
    all_tags = set()        
    for score in sorted_scores:
        score_tags = [x['name'] for x in score.role_data['summary_fields']['versions']]
        for st in score_tags:
            all_tags.add(st)
    
    # check if the best score is missing any ...
    missing_tags = []
    if all_tags:
        best_tags = [
            x['name'] for x in 
            sorted_scores[0].role_data['summary_fields']['versions']
        ]
        do_import = False
        for tag in all_tags:
            if tag not in best_tags:
                missing_tags.append(tag)

    return missing_tags



def compare_and_fix(
    old_roles,
    new_roles,
    write=False,
    token=None,
    downstream=None,
    limit=None
):

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

    total_changed = 0
    uidkeys = sorted(list(new_by_uid.keys()))
    for _id,uid in enumerate(uidkeys):

        if uid not in old_by_id:
            continue

        role_ids = new_by_uid[uid]

        if len(role_ids) < 2:
            continue

        upstream = old_by_id[uid]
        roles = [new_by_id[x] for x in role_ids]

        ns_name = upstream['summary_fields']['namespace']['name']
        name = upstream['name']
        fqn = ns_name + '.' + name

        logger.info(f'{_id}. {uid} - {fqn}')

        # score each role against the upstream data
        scores = [Score(x, upstream) for x in roles]
        scores = sorted(scores, reverse=True)

        # we can't edit fields yet ...
        if scores[0].score != 100:
            logger.warning(f'\tSKIPPING due to best score < 100 ... {scores[0].score}')
            continue

        logger.info('-'  * 50)
        logger.info(total_changed)
        logger.info('-'  * 50)

        # show the user which one was best
        logger.info(f'\tKEEP {scores[0]}')
        for k,v in scores[0].fixes.items():
            logger.info(f'\t\t{k} {v[0]} -> {v[1]}')

        # delete all the others (usually just 1)
        for x in scores[1:]:
            logger.info(f'\tDELETE {x}')
            for k,v in x.fixes.items():
                logger.info(f'\t\t{k} {v[0]} -> {v[1]}')
            if write and token:
                drr = delete_role(downstream, x.role_data['id'], token)
                logger.info(f'\t\t{drr.status_code}')

        missing_tags = get_missing_tags(scores)
        if missing_tags:
            # do a re-import ...
            logger.warning(
                f'\treimporting {fqn} to recover missing tags {missing_tags}'
            )
            github_user = scores[0].role_data['github_user']
            github_repo = scores[0].role_data['github_repo']
            role_name = scores[0].role_data['name']
            cmd = (
                f'ansible-galaxy role import'
                + f' -s {downstream}'
                + f' --token={token}'
                + f' --role-name={role_name}'
                + f' {github_user} {github_repo}'
            )
            logger.info(f'\t{cmd}')
            if write and token:
                subprocess.run(cmd, shell=True)
            import epdb; epdb.st()
        
        total_changed += 1
        if limit and total_changed >= limit:
            break


def delete_role(baseurl, role_id, token):
    url = f'{baseurl}/api/v1/roles/{role_id}/'
    logger.info(f'\t\tDELETE {url}')
    rr = requests.delete(
        url,
        headers={'Authorization': f'token {token}'}
    )
    # import epdb; epdb.st()
    return rr

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--upstream',
        default='https://old-galaxy.ansible.com',
        help='the old server'
    )    
    parser.add_argument(
        '--downstream',
        default='https://galaxy.ansible.com',
        help='the beta server'
    )
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--clean-downstream-cache', action='store_true')
    parser.add_argument('--write', action='store_true', help='commit changes')
    parser.add_argument('--token', default=os.environ.get('GALAXY_DOWNSTREAM_TOKEN'))
    parser.add_argument('--limit', type=int)

    args = parser.parse_args()

    if args.write and not args.token:
        raise Exception('A token must be provided to make changes.')

    if os.path.exists('role_fixes.log'):
        os.remove('role_fixes.log')
    logzero.logfile("role_fixes.log")

    # make cache
    cacher = Cacher(refresh=args.refresh)
    if args.clean_downstream_cache:
        cacher.clean(baseurl=args.downstream)

    # get all roles from old
    old = scrape_roles(cacher, server=args.upstream)

    # get all roles from new
    new = scrape_roles(cacher, server=args.downstream)

    compare_and_fix(
        old,
        new,
        write=args.write,
        token=args.token,
        downstream=args.downstream,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
