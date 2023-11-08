import glob
import os
import json
import uuid
import requests

from logzero import logger


class Cacher:
    def __init__(self):
        self.cachedir = '.cache'
        if not os.path.exists(self.cachedir):
            os.makedirs(self.cachedir)

        self.cmap = {}
        cachefiles = glob.glob(f'{self.cachedir}/*.json')
        for cachefile in cachefiles:
            with open(cachefile, 'r') as f:
                ds = json.loads(f.read())
            self.cmap[ds['url']] = cachefile

    def store(self, url, data):
        fn = os.path.join(self.cachedir, str(uuid.uuid4()) + '.json')
        with open(fn, 'w') as f:
            f.write(json.dumps({'url': url, 'data': data}))
        self.cmap[url] = fn

    def get(self, url):

        if url in self.cmap:
            with open(self.cmap[url], 'r') as f:
                ds = json.loads(f.read())
            return ds['data']

        logger.info(f'cacher.get {url}')
        rr = requests.get(url)
        ds = rr.json()
        self.store(url, ds)
        return ds

    def wipe_server(self, baseurl):
        keys = sorted(list(self.cmap.keys()))
        keys = [x for x in keys if x.startswith(baseurl)]

        for key in keys:
            logger.warning(f'DELETE CACHE {key}')
            os.remove(self.cmap[key])
            self.cmap.pop(key, None)
            #import epdb; epdb.st()
