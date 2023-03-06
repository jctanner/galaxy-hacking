#!/usr/bin/env python

import requests
import requests_cache
from logzero import logger

requests_cache.install_cache('/tmp/beta_cache')


"""
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/
api_1          | 172.23.0.1 - - [23/Feb/2023:17:41:25 +0000] "GET /api/automation-hub/_ui/v1/remotes/?tab=remote&offset=0&limit=10 HTTP/1.1" 200 2971 "http://localhost:8002/ui/repositories/?page_size=10&tab=remote" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"                                                                                                                                                                                                                            worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/all/
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/excludes/
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/?limit=100&offset=0
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/?limit=100&offset=100
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/yukta2000/default
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/rucdev/ix
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/tobias_flitsch/my_collection
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/rgroux/mirror
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/ddorgan/node_role
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/planeta/experiments
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/vishnukiranreddy4/war_deploy_collection
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/tobias_flitsch/my_collection/versions/?limit=100&offset=0
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/nitzmahtest/blah
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/validationsframework/operators_validations
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/vishnukiranreddy4/war_deploy_collection/versions/?limit=100&offset=0
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/rucdev/ix/versions/?limit=100&offset=0
api_1          | 172.23.0.1 - - [23/Feb/2023:17:41:28 +0000] "GET /api/automation-hub/_ui/v1/feature-flags/ HTTP/1.1" 200 581 "http://localhost:8002/ui/tasks/" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"      api_1          | 172.23.0.1 - - [23/Feb/2023:17:41:28 +0000] "GET /api/automation-hub/_ui/v1/me/ HTTP/1.1" 200 8800 "http://localhost:8002/ui/tasks/" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/ddorgan/node_role/versions/?limit=100&offset=0
api_1          | 172.23.0.1 - - [23/Feb/2023:17:41:28 +0000] "GET /api/automation-hub/_ui/v1/settings/ HTTP/1.1" 200 563 "http://localhost:8002/ui/tasks/" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"           worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/planeta/experiments/versions/?limit=100&offset=0
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/?limit=100&offset=200                                                                                      api_1          | 172.23.0.1 - - [23/Feb/2023:17:41:28 +0000] "GET /api/automation-hub/pulp/api/v3/tasks/?ordering=-pulp_created&offset=0&limit=10 HTTP/1.1" 200 10947 "http://localhost:8002/ui/tasks/" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/validationsframework/operators_validations/versions/?limit=100&offset=0
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/nitzmahtest/blah/versions/?limit=100&offset=0
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/rgroux/mirror/versions/?limit=100&offset=0
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/yukta2000/default/versions/?limit=100&offset=0
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/jheddings/github
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/tosin2013/qubinode_kvmhost_setup_collection
worker_1       | DOWNLOADER _RUN self.session:<aiohttp.client.ClientSession object at 0x7fdc3807e0a0> self.url:https://beta-galaxy.ansible.com/api/v3/collections/anisf/system


https://beta-galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/index/oracleansible/collections/
"""


def main():

    found_collections = []
    failed_urls = []

    _baseurl = 'https://beta-galaxy.ansible.com'
    baseurl = 'https://beta-galaxy.ansible.com/api/'
    collections_url = baseurl + 'v3/collections/all/'
    collections_url = baseurl + 'v3/collections/?limit=100&offset=0'

    next_collections_url = collections_url
    while next_collections_url:

        logger.info(next_collections_url)
        rr = requests.get(next_collections_url)
        logger.info(rr.status_code)
        cresp = rr.json()

        if cresp['links']['next'] is None:
            break

        total_collections = cresp['meta']['count']

        collections = cresp['data']
        for collection in collections:
            # https://beta-galaxy.ansible.com/api/v3/collections/yukta2000/default
            namespace = collection['namespace']
            name = collection['name']

            found_collections.append((namespace, name))

            collection_url = baseurl + f'v3/collections/{namespace}/{name}'
            logger.info(str(total_collections) + '|' + str(len(found_collections)) + '\t' + collection_url)
            crr = requests.get(collection_url)
            logger.info(str(total_collections) + '|' + str(len(found_collections)) +'\t' + str(crr.status_code))
            #if crr.status_code == 404:
            #    import epdb; epdb.st()

            collection_resp = crr.json()

            #index_url = _baseurl + collection_resp['href']
            index_url = _baseurl + collection['href']

            logger.info(str(total_collections) + '|' + str(len(found_collections)) +'\t' + index_url)
            irr = requests.get(index_url)
            logger.info(str(total_collections) + '|' + str(len(found_collections)) +'\t' + str(irr.status_code))

            if crr.status_code == 404:
                failed_urls.append([collection_url, crr.status_code])

            if irr.status_code == 404:
                failed_urls.append([index_url, irr.status_code])

            if namespace == 'oracle':
                import epdb; epdb.st()

            '''
            next_versions_url = collection_url + '/versions/?limit=100&offset=0'
            while next_versions_url:
                logger.info('\t\t' + next_versions_url)
                vrr = requests.get(next_versions_url)
                logger.info('\t\t' + str(vrr.status_code))
                vresp = vrr.json()
                if vresp['links']['next'] is None:
                    break
                next_versions_url = _baseur + vresp['links']['next']
            '''

            #import epdb; epdb.st()

        if cresp['links']['next'] is None:
            break

        next_collections_url = _baseurl + cresp['links']['next']

    import epdb; epdb.st()


if __name__ == "__main__":
    main()
