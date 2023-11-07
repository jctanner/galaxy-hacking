#!/usr/bin/env python

import os
import json
import glob


def main():

    umap = {}

    fns = glob.glob('.cache/namespaces/*.json')
    for fn in fns:
        with open(fn, 'r') as f:
            ds = json.loads(f.read())
        print(ds)
        for owner in ds['owners']:
            guser = owner['galaxy_username']
            if guser not in umap:
                umap[guser] = {
                    'github_id': None,
                    'github_login': None,
                    'aliases': [],
                    'namespaces': []
                }

                # find the cached user info ...
                import epdb; epdb.st()

            umap[guser]['namespaces'].append(ds['namespace'])

    with open('ownership_by_user.json', 'w') as f:
        f.write(json.dumps(umap, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
