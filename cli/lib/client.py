import requests
from urllib.parse import urljoin
from urllib.parse import urlparse
from logzero import logger


def safe_url_join(*args):
    parts = [x.strip('/') for x in args]
    return '/'.join(parts)


class GalaxyClient:

    _baseurl = None
    _available_versions = None

    def __init__(self, token=None, server=None):
        self.token = token
        self.server = server
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

    def enumerate_baseurl(self):
        o = urlparse(self.server)

        baseurl = o.scheme + '://' + o.netloc + '/api/'
        rr = requests.get(baseurl, headers=self.auth_headers)

        ds = None
        try:
            ds = rr.json()
        except Exception as e:
            pass

        if rr.status_code == 200 and ds and 'available_versions' in ds:
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
        rr = requests.post(url, json=payload, headers=self.auth_headers)
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
