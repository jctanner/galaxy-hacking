#!/usr/bin/env python

import json
import os
import requests
import subprocess

from pysondb import db as Database


def fetch_and_store(db, cache, baseurl, col, cv_url):
    v_url = baseurl + cv_url
    vrr = requests.get(v_url)
    vds = vrr.json()
    download_url = vds['download_url']
    artifact_fn = os.path.basename(download_url)
    artifact_dst = os.path.join(cache, artifact_fn)

    fqn = f"{col['namespace']}.{col['name']}.{vds['version']}"
    print(f'\t{fqn}')

    locations = []
    if not os.path.exists(artifact_dst):
        cmd = f'curl --no-progress-meter -L -v -o {artifact_dst} {download_url}'
        pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert pid.returncode == 0, pid.stdout.decode('utf-8')

        stdout = pid.stdout.decode('utf-8')
        stdout = stdout.split('\n')
        stdout = [x for x in stdout if '< location:' in x]
        locations = [x.replace('< location:', '').strip() for x in stdout]

    db.add({
        "fqn": fqn,
        "namespace": col['namespace'],
        "name": col['name'],
        "version": vds['version'],
        "download_url": download_url,
        "locations": locations,
        "artifact": artifact_dst,
    })

    info_fn = artifact_dst.replace('.tar.gz', '.json')
    with open(info_fn, 'w') as f:
        f.write(json.dumps(vds))


def main():

    cache = 'cache'
    if not os.path.exists(cache):
        os.makedirs(cache)

    db = Database.getDb("collections.json")

    baseurl = 'https://beta-galaxy-dev.ansible.com'

    col_total = None
    col_count = 0
    next_collections_url = baseurl + '/api/v3/collections/'
    while next_collections_url:
        cols_rr = requests.get(next_collections_url)
        ds = cols_rr.json()
        col_total = ds['meta']['count']

        next_collections_url = None
        if ds['links']['next']:
            next_collections_url = baseurl + ds['links']['next']

        for col in ds['data']:
            col_count += 1
            print(f"{col_total}|{col_count} {col['updated_at']} {col['namespace']} {col['name']}")
            highest_version = col['highest_version']['version']

            fqn = f"{col['namespace']}.{col['name']}.{highest_version}"
            record = db.getByQuery({"fqn": fqn}) or None
            if record:
                record = record[0]

            # skip if this version is already known
            if record:
                continue

            # make sure to get all versions if the highest isn't yet scraped
            next_versions_url = baseurl + col['versions_url']
            while next_versions_url:
                vrr = requests.get(next_versions_url)
                vds = vrr.json()

                next_versions_url = None
                if vds['links']['next']:
                    next_versions_url = baseurl + vds['links']['next']

                for version in vds['data']:
                    fetch_and_store(db, cache, baseurl, col, version['href'])

    db.close()


if __name__ == "__main__":
    main()
