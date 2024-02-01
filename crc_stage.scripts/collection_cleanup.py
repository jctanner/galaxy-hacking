#!/usr/bin/env python


import argparse
import datetime
import json
import os
import sys
import platform
import requests
import time
import urllib3

from datetime import timedelta
from requests_cache import CachedSession
from logzero import logger
from urllib.parse import urlparse, urljoin
from galaxykit.utils import GalaxyClientError


VERSION = 'stage-cleaner'


class CollectionNotFoundException(Exception):
    pass


class CollectionDeleteFailedException(Exception):
    pass


class CollectionDeleteFailedOnDependencyException(Exception):
    pass


class ServerErrorException(Exception):
    pass


class ActionCacher:
    def __init__(self):
        self.cachefile = '.actions.json'
        self._cache = None
        self.get_cache()

    def get_cache(self):
        if not os.path.exists(self.cachefile):
            self._cache = {}
        else:
            try:
                with open(self.cachefile, 'r') as f:
                    self._cache = json.loads(f.read())
            except json.decoder.JSONDecodeError:
                self._cache = {}

        return self._cache

    def repo_collection_is_deleted(self, repo, namespace, name):
        key = self.key_for_repo_collection(repo, namespace, name)
        if key not in self._cache:
            return False
        if self._cache[key].get('deleted') == True:
            return True
        return False

    def key_for_repo_collection(self, repo, namespace, name):
        key = '.'.join([repo, namespace, name])
        return key

    def write_cache(self):
        with open(self.cachefile, 'w') as f:
            f.write(json.dumps(self._cache))

    def store_collection_deleted(self, repo, namespace, name):
        key = self.key_for_repo_collection(repo, namespace, name)
        if key not in self._cache:
            self._cache[key] = {'deleted': True}
        else:
            self._cache[key]['deleted'] = True
        self.write_cache()


def seconds_to_dhms(seconds):
    days = seconds // (24 * 3600)
    seconds %= (24 * 3600)
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return f"{days} days, {hours} hours, {minutes} minutes"


# https://github.com/ansible/galaxykit/blob/main/galaxykit/client.py#L29
def user_agent():
    """Returns a user agent used by ansible-galaxy to include the Ansible version,
    platform and python version."""

    python_version = sys.version_info
    return "galaxy-kit/{version} ({platform}; python:{py_major}.{py_minor}.{py_micro})".format(
        version=VERSION,
        platform=platform.system(),
        py_major=python_version.major,
        py_minor=python_version.minor,
        py_micro=python_version.micro,
    )


# https://github.com/ansible/galaxykit/blob/main/galaxykit/client.py#L43
def send_request_with_retry_if_504(
    method, url, headers, verify, retries=3, *args, **kwargs
):
    for _ in range(retries):
        resp = requests.request(
            method, url, headers=headers, verify=verify, *args, **kwargs
        )
        if resp.status_code == 504:
            logger.debug("504 Gateway timeout. Retrying.")
        else:
            return resp
    raise GalaxyClientError(resp, resp.status_code, resp.text)


class RepositoryCollectionVersion:
    def __init__(self, data):
        self.data = data

    @property
    def __tuple__(self):
        return [self.repository, self.namespace, self.name, self.version]

    def __repr__(self):
        return f'<rcv {self.repository}:{self.namespace}.{self.name}:{self.version}>'

    def __str__(self):
        return f'{self.repository}:{self.namespace}.{self.name}:{self.version}'

    def __gt__(self, other):
        return self.__tuple__ > other.__tuple__

    @property
    def created(self):
        return self.data['collection_version']['pulp_created']

    @property
    def pulp_href(self):
        return self.data['collection_version']['pulp_href']

    @property
    def repository(self):
        return self.data['repository']['name']

    @property
    def namespace(self):
        return self.data['collection_version']['namespace']

    @property
    def name(self):
        return self.data['collection_version']['name']

    @property
    def version(self):
        return self.data['collection_version']['version']


class SSOClient:

    token = None
    token_type = None

    def __init__(self, http_proxy=None, auth_url=None, username=None, password=None, refresh_token=None, api_host=None):
        self.http_proxy = http_proxy
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.refresh_token = refresh_token
        self.api_host = api_host

        self.proxies = {
            'http': self.http_proxy,
            'https': self.http_proxy
        }
        self.headers = {}
        self.https_verify = False
        self.galaxy_root = self.api_host + '/api/automation-hub'

        # This makes development iteration a lot faster ...
        self.session = CachedSession('demo_cache', expire_after=timedelta(hours=24))

        self._refresh_jwt_token()

    def paginated_get(self, *args, **kwargs):

        results = []

        count = None

        next_url = args[0]
        while next_url:

            progress = f'{count}|{len(results)} '
            logger.info(progress + next_url)

            rr = self.get(next_url)
            try:
                ds = rr.json()
            except requests.exceptions.JSONDecodeError:
                if 'Server Error (500)' in rr.text:
                    raise ServerErrorException(rr.text)

            # check for expired token ...
            if 'data' not in ds:
                if ds.get('errors') and 'Invalid JWT' in str(ds):
                    self._refresh_jwt_token()
                rr = self.get(next_url)
                ds = rr.json()

            dkey = 'data'
            if 'results' in ds:
                dkey = 'results'
            for res in ds[dkey]:
                results.append(res)

            if 'count' in ds:
                count = ds['count']
            else:
                count = ds['meta']['count']

            next_url = None
            if 'next' in ds and ds['next']:
                import epdb; epdb.st()
            elif 'links' in ds:
                if ds['links'].get('next'):
                    next_url = self.api_host.rstrip('/') + ds['links']['next']

        return results

    def get(self, *args, **kwargs):
        url = args[0]
        headers = {'Authorization': f'Bearer {self.token}'}
        if kwargs.get('headers'):
            headers.update(kwargs.get('headers'))
        rkwargs = {}
        rkwargs['headers'] = headers
        rkwargs['proxies'] = self.proxies
        if kwargs.get('data'):
            rkwargs['data'] = kwargs['data']

        try:
            if kwargs.get('usecache') == False:
                rr = requests.get(url, **rkwargs)
            else:
                rr = self.session.get(url, **rkwargs)
        except urllib3.exceptions.MaxRetryError:
            logger.error('MAXTRETRYERROR ... waiting 5s')
            time.sleep(5)
            return self.get(*args, **kwargs)
        except requests.exceptions.SSLError:
            logger.error('SSLERROR ... waiting 5s')
            time.sleep(5)
            return self.get(*args, **kwargs)

        if rr.status_code == 401 and 'claim expired' in rr.text:
            self._refresh_jwt_token()
            return self.get(*args, **kwargs)

        return rr

    def post(self, *args, **kwargs):
        url = args[0]
        headers = {'Authorization': f'Bearer {self.token}'}
        if kwargs.get('headers'):
            headers.update(kwargs.get('headers'))
        rkwargs = {}
        rkwargs['headers'] = headers
        rkwargs['proxies'] = self.proxies
        if kwargs.get('data'):
            rkwargs['data'] = kwargs['data']

        if kwargs.get('usecache') == False:
            return requests.post(url, **rkwargs)
        else:
            return self.session.post(url, **rkwargs)

    def delete(self, *args, **kwargs):
        url = args[0]
        headers = {'Authorization': f'Bearer {self.token}'}
        if kwargs.get('headers'):
            headers.update(kwargs.get('headers'))

        rkwargs = {}
        rkwargs['headers'] = headers
        rkwargs['proxies'] = self.proxies
        if kwargs.get('data'):
            rkwargs['data'] = kwargs['data']

        if kwargs.get('usecache') == False:
            rr = requests.delete(url, **rkwargs)
        else:
            rr = self.session.delete(url, **rkwargs)

        if rr.status_code == 401 and 'claim expired' in rr.text:
            self._refresh_jwt_token()
            return self.delete(*args, **kwargs)

        return rr

    def _refresh_jwt_token(self, grant_type='password'):
        logger.info('refresh token')

        if grant_type != 'password':
            payload = {
                'grant_type': 'refresh_token',
                'client_id': 'cloud-services',
                'refresh_token': self.refresh_token
            }
        else:
            payload = {
                'grant_type': 'password',
                'client_id': 'cloud-services',
                'username': self.username,
                'password': self.password,
            }

        rr = self.post(self.auth_url, data=payload)
        assert rr.status_code == 200, rr.text

        ds = rr.json()
        self.token = ds["access_token"]
        self.token_type = "Bearer"


class StageCleaner:
    def __init__(self):

        self.ac = ActionCacher()

        self.http_proxy = os.environ.get('HTTP_PROXY', 'http://squid.corp.redhat.com:3128')
        self.auth_url = os.environ.get('AUTH_URL')
        self.refresh_token = os.environ.get('GALAXY_REFRESH_TOKEN')
        self.username = os.environ.get('GALAXY_USERNAME')
        self.password = os.environ.get('GALAXY_PASSWORD')
        self.api_host = os.environ.get('GALAXY_HOST')

        self.client = SSOClient(
            http_proxy=self.http_proxy,
            auth_url=self.auth_url,
            refresh_token=self.refresh_token,
            username=self.username,
            password=self.password,
            api_host=self.api_host
        )

        # smoketest ...
        rr = self.client.get(self.api_host.rstrip('/') + '/api/automation-hub/', usecache=False)
        ds = rr.json()
        assert "available_versions" in ds, rr.text

        self.process()

    def process(self):
        # list all namespaces ...
        results = self.client.paginated_get(
            self.api_host.rstrip('/') + '/api/automation-hub/_ui/v1/namespaces/?limit=100'
        )
        self.namespaces = dict((x['name'], x) for x in results)

        # list all repos ...
        repos = self.client.paginated_get(self.api_host.rstrip('/') + '/api/automation-hub/pulp/api/v3/repositories/')
        self.repos = dict((x['name'], x) for x in repos)

        # list all collections in each repo ...
        self.cols_by_repo = self.get_collections_in_all_repos(list(self.repos.keys()))

        # list all collection versions ...
        results = self.client.paginated_get(
            self.api_host.rstrip('/') + '/api/automation-hub/v3/plugin/ansible/search/collection-versions/?limit=100'
        )
        self.cvs = [RepositoryCollectionVersion(x) for x in results]
        self.cvs = sorted(self.cvs)

    def delete_all_cmd(self):
        raise Exception('not yet implemented')

    def delete_repositories_cmd(self):
        raise Exception('not yet implemented')

    def delete_namespaces_cmd(self):
        self.delete_empty_namespaces()

    def delete_collections_cmd(self):
        raise Exception('not yet implemented')

    def delete_collection_versions_cmd(self):
        self.delete_collection_versions()

    def delete_empty_namespaces(self):

        # cnamespaces = sorted(set([x.namespace for x in self.cvs]))

        repo_namespaces = set()
        for reponame, cmap in self.cols_by_repo.items():
            for cv,cdata in cmap.items():
                repo_namespaces.add(cdata['namespace'])
        cnamespaces = sorted(repo_namespaces)

        anamespaces = sorted(list(self.namespaces.keys()))
        empty_namespaces = set(anamespaces) - set(cnamespaces)
        self.delete_namespaces(empty_namespaces)

    def delete_collection_versions(self):

        unique_cvs = dict((x.pulp_href, None) for x in self.cvs)
        unique_cvs = sorted(list(unique_cvs.keys()))
        print(f'TOTAL UNIQUE CVS: {len(unique_cvs)}')

        # map out by namespace.name ...
        col_map = {}
        for cv in self.cvs:
            fqn = (cv.namespace, cv.name)
            if fqn not in col_map:
                col_map[fqn] = {
                    'vcount': 0,
                    'versions': [],
                }

            if cv.version not in col_map[fqn]['versions']:
                col_map[fqn]['versions'].append(cv.version)
                col_map[fqn]['vcount'] += 1

        vcounts = [(x[0],x[1]['vcount']) for x in col_map.items()]
        vcounts = sorted(vcounts, key=lambda x: x[1])

        # DELETE ALL COLS FROM OLDEST TO NEWEST ...
        cvs_by_age = sorted(self.cvs, key=lambda x: x.created)
        cols_by_age = dict(((x.namespace, x.name), x.created) for x in cvs_by_age)
        cols_by_age = [(x[0],x[1]) for x in cols_by_age.items()]
        cols_by_age = sorted(cols_by_age, key=lambda x: x[1])
        logger.info(f'DELETE {len(cols_by_age)} COLLECTIONS ...')

        durations = []

        for idc,ctuple in enumerate(cols_by_age):
            namespace = ctuple[0][0]
            name = ctuple[0][1]
            logger.info(f'DELETE {idc+1} of {len(cols_by_age)} {namespace}.{name} ...')
            t1 = datetime.datetime.now()
            self.delete_collection(namespace, name)
            tN = datetime.datetime.now()
            delta = (tN - t1).total_seconds()
            durations.append(delta)

            if len(durations) > 2:
                avg = sum(durations) / len(durations)
                seconds_left = (len(cols_by_age) - idc) * avg
                remaining = seconds_to_dhms(seconds_left)
                logger.info(f'ESTIMATED TIME REMAINING {remaining}')

    def get_collections_in_all_repos(self, reponames):
        rmap = {}
        reponames = sorted(reponames)
        for reponame in reponames:
            cols = self.get_collections_in_repo(reponame)
            rmap[reponame] = cols
            # import epdb; epdb.st()
        return rmap

    def get_collections_in_repo(self, reponame):
        # https://github.com/ansible/galaxy_ng/blob/master/galaxy_ng/tests/integration/utils/collections.py#L564C9-L564C66
        # https://console.stage.redhat.com/api/automation-hub/content/published/v3/plugin/ansible/content/published/collections/index/?limit=10&offset=650
        url = self.api_host.rstrip('/') + f'/api/automation-hub/content/{reponame}/v3/plugin/ansible/content/{reponame}/collections/index/?limit=100'
        try:
            results = self.client.paginated_get(url)
        except ServerErrorException:
            logger.error(f'500ISE trying to get collections in {reponame}')
            return {}
        cols = dict(((x['namespace'], x['name']), x) for x in results)
        return cols

    def delete_namespaces(self, namespaces):
        for nsid,ns in enumerate(namespaces):
            logger.info(f'{len(namespaces)}|{nsid} DELETE NAMESPACE {ns}')
            self.delete_namespace(ns)

    def delete_namespace(self, namespace, retry=True):
        # https://github.com/ansible/galaxykit/blob/main/galaxykit/namespaces.py#L104-L109
        url = self.api_host.rstrip('/') + f'/api/automation-hub/_ui/v1/namespaces/{namespace}/'

        rr = self.client.delete(url, usecache=False)

        if rr.status_code == 400:
            if 'still collections associated with it' in rr.text and retry:
                self.delete_namespace_collections(namespace)
                self.delete_namespace(namespace, retry=False)
            # raise Exception(f'CAN NOT DELETE {namespace} {rr.text}')
            logger.error(f'CAN NOT DELETE {namespace} {rr.text}')
            return

        '''
        if 'task' not in ds:
            if 'require it' in ds.get('detail', ''):
                raise CollectionDeleteFailedOnDependencyException()

            import epdb; epdb.st()
        '''

        # no json nor any tasks are returned from a namespace delete
        if rr.status_code == 404:
            return
        if rr.status_code != 204:
            import epdb; epdb.st()
        assert rr.status_code == 204

    def delete_namespace_collections(self, namespace):
        to_delete = []
        for reponame, cmap in self.cols_by_repo.items():
            for ckey in cmap.keys():
                if ckey[0] == namespace:
                    to_delete.append([reponame, ckey[0], ckey[1]])

        if not to_delete:
            return

        for idx,rcol in enumerate(to_delete):
            logger.info(f'{len(to_delete)}|{idx} DELETE {rcol} FOR NAMESPACE {namespace} CLEANUP')
            self.delete_collection_from_repo(rcol[1], rcol[2], rcol[0])

        # import epdb; epdb.st()

    def delete_collection(self, namespace, name):
        # https://github.com/ansible/galaxy_ng/blob/master/galaxy_ng/tests/integration/api/test_collection_delete.py#L27
        #resp = api_client(
        #    (f'{api_prefix}/v3/plugin/ansible/content'
        #    f'/published/collections/index/{cnamespace}/{cname}/'),
        #    method='DELETE'
        #)

        # What repos is it in?
        matches = [x.repository for x in self.cvs if x.namespace == namespace and x.name == name]
        matches = sorted(set(matches))

        for repo in matches:
            if self.ac.repo_collection_is_deleted(repo, namespace, name):
                logger.info('SKIPPING: ALREADY DELETED')
                continue

            logger.info(f'DELETE {namespace}.{name} FROM {repo} ...')
            try:
                self.delete_collection_from_repo(namespace, name, repo)
                self.ac.store_collection_deleted(repo, namespace, name)
                continue
            except CollectionNotFoundException:
                logger.info('SKIPPING: COLLECTION NOT FOUND')
                self.ac.store_collection_deleted(repo, namespace, name)
                continue
            except CollectionDeleteFailedException:
                logger.error('SKIPPING: COLLECTION DELETE FAILED')
            except CollectionDeleteFailedOnDependencyException:
                logger.error('SKIPPING: COLLECTION DELETE FAILED - DEPENDENCIES')

    def delete_collection_from_repo(self, namespace, name, repo):
        # https://github.com/ansible/galaxy_ng/blob/master/galaxy_ng/tests/integration/api/test_collection_delete.py#L27
        #resp = api_client(
        #    (f'{api_prefix}/v3/plugin/ansible/content'
        #    f'/published/collections/index/{cnamespace}/{cname}/'),
        #    method='DELETE'
        #)

        url = (
            self.api_host.rstrip('/')
            + '/api/automation-hub/v3/plugin/ansible/content/'
            + repo
            + '/collections/index/'
            + namespace
            + '/'
            + name
            + '/'
        )

        rr = self.client.get(url, usecache=False)
        if rr.status_code != 200:
            logger.error(rr.text)
            if rr.status_code == 404:
                raise CollectionNotFoundException()

        rr = self.client.delete(url, usecache=False)
        try:
            ds = rr.json()
        except requests.exceptions.JSONDecodeError:
            import epdb; epdb.st()

        if 'task' not in ds:
            if 'require it' in ds.get('detail', ''):
                raise CollectionDeleteFailedOnDependencyException()

            import epdb; epdb.st()

        task_url = self.api_host.rstrip('/') + ds['task']
        res = self.wait_for_task(task_url)
        res_ds = res.json()
        if res_ds['state'] != 'completed':
            raise CollectionDeleteFailedException()

        # import epdb; epdb.st()
        return res_ds['state']

    def wait_for_task(self, task_url):
        while True:
            # logger.info(task_url)
            rr = self.client.get(task_url, usecache=False)

            try:
                ds = rr.json()
            except requests.exceptions.JSONDecodeError:
                import epdb; epdb.st()

            if 'state' not in ds:
                import epdb; epdb.st()

            state = ds['state']
            logger.info(f'{task_url} -> {state}')
            if state not in ['waiting', 'running']:
                return rr

            time.sleep(2)
            # import epdb; epdb.st()

        return None



def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['all', 'repositories', 'namespaces', 'collections', 'collection_versions'])
    args = parser.parse_args()

    sc = StageCleaner()
    function_name = 'delete_' + args.action + '_cmd'
    function = getattr(sc, function_name)
    function()


if __name__ == "__main__":
    main()
