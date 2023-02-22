#!/usr/bin/env python


import time
import requests
from logzero import logger


class Client:
    def __init__(self, baseurl, username, password):
        self.baseurl = baseurl
        self.username = username
        self.password = password

        self.remotes_url = baseurl + '/pulp/api/v3/remotes/ansible/collection/'
        self.distros_url = baseurl + '/pulp/api/v3/distributions/ansible/ansible/'
        self.repos_url = baseurl + '/pulp/api/v3/repositories/ansible/ansible/'

    def get_remotes(self):
        repos = {}
        next_url = self.remotes_url
        while next_url:
            rr = requests.get(next_url, auth=(self.username, self.password))
            ds = rr.json()
            for res in ds['results']:
                repos[res['name']] = res
            next_url = None
            if ds['next']:
                import epdb; epdb.st()
        return repos

    def get_repos(self):
        repos = {}
        next_url = self.repos_url
        while next_url:
            rr = requests.get(next_url, auth=(self.username, self.password))
            ds = rr.json()
            for res in ds['results']:
                repos[res['name']] = res
            next_url = None
            if ds['next']:
                import epdb; epdb.st()
        return repos

    def get_distros(self):
        distros = {}
        next_url = self.distros_url
        while next_url:
            rr = requests.get(next_url, auth=(self.username, self.password))
            ds = rr.json()
            for res in ds['results']:
                distros[res['name']] = res
            next_url = None
            if ds['next']:
                import epdb; epdb.st()
        return distros

    def poll_task(self, task_url):

        state = None
        while state != 'completed':
            rr = requests.get(self.baseurl + task_url, auth=(self.username, self.password))
            ds = rr.json()
            state = ds['state']
            logger.info(state)
            if 'progress_reports' in ds:
                for pr in ds['progress_reports']:
                    logger.info(f"{pr['code']} {pr['state']} {pr['message']}")
            if state == 'completed':
                break
            time.sleep(.5)



def main():

    username = 'admin'
    password = 'password'
    #baseurl = 'http://localhost:5001'
    baseurl = 'http://172.18.0.2'
    #distros_url = base_url + '/pulp/api/v3/distributions/ansible/ansible/'
    #repos_url = base_url + '/pulp/api/v3/repositories/ansible/ansible/'
    repo_name = 'community2'

    client = Client(baseurl, username, password)

    repo_name = 'community3'

    remotes = client.get_remotes()
    repos = client.get_repos()
    distros = client.get_distros()

    # make the repo
    if repo_name not in repos:
        rr_repo = requests.post(client.repos_url, json={'name': repo_name}, auth=(username, password))
        repos = client.get_repos()

    # make the distro
    if repo_name not in distros:
        payload = {
            'base_path': repo_name,
            'name': repo_name,
            'repository': repos[repo_name]['pulp_href']
        }
        rr_distro = requests.post(client.distros_url, json=payload, auth=(username, password))
        ds = rr_distro.json()
        if ds.get('task') is not None:
            task_url = ds['task']
            client.poll_task(task_url)

        distros = client.get_distros()

    # create the remote
    remote_payload = {
        'name': repo_name,
        'rate_limit': 5,
        #'sync_dependencies': False,
        'sync_dependencies': True,
        #'url': 'https://galaxy.ansible.com',
        #'url': 'http://172.24.0.3',
        'url': 'http://172.18.0.3/',
        #'requirements_file': "collections:\n  - name: community.molecule\n    version: 0.1.0",
        #'requirements_file': '',
        'requirements_file': '{"collections":[]}',
    }

    if repo_name not in remotes:
        rr_remote = requests.post(client.remotes_url, json=remote_payload, auth=(username, password))
        assert rr_remote.status_code == 201, f'{rr_remote.status_code} {rr_remote.text}'
    else:
        remote = remotes[repo_name]
        rr = requests.patch(client.baseurl + remote['pulp_href'], json=remote_payload, auth=(username, password))
        assert rr.status_code == 202, f'{rr.status_code} {rr.text}'
        client.poll_task(rr.json()['task'])

    remotes = client.get_remotes()

    # start the sync
    """
    {'mirror': False,
     'optimize': True,
     'remote': '/pulp/api/v3/remotes/ansible/collection/455919af-390d-4c5f-a46e-7ad846bcafa5/'}
    """
    payload = {
        'mirror': False,
        #'optimize': True,
        'remote': remotes[repo_name]['pulp_href']
    }
    sync_url = client.baseurl + repos[repo_name]['pulp_href'] + 'sync/'
    rr = requests.post(sync_url, json=payload, auth=(username, password))
    task_url = rr.json()['task']
    client.poll_task(task_url)

    # wait ...

    import epdb; epdb.st()


if __name__ == "__main__":
    main()
