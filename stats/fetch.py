#!/usr/bin/env python

import os
import requests
import subprocess


BASEURL = 'http://172.18.0.3'
CACHEDIR = '/data/galaxy.content'


def fetch_collections(next_url):

    collections_cache = os.path.join(CACHEDIR, 'collections')
    if not os.path.exists(collections_cache):
        os.makedirs(collections_cache)

    while next_url:
        rr = requests.get(next_url)
        ds = rr.json()

        next_url = None
        if ds['next_link']:
            next_url = BASEURL + ds['next_link']

        for result in ds['results']:
            print(result['latest_version']['href'])
            lvurl = result['latest_version']['href']
            rr2 = requests.get(lvurl)
            ds2 = rr2.json()
            dl_url = ds2['download_url']

            bn = os.path.basename(dl_url)
            fp = os.path.join(collections_cache, bn)
            if not os.path.exists(fp):
                cmd = f'curl -o {fp} {dl_url}'
                pid = subprocess.run(cmd, shell=True)

            extract = fp.replace('.tar.gz', '')
            if not os.path.exists(extract):
                os.makedirs(extract)
                cmd = f'tar xzvf {fp} -C {extract}'
                pid = subprocess.run(cmd, shell=True)


def fetch_roles(next_url):

    roles_cache = os.path.join(CACHEDIR, 'roles')
    if not os.path.exists(roles_cache):
        os.makedirs(roles_cache)

    while next_url:
        rr = requests.get(next_url)
        ds = rr.json()

        next_url = None
        if ds['next_link']:
            next_url = BASEURL + ds['next_link']

        for result in ds['results']:

            dst = os.path.join(roles_cache, f"{result['github_user']}.{result['name']}")
            print(dst)

            if not os.path.exists(dst):

                git_url = f"https://github.com/{result['github_user']}/{result['github_repo']}/"
                print(git_url)

                if result['github_branch']:
                    cmd = f"git clone {git_url} --branch {result['github_branch']} --single-branch --depth 1 {dst}"
                else:
                    cmd = f"git clone {git_url} --depth 1 {dst}"
                # cmd = 'timeout 30s ' + 'GIT_TERMINAL_PROMPT=0 ' + cmd
                cmd = 'GIT_TERMINAL_PROMPT=0 ' + cmd
                print(cmd)

                cmd = subprocess.run(cmd, shell=True)
                #import epdb; epdb.st()


def main():

    # roles
    fetch_roles(BASEURL + '/api/v1/roles')

    # collections
    fetch_collections(BASEURL + '/api/v2/collections')




if __name__ == "__main__":
    main()
