#!/usr/bin/env python

import json

import pandas as pd
import matplotlib.pyplot as plt


def summarize_result_to_numerical_dict(result):
    ds = {
        'duration': result['duration_seconds'],
        'repository_count': result['repo_count'],
        'collection_version_count': result['cvs_count'],
        'namespace': -1,
        'name': -1,
        'version': -1
    }
    if 'signed' in result['url']:
        ds['signed'] = 1
    else:
        ds['signed'] = -1
    if '?' in result['url']:
        ds['params'] = 1
    else:
        ds['params'] = -1

    url = result['url']
    if '?namespace=' in url:
        ds['namespace'] = 1
    if '?name=' in url:
        ds['name'] = 1
    if '?version=' in url:
        ds['version'] = 1

    return ds


def main():
    jfile = 'benchmark_results.json'
    with open(jfile, 'r') as f:
        jdata = json.loads(f.read())

    rows = []
    for x in jdata:
        y = x[1]
        for url,v in y.items():

            if 'pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions' not in url:
                continue

            ds = summarize_result_to_numerical_dict(v)
            rows.append(ds)

    #rows = sorted(rows, key=lambda x: (x['duration'], x['collection_version_count']))
    rows = sorted(rows, key=lambda x: (x['collection_version_count'], x['repository_count']))

    df = pd.DataFrame.from_records(rows)
    #df = df.sort_values(by=['duration', 'collection_version_count'])
    #import epdb; epdb.st()
    print(df.corr())

    print('-' * 50)

    corr_mat = df.corr(method='pearson')
    sorted_mat = corr_mat.unstack().sort_values()
    print(sorted_mat['duration'])

    df.plot(subplots=True)
    plt.show()
    import epdb; epdb.st()


if __name__ == "__main__":
    main()
