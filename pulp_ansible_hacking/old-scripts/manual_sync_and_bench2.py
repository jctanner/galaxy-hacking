#!/usr/bin/env python

import datetime
import os
import subprocess
import time

import requests
import requests_cache

from logzero import logger


HOST = 'http://localhost:5001'
USERNAME = 'admin'
PASSWORD = 'password'
#UPSTREAM_BASEURL = 'https://beta-galaxy.ansible.com'
UPSTREAM_BASEURL = 'http://192.168.1.20:8080'
#CACHEDIR = '/vagrant/artifacts'
CACHEDIR = 'artifacts'
CACHED_SESSION = requests_cache.CachedSession(os.path.expanduser('~/upstream_cache'))

UPLOADED = None


def fix_url(url):
    url = url.replace('http://192.168.1.20:8080http://172.18.0.3', 'http://192.168.1.20:8080')
    url = url.replace('http://172.18.0.3', 'http://192.168.1.20:8080')
    return url


def get_upstream_url(url, usecache=True):

    '''
    if usecache:
        session = CACHED_SESSION
    else:
        session = requests.Session()
    '''

    url = fix_url(url)
    session = requests.Session()
    rr = session.get(url)
    return rr


def iterate_upstream_collections(url):

    url = fix_url(url)
    next_url = url
    while next_url:
        logger.info(next_url)
        rr = get_upstream_url(next_url)
        ds = rr.json()

        if 'results' in ds:
            for res in ds['results']:
                yield res
        else:
            for res in ds['data']:
                yield res

        import epdb; epdb.st()
        if ds['links']['next'] is None:
            break
        next_url = UPSTREAM_BASEURL + ds['links']['next']


def iterate_upstream_collection_versions(url):

    url = fix_url(url)
    next_url = url
    while next_url:
        logger.info(next_url)
        rr = get_upstream_url(next_url)
        ds = rr.json()

        if 'results' in ds:
            for res in ds['results']:
                yield res

        else:
            for res in ds['data']:

                cv_url = UPSTREAM_BASEURL + res['href']
                logger.info(cv_url)
                cv_rr = get_upstream_url(cv_url)
                yield cv_rr.json()

        import epdb; epdb.st()
        if ds['links']['next'] is None:
            break
        next_url = UPSTREAM_BASEURL + ds['links']['next']


def download(url, dest):
    cmd = f'curl -L -o {dest} {url}'
    pid = subprocess.run(cmd, shell=True)


def get_or_create_repo(name):
    next_url = HOST + '/pulp/api/v3/repositories/ansible/ansible/'

    rmap = {}

    while next_url:
        rr = requests.get(next_url, auth=(USERNAME, PASSWORD))
        ds = rr.json()
        for res in ds['results']:
            rmap[res['name']] = res
        if ds['next'] is None:
            break
        print('have a next url ...')
        import epdb; epdb.st()

    if name in rmap:
        return rmap[name]

    url = HOST + '/pulp/api/v3/repositories/ansible/ansible/'
    payload = {'name': name}
    rr = requests.post(url, json=payload, auth=(USERNAME, PASSWORD))
    return rr.json()


def get_or_create_dist(name, base_path, repository_data):

    next_url = HOST + '/pulp/api/v3/distributions/ansible/ansible/'

    dmap = {}

    while next_url:
        rr = requests.get(next_url, auth=(USERNAME, PASSWORD))
        ds = rr.json()
        for res in ds['results']:
            dmap[res['name']] = res
        if ds['next'] is None:
            break
        print('have a next url ...')
        import epdb; epdb.st()

    if name in dmap:
        return dmap[name]

    url = HOST + '/pulp/api/v3/distributions/ansible/ansible/'
    payload = {
        'base_path': base_path,
        'name': name,
        'repository': repository_data['pulp_href']
    }
    rr = requests.post(url, json=payload, auth=(USERNAME, PASSWORD))
    task = rr.json()
    task_url = HOST + task['task']
    while True:
        trr = requests.get(task_url, auth=(USERNAME, PASSWORD))
        tresp = trr.json()
        if tresp['state'] == 'completed':
            break

    return get_or_create_dist(name, base_path, repository_data)


def write_stat(url, duration, col_count, cv_count):
    fn = os.path.expanduser('~/benchmark.log')
    ts = datetime.datetime.now().isoformat()
    with open(fn, 'a') as f:
        f.write(f'{ts},{col_count},{cv_count},{duration},{url}\n')


def upload_and_benchmark(cv, artifact, namespace=None, name=None, version=None):

    global UPLOADED

    def count_cols(base_path):
        url = HOST + f'/pulp_ansible/galaxy/{base_path}/api/v3/plugin/ansible/content/{base_path}/collections/index/'
        logger.info(url)
        t1 = datetime.datetime.now()
        rr = requests.get(url, auth=(USERNAME, PASSWORD))
        t2 = datetime.datetime.now()
        ds = rr.json()
        delta = (t2 - t1)
        write_stat("REPO_CONTENT", delta.total_seconds(), ds['meta']['count'], None)
        return ds['meta']['count']

    def get_cvs(base_path, detail=True, limit=None, bench=True):
        next_url = HOST + f'/pulp_ansible/galaxy/{base_path}/api/v3/plugin/ansible/content/{base_path}/collections/index/'

        cvs = []
        while next_url:
            logger.info(next_url)
            rr = requests.get(next_url, auth=(USERNAME, PASSWORD))
            ds = rr.json()

            for col in ds['data']:
                nextv_url = HOST + col['versions_url']
                while nextv_url:
                    logger.info(nextv_url)
                    vrr = requests.get(nextv_url, auth=(USERNAME, PASSWORD))
                    vds = vrr.json()
                    for cversion_summary in vds['data']:
                        cvs.append((col['namespace'], col['name'], cversion_summary['version']))
                        if not detail:
                            continue

                        t1 = datetime.datetime.now()
                        cvdrr = requests.get(HOST + cversion_summary['href'], auth=(USERNAME, PASSWORD))
                        t2 = datetime.datetime.now()
                        delta = (t2 - t1)
                        if bench:
                            write_stat("CV_DETAIL", delta.total_seconds(), ds['meta']['count'], None)

                        if limit and len(cvs) >= limit:
                            return cvs

                    if vds['links']['next'] is None:
                        break
                    nextv_url = HOST + vds['links']['next']

            if ds['links']['next'] is None:
                break
            next_url = HOST + ds['links']['next']

        return cvs

    base_path = "community"
    repo = get_or_create_repo("community")
    dist = get_or_create_dist("community", base_path, repo)

    if UPLOADED is None:
        UPLOADED = {}
        cvs = get_cvs(base_path, bench=False, detail=False)
        for cv in cvs:
            UPLOADED[cv] = None

    key = (namespace, name, version)
    if key in UPLOADED:
        return

    current_cvs = get_cvs(base_path, limit=1)
    current_count = count_cols(base_path)

    url = HOST + f'/pulp_ansible/galaxy/{base_path}/api/v3/artifacts/collections/'
    rr = requests.post(
        url,
        json={'file': os.path.basename(artifact)},
        files={'file': open(artifact, 'rb')},
        auth=(USERNAME, PASSWORD)
    )

    if rr.status_code == 400:
        return

    try:
        task = rr.json()
    except Exception as e:
        if 'Entity Too Large' in rr.text:
            return
        import epdb; epdb.st()
    task_url = HOST + task['task']

    tds = None
    while True:
        trr = requests.get(task_url, auth=(USERNAME, PASSWORD))
        tds = trr.json()
        logger.info(tds)
        if tds['state'] in ['completed', 'failed']:
            break
        time.sleep(1)

    t1 = tds['started_at']
    t1 = datetime.datetime.strptime(t1, '%Y-%m-%dT%H:%M:%S.%fZ')
    t2 = tds['finished_at']
    t2 = datetime.datetime.strptime(t2, '%Y-%m-%dT%H:%M:%S.%fZ')
    upload_delta = (t2 - t1)

    write_stat("UPLOAD", upload_delta.total_seconds(), current_count, None)

    next_url = (
        HOST
        + '/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/'
        + f'?distribution_base_path={base_path}'
    )

    found = []
    while next_url:
        nt1 = datetime.datetime.now()
        nrr = requests.get(next_url, auth=(USERNAME, PASSWORD))
        nt2 = datetime.datetime.now()
        nds = nrr.json()
        ndelta = (nt2 - nt1)

        count = nds['meta']['count']
        write_stat("X-REPO-SEARCH", ndelta.total_seconds(), None, count)

        for cv in nds['data']:
            found.append(cv)

        if not nds['links']['next']:
            break
        next_url = HOST + nds['links']['next']

    # import epdb; epdb.st()



def main():

    if not os.path.exists(CACHEDIR):
        os.makedirs(CACHEDIR)

    col_count = 0
    cv_count = 0

    for col in iterate_upstream_collections(UPSTREAM_BASEURL + '/api/v2/collections/'):
        col_count += 1

        v_url = UPSTREAM_BASEURL + col['versions_url']
        for cv in iterate_upstream_collection_versions(v_url):
            cv_count += 1

            print('-' * 50)
            print(f'COLS:{col_count} CVS:{cv_count}')
            print('-' * 50)

            dl_url = cv['download_url']
            afn = os.path.basename(dl_url)
            dst = os.path.join(CACHEDIR, afn)
            if not os.path.exists(dst):
                download(dl_url, dst)

            upload_and_benchmark(cv, dst, namespace=col['namespace'], name=col['name'], version=cv['version'])


if __name__ == "__main__":
    main()
