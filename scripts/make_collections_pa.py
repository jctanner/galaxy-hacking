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
API_ROOT = BASEURL + '/pulp/api/'
V3_ROOT = BASEURL + '/pulp/api/v3/'
#COL_LIST = V3_ROOT + 'pulp/api/v3/ansible/collections/'
#COL_LIST = BASEURL + '/api/automation-hub/pulp/api/v3/ansible/collections/'
COL_LIST = BASEURL + '/pulp/api/v3/ansible/collections/'
#SEARCH_ROOT = V3_ROOT + 'plugin/ansible/search/collection-versions/'
SEARCH_ROOT = BASEURL + '/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/'
NAMESPACE_LIST = BASEURL + '/api/automation-hub/_ui/v1/namespaces/'
USERNAME = 'admin'
PASSWORD = 'password'
AUTH = (USERNAME, PASSWORD)

ANSIBLE_DISTRIBUTION_PATH = '/pulp/api/v3/distributions/ansible/ansible/'
ANSIBLE_REPO_PATH = '/pulp/api/v3/repositories/ansible/ansible/'

DESIRED_COLLECTION_COUNT = 16100
DESIRED_COLLECTION_VERSION_COUNT = 35000

ARTIFACT_DIR = 'artifacts'

#client = GalaxyClient(API_ROOT, auth=(USERNAME, PASSWORD))
#TOKEN = client.token


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

    #client = GalaxyClient(API_ROOT, auth={'token': TOKEN})
    #logger.info(client.token)
    #client.server_version
    #artifact = MockedArtifact(artifact_filename)

    # /tmp/orion-utils-aiply4th/collections/skeleton/sxcqhtvw-uhfilljj-1.0.1.tar.gz
    fn = os.path.basename(artifact_filename).replace('.tar.gz', '')
    parts = fn.split('-')
    namespace = parts[0]
    name = parts[1]
    version = parts[2]

    url = f'/pulp_ansible/galaxy/published/api/v3/artifacts/collections/'
    url = BASEURL + url

    # make payload ...
    files = {
        'file': (os.path.basename(artifact_filename), open(artifact_filename, 'rb'))
    }

    t0 = datetime.datetime.now()

    #ds = galaxykit_upload_artifact({}, client, artifact)
    #task_url = BASEURL + ds['task']

    rr = requests.post(url, auth=AUTH, files=files)
    ds = rr.json()
    task_url = BASEURL + ds['task']

    time.sleep(.5)
    while True:
        rr = requests.get(
            task_url,
            auth=(USERNAME, PASSWORD)
        )
        logger.info(rr.json())
        state = rr.json()['state']
        if state == 'failed':
            raise Exception(rr.json())

        if rr.json()['state'] in ['completed', 'failed']:
            break

        time.sleep(2)

    # now we have to wait for it to actually show up?
    #final_url = V3_ROOT + f'collections/{namespace}/{name}/versions/{version}/'
    #final_url = V3_ROOT + f'plugin/ansible/content/staging/collections/index/{namespace}/{name}/versions/{version}/'
    final_url = SEARCH_ROOT + f'?namespace={namespace}&name={name}&version={version}'
    while True:
        logger.info(final_url)
        srr = requests.get(
            final_url,
            auth=(USERNAME, PASSWORD)
        )
        if srr.json()['meta']['count'] == 1:
            break
        if srr.status_code == 200:
            break
        time.sleep(2)

    tN = datetime.datetime.now()

    started = rr.json()['started_at'].replace('Z', '')
    started = datetime.datetime.fromisoformat(started)
    finished = rr.json()['finished_at'].replace('Z', '')
    finished = datetime.datetime.fromisoformat(finished)
    duration = (finished - started).total_seconds()

    #return t0.isoformat(), tN.isoformat(), (tN - t0).total_seconds()
    return started.isoformat(), finished.isoformat(), duration


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


def run_sql(sql):
    CONTAINER='oci_env-postgres-1'
    cmd = (
        f'docker exec {CONTAINER} '
        + '/bin/bash -c '
        + f'\'psql -U pulp -c "{sql}"\''
    )
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = pid.stdout.decode('utf-8')
    rows = stdout.split('\n')
    rows = [x for x in rows if '|' in x]
    rows = [x.split('|') for x in rows]
    for idx,x in enumerate(rows):
        stripped = [y.strip() for y in x]
        rows[idx] = stripped
    return rows


def get_collection_versions_from_db():
    sql = "SELECT namespace,name,version FROM ansible_collectionversion"
    rows = run_sql(sql)
    rows = rows[1:]
    rows = sorted(rows)
    return rows


def get_repositories_from_db(name_only=True):
    sql = (
        'SELECT * from ansible_ansiblerepository'
        + ' inner join core_repository'
        + ' ON core_repository.pulp_id=ansible_ansiblerepository.repository_ptr_id'
    )
    rows = run_sql(sql)
    if name_only:
        ix = rows[0].index('name')
        rows = [x[ix] for x in rows]
        rows = rows[1:]
    return rows


def create_repo(reponame, force=False):

    '''
    if not force:
        rmap = get_all_repos()
        if reponame in rmap:
            return rmap[reponame]
    '''

    '''
    if not force:
        repos_data = get_repositories_from_db(name_only=False)
        rmap = {}
        if repos_data:
            colnames = repos_data[0]
            for row in repos_data[1:]:
                ds = {}
                for x in range(0, len(colnames)):
                    ds[colnames[x]] = row[x]
                ds['pulp_href'] = f'/pulp/api/v3/repositories/ansible/ansible/{ds["pulp_id"]}/'
                rmap[ds['name']] = ds

        if reponame in rmap:
            return rmap[reponame]
    '''

    url = BASEURL + ANSIBLE_REPO_PATH
    rr = requests.get(url, auth=AUTH)
    rmap = dict((x['name'], x) for x in rr.json()['results'])

    if reponame in rmap:
        return rmap[reponame]

    payload = {'name': reponame}
    rr = requests.post(url, json=payload, auth=AUTH)


    if rr.status_code == 400:
        raise Exception(rr.text)

    if rr.status_code == 201:
        return rr.json()

    if force:
        return rr.json()

    import epdb; epdb.st()


def create_distro(reponame):

    '''
    dmap = get_all_distros()
    if reponame in dmap:
        return dmap[reponame]
    '''

    #dist_names = get_distributions_from_db()
    #if reponame in dist_names:
    #    return

    url = BASEURL + ANSIBLE_DISTRIBUTION_PATH
    rr = requests.get(url, auth=AUTH)
    dmap = dict((x['name'], x) for x in rr.json()['results'])
    if reponame in dmap:
        return dmap[reponame]

    repo = create_repo(reponame)
    payload = {
        'base_path': reponame,
        'name': reponame,
        'repository': repo['pulp_href']
    }
    url = BASEURL + ANSIBLE_DISTRIBUTION_PATH
    rr = requests.post(url, json=payload, auth=AUTH)
    ds = rr.json()
    task_url = ds['task']
    if not task_url.startswith(BASEURL):
        task_url = BASEURL + task_url
    completed = False
    while not completed:
        trr = requests.get(task_url, auth=('admin', 'password'))
        state = trr.json()['state']
        logger.info(f'waiting for distro to create {task_url} {state}')
        if state == 'failed':
            raise Exception(trr.json())
        completed = trr.json()['state'] == 'completed'
        if not completed:
            time.sleep(.1)


def get_distributions_from_db():
    sql = (
        'SELECT * from ansible_ansibledistribution'
        + ' inner join core_distribution'
        + ' ON core_distribution.pulp_id=ansible_ansibledistribution.distribution_ptr_id'
    )
    rows = run_sql(sql)
    ix = rows[0].index('name')
    rows = [x[ix] for x in rows]
    rows = rows[1:]
    return rows


def get_all_repos():

    url = 'http://localhost:5001' + ANSIBLE_REPO_PATH

    repos = []
    next_url = url
    while next_url:
        nrr = requests.get(next_url, auth=('admin', 'password'))
        ds = nrr.json()

        repos.extend(ds['results'])

        next_url = None
        if ds['next']:
            next_url = ds['next']

    rmap = dict((x['name'], x) for x in repos)
    return rmap


def get_all_distros():

    url = BASEURL + ANSIBLE_DISTRIBUTION_PATH

    distros = []
    next_url = url
    while next_url:
        nrr = requests.get(next_url, auth=('admin', 'password'))
        ds = nrr.json()

        distros.extend(ds['results'])

        next_url = None
        if ds['next']:
            next_url = ds['next']

    dmap = dict((x['name'], x) for x in distros)
    return dmap


def wait_for_all_tasks_to_finish():
    # http://192.168.1.199:8002/api/automation-hub/pulp/api/v3/tasks/?ordering=-pulp_created&offset=0&limit=10

    url = BASEURL + '/pulp/api/v3/tasks/?state__in=waiting,running'
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

        total_threads = 10
        #total_threads = 1

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

        #total_threads = 5
        total_threads = 1

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

    repo = create_repo('published')
    dist = create_distro('published')
    #import epdb; epdb.st()

    mucker = Mucker()
    #mucker.clear_staging()
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
            #mucker.make_namespaces(artifact_map)
            mucker.upload_and_benchmark(artifact_map)
            #mucker.approve_and_benchmark(artifact_map)
            wait_for_all_tasks_to_finish()
            #mucker.clear_staging()
            mucker.write_benchmark()
            mucker.clean()
            to_make = []
            #import epdb; epdb.st()


if __name__ == "__main__":
    main()
