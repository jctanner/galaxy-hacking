#!/usr/bin/env python3

import datetime
import glob
import json
import os
import shutil
import subprocess


def hash_string(text):
    pid = subprocess.run(f"go run hasher2.go '{text}'", shell=True, stdout=subprocess.PIPE)
    hashed = pid.stdout.decode('utf-8').strip()
    return hashed


def main():

    hmap = {}

    filenames = glob.glob('.cache.bak/*/*.json')
    for fn in filenames:

        print('')
        print(fn)
        with open(fn, 'r') as f:
            ds = json.loads(f.read())

        # url to hash ... ?
        print(ds['Url'])
        hashed = hash_string(ds['Url'])
        if hashed in hmap:
            import epdb; epdb.st()
        hmap[hashed] = ds['Url']

        # filename to write
        prefix = hashed[0:3]
        newfn = os.path.join('.cache', prefix, hashed + '.json')
        print(newfn)

        if os.path.exists(newfn):
            continue

        '''
        # headers[Date] -> isoformat
        # Thu, 28 Jul 2022 22:27:30 GMT
        ts = ds['headers']['Date']
        ts = datetime.datetime.strptime(ts, '%a, %d %b %Y %H:%M:%S GMT')
        ts = ts.isoformat() + '-04:00'

        newds = {
            'Code': ds['status_code'],
            'Url': ds['url'],
            'Headers': json.dumps(ds['headers']),
            'Body': ds['text'],
            'Fetched': ts

        }
        '''

        if os.path.exists(newfn):
            continue

        if not os.path.exists(os.path.dirname(newfn)):
            os.makedirs(os.path.dirname(newfn))

        '''
        with open(newfn, 'w') as f:
            f.write(json.dumps(newds, indent=2))
        '''

        shutil.copy(fn, newfn)

        #import epdb; epdb.st()


if __name__ == "__main__":
    main()
