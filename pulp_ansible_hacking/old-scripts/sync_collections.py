#!/usr/bin/env python

import argparse
import datetime
import json
import os
import time
import requests
import requests_cache
import subprocess

from threading import Thread
from logzero import logger

'''
HOST = 'http://localhost:5001'
USERNAME = 'admin'
PASSWORD = 'password'
UPSTREAM_BASEURL = 'https://beta-galaxy.ansible.com'
CACHED_SESSION = requests_cache.CachedSession(os.path.expanduser('.upstream_cache'))
'''


def pscollector():
    colnames = ['USER', 'PID', '%CPU', '%MEM','VSZ', 'RSS', 'TTY', 'STAT', 'START', 'TIME', 'COMMAND']
    container = 'oci_env_pulp_1'
    fn = 'benchmark_stats.log'
    while True:
        with open(fn, 'a') as f:
            cmd = f"docker exec -e COLUMNS=200 -it {container} /bin/bash -c 'ps -auxe'"
            ts = datetime.datetime.now().isoformat()
            pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
            stdout = pid.stdout.decode('utf-8')
            for line in stdout.split('\n'):
                line = line.strip()
                if not line:
                    continue
                cols = line.split(None, len(colnames) - 1)
                if cols[-1].startswith('ps '):
                    continue
                if cols[0] == 'USER':
                    continue

                ds = {}
                for idx,x in enumerate(colnames):
                    ds[x] = cols[idx]

                f.write(f"{ts},PS_STATS,{json.dumps(ds)}\n")

            ts = datetime.datetime.now().isoformat()
            pid = subprocess.run(
                'docker stats --no-stream --format=json --no-trunc', shell=True, stdout=subprocess.PIPE
            )
            cstats = pid.stdout.decode('utf-8')
            cstats = json.loads(cstats)
            f.write(f'{ts},DOCKER_STATS,{json.dumps(cstats)}\n')

        time.sleep(5)


class BenchMarker:

    api_container = 'oci_env_pulp_1'
    db_container = 'oci_env_pulp_1'
    sync_collections_log = 'sync_collections.log'
    benchmark_log = 'benchmark.log'

    def __init__(self):
        self.HOST = 'http://localhost:5001'
        self.USERNAME = 'admin'
        self.PASSWORD = 'password'
        self.UPSTREAM_BASEURL = 'https://beta-galaxy.ansible.com'
        self.CACHED_SESSION = requests_cache.CachedSession(os.path.expanduser('.upstream_cache'))

        self.base_path = 'community'
        self.repo_name = 'community'
        self.dist_name = 'community'
        self.repo = self.get_or_create_repo(self.repo_name)
        self.dist = self.get_or_create_dist(self.dist_name, self.base_path, self.repo)

        self.pscollector_thread = Thread(target=pscollector, daemon=True, name='pscollector')
        self.pscollector_thread.start()

        import epdb; epdb.st()

    def __del__(self):
        self.pscollector_thread.stop()

    def reset(self):
        import epdb; epdb.st()

    @property
    def auth(self):
        return (self.USERNAME, self.PASSWORD)

    def get_upstream_url(self, url, usecache=True):

        if usecache:
            session = self.CACHED_SESSION
        else:
            session = requests.Session()

        rr = session.get(url)
        return rr

    def iterate_upstream_collections(self, url):

        next_url = url
        while next_url:
            logger.info(next_url)
            rr = self.get_upstream_url(next_url)
            ds = rr.json()

            for res in ds['data']:
                yield res

            if ds['links']['next'] is None:
                break
            next_url = self.UPSTREAM_BASEURL + ds['links']['next']

    def get_or_create_repo(self, name):
        next_url = self.HOST + '/pulp/api/v3/repositories/ansible/ansible/'

        rmap = {}

        while next_url:
            rr = requests.get(next_url, auth=self.auth)
            ds = rr.json()
            for res in ds['results']:
                rmap[res['name']] = res
            if ds['next'] is None:
                break
            print('have a next url ...')
            import epdb; epdb.st()

        if name in rmap:
            return rmap[name]

        url = self.HOST + '/pulp/api/v3/repositories/ansible/ansible/'
        payload = {'name': name}
        rr = requests.post(url, json=payload, auth=self.auth)
        return rr.json()

    def get_or_create_dist(self, name, base_path, repository_data):

        next_url = self.HOST + '/pulp/api/v3/distributions/ansible/ansible/'

        dmap = {}

        while next_url:
            rr = requests.get(next_url, auth=self.auth)
            ds = rr.json()
            for res in ds['results']:
                dmap[res['name']] = res
            if ds['next'] is None:
                break
            print('have a next url ...')
            import epdb; epdb.st()

        if name in dmap:
            return dmap[name]

        url = self.HOST + '/pulp/api/v3/distributions/ansible/ansible/'
        payload = {
            'base_path': base_path,
            'name': name,
            'repository': repository_data['pulp_href']
        }
        rr = requests.post(url, json=payload, auth=self.auth)
        task = rr.json()
        task_url = self.HOST + task['task']
        while True:
            trr = requests.get(task_url, auth=self.auth)
            tresp = trr.json()
            if tresp['state'] == 'completed':
                break

        return self.get_or_create_dist(name, base_path, repository_data)

    def get_or_create_remote(self, name, remote_url, requirements):

        next_url = self.HOST + '/pulp/api/v3/remotes/ansible/collection/'

        rmap = {}

        while next_url:
            rr = requests.get(next_url, auth=self.auth)
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

            url = self.HOST + rmap[name]['pulp_href']
            body = {
                'name': name,
                'rate_limit': 5,
                'requirements_file': requirements,
                'sync_dependencies': False,
                'url': remote_url,
            }
            rr = requests.patch(url, json=body, auth=self.auth)
            task = rr.json()
            task_url = self.HOST + task['task']
            while True:
                trr = requests.get(task_url, auth=self.auth)
                tresp = trr.json()
                # import epdb; epdb.st()
                if tresp['state'] == 'completed':
                    break

            return self.get_or_create_remote(name, remote_url, requirements)

        else:
            url = self.HOST + '/pulp/api/v3/remotes/ansible/collection/'
            body = {
                'name': name,
                'rate_limit': 1,
                'requirements_file': requirements,
                'sync_dependencies': False,
                'url': remote_url,
            }
            rr = requests.post(url, body, auth=self.auth)
            ds = rr.json()
            return ds

    def get_cv_count_from_db(self):
        logger.info('count collectionversions in DB')
        cmd = f"docker exec -it {self.db_container} psql -U pulp -c 'select count(*) from ansible_collectionversion;'"
        pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
        stdout = pid.stdout.decode('utf-8')
        lines = [x.strip() for x in stdout.split('\n') if x.strip()]
        lines = [x for x in lines if x.isdigit()]
        count = int(lines[0])
        return count

    def get_cvs_from_db(self):
        logger.info('get collectionversions from DB')
        cmd = f"docker exec -it {self.db_container} psql -P pager=off -U pulp -c 'select namespace,name,version from ansible_collectionversion;'"
        pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
        stdout = pid.stdout.decode('utf-8')
        lines = [x.strip() for x in stdout.split('\n') if x.strip()]
        lines = [x for x in lines if not x.startswith('(')]
        lines = [x for x in lines if not x.startswith('-')]
        lines = lines[1:]

        cvs = []
        for line in lines:
            cv = [x.strip() for x in line.split('|') if x.strip()]
            cvs.append(cv)

        return cvs

    def get_cols_from_db(self):
        logger.info('get collections from DB')
        cvs = self.get_cvs_from_db()
        fqns = [x[:2] for x in cvs]
        cols = []
        for fqn in fqns:
            if fqn not in cols:
                cols.append(fqn)
        return cols

    def run_sync(self, repo, remote, colcount=None, cvcount=None):
        t1 = datetime.datetime.now()
        sync_url = self.HOST + repo['pulp_href'] + 'sync/'
        payload = {
            'mirror': False,
            'optimize': True,
            'remote': remote['pulp_href']
        }
        rr = requests.post(sync_url, json=payload, auth=self.auth)
        task = rr.json()
        task_url = self.HOST + task['task']
        ds = None
        while True:
            trr = requests.get(task_url, auth=self.auth)
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
        self.write_stat('SYNC', delta, colcount, cvcount)

        return ds

    def write_stat(self, url_or_tag, duration, col_count, cv_count):
        fn = os.path.expanduser(self.benchmark_log)
        ts = datetime.datetime.now().isoformat()
        with open(fn, 'a') as f:
            f.write(f'{ts},{col_count},{cv_count},{duration},{url_or_tag}\n')

    def write_cstats(self):
        fn = os.path.expanduser(self.benchmark_log)
        ts = datetime.datetime.now().isoformat()
        pid = subprocess.run('docker stats --no-stream --format=json --no-trunc', shell=True, stdout=subprocess.PIPE)
        cstats = pid.stdout.decode('utf-8')
        cstats = json.loads(cstats)
        with open(fn, 'a') as f:
            f.write(f'{ts},CSTATS,{json.dumps(cstats)}\n')

    def run_benchmarks(self):
        current_collections = self.get_cols_from_db()
        current_collectionversions = self.get_cvs_from_db()

        def crawl_and_record(tag, next_url, max_depth=None):

            depth = 0
            while next_url:
                depth += 1
                if max_depth and depth >= max_depth:
                    break

                logger.info(str(depth) + " " + next_url)
                t1 = datetime.datetime.now()
                rr = requests.get(next_url, auth=self.auth)
                t2 = datetime.datetime.now()
                delta = (t2 - t1).total_seconds()

                self.write_stat(tag, delta, len(current_collections), len(current_collectionversions))

                if rr.status_code == 404:
                    break

                try:
                    ds = rr.json()
                except Exception as e:
                    #print(e)
                    break

                next_url = None

                if isinstance(ds, list):
                    break

                if ds.get('next'):
                    import epdb; epdb.st()

                if ds.get('links', {}).get('next'):
                    next_url = self.HOST + ds['links']['next']

        # what urls do we want to explore ... ?
        baseurls = {
            'API_ROOT': '/pulp_ansible/galaxy/default/api/',
            'API_V3_ROOT': '/pulp_ansible/galaxy/default/api/v3/',
            'NAMESPACE_INDEX': f'/pulp_ansible/galaxy/default/api/v3/plugin/ansible/content/{self.base_path}/namespaces/',
            'COL_INDEX': f'/pulp_ansible/galaxy/{self.base_path}/api/v3/plugin/ansible/content/{self.base_path}/collections/index/',
            'COL_ALL': f'/pulp_ansible/galaxy/{self.base_path}/api/v3/collections/all/',
            'ALL_COLLECTIONS': f'/pulp_ansible/galaxy/{self.base_path}/api/v3/plugin/ansible/content/{self.base_path}/collections/all-collections/',
            #'ALL_VERSIONS': f'/pulp_ansible/galaxy/{self.base_path}/api/v3/plugin/ansible/content/{self.base_path}/collections/all-versions/',
            'CONTENT_COLLECTIONS_INDEX': f'/pulp_ansible/galaxy/{self.base_path}/api/v3/plugin/ansible/content/{self.base_path}/collections/index/',
        }

        for tag, baseurl in baseurls.items():
            url = self.HOST + baseurl
            crawl_and_record(tag, url, max_depth=3)

        self.write_cstats()
        # import epdb; epdb.st()

    def incremental_sync(self):

        current_collections = self.get_cols_from_db()
        current_collectionversions = self.get_cvs_from_db()

        col_counter = 0
        batch = []
        for col in self.iterate_upstream_collections(self.UPSTREAM_BASEURL + '/api/v3/collections/'):

            # skip if already synced
            col_fqn = [col['namespace'], col['name']]
            if col_fqn in current_collections:
                continue

            col_counter += 1
            logger.info('-' * 50)
            logger.info(str(col_counter) + " " + str(col_fqn))
            logger.info('-' * 50)

            batch.append(col_fqn)
            if len(batch) >= 10:

                logger.info(f'BATCH: {batch}')

                spec = ['.'.join(x) for x in batch]
                spec = '\n - ' + '\n - '.join(spec)

                # make the remote
                logger.info('get remote')
                remote = self.get_or_create_remote(
                    "community",
                    'https://beta-galaxy.ansible.com/',
                    f'collections:' + spec
                )

                # start sync
                logger.info('start sync')
                res = self.run_sync(self.repo, remote, colcount=len(current_collections), cvcount=len(current_collectionversions))
                if res['state'] != 'completed':
                    batch = []
                    continue
                    #import epdb; epdb.st()

                # reset batch
                batch = []

                # run benchmark
                self.run_benchmarks()

        # remaining
        if batch:

            current_collections = self.get_cols_from_db()
            current_collectionversions = self.get_cvs_from_db()

            logger.info(f'BATCH: {batch}')

            spec = ['.'.join(x) for x in batch]
            spec = '\n - ' + '\n - '.join(spec)

            # make the remote
            logger.info('get remote')
            remote = self.get_or_create_remote(
                "community",
                'https://beta-galaxy.ansible.com/',
                f'collections:' + spec
            )

            # start sync
            logger.info('start sync')
            res = self.run_sync(self.repo, remote, colcount=len(current_collections), cvcount=len(current_collectionversions))
            if res['state'] != 'completed':
                import epdb; epdb.st()

            # run benchmark
            self.run_benchmarks()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    if args.reset:
        pass

    BMK = BenchMarker()
    BMK.run_benchmarks()
    BMK.incremental_sync()


if __name__ == "__main__":
    main()
