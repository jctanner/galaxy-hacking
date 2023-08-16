import requests
import subprocess
import time

from pprint import pprint
from urllib.parse import urljoin
from urllib.parse import urlparse
from logzero import logger


def safe_url_join(*args):
    parts = [x.strip('/') for x in args]
    return '/'.join(parts)


def get_sha256(filepath):
    pid = subprocess.run(f'sha256sum {filepath}', shell=True, stdout=subprocess.PIPE)
    checksum = pid.stdout.decode('utf-8').split()[0].strip()
    return checksum


class GalaxyClient:

    _baseurl = None
    _available_versions = None

    def __init__(self, token=None, username=None, password=None, server=None, prefix=None):
        self.token = token
        self.server = server or 'http://localhost:5001/'
        self.prefix = prefix or '/api/automation-hub/'

        if not self.token:
            self.username = username or 'iqe_admin'
            self.password = password or 'redhat'

        self.enumerate_baseurl()

    @property
    def available_versions(self):
        return self._available_versions

    @property
    def baseurl(self):
        return self._baseurl

    @property
    def auth_headers(self):
        return {'Authorization': f'token {self.token}'}

    @property
    def auth_kwargs(self):
        if self.token:
            return {'headers': self.auth_headers}
        return {'auth': (self.username, self.password)}

    def enumerate_baseurl(self):
        o = urlparse(self.server)

        if self.prefix:
            prefixes = [self.prefix]
        else:
            prefixes = ['/api/', '/api/galaxy', '/api/automation-hub/']

        for prefix in prefixes:

            baseurl = o.scheme + '://' + o.netloc + prefix

            #rr = requests.get(baseurl, headers=self.auth_headers)
            rr = requests.get(baseurl, **self.auth_kwargs)

            ds = None
            try:
                ds = rr.json()
            except Exception as e:
                pass

            if rr.status_code == 200 and ds and 'available_versions' in ds:
                self.prefix = prefix
                self._baseurl = baseurl
                self._available_versions = list(ds['available_versions'].keys())
                return

        import epdb; epdb.st()

    def namespaces_create(self, name=None):
        payload = {
            'name': name,
            'groups': []
        }
        url = safe_url_join(self.baseurl, 'v3', 'namespaces').rstrip('/') + '/'
        kwargs = self.auth_kwargs
        kwargs['json'] = payload
        rr = requests.post(url, **kwargs)
        print(rr.text)

    def namespaces_list(self):

        nsmap = {}

        for version in ['v1', 'v2', 'v3']:
            if version not in self.available_versions:
                continue
            nsmap[version] = []
            url = safe_url_join(self.baseurl, version, 'namespaces').rstrip('/') + '/'
            while url:
                logger.info(f'GET {url}')
                rr = requests.get(url, headers=self.auth_headers)
                # print(rr.text)
                ds = rr.json()
                if 'results' not in ds:
                    nsmap[version].extend(ds['data'])
                    url = ds['links']['next']
                    if url:
                        url = safe_url_join(self.baseurl, url)
                else:
                    nsmap[version].extend(ds['results'])
                    url = ds.get('next')

        for version, namespaces in nsmap.items():
            names = sorted([x['name'] for x in namespaces])
            for name in names:
                print(f'{version} {name}')

    def roles_list(self, name=None):
        import epdb; epdb.st()

    def collections_list(self, filepath=None):

        o = urlparse(self.server)

        next_url = safe_url_join(self.baseurl, 'v3', 'plugin', 'ansible', 'search', 'collection-versions') + '/'
        while next_url:
            rr = requests.get(next_url, **self.auth_kwargs)
            for res in rr.json()['data']:
                pulp_id = res['collection_version']['pulp_href'].split('/')[-2]
                print(
                    pulp_id + "/"
                    + f"{res['repository']['name']}/"
                    + f"{res['collection_version']['namespace']}/"
                    + f"{res['collection_version']['name']}/"
                    + f"{res['collection_version']['version']}/"
                )
            next_url = None
            if rr.json()['links']['next']:
                next_url = o.scheme + '://' + o.netloc + rr.json()['links']['next']

    def collections_upload(self, filepath=None):

        url = safe_url_join(self.baseurl, 'v3', 'artifacts', 'collections') + '/'

        kwargs = self.auth_kwargs
        kwargs['files'] = {'file': open(filepath, 'rb')}
        kwargs['data'] = {'sha256': get_sha256(filepath)}

        rr = requests.post(url, **kwargs)
        if rr.status_code == 400:
            pprint(rr.json())
            return

        task = rr.json()['task']

        o = urlparse(self.server)
        task_url = o.scheme + '://' + o.netloc + task

        while True:
            time.sleep(.5)
            trr = requests.get(task_url, **self.auth_kwargs)
            tjson = trr.json()
            pprint(tjson)
            if tjson['state'] in ['completed', 'failed', 'error']:
                break
