#!/usr/bin/env python

import argparse
import datetime
import os
import time
import requests
import requests_cache

from logzero import logger

HOST = 'http://localhost:5001'
USERNAME = 'admin'
PASSWORD = 'password'
UPSTREAM_BASEURL = 'https://beta-galaxy.ansible.com'
CACHED_SESSION = requests_cache.CachedSession(os.path.expanduser('.upstream_cache'))


def get_upstream_url(url, usecache=True):

    if usecache:
        session = CACHED_SESSION
    else:
        session = requests.Session()

    rr = session.get(url)
    return rr


def iterate_upstream_collections(url):

    next_url = url
    while next_url:
        logger.info(next_url)
        rr = get_upstream_url(next_url)
        ds = rr.json()

        for res in ds['data']:
            yield res

        if ds['links']['next'] is None:
            break
        next_url = UPSTREAM_BASEURL + ds['links']['next']


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


def get_or_create_remote(name, remote_url, requirements):

    next_url = HOST + '/pulp/api/v3/remotes/ansible/collection/'

    rmap = {}

    while next_url:
        rr = requests.get(next_url, auth=(USERNAME, PASSWORD))
        ds = rr.json()
        for res in ds['results']:
            rmap[res['name']] = res
        if ds['next'] is None:
            break
        print('has next url')
        import epdb; epdb.st()

    if name in rmap:
        needs_change = False
        if rmap[name]['url'] != remote_url or rmap[name]['requirements_file'].strip() != requirements.strip():
            needs_change = True
        if not needs_change:
            return rmap[name]

        url = HOST + rmap[name]['pulp_href']
        body = {
            'name': name,
            'rate_limit': 5,
            'requirements_file': requirements,
            'sync_dependencies': False,
            'url': remote_url,
        }
        rr = requests.patch(url, json=body, auth=(USERNAME, PASSWORD))
        task = rr.json()
        task_url = HOST + task['task']
        while True:
            trr = requests.get(task_url, auth=(USERNAME, PASSWORD))
            tresp = trr.json()
            # import epdb; epdb.st()
            if tresp['state'] == 'completed':
                break

        return get_or_create_remote(name, remote_url, requirements)

    else:
        url = HOST + '/pulp/api/v3/remotes/ansible/collection/'
        body = {
            'name': name,
            'rate_limit': 1,
            'requirements_file': requirements,
            'sync_dependencies': False,
            'url': remote_url,
        }
        rr = requests.post(url, body, auth=(USERNAME, PASSWORD))
        ds = rr.json()
        return ds


def get_cv_count_from_db():
    container = 'oci_env_pulp_1'
    cmd = f"docker exec -it {container} psql -U pulp -c 'select count(*) from ansible_collectionversion;'"
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    stdout = pid.stdout.decode('utf-8')


def get_cvs(base_path, detail=True, limit=None, bench=True):

    cvs = []
    colnames = []

    cv_count = get_cv_count_from_db()
    import epdb; epdb.st()

    next_url = HOST + f'/pulp_ansible/galaxy/{base_path}/api/v3/plugin/ansible/content/{base_path}/collections/index/'
    while next_url:
        logger.info(next_url)
        rr = requests.get(next_url, auth=(USERNAME, PASSWORD))
        ds = rr.json()

        for col in ds['data']:

            colname = [col['namespace'], col['name']]
            if colname in colnames:
                continue

            colnames.append(colname)

            nextv_url = HOST + col['versions_url']
            while nextv_url:
                logger.info(nextv_url)

                t1 = datetime.datetime.now()
                vrr = requests.get(nextv_url, auth=(USERNAME, PASSWORD))
                t2 = datetime.datetime.now()
                vds = vrr.json()
                delta = (t2 - t1)
                if bench:
                     write_stat("CV_DETAIL", delta.total_seconds(), vds['meta']['count'], None)

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

            with open(fn, 'w') as f:
                f.write(json.dumps(colnames))

        if ds['links']['next'] is None:
            break
        next_url = HOST + ds['links']['next']

    write_stat("CV_COUNT", None, None, len(cvs))

    return cvs


def run_sync(repo, remote, colcount=None, cvcount=None):
    t1 = datetime.datetime.now()
    sync_url = HOST + repo['pulp_href'] + 'sync/'
    payload = {
        'mirror': False,
        'optimize': True,
        'remote': remote['pulp_href']
    }
    rr = requests.post(sync_url, json=payload, auth=(USERNAME, PASSWORD))
    task = rr.json()
    task_url = HOST + task['task']
    ds = None
    while True:
        trr = requests.get(task_url, auth=(USERNAME, PASSWORD))
        ds = trr.json()
        t2 = datetime.datetime.now()
        delta = (t2 - t1)
        logger.info(ds['state'] + " " + str(delta.total_seconds()))
        if ds['state'] in ['completed', 'failed']:
            break
        time.sleep(2)

    t1 = ds['started_at']
    t1 = datetime.datetime.strptime(t1, '%Y-%m-%dT%H:%M:%S.%fZ')
    t2 = ds['finished_at']
    t2 = datetime.datetime.strptime(t2, '%Y-%m-%dT%H:%M:%S.%fZ')
    delta = (t2 - t1).total_seconds()

    # import epdb; epdb.st()
    write_stat('SYNC', delta, colcount, cvcount)

    return ds


def record_synced_collection(fqn):
    with open('sync_collections.log', 'a') as f:
        f.write(fqn + '\n')


def get_synced_collections():
    if not os.path.exists('sync_collections.log'):
        return []
    with open('sync_collections.log', 'r') as f:
        fdata = f.read()
    cols = fdata.split('\n')
    cols = [x.strip() for x in cols if x.strip()]
    cols = sorted(set(cols))
    return cols


def write_stat(url, duration, col_count, cv_count):
    fn = os.path.expanduser('benchmark.log')
    ts = datetime.datetime.now().isoformat()
    with open(fn, 'a') as f:
        f.write(f'{ts},{col_count},{cv_count},{duration},{url}\n')


def main():

    parser = argparse.ArgumentParser()
    import epdb; epdb.st()

    base_path = "community"

    # make a community repo
    logger.info('get repo')
    repo = get_or_create_repo('community')

    # make the community dist
    logger.info('get dist')
    dist = get_or_create_dist("community", "community", repo)

    already_synced = get_synced_collections()

    batch = []
    col_count = 0
    cv_count = 0
    for col in iterate_upstream_collections(UPSTREAM_BASEURL + '/api/v3/collections/'):

        col_count += 1
        col_fqn = f"{col['namespace']}.{col['name']}"

        if col_fqn in already_synced:
            continue

        logger.info('-' * 50)
        logger.info(str(col_count) + " " + col_fqn)
        logger.info('-' * 50)

        batch.append(col_fqn)

        if len(batch) >= 10:

            logger.info(f'BATCH: {batch}')

            spec = '\n - ' + '\n - '.join(batch)

            # make the remote
            logger.info('get remote')
            remote = get_or_create_remote(
                "community",
                'https://beta-galaxy.ansible.com/',
                #'collections:\n  - testing.k8s_demo_collection'
                #'collections:\n  - geerlingguy.mac'
                #'collections: []\n'
                #f'collections:\n  - {col_fqn}'
                f'collections:' + spec
            )

            # start sync
            logger.info('start sync')
            res = run_sync(repo, remote, colcount=col_count, cvcount=cv_count)
            if res['state'] != 'completed':
                import epdb; epdb.st()

            # cache
            for bfqn in batch:
                record_synced_collection(bfqn)

            # reset batch
            batch = []

            # baseline
            cvs = get_cvs(base_path, detail=True, limit=None, bench=True)
            cv_count = len(cvs)

            '''
            # x-repo
            next_url = (
                HOST
                + '/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/'
                + f'?distribution_base_path={base_path}'
            )
            while next_url:
                nt1 = datetime.datetime.now()
                nrr = requests.get(next_url, auth=(USERNAME, PASSWORD))
                nt2 = datetime.datetime.now()
                nds = nrr.json()
                ndelta = (nt2 - nt1)

                count = nds['meta']['count']
                write_stat("X-REPO-SEARCH", ndelta.total_seconds(), col_count, count)

                if not nds['links']['next']:
                    break
                next_url = HOST + nds['links']['next']
            '''


if __name__ == "__main__":
    main()
