#!/usr/bin/env python

from pprint import pprint
from utils import *


def main():

    packages = []

    with open('packages.txt', 'a') as f:

        count = 0
        for taskmeta in find_tasks():
            count += 1

            pts = extract_package_tasks(taskmeta)

            if pts:
                for pt in pts:
                    if pt.module not in ['yum', 'dnf', 'package']:
                        continue
                    for package_name in pt.packages:
                        if package_name is None:
                            continue
                        if isinstance(package_name, (int, float)):
                            continue
                        if len(package_name) == 1:
                            continue
                        if isinstance(package_name, dict):
                            import epdb; epdb.st()
                        f.write(package_name + '\n')

    import epdb; epdb.st()


if __name__ == "__main__":
    main()
