#!/usr/bin/env python

import json
import datetime
import subprocess


def main():

    results = []

    for x in range(0, 100):
        cmd = 'HUB_LOCAL=1 ./dev/common/RUN_INTEGRATION.sh'
        #cmd = 'whoami'
        t0 = datetime.datetime.now()
        pid = subprocess.run(cmd, shell=True)
        t1 = datetime.datetime.now()

        delta = (t1 - t0).seconds
        rc = pid.returncode

        results.append([rc, delta])

        with open('test_results.json', 'w') as f:
            f.write(json.dumps(results, indent=2))

        if rc != 0:
            import epdb; epdb.st()



if __name__ == "__main__":
    main()
