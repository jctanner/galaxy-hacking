#!/usr/bin/env python3

'''
#################################
# DOWNSTREAM 4.2
#################################

resource-manager_1  | pulp: rq.worker:INFO: resource-manager: pulpcore.tasking.tasks._queue_reserved_task(<function sync at 0x7f7a2e122d90>, '8d538d95-d852-4f96-94f8-1f9c63943c82', ['/pulp/api/v3/remotes/ansible/collection/80ae4b6b-bfb9-4831-aa0c-b43d32ce2..., (), {'remote_pk': UUID('80ae4b6b-bfb9-4831-aa0c-b43d32ce2fed'), 'repository_pk'..., {}) (a42067e2-259d-45d8-9203-825a67e7f7dc)
api_1               | 172.18.0.8 - - [27/Apr/2022:18:23:11 +0000] "POST /api/automation-hub/content/rh-certified/v3/sync/ HTTP/1.1" 200 47 "http://192.168.122.22:8002/ui/repositories?page_size=10&tab=remote" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
api_1               | 172.18.0.8 - - [27/Apr/2022:18:23:11 +0000] "GET /api/automation-hub/_ui/v1/remotes/?tab=remote&offset=0&limit=10 HTTP/1.1" 200 2603 "http://192.168.122.22:8002/ui/repositories?page_size=10&tab=remote" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
resource-manager_1  | pulp: rq.worker:INFO: resource-manager: Job OK (a42067e2-259d-45d8-9203-825a67e7f7dc)
worker_1            | pulp: rq.worker:INFO: 1@3278c1f5fe97: pulp_ansible.app.tasks.collections.sync(mirror=True, remote_pk=UUID('80ae4b6b-bfb9-4831-aa0c-b43d32ce2fed'), repository_pk=UUID('7eb27e4f-1847-49a2-ba37-a1c3198f923e')) (8d538d95-d852-4f96-94f8-1f9c63943c82)
worker_1            | pulp: rq.worker:INFO: 1@3278c1f5fe97: Job OK (8d538d95-d852-4f96-94f8-1f9c63943c82)
worker_1            | pulp: rq.worker:INFO: 1@3278c1f5fe97: pulpcore.tasking.tasks._release_resources('8d538d95-d852-4f96-94f8-1f9c63943c82') (87bfda40-2dcd-4cfd-8535-c07ece68ec4a)
worker_1            | pulp: rq.worker:INFO: 1@3278c1f5fe97: Job OK (87bfda40-2dcd-4cfd-8535-c07ece68ec4a)
api_1               | 172.18.0.8 - - [27/Apr/2022:18:23:16 +0000] "GET /api/automation-hub/_ui/v1/remotes/?tab=remote&offset=0&limit=10 HTTP/1.1" 200 2707 "http://192.168.122.22:8002/ui/repositories?page_size=10&tab=remote" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"

#################################
# UPSTREAM HEAD
#################################

api_1          | 172.18.0.8 - - [27/Apr/2022:18:22:09 +0000] "GET /api/automation-hub/ HTTP/1.1" 200 245 "-" "pulpcore/3.7.9 (cpython 3.6.8-final0, Linux x86_64) (aiohttp 3.7.4.post0)"
api_1          | 172.18.0.8 - - [27/Apr/2022:18:22:10 +0000] "GET /api/automation-hub/v3/collections/?offset=0&limit=100 HTTP/1.1" 302 0 "-" "pulpcore/3.7.9 (cpython 3.6.8-final0, Linux x86_64) (aiohttp 3.7.4.post0)"
api_1          | 172.18.0.8 - - [27/Apr/2022:18:22:10 +0000] "GET /api/automation-hub/v3/plugin/ansible/content/published/collections/index/?offset=0&limit=100 HTTP/1.1" 200 275 "-" "pulpcore/3.7.9 (cpython 3.6.8-final0, Linux x86_64) (aiohttp 3.7.4.post0)"
api_1          | 172.18.0.8 - - [27/Apr/2022:18:23:11 +0000] "GET /api/automation-hub/ HTTP/1.1" 200 245 "-" "pulpcore/3.7.9 (cpython 3.6.8-final0, Linux x86_64) (aiohttp 3.7.4.post0)"
api_1          | 172.18.0.8 - - [27/Apr/2022:18:23:12 +0000] "GET /api/automation-hub/v3/collections/?offset=0&limit=100 HTTP/1.1" 302 0 "-" "pulpcore/3.7.9 (cpython 3.6.8-final0, Linux x86_64) (aiohttp 3.7.4.post0)"
api_1          | 172.18.0.8 - - [27/Apr/2022:18:23:12 +0000] "GET /api/automation-hub/v3/plugin/ansible/content/published/collections/index/?offset=0&limit=100 HTTP/1.1" 200 275 "-" "pulpcore/3.7.9 (cpython 3.6.8-final0, Linux x86_64) (aiohttp 3.7.4.post0)"
'''

# 4.2
#   pulp-ansible==0.5.10
# 4.3
#   pulp-ansible==0.7.4
# 4.4
#   pulp-ansible>=0.10.2,<0.11.0

import asyncio
from unittest.mock import MagicMock
from unittest.mock import patch
import sys


def synchronize_async_helper(to_await):

    print('start helper')
    async_response = []

    async def run_and_capture_result():
        print('run and capture result ...')
        r = await to_await
        async_response.append(r)

    print('get event loop')
    loop = asyncio.get_event_loop()

    print('call run and capture result')
    coroutine = run_and_capture_result()

    print('run until complete')
    loop.run_until_complete(coroutine)

    print('return async response')
    return async_response[0]


def main():

    # pulp_ansible.app.tasks.collections.sync(
    #    mirror=True,
    #    remote_pk=UUID('80ae4b6b-bfb9-4831-aa0c-b43d32ce2fed'),
    #    repository_pk=UUID('7eb27e4f-1847-49a2-ba37-a1c3198f923e')
    # ) (8d538d95-d852-4f96-94f8-1f9c63943c82)

    # https://github.com/pulp/pulp_ansible/blob/0.5/pulp_ansible/app/tasks/collections.py#L62
    # from pulp_ansible.app.tasks.collections import sync
    #   from pulpcore.plugin.models import (...

    '''
    class StageMock:
        pass

    stages = MagicMock(name='a-stage')
    #stages.Stage = MagicMock(name='b-stage')
    stages.Stage = StageMock

    #sys.modules['pulpcore.plugin.stages.stage'] = MagicMock(name='pulpcore.plugin.stages.stage')
    sys.modules['pulpcore'] = MagicMock
    sys.modules['pulpcore.plugin'] = MagicMock()
    sys.modules['pulpcore.plugin.models'] = MagicMock(name='pulpcore.plugin.models')
    #sys.modules['pulpcore.plugin.stages.stage'] = MagicMock(name='pulpcore.plugin.stages.stage')
    sys.modules['pulpcore.plugin.stages'] = stages
    #sys.modules['pulpcore.plugin.stages'].stage = MagicMock(name='STAGE!')
    #sys.modules['pulpcore.plugin.stages.Stage'] = MagicMock(name='pulpcore.plugin.stages.Stage', response='foobar')
    #sys.modules['pulpcore.plugin.stages.stage'] = StageMock
    sys.modules['pulpcore.plugin.download'] = MagicMock()
    sys.modules['pulpcore.plugin.serializers'] = MagicMock()

    sys.modules['pulp_ansible.app.serializers'] = MagicMock()
    sys.modules['pulp_ansible.app.models'] = MagicMock(name='pulp_ansible.app.models')
    sys.modules['pulp_ansible.app.models.AnsibleRepository'] = \
        MagicMock(name='pulp_ansible.app.models.AnsibleRepository')
    sys.modules['pulp_ansible.app.models.CollectionRemote'] = \
        MagicMock(name='pulp_ansible.app.models.CollectionRemote')

    #from pulp_ansible.app.tasks.collections import sync
    from pulp_ansible.app.tasks.collections import CollectionSyncFirstStage

    #import epdb; epdb.st()
    #res = sync(mirror=True, remote_pk=None, repository_pk=None)

    remote = MagicMock(name='a-remote')
    #fs = CollectionSyncFirstStage(remote)
    #res = fs._fetch_collections()

    #print('call helper ..')
    #res = synchronize_async_helper(CollectionSyncFirstStage(remote))
    '''


    # for metadata in self._fetch_collections():
    #   async def _fetch_collections(self):
    #       async def _get_collection_api(root):
    #           downloader = remote.get_downloader(url=root)
    #           api_data = parse_metadata(await downloader.run())
    #           self.api_version = 3
    #           endpoint = f"{root}v{self.api_version}/collections/"
    #   with ProgressReport(**progress_data) as progress_bar:
    #       done, not_done = await asyncio.wait(not_done, return_when=asyncio.FIRST_COMPLETED)
    #       for item in done:
    #           data = parse_metadata(item.result())
    #           results = data["data"]
    #           for result in results:
    #               download_url = result.get("download_url")
    #               versions_url = _build_url(result.get("versions_url"))
    #               await _loop_through_pages(not_done, versions_url)
    #               not_done.update([remote.get_downloader(url=version_url).run()])
    #
    # from pulpcore.plugin.download import DownloaderFactory, FileDownloader, HttpDownloader
    # https://github.com/pulp/pulpcore/blob/61c3aa74a367e1808e1fd1848022e060ea9b5deb/pulpcore/app/models/repository.py#L415
    # from pulpcore.download.factory import DownloaderFactory
    # https://github.com/pulp/pulpcore/blob/61c3aa74a367e1808e1fd1848022e060ea9b5deb/pulpcore/download/factory.py#L27

    # async def _run(self, extra_data=None):
    #  https://github.com/pulp/pulpcore/blob/61c3aa74a367e1808e1fd1848022e060ea9b5deb/pulpcore/download/http.py

    sys.modules['pulpcore.downloader.base'] = MagicMock()
    #sys.modules['pulpcore.downloader.base.BaseDownloader'] = MagicMock()
    #sys.modules['pulpcore.downloader.base.DownloadResult'] = MagicMock()
    sys.modules['pulpcore.app.models'] = MagicMock(name='pulpcore.plugin.models')
    sys.modules['pulpcore.app.models.artifact'] = MagicMock(name='pulpcore.plugin.models.Artifact')

    '''
    #from pulpcore.downloader.base import BaseDownloder
    from pulpcore.download import DownloaderFactory
    remote = MagicMock(name='a-remote')
    remote.ca_cert = ''
    remote.client_key = ''
    remote.download_concurrency = 1
    df = DownloaderFactory(remote)
    '''

    from pulpcore.download import HttpDownloader

    '''
    def __init__(
        self,
        url,
        session=None,
        auth=None,
        proxy=None,
        proxy_auth=None,
        headers_ready_callback=None,
        headers=None,
        throttler=None,
        max_retries=0,
        **kwargs,
    ):
    '''

    httpd = HttpDownloader(
        url,
        session=None,
        auth=None,
        proxy=None,
        proxy_auth=None,
        headers_ready_callback=None,
        headers=None,
        throttler=None,
        max_retries=0
    )

    import epdb; epdb.st()


if __name__ == "__main__":
    main()
