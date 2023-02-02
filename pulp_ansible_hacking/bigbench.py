#!/usr/bin/env python3

import argparse
import datetime
import glob
import json
import keyword
import os
import random
import shutil
import subprocess
import tempfile
import time
import yaml

import concurrent.futures

import requests
from logzero import logger
from random_word import RandomWords


BASEURL = 'http://localhost:5001'
AUTH = ('admin', 'password')
ANSIBLE_DISTRIBUTION_PATH = '/pulp/api/v3/distributions/ansible/ansible/'
ANSIBLE_REPO_PATH = '/pulp/api/v3/repositories/ansible/ansible/'

RW = RandomWords()


def run_sql(sql):
    cmd = (
        'docker exec oci_env_pulp_1 '
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


def build_artifact(namespace, name, version, requires_ansible='>=2.12', dest=None):

    if dest:
        logger.debug(f'BUILD {dest}')
    else:
        logger.debug(f'BUILD {namespace}-{name}-{version}.tar.gz')

    workdir = tempfile.TemporaryDirectory(prefix='galaxy-build-')

    cmd = f'ansible-galaxy collection init {namespace}.{name}'
    pid = subprocess.run(cmd, shell=True, cwd=workdir.name, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert pid.returncode == 0, pid

    root = os.path.join(workdir.name, namespace, name)
    yfile = os.path.join(root, 'galaxy.yml')
    mdir = os.path.join(root, 'meta')
    runtime_file = os.path.join(mdir, 'runtime.yml')

    with open(yfile, 'r') as f:
        ydata = yaml.safe_load(f.read())
    ydata['version'] = version
    with open(yfile, 'w') as f:
        f.write(yaml.dump(ydata))

    os.makedirs(mdir)
    with open(runtime_file, 'w') as f:
        f.write(yaml.dump({'requires_ansible': requires_ansible}))

    cmd = 'ansible-galaxy collection build .'
    pid = subprocess.run(cmd, shell=True, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert pid.returncode == 0, pid

    fn = pid.stdout.decode('utf-8').strip().split()[-1]
    if dest is None:
        return fn

    shutil.copy(fn, dest)
    workdir.cleanup()
    return dest


def get_artifact(namespace, name, version):
    artifact_cache = 'artifacts'
    if not os.path.exists(artifact_cache):
        os.makedirs(artifact_cache)
    afile = os.path.join(artifact_cache, f'{namespace}-{name}-{version}.tar.gz')
    if not os.path.exists(afile):
        build_artifact(namespace, name, version, dest=afile)
    return afile


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


def create_repo(reponame, force=False):

    '''
    if not force:
        rmap = get_all_repos()
        if reponame in rmap:
            return rmap[reponame]
    '''

    if not force:
        repos_data = get_repositories_from_db(name_only=False)
        rmap = {}
        colnames = repos_data[0]
        for row in repos_data[1:]:
            ds = {}
            for x in range(0, len(colnames)):
                ds[colnames[x]] = row[x]
            ds['pulp_href'] = f'/pulp/api/v3/repositories/ansible/ansible/{ds["pulp_id"]}/'
            rmap[ds['name']] = ds

        if reponame in rmap:
            return rmap[reponame]

    payload = {'name': reponame}
    url = BASEURL + ANSIBLE_REPO_PATH
    rr = requests.post(url, json=payload, auth=AUTH)

    #import epdb; epdb.st()

    #if rr.status_code != 201:
    #    import epdb; epdb.st()

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

    dist_names = get_distributions_from_db()
    if reponame in dist_names:
        return

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
        completed = trr.json()['state'] == 'completed'
        if not completed:
            time.sleep(.1)


def get_collection_versions_by_repo(reponame):

    repo_info = create_repo(reponame)
    url = BASEURL + repo_info['latest_version_href']
    rr = requests.get(url, auth=('admin', 'password'))
    ds = rr.json()
    if ds['number'] == 0:
        return {}
    next_url = 'http://localhost:5001' + ds['content_summary']['present']['ansible.collection_version']['href']

    contents = []
    while next_url:
        nrr = requests.get(next_url, auth=('admin', 'password'))
        ds = nrr.json()
        contents.extend(ds['results'])

        next_url = None
        if ds['next']:
            next_url = ds['next']

    cvmap = {}
    for content in contents:
        key = (reponame, content['namespace'], content['name'], content['version'])
        cvmap[key] = content

    return cvmap


def get_all_collection_versions_by_all_repos():

    cvmap = {}
    repos = get_all_repos()
    for reponame in repos.keys():
        _cvs = get_collection_versions_by_repo(reponame)
        cvmap.update(_cvs)

    return cvmap


def publish_artifact(artifact_file, repo='automation-hub-1', force=False):

    logger.debug(f'PUBLISH {artifact_file} -> {repo}')

    # no duplicate uploads ...
    if not force:
        cvs = get_all_collection_versions_by_all_repos()
        spec = tuple([repo] + os.path.basename(artifact_file).replace('.tar.gz', '').split('-'))
        if spec in cvs:
            return cvs[spec]

    create_distro(repo)

    # make upload path ...
    url = f'/pulp_ansible/galaxy/{repo}/api/v3/artifacts/collections/'
    url = BASEURL + url

    # make payload ...
    files = {
        'file': (os.path.basename(artifact_file), open(artifact_file, 'rb'))
    }

    # start the request
    rr = requests.post(url, auth=AUTH, files=files)
    ds = rr.json()
    if 'errors' in ds:
        if 'detail' in ds['errors'][0]:
            if ds['errors'][0]['detail'] == 'Artifact already exists':
                return
        elif rr.status_code == 404:
            # missing repo? ...
            import epdb; epdb.st()
        else:
            raise Exception(f'BAD {rr}')

    task_url = 'http://localhost:5001' + ds['task']
    completed = False
    while not completed:
        rr = requests.get(task_url, auth=('admin', 'password'))
        completed = rr.json()['state'] == 'completed'
        if not completed:
            time.sleep(.1)


def random_safe_word():
    word = None
    while word is None or keyword.iskeyword(word):
        word = RW.get_random_word().lower()
    return word


def random_spec(fakearg=None):
    namespace = random_safe_word()
    name = random_safe_word()
    version = '.'.join([
        str(random.choice(range(0, 100))),
        str(random.choice(range(0, 100))),
        str(random.choice(range(0, 100)))
    ])
    spec = [namespace, name, version]
    # print(spec)
    return spec


def get_specs(count=100, build=True):

    specs = []

    cdir = 'artifacts'
    if not os.path.exists(cdir):
        os.makedirs(cdir)

    artifacts = glob.glob(f'{cdir}/*.tar.gz')
    for artifact in artifacts:
        parts = artifact.replace(cdir + '/', '').replace('.tar.gz', '').split('-')
        specs.append(parts)
    specs = sorted(specs)

    # make more if needed
    if len(specs) < count:

        logger.info(f'generate {count - len(specs)} more specs')
        args = [None for x in range(0, count - len(specs))]
        with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
            res = executor.map(random_spec, args)
        newspecs = [x for x in res]

        if not build:
            return newspecs

        for nspec in newspecs:
            get_artifact(*nspec)
        specs.extend(newspecs)

        '''
        for x in range(0, count - len(specs)):
            logger.info(f'spec {x}')
            rspec = random_spec()

            if build:
                get_artifact(*rspec)
            specs.append(rspec)
        '''

    specs = sorted(specs)
    if len(specs) > count:
        return specs[:count]

    return specs


def get_artifact_helper(args):
    return get_artifact(args[0], args[1], args[2])


def multi_build(count):
    """Parallel builds ..."""
    specs = get_specs(count=count, build=False)
    logger.info('specs collected')

    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
        logger.info('starting parallel build execution')
        #res = executor.map(get_artifact, *izip(*specs))
        for res in executor.map(get_artifact_helper, specs):
            #logger.info(f'res: {res}')
            pass
        #import epdb; epdb.st()

    #import epdb; epdb.st()


def get_stats():

    def timed_get(url):
        logger.info(f'timing call to {url}')
        t1 = datetime.datetime.now()
        rr = requests.get(url, auth=('admin', 'password'))
        t2 = datetime.datetime.now()
        td = (t2 - t1).total_seconds()
        logger.info(f'result: {td}s')
        return td, rr

    '''
    rspec = get_all_repos()
    repocount = len(list(rspec.keys()))
    '''

    repos = get_repositories_from_db()
    repos_count = len(repos)
    random_repo = random.choice(repos)

    '''
    cvmap = get_all_collection_versions_by_all_repos()
    rcv_keys = list(cvmap.keys())
    cv_keys = sorted(set([x[1:] for x in rcv_keys]))
    '''

    cv_keys = get_collection_versions_from_db()
    random_namespace = random.choice([x[0] for x in cv_keys])
    random_name = random.choice([x[1] for x in cv_keys])
    random_version = random.choice([x[2] for x in cv_keys])

    baseurl = 'http://localhost:5001'
    bench_urls = [
        baseurl + "/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/",
        baseurl + "/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/?repository=automation-hub-1",
        baseurl + f"/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/?repository={random_repo}",
        baseurl + f"/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/?namespace={random_namespace}",
        baseurl + f"/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/?name={random_name}",
        baseurl + f"/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/?version={random_version}",
        baseurl + "/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/?signed=true",
        baseurl + "/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/?signed=false",
    ]

    '''
    for reponame, repodata in rspec.items():
        repo_content_url = (
            BASEURL
            + '/pulp/api/v3/content/ansible/collection_versions/'
            + '?repository_version='
            + repodata['latest_version_href']
        )
        bench_urls.append(repo_content_url)
    '''

    stats = {}
    for next_page in bench_urls:

        while next_page:
            delta, rr = timed_get(next_page)
            try:
                ds = rr.json()
            except requests.exceptions.JSONDecodeError as e:
                logger.error(e)
                next_page = None
                continue

            params = next_page.split('?')
            if len(params) == 1:
                page_number = 1
            else:
                params = params[-1]
                params = params.split('&')
                params = dict(x.split('=') for x in params)
                if 'page' in params:
                    page_number = int(params['page'])
                else:
                    page_number = 1

            if 'count' not in ds:
                import epdb; epdb.st()

            stats[next_page] = {
                'url': next_page,
                'status_code': rr.status_code,
                'page_number': page_number,
                'duration_seconds': delta,
                #'repos_cvs_count': len(rcv_keys),
                'cvs_count': len(cv_keys),
                'page_meta_count': ds['count'],
                'page_result_count': len(ds['results']),
                'repo_count': repos_count,
                'signed': 'signed=' in next_page
            }

            next_page = None
            if ds['next']:
                next_page = ds['next']

    return stats


def fibonacci(n):
    if n < 0:
        raise
    elif n == 0:
        return 0
    elif n == 1 or n == 2:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--build', type=int)
    args = parser.parse_args()
    if args.build:
        multi_build(args.build)
        return

    # make a scaling upwards seriees of numbers ...
    fib_sequence = []
    for x in range(2, 23):
        fib_sequence.append(fibonacci(x))

    # can't bench a number smaller than what is in the system ...
    #cvmap = get_all_collection_versions_by_all_repos()
    #published_specs = [list(x[1:]) for x in cvmap.keys()]
    #total = len(list(cvmap.keys()))
    published_specs = get_collection_versions_from_db()
    total = len(published_specs)
    fib_sequence = [x for x in fib_sequence if x >= total]

    '''
    # make a bunch of repositories ...
    repos = get_repositories_from_db()
    if len(repos) < 1000:
        sequence = [x for x in range(0, 1000 - len(repos))]
        for x in sequence:
            reponame = RW.get_random_word()
            logger.debug(f'make repo {reponame} {x} of {len(sequence)}')
            create_repo(reponame, force=True)
    '''

    # benchmark each total count of CVs
    all_stats = []
    for total in fib_sequence:

        logger.info('-' * 50)
        logger.info(f'BENCH {total} CVs')
        logger.info('-' * 50)

        # make a bunch of repositories (sometimes) ...
        if random.choice([True, False]):
            repos = get_repositories_from_db()

            if len(repos) < total:

                desired_count = random.choice([x for x in range(len(repos), total)])

                sequence = [x for x in range(0, desired_count)]
                for x in sequence:
                    reponame = None
                    while reponame is None or reponame in repos:
                        reponame = RW.get_random_word()
                    logger.debug(f'make repo {reponame} {x} of {len(sequence)}')
                    create_repo(reponame, force=True)
                    repos.append(reponame)

        create_repo('automation-hub-1', force=True)
        create_repo('automation-hub-2', force=True)
        create_repo('automation-hub-3', force=True)
        repos = get_repositories_from_db()

        # define the CVs ...
        #spec_map = {}
        specs = get_specs(count=total)
        '''
        for spec in specs:
            artifact = get_artifact(*spec)
            spec_map[tuple(spec)] = {'artifact': artifact, 'published': False}
        '''

        # upload the CVs ...
        #for k,v in spec_map.items():
        for spec in specs:
            if spec not in published_specs:
                artifact = get_artifact(*spec)
                publish_artifact(artifact, force=True, repo=random.choice(repos))
                published_specs.append(spec)
            #spec_map[k]['published'] = True

        #import epdb; epdb.st()

        # make some numbers ...
        stats = get_stats()
        #all_stats.append([total, stats])
        #with open('benchmark_results.json', 'w') as f:
        #    f.write(json.dumps(all_stats, indent=2))

        if os.path.exists('benchmark_results.json'):
            with open('benchmark_results.json', 'r') as f:
                all_stats = json.loads(f.read())

        all_stats.append([total, stats])
        with open('benchmark_results.json', 'w') as f:
            f.write(json.dumps(all_stats, indent=2))

    #import epdb; epdb.st()



if __name__ == "__main__":
    main()
