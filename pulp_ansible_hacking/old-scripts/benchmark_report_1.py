#!/usr/bin/env python

import statistics
import pandas as pd
import matplotlib.pyplot as plt


def fill_forward(rows, colname):

    for idr, row in enumerate(rows):
        for k,v in row.items():
            if isinstance(v, (int, float)):
                continue
            if v == 'None':
                rows[idr][k] = None
            elif v and v.isdigit() and not '.' in v:
                rows[idr][k] = int(v)
                continue
            if k == 'duration':
                rows[idr][k] = float(v)

    last_val = None
    for idr,row in enumerate(rows):
        if row.get(colname):
            last_val = row[colname]
            continue
        if not row.get(colname) and last_val:
            rows[idr][colname] = last_val

    return rows


def main():
    fn = 'benchmark.log'
    with open(fn, 'r') as f:
        fdata = f.read()
    lines = fdata.split('\n')

    rows = []
    for line in lines:
        row = line.split(',')
        if len(row) < 2:
            continue
        ds = {
            'time': row[0],
            'collections': row[1],
            'collection_versions': row[2],
            'duration': row[3],
            'info': row[4]
        }
        rows.append(ds)

    # info_keys = sorted(set([x['info'] for x in rows]))

    #uploads = [x for x in rows if x['info'] == 'UPLOAD']
    #for x in uploads:
    #    print(x['duration'])

    rows = fill_forward(rows, 'collections')
    rows = fill_forward(rows, 'collection_versions')

    keys = []
    dsmap = {}
    for row in rows:
        if row['collections'] and row['collection_versions']:
            key = (row['collections'], row['collection_versions'])
            if key not in keys:
                keys.append(key)
            if key not in dsmap:
                dsmap[key] = {
                    'time': row['time'],
                    'collections': row['collections'],
                    'collection_versions': row['collection_versions']
                }
            tag = row['info']
            if tag not in dsmap[key]:
                dsmap[key][tag] = []
            dsmap[key][tag].append(row['duration'])

    for k,v in dsmap.items():
        for tag, tag_values in v.items():
            if tag in ['collections', 'collection_versions', 'time']:
                continue
            if len(tag_values) == 1:
                dsmap[k][tag] = tag_values[0]
            else:
                dsmap[k][tag] = statistics.mean(tag_values)

    df = pd.DataFrame.from_records(list(dsmap.values()))
    #df = df.sort_values(by=['collections', 'collection_versions'])
    #df = df.sort_values(by=['collections', 'collection_versions'])

    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values(by=['time'])
    df = df.set_index('time')

    df = df.ffill(axis = 0)
    df.plot(subplots=True)
    plt.show()



if __name__ == "__main__":
    main()
