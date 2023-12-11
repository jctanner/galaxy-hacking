#!/usr/bin/env python

import json
import os
import glob
import subprocess


def compile_galaxy_namespaces():
    basedir = '.cache/galaxy_namespaces/'

    by_id = {}
    by_name = {}

    jfiles = glob.glob(f'{basedir}/*.json')

    for jfile in jfiles:
        with open(jfile, 'r') as f:
            ds = json.loads(f.read())

        if ds.get('results'):
            ns = ds['results'][0]
            by_id[ns['id']] = ns
            by_name[ns['name']] = ns

    # write raw
    ds = {'by_id': by_id, 'by_name': by_name}
    with open('galaxy_namespaces.json', 'w') as f:
        f.write(json.dumps(ds))

    # gzip it
    if os.path.exists('galaxy_namespaces.json' + '.gz'):
        os.remove('galaxy_namespaces.json' + '.gz')
    pid = subprocess.run('gzip galaxy_namespaces.json', shell=True)
    assert pid.returncode == 0


def compile_galaxy_users():
    basedir = '.cache/galaxy_users/'

    by_id = {}
    by_name = {}

    jfiles = glob.glob(f'{basedir}/*.json')

    for jfile in jfiles:
        with open(jfile, 'r') as f:
            ds = json.loads(f.read())

        by_id[ds['id']] = ds
        by_name[ds['username']] = ds

    # write raw
    ds = {'by_id': by_id, 'by_name': by_name}
    with open('galaxy_users.json', 'w') as f:
        f.write(json.dumps(ds))

    # gzip it
    if os.path.exists('galaxy_users.json' + '.gz'):
        os.remove('galaxy_users.json' + '.gz')
    pid = subprocess.run('gzip galaxy_users.json', shell=True)
    assert pid.returncode == 0


def compile_github_users():
    basedir = '.cache/github_users/'

    by_id = {}
    by_name = {}

    for dn in ['by_id', 'by_name']:
        path = os.path.join(basedir, dn)
        jfiles = glob.glob(f'{path}/*.json')

        for jfile in jfiles:
            with open(jfile, 'r') as f:
                ds = json.loads(f.read())

            filename_login = None
            if dn == 'by_name':
                filename_login = os.path.basename(jfile).replace('.json', '')

            if 'id' not in ds or ds.get('message') == 'Not Found':
                if not filename_login:
                    continue

                by_name[filename_login] = None
                continue

            uid = ds['id']
            login = ds['login']
            by_id[uid] = ds

            if dn == 'by_name':
                pass

    # write raw
    ds = {'by_id': by_id, 'by_name': by_name}
    with open('github_users.json', 'w') as f:
        f.write(json.dumps(ds))

    # gzip it
    if os.path.exists('github_users.json' + '.gz'):
        os.remove('github_users.json' + '.gz')
    pid = subprocess.run('gzip github_users.json', shell=True)
    assert pid.returncode == 0


def main():
    compile_galaxy_namespaces()
    compile_galaxy_users()
    compile_github_users()


if __name__ == "__main__":
    main()
