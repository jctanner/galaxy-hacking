#!/usr/bin/env python

import glob
import json
import os


def main():

    umap = {}

    fns = glob.glob(f'.cache/github_users/by_id/*.json')
    for fn in fns:
        with open(fn, 'r') as f:
            ds = json.loads(f.read())
        if ds.get('message'):
            # import epdb; epdb.st()
            continue
        umap[ds['login']] = ds['id']

    with open('verified_users.json', 'w') as f:
        f.write(json.dumps(umap, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
