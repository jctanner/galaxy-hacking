#!/usr/bin/env python3

import datetime
import glob
import json
import os
import subprocess


def hash_string(text):
    pid = subprocess.run(f"go run hasher.go '{text}'", shell=True, stdout=subprocess.PIPE)
    hashed = pid.stdout.decode('utf-8').strip()
    return hashed


def main():

    hmap = {}

    filenames = glob.glob('data.old/*/*.json')
    for fn in filenames:

        print(fn)
        with open(fn, 'r') as f:
            ds = json.loads(f.read())

        # headers[Date] -> isoformat
        # Thu, 28 Jul 2022 22:27:30 GMT
        ts = ds['headers']['Date']
        ts = datetime.datetime.strptime(ts, '%a, %d %b %Y %H:%M:%S GMT')
        ts = ts.isoformat() + '-04:00'

        # url to hash ... ?
        print(ds['url'])
        hashed = hash_string(ds['url'])
        if hashed in hmap:
            import epdb; epdb.st()
        hmap[hashed] = ds['url']

        # filename to write
        prefix = hashed[0:3]
        newfn = os.path.join('.cache', prefix, hashed + '.json')
        print(newfn)

        newds = {
            'Code': ds['status_code'],
            'Url': ds['url'],
            'Headers': json.dumps(ds['headers']),
            'Body': ds['text'],
            'Fetched': ts

        }

        if os.path.exists(newfn):
            continue

        if not os.path.exists(os.path.dirname(newfn)):
            os.makedirs(os.path.dirname(newfn))

        with open(newfn, 'w') as f:
            f.write(json.dumps(newds, indent=2))

        #import epdb; epdb.st()


if __name__ == "__main__":
    main()
