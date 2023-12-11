#!/usr/bin/env python

import json
import gzip
import logging
import os
import random
import re
import string
import time

import requests
# import requests_cache
# from logzero import logger
from pprint import pprint


logger = logging.getLogger(__name__)


# https://github.com/ansible/galaxy-importer/blob/master/galaxy_importer/constants.py#L45
NAME_REGEXP = re.compile(r"^(?!.*__)[a-z]+[0-9a-z_]*$")

#UPSTREAM = os.environ.get("GALAXY_UPSTREAM_BASEURL", "https://galaxy.ansible.com")
UPSTREAM = os.environ.get("GALAXY_UPSTREAM_BASEURL", "http://192.168.1.20:8000")
DOWNSTREAM = os.environ.get("GALAXY_DOWNSTREAM_BASEURL", "http://localhost:5001")
DOWNSTREAM_USER = os.environ.get("HUB_USERNAME", 'admin')
DOWNSTREAM_PASS = os.environ.get("HUB_PASSWWORD", 'admin')
DOWNSTREAM_TOKEN = os.environ.get('HUB_TOKEN')
#SESSION = requests_cache.CachedSession('demo_cache')
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", None)


prefix = "gh_"
no_start = tuple(x for x in "0123456789_")


# LOAD THE CACHE
with gzip.open('github_users.json.gz', 'rt') as gzipped_file:
    CACHE = json.load(gzipped_file)
IDS = list(CACHE['by_id'].keys())
for ID in IDS:
    newid = int(ID)
    CACHE['by_id'][newid] = CACHE['by_id'][ID]
    CACHE['by_id'].pop(ID)


def store_github_user_lookup_result(ds, userid=None, login=None):
    cachedir_id = '.cache/github_users/by_id'
    cachedir_name = '.cache/github_users/by_name'
    if not os.path.exists(cachedir_id):
        os.makedirs(cachedir_id)
    if not os.path.exists(cachedir_name):
        os.makedirs(cachedir_name)

    fn = None
    if ds.get('id'):
        fn = os.path.join(cachedir_id, str(ds['id']) + '.json')
    elif userid:
        fn = os.path.join(cachedir_id, str(userid) + '.json')
    if fn:
        with open(fn, 'w') as f:
            f.write(json.dumps(ds))

    if ds.get('login'):
        usernames = [ds['login']]
    else:
        usernames = []
    if login:
        usernames.append(login)
        usernames = sorted(set(usernames))
    for username in usernames:

        safe_name = username.replace('/', '__SLASH__')

        fn = os.path.join(cachedir_name, safe_name + '.json')
        with open(fn, 'w') as f:
            f.write(json.dumps(ds))


def fetch_userdata_by_id(userid):

    if userid is None:
        return None

    cachedir = '.cache/github_users/by_id'
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)

    cfile_id = os.path.join(cachedir, str(userid) + '.json')
    if os.path.exists(cfile_id):
        with open(cfile_id, 'r') as f:
            ds = json.loads(f.read())
        if ds.get('message') == 'Bad credentials':
            os.remove(cfile_id)
        else:
            return ds

    # https://api.github.com/user/3591551
    url = f'https://api.github.com/user/{userid}'
    logger.info(url)
    while True:
        try:
            if GITHUB_TOKEN:
                rr = requests.get(url, headers={'Authorization': f'Bearer {GITHUB_TOKEN}'})
                break
            else:
                rr = requests.get(url)
                break
        except requests.exceptions.ConnectTimeout as e:
            logger.exception(e)
            time.sleep(10)

    ds = rr.json()

    if ds.get('message') == 'Bad credentials':
        import epdb; epdb.st()

    if ds.get('message') == 'Not Found':
        logger.info(f'\t{rr.status_code}')
        store_github_user_lookup_result(ds, userid=userid)
        return None

    if 'rate limit exceeded' in ds.get('message', ''):
        #import epdb; epdb.st()
        #raise Exception('RATE LIMITED')
        wait_for_rate_limit(dict(rr.headers))
        return fetch_userdata_by_id(userid)

    store_github_user_lookup_result(ds, userid=userid)

    return ds


def fetch_userdata_by_name(username):

    if username is None:
        return None

    cachedir = '.cache/github_users/by_name'
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)

    cfile_login = os.path.join(cachedir, username + '.json')
    if os.path.exists(cfile_login):
        with open(cfile_login, 'r') as f:
            return json.loads(f.read())

    # https://api.github.com/user/3591551
    url = f'https://api.github.com/users/{username}'
    #logger.info(url)

    '''
    if GITHUB_TOKEN:
        rr = requests.get(url, headers={'Authorization': f'Bearer {GITHUB_TOKEN}'})
    else:
        rr = requests.get(url)
    '''

    while True:
        # logger.info(url)
        print(f'\t{url}')
        try:
            if GITHUB_TOKEN:
                rr = requests.get(url, headers={'Authorization': f'Bearer {GITHUB_TOKEN}'})
                break
            else:
                rr = requests.get(url)
                break
        except requests.exceptions.ConnectTimeout as e:
            logger.exception(e)
            time.sleep(10)

    ds = rr.json()
    #if username == 'gsemet':
    #    import epdb; epdb.st()
    if ds.get('message') == 'Not Found':
        logger.info(f'\t{rr.status_code}')
        store_github_user_lookup_result(ds, login=username)
        #import epdb; epdb.st()
        return None
    if 'rate limit exceeded' in ds.get('message', ''):
        #import epdb; epdb.st()
        #raise Exception('RATE LIMITED')
        wait_for_rate_limit(dict(rr.headers))
        return fetch_userdata_by_name(username)

    if 'Bad credentials' in ds.get('message', ''):
        raise Exception('bad github token')

    if 'id' not in ds:
        import epdb; epdb.st()
        return None

    store_github_user_lookup_result(ds, login=username)

    return ds


def wait_for_rate_limit(headers):
    # 'X-RateLimit-Reset': '1693425833',
    reset = headers.get('X-RateLimit-Reset')
    reset = int(reset)
    current_time = time.time()
    delta = reset - current_time

    logger.info(f'waiting ~{delta/60}m for rate limit')
    minutes = int((delta / 60)) + 2
    for x in range(0, minutes):
        logger.info(f'waiting {minutes - x} more minutes for rate limit')
        time.sleep(60)

    #import epdb; epdb.st()
