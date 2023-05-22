#!/usr/bin/env python3

import datetime
import os
import requests
import subprocess
import time

import concurrent.futures

from orionutils.generator import randstr
from orionutils.generator import build_collection
from galaxykit.collections import upload_artifact as galaxykit_upload_artifact
from galaxykit.client import GalaxyClient

from logzero import logger


BASEURL = 'http://localhost:5001'
API_ROOT = BASEURL + '/api/automation-hub/'
V3_ROOT = BASEURL + '/api/automation-hub/v3/'
COL_LIST = V3_ROOT + 'pulp/api/v3/ansible/collections/'
COL_LIST = BASEURL + '/api/automation-hub/pulp/api/v3/ansible/collections/'
SEARCH_ROOT = V3_ROOT + 'plugin/ansible/search/collection-versions/'
NAMESPACE_LIST = BASEURL + '/api/automation-hub/_ui/v1/namespaces/'
USERNAME = 'admin'
PASSWORD = 'admin'

DESIRED_COLLECTION_COUNT = 16100
DESIRED_COLLECTION_VERSION_COUNT = 35000

ARTIFACT_DIR = 'artifacts'

client = GalaxyClient(API_ROOT, auth=(USERNAME, PASSWORD))
TOKEN = client.token


class MockedArtifact:
    def __init__(self, filename):
        self.filename = filename


def build_artifact(namespace, name, version):
    logger.info(f'build_artifact {namespace} {name} {version}')
    res = build_collection(
        'skeleton',
        config={
            'namespace': namespace,
            'name': name,
            'version': version
        },
        extra_files={
            'CHANGELOG.md': ''
        }
    )
    print(res)
    return res.filename


def upload_artifact_and_benchmark(artifact_filename):

    client = GalaxyClient(API_ROOT, auth={'token': TOKEN})
    #logger.info(client.token)
    #client.server_version
    artifact = MockedArtifact(artifact_filename)

    # /tmp/orion-utils-aiply4th/collections/skeleton/sxcqhtvw-uhfilljj-1.0.1.tar.gz
    fn = os.path.basename(artifact_filename).replace('.tar.gz', '')
    parts = fn.split('-')
    namespace = parts[0]
    name = parts[1]
    version = parts[2]

    t0 = datetime.datetime.now()
    ds = galaxykit_upload_artifact({}, client, artifact)
    task_url = BASEURL + ds['task']

    time.sleep(.5)
    while True:
        rr = requests.get(
            task_url,
            auth=(USERNAME, PASSWORD)
        )
        logger.info(rr.json())
        if rr.json()['state'] in ['completed', 'failed']:
            break
        time.sleep(2)

    # now we have to wait for it to actually show up?
    #final_url = V3_ROOT + f'collections/{namespace}/{name}/versions/{version}/'
    final_url = V3_ROOT + f'plugin/ansible/content/staging/collections/index/{namespace}/{name}/versions/{version}/'
    while True:
        rr = requests.get(
            final_url,
            auth=(USERNAME, PASSWORD)
        )
        if rr.status_code == 200:
            break
        time.sleep(2)

    tN = datetime.datetime.now()

    return t0.isoformat(), tN.isoformat(), (tN - t0).total_seconds()


def approve_cv_and_benchmark(namespace, name, version):
    # POST http://localhost:8002/api/automation-hub/v3/collections/ycmytpuu/ajhxtquw/versions/1.0.0/move/staging/published/
    move_url = V3_ROOT + f'collections/{namespace}/{name}/versions/{version}/move/staging/published/'
    logger.info(move_url)

    t0 = datetime.datetime.now()

    rr = requests.post(
        move_url,
        auth=(USERNAME, PASSWORD)
    )

    logger.info(rr)
    logger.info(rr.text)
    logger.info(rr.json())

    # we should have a copy_task_id and a remove_task_id in the response .. we need to wait on both.
    while True:
        states = []
        for task_type, taskid in rr.json().items():
            if not taskid:
                continue

            task_url = V3_ROOT + f'tasks/{taskid}/'
            rr2 = requests.get(
                task_url,
                auth=(USERNAME, PASSWORD)
            )
            ds = rr2.json()
            #logger.info(task_type, taskid)
            #logger.info(task_url)
            #logger.info(ds)
            logger.info(f"approve [{task_type}] ({namespace},{name},{version}) {ds['name']} {ds['state']}")
            states.append(ds['state'])

        if not states:
            break

        if [x for x in states if x not in ['completed', 'failed']]:
            time.sleep(5)
        else:
            break

    tN = datetime.datetime.now()

    return t0.isoformat(), tN.isoformat(), (tN - t0).total_seconds()


def make_namespace(name):
    logger.info(f'create {name} namespace')
    rr = requests.post(
        NAMESPACE_LIST,
        json={'name': name, 'groups': []},
        auth=(USERNAME, PASSWORD)
    )


def wait_for_all_tasks_to_finish():
    # http://192.168.1.199:8002/api/automation-hub/pulp/api/v3/tasks/?ordering=-pulp_created&offset=0&limit=10

    url = API_ROOT + 'pulp/api/v3/tasks/?state__in=waiting,running'
    while True:
        rr = requests.get(
            url,
            auth=(USERNAME, PASSWORD)
        )
        ds = rr.json()
        logger.info(f"{ds['count']} tasks not finished")
        if ds['count'] > 0:
            for task in ds['results']:
                logger.info(f"\t{task['name']} {task['state']}")
        if ds['count'] == 0:
            break
        time.sleep(2)


class BenchMarks:
    def __init__(self):
        self._rows = []

    def add(self, action, start, stop, duration):
        self._rows.append([action, start, stop, duration])

    def write(self, extra=None):
        with open('benchmark.log', 'a') as f:
            for row in self._rows:
                if extra:
                    f.write(','.join([str(x) for x in row+extra]) + '\n')
                else:
                    f.write(','.join([str(x) for x in row]) + '\n')
        self._rows = []


class Mucker:

    def __init__(self):
        self.session = requests.session()
        self.artifact_map = {}
        if not os.path.exists(ARTIFACT_DIR):
            os.makedirs(ARTIFACT_DIR)

        self.benchmarks = BenchMarks()

    def clear_staging(self):
        wait_for_all_tasks_to_finish()

        collections = []
        next_url = BASEURL + '/api/automation-hub/v3/plugin/ansible/content/staging/collections/index/'
        while next_url:
            logger.info(next_url)
            rr = requests.get(
                next_url,
                auth=(USERNAME, PASSWORD)
            )
            results = rr.json()
            for collection in results['data']:
                collections.append(collection['href'])
            next_url = results['links']['next']
            if not next_url:
                break
            next_url = BASEURL + next_url

        for idc,collection_href in enumerate(collections):
            logger.info(f'{len(collections)}|{idc} DELETE {collection_href}')
            rr = requests.delete(
                BASEURL + collection_href,
                auth=(USERNAME, PASSWORD)
            )
            ds = rr.json()
            wait_for_all_tasks_to_finish()
            #import epdb; epdb.st()

        url = BASEURL + '/api/automation-hub/pulp/api/v3/orphans/cleanup/'
        rr = requests.post(
            url,
            auth=(USERNAME, PASSWORD)
        )
        wait_for_all_tasks_to_finish()

    def write_benchmark(self):
        cols = self.get_total_remote_collections()
        cvs = self.get_total_remote_collection_versions()

        self.benchmarks.write(extra=[cols, cvs])

    def clean(self):
        subprocess.run('rm -rf /tmp/orion-utils*', shell=True)

    def get_total_remote_collections(self):
        rr = self.session.get(
            COL_LIST,
            auth=(USERNAME, PASSWORD)
        )
        return rr.json()['count']

    def get_total_remote_collection_versions(self):
        rr = self.session.get(
            SEARCH_ROOT,
            auth=(USERNAME, PASSWORD)
        )
        return rr.json()['meta']['count']

    def batch_build(self, specs):

        artifact_map = {}
        total_threads = 5
        args_list = specs[:]
        kwargs_list = [{} for x in range(0, len(args_list))]

        with concurrent.futures.ThreadPoolExecutor(max_workers=total_threads) as executor:
            future_to_args_kwargs = {
                executor.submit(build_artifact, *args, **kwargs): (args, kwargs)
                for args, kwargs in zip(args_list, kwargs_list)
            }

            for future in concurrent.futures.as_completed(future_to_args_kwargs):
                args, kwargs = future_to_args_kwargs[future]
                artifact_fn = future.result()
                artifact_map[tuple(args)] = artifact_fn

        self.artifact_map.update(artifact_map)
        return artifact_map


    def make_namespaces(self, artifact_map):

        namespace_names = sorted(set([x[0] for x in artifact_map.keys()]))

        total_threads = 5
        args_list = namespace_names[:]
        kwargs_list = [{} for x in range(0, len(args_list))]

        with concurrent.futures.ThreadPoolExecutor(max_workers=total_threads) as executor:
            future_to_args_kwargs = {
                executor.submit(make_namespace, args, **kwargs): (args, kwargs)
                for args, kwargs in zip(args_list, kwargs_list)
            }

            for future in concurrent.futures.as_completed(future_to_args_kwargs):
                args, kwargs = future_to_args_kwargs[future]
                future.result()

        wait_for_all_tasks_to_finish()

    def upload_and_benchmark(self, artifact_map):

        filenames = list(artifact_map.values())
        duration_map = {}

        total_threads = 5
        args_list = filenames[:]
        kwargs_list = [{} for x in range(0, len(args_list))]

        with concurrent.futures.ThreadPoolExecutor(max_workers=total_threads) as executor:
            future_to_args_kwargs = {
                executor.submit(upload_artifact_and_benchmark, args, **kwargs): (args, kwargs)
                for args, kwargs in zip(args_list, kwargs_list)
            }

            for future in concurrent.futures.as_completed(future_to_args_kwargs):
                args, kwargs = future_to_args_kwargs[future]
                start,stop,duration = future.result()
                duration_map[args] = {
                    'start': start,
                    'stop': stop,
                    'duration': duration
                }
                self.benchmarks.add('upload', start, stop, duration)

        return duration_map

    def approve_and_benchmark(self, artifact_map):

        filenames = list(artifact_map.values())
        duration_map = {}

        total_threads = 5
        #total_threads = 1

        args_list = [list(x) for x in artifact_map.keys()]
        kwargs_list = [{} for x in range(0, len(args_list))]

        with concurrent.futures.ThreadPoolExecutor(max_workers=total_threads) as executor:
            future_to_args_kwargs = {
                executor.submit(approve_cv_and_benchmark, *args, **kwargs): (args, kwargs)
                for args, kwargs in zip(args_list, kwargs_list)
            }

            for future in concurrent.futures.as_completed(future_to_args_kwargs):
                args, kwargs = future_to_args_kwargs[future]
                start,stop,duration = future.result()
                duration_map[tuple(args)] = {
                    'start': start,
                    'stop': stop,
                    'duration': duration
                }
                self.benchmarks.add('move', start, stop, duration)

        #import epdb; epdb.st()
        return duration_map



def main():

    mucker = Mucker()
    mucker.clear_staging()
    col_count = mucker.get_total_remote_collections()
    cv_count = mucker.get_total_remote_collection_versions()
    cv_per_col = int(DESIRED_COLLECTION_VERSION_COUNT / DESIRED_COLLECTION_COUNT)
    batch_size = 10

    collections_needed = DESIRED_COLLECTION_COUNT - cv_count
    logger.info(f'need to make {collections_needed} new collections')
    to_make = []
    for x in range(0, collections_needed):
        logger.info(x)
        namespace = randstr()
        name = randstr()
        for v in range(0, cv_per_col):
            to_make.append([namespace, name, '1.0.' + str(v)])

        if len(to_make) >= batch_size:
            artifact_map = mucker.batch_build(to_make)
            mucker.make_namespaces(artifact_map)
            mucker.upload_and_benchmark(artifact_map)
            mucker.approve_and_benchmark(artifact_map)
            wait_for_all_tasks_to_finish()
            mucker.clear_staging()
            mucker.write_benchmark()
            mucker.clean()
            to_make = []
            #import epdb; epdb.st()


if __name__ == "__main__":
    main()
