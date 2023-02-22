#!/usr/bin/env python


import argparse
import copy
import datetime
import glob
import json
import os
import subprocess
import uuid
import keyword
import random

import psycopg2
import psycopg2.extras
from logzero import logger
import concurrent.futures
from logzero import logger


def copy_file_to_container(src, dst):
    container_name = "foobar"
    cmd = f'docker cp {src} {container_name}:{dst}'
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert pid.returncode == 0


def get_connection():
    cname = "foobar"
    database = "pulp"
    username = "pulp"
    password = "pulp"

    cmd = f'docker inspect {cname}'
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ds = json.loads(pid.stdout.decode('utf-8'))
    ipaddress = ds[0]['NetworkSettings']['IPAddress']

    conn = psycopg2.connect(
        host=ipaddress,
        database=database,
        user=username,
        password=password
    )

    #import epdb; epdb.st()
    return conn



def make_database(reset=False):
    cname = "foobar"
    password = "foobar"

    cmd = f"docker inspect {cname}"
    pid = subprocess.run(cmd, shell=True)
    if (pid.returncode == 0 and reset) or pid.returncode == 1:

        cmd = f"docker kill {cname}"
        logger.info(cmd)
        subprocess.run(cmd, shell=True)
        cmd = f"docker rm {cname}"
        logger.info(cmd)
        subprocess.run(cmd, shell=True)

        cmd = f"docker run --name={cname} -e POSTGRES_DB=pulp -e POSTGRES_USER=pulp -e POSTGRES_PASSWORD=pulp -d postgres"
        logger.info(cmd)
        pid = subprocess.run(cmd, shell=True)

        cmd = f"docker logs {cname}"
        while True:
            pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout = pid.stdout.decode('utf-8')
            if 'init process complete' in stdout:
                break
            #import epdb; epdb.st()

        cmd = f'docker exec -t {cname} psql -U pulp -c "create extension hstore"'
        logger.info(cmd)
        pid = subprocess.run(cmd, shell=True)


        make_tables()


def make_tables():

    cname = "foobar"

    table_files = glob.glob("tables/*.sql")
    table_files = sorted(table_files)
    for tf in table_files:

        logger.info('*' * 50)
        logger.info(f'make table {tf}')

        tbn = os.path.basename(tf)
        dst = os.path.join('/tmp', tbn)

        cmd = f'docker exec -t {cname} /bin/bash -c "rm -f {dst}"'
        logger.info(cmd)
        subprocess.run(cmd, shell=True)

        cmd = f'docker cp {tf} {cname}:{dst}'
        logger.info(cmd)
        subprocess.run(cmd, shell=True)

        cmd = f'docker exec -t {cname} psql -U pulp -d pulp --file={dst}'
        logger.info(cmd)
        pid = subprocess.run(cmd, shell=True)
        if pid.returncode != 0:
            import epdb; epdb.st()


class PulpMocker:

    container_name = 'foobar'
    _connection = None

    extra_cvs = [
        ['x', 'bob', 'jones', '2.0.0'],
        ['x', 'bob', 'jones', '2.0.0.1'],
        ['x', 'bob', 'jones', 'v1.0.0'],
        ['x', 'bob', 'jones', '1.0.0-alpha'],
        ['x', 'bob', 'jones', '1.0.0-alpha'],
        ['x', 'bob', 'jones', '1.0.0-alpha.1'],
        ['x', 'bob', 'jones', '1.0.0-0.3.7'],
        ['x', 'bob', 'jones', '1.0.0-x.7.z.92'],
        ['x', 'bob', 'jones', '9.1.6+41189.git68efef5'],
    ]

    def __init__(self):
        self.check_database()

    def __del__(self):
        if self._connection is not None:
            self._connection.close()

    def check_database(self):
        make_database(reset=False)

    def reset_database(self):
        self._collectionmap = {}
        self._collectionversionmap = {}
        self._repomap = {}
        self._repocontentmap = {}
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        make_database(reset=True)
        make_tables()

    def get_connection(self):
        if self._connection is None:
            self._connection = get_connection()
        return self._connection

    def make_collection_versions(self):
        logger.info('make collection versions')

        conn = self.get_connection()
        cur = conn.cursor()

        with open('cversions.txt', 'r') as f:
            rawdata = f.read()
        cvs = rawdata.split('\n')
        cvs = [x for x in cvs if x.strip()]
        cvs = sorted(cvs)
        cvs = [x.split(',') for x in cvs]

        cvs = cvs + self.extra_cvs

        for cv in cvs:

            pulp_id = str(uuid.uuid4())

            sql = 'INSERT INTO ansible_collectionversion '
            sql += '(content_ptr_id, host, namespace, name, version)'
            sql += ' VALUES '
            sql += f"(%s, %s, %s, %s, %s);"
            try:
                cur.execute(sql, (pulp_id, cv[0], cv[1], cv[2], cv[3],))
            except psycopg2.errors.UniqueViolation:
                pass

            conn.commit()

    def run_sql_script(self, filename):
        container_name = 'foobar'
        cmd = f'psql -U pulp --file={filename}'
        cmd = f'docker exec {container_name} ' + cmd
        subprocess.run(cmd, shell=True)

    def run_query_by_keyword(self, keyword):
        query_files = sorted(glob.glob('queries/*.sql'))
        query_files = [x for x in query_files if keyword in x]
        for qf in query_files:
            dst = '/tmp/' + os.path.basename(qf)
            copy_file_to_container(qf, dst)
            logger.info(f'RUN {dst}')
            self.run_sql_script(dst)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true', help='delete and recreate database')
    args = parser.parse_args()

    # redfine tables, kill database, make tables ...
    if args.reset:
        make_database(reset=True)
        make_tables()

    # make the ORM
    pm = PulpMocker()
    if args.reset:
        pm.make_collection_versions()
    pm.run_query_by_keyword('5')


if __name__ == "__main__":
    main()
