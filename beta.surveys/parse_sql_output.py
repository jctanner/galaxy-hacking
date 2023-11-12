#!/usr/bin/env python

import sys
import json


def parse_sql(fn):

    column_names = []
    rows = []

    with open(fn, 'r') as f:
        raw = f.read()
    lines = raw.split('\n')

    column_names = lines[0].split('|')
    column_names = [x.strip() for x in column_names if x.strip()]
    #import epdb; epdb.st()

    for line in lines[1:]:
        if line.startswith('-'):
            continue
        if not line.strip():
            continue
        if 'rows)' in line:
            continue

        #print(line)

        values = line.split('|', len(column_names) - 1)
        values = [x.strip() for x in values]

        row = {}
        for idx,x in enumerate(column_names):
            try:
                row[x] = values[idx]
            except IndexError:
                pass
        rows.append(row)

    #import epdb; epdb.st()
    return rows



def main():

    fn = sys.argv[1]
    rows = parse_sql(fn)
    print(json.dumps(rows, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
