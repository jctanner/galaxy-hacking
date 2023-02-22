#!/usr/bin/env python3

import argparse
import datetime
import glob
import json
import os
import random
import shutil
import subprocess
import tempfile
import time
import yaml

import requests
from logzero import logger
# from random_word import RandomWords


BASEURL = 'http://localhost:5001'
AUTH = ('admin', 'password')
ANSIBLE_DISTRIBUTION_PATH = '/pulp/api/v3/distributions/ansible/ansible/'
ANSIBLE_REPO_PATH = '/pulp/api/v3/repositories/ansible/ansible/'



def copy_file_to_conainer(container_name, src, dst):
    cmd = f'docker cp {src} {container_name}:{dst}'
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert pid.returncode == 0


def run_timed_sql_script(container_name, script_file, debug=False):

    if not debug:
        cmd = f'psql -U pulp --file={script_file} | wc -l'
        cmd = f'docker exec {container_name} ' + cmd
        t1 = datetime.datetime.now()
        pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        t2 = datetime.datetime.now()
        delta = (t2 - t1).total_seconds()

        stdout = pid.stdout.decode('utf-8')
        rowcount = int(stdout.strip())
        #import epdb; epdb.st()
        return delta, rowcount

    cmd = f'psql -U pulp --file={script_file}'
    cmd = f'docker exec {container_name} ' + cmd
    t1 = datetime.datetime.now()
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    t2 = datetime.datetime.now()
    delta = (t2 - t1).total_seconds()
    stdout = pid.stdout.decode('utf-8')
    print(stdout)

    return delta, len(stdout.split('\n'))



def run_sql(sql):
    cmd = (
        'docker exec oci_env_pulp_1 '
        + '/bin/bash -c '
        + f'\'psql -U pulp -c "{sql}"\''
    )
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = pid.stdout.decode('utf-8')
    rows = stdout.split('\n')
    rows = [x for x in rows if '|' in x]
    rows = [x.split('|') for x in rows]
    for idx,x in enumerate(rows):
        stripped = [y.strip() for y in x]
        rows[idx] = stripped
    return rows


def get_collection_versions_from_db():
    sql = "SELECT namespace,name,version FROM ansible_collectionversion"
    rows = run_sql(sql)
    rows = rows[1:]
    rows = sorted(rows)
    return rows


def get_repositories_from_db(name_only=True):
    sql = (
        'SELECT * from ansible_ansiblerepository'
        + ' inner join core_repository'
        + ' ON core_repository.pulp_id=ansible_ansiblerepository.repository_ptr_id'
    )
    rows = run_sql(sql)
    if name_only:
        ix = rows[0].index('name')
        rows = [x[ix] for x in rows]
        rows = rows[1:]
    return rows


def get_distributions_from_db():
    sql = (
        'SELECT * from ansible_ansibledistribution'
        + ' inner join core_distribution'
        + ' ON core_distribution.pulp_id=ansible_ansibledistribution.distribution_ptr_id'
    )
    rows = run_sql(sql)
    ix = rows[0].index('name')
    rows = [x[ix] for x in rows]
    rows = rows[1:]
    return rows



def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--filter')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    container_name = 'oci_env_pulp_1'

    query_files = glob.glob('queries/*.sql')
    query_files = sorted(query_files)

    if args.filter:
        query_files = [x for x in query_files if args.filter in x]

    for qf in query_files:
        print(qf)
        with open(qf, 'r') as f:
            sql = f.read()
        dst = '/tmp/' + os.path.basename(qf)
        copy_file_to_conainer(container_name, qf, dst)
        duration, rowcount = run_timed_sql_script(container_name, dst, debug=args.debug)
        print(f'{qf} duration:{duration}s rows:{rowcount}')
        #import epdb; epdb.st()



if __name__ == "__main__":
    main()
