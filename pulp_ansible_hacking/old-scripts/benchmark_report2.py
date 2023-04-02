#!/usr/bin/env python

import copy
import os
import json
import statistics
import pandas as pd
import matplotlib.pyplot as plt
from pprint import pprint


def fill_forward(rows, colname):

    for idr, row in enumerate(rows):
        if colname not in row:
            rows[idr][colname] = None

    for idr, row in enumerate(rows):
        for k,v in row.items():
            if isinstance(v, (int, float)):
                continue
            if v == 'None':
                rows[idr][k] = None
            elif v and v.isdigit() and not '.' in v:
                rows[idr][k] = int(v)
                continue
            if k == 'duration' and v:
                rows[idr][k] = float(v)

    last_val = None
    for idr,row in enumerate(rows):
        if row.get(colname):
            last_val = row[colname]
            continue
        if not row.get(colname) and last_val:
            rows[idr][colname] = last_val

    return rows


def summarize_command(cmd, pid=None):
    parts = cmd.split()
    parts[0] = os.path.basename(parts[0].replace(':', ''))

    if len(parts) < 2:
        #import epdb; epdb.st()
        return None

    if parts[0] == 's6-svscan':
        return None
    if parts[0] == 's6-supervise':
        return None
    if parts[0] == 's6-linux-init-shutdownd':
        return None
    if parts[0] == 's6-ipcserverd':
        return None

    if parts[0] == 'redis-server':
        return 'redis-server'
    if parts[0] == 'postgres' and parts[1] == '-D':
        return 'postgresd'
    if parts[0] == 'postgres':
        return 'postgresd-' + parts[1] + "-" + str(pid)
    if parts[0] == 'nginx':
        return 'nginx-' + parts[1] + "-" + str(pid)
    if parts[0] == 'gunicorn':
        if len(parts) >= 4:
            return 'gunicorn-' + parts[1] + '-' + parts[2] + '-' + parts[3]
        else:
            return 'gunicorn-' + parts[1] + '-' + parts[2]
    if 'pulpcore-worker' in parts[1]:
        # return 'pulpcore-worker-' + str(pid)
        return 'pulpcore-worker'

    return cmd


def group_stats_by_time(stats_rows):
    tmap = {}
    for sr in stats_rows:
        ts = sr['time']
        if ts not in tmap:
            tmap[ts] = {}
        for k,v in sr.items():
            tmap[ts][k] = v
    newdata = list(tmap.values())
    newdata = sorted(newdata, key=lambda x: x['time'])
    #import epdb; epdb.st()
    return newdata


def main():

    '''
    fn = 'benchmark_stats.log'
    with open(fn, 'r') as f:
        fdata = f.read()
    stat_rows = []
    for line in fdata.split('\n'):
        if not line.strip():
            continue
        parts = line.split(',', 2)
        try:
            stats = json.loads(parts[-1])
        except json.decoder.JSONDecodeError:
            import epdb; epdb.st()

        if 'COMMAND' in stats:

            if stats['COMMAND'] == 'COMMAND':
                continue

            #stats['time'] = parts[0]
            #stats['duration'] = None
            #stats['collections'] = None
            #stats['collection_versions'] = None
            #stats['info'] = parts[1]

            prefix = summarize_command(stats['COMMAND'], pid=stats['PID'])
            if not prefix:
                continue

            for key in ['PID', 'START', 'STAT', 'TIME', 'TTY', 'USER', 'COMMAND']:
                if key in stats:
                    stats.pop(key, None)

            ds = {}
            for k,v in stats.items():
                if '%' in k:
                    ds[prefix+"_"+k] = float(v)
                else:
                    ds[prefix+"_"+k] = int(v)

            ds['time'] = parts[0]
            stat_rows.append(ds)

    stats_data = group_stats_by_time(stat_rows)
    stats_df = pd.DataFrame.from_records(stats_data)
    stats_df['time'] = pd.to_datetime(stats_df['time'])
    stats_df = stats_df.sort_values(by=['time'])
    stats_df = stats_df.set_index('time')
    stats_df = stats_df.ffill(axis = 0)
    '''

    fn = 'logs/benchmark.log'
    with open(fn, 'r') as f:
        fdata = f.read()
    lines = fdata.split('\n')

    docker_stat_rows = []
    rows = []
    for line in lines:
        #if 'CSTATS' in line:
        #    continue

        if 'CSTATS' in line:
            row = line.split(',', 2)
            try:
                data = json.loads(row[-1])
            except json.decoder.JSONDecodeError:
                continue
            ds = {'time': row[0]}
            ds['docker_CPUPerc'] = float(data['CPUPerc'].replace('%', ''))
            ds['docker_MemPerc'] = float(data['MemPerc'].replace('%', ''))
            mem_usage = data['MemUsage'].split('/')[0].strip()
            if 'MiB' not in mem_usage:
                import epdb; epdb.st()
            else:
                ds['docker_MemUsage'] = float(mem_usage.replace('MiB', ''))
            #ds['info'] = 'docker_stats'
            #ds['duration'] = None
            docker_stat_rows.append(ds)

        else:
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
            tag_values = [x for x in tag_values if x]
            if len(tag_values) == 0:
                dsmap[k][tag] = None
            elif len(tag_values) == 1:
                dsmap[k][tag] = tag_values[0]
            else:
                dsmap[k][tag] = statistics.mean(tag_values)

    # df = pd.DataFrame.from_records(list(dsmap.values()))

    '''
    stats_data_clean = []
    for idx,x in enumerate(stats_data):
        for k,v in copy.deepcopy(x).items():
            if k == 'time':
                continue
            if '%MEM' not in k and '%CPU' not in k:
                x.pop(k, None)
                continue
            if 'worker' not in k and 'api' not in k and 'content' not in k:
                x.pop(k, None)
                continue
        stats_data_clean.append(x)
        #import epdb; epdb.st()
    '''

    #df = pd.DataFrame.from_records(list(dsmap.values()) + docker_stat_rows + stats_data_clean)
    df = pd.DataFrame.from_records(list(dsmap.values()) + docker_stat_rows)

    #df = df.sort_values(by=['collections', 'collection_versions'])
    #df = df.sort_values(by=['collections', 'collection_versions'])

    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values(by=['time'])
    df = df.set_index('time')
    df = df.ffill(axis = 0)

    #merged = pd.concat([df, stats_df], join='inner')
    #merged = pd.concat([df, stats_df], join='outer')
    #merged = merged.ffill(axis = 0)

    #other_colnames = [x for x in stats_df.columns if 'worker' in x and '%MEM' in x]
    #for colname in other_colnames:
    #    df[colname] = stats_df[colname]
    #    df = pd.concat([df, stats_df[colname]])
    #df = df.ffill(axis = 0)
    #import epdb; epdb.st()

    #subplots = df.plot(subplots=True, legend=True)

    colgroups = [('collections', 'collection_versions')]
    if 'SYNC' in [x for x in df.columns]:
        colgroups.append(('SYNC',))

    bgroup = []
    for x in [x for x in df.columns]:
        if x in ['collections', 'collection_versions', 'SYNC']:
            continue
        #if x.startswith('ALL_'):
        #    continue
        if x[0] == x[0].upper():
            bgroup.append(x)
    colgroups.append(bgroup)

    '''
    mgroup = []
    for x in [x for x in df.columns]:
        if '%MEM' in x:
            mgroup.append(x)
    colgroups.append(mgroup)

    cgroup = []
    for x in [x for x in df.columns]:
        if '%CPU' in x:
            cgroup.append(x)
    colgroups.append(cgroup)
    '''

    subplots = df.plot(subplots=colgroups, legend=True)
    for sp in subplots:
        sp.legend(loc='upper left')

    #import epdb; epdb.st()

    #merged.plot(subplots=True)
    #merged[['collections', 'collection_versions']].plot()


    plt.show()



if __name__ == "__main__":
    main()
