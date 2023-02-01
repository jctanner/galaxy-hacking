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
from random_word import RandomWords
from logzero import logger


RW = RandomWords()


def random_safe_word():
    word = None
    while word is None or keyword.iskeyword(word):
        word = RW.get_random_word().lower()
    return word


def random_spec(fakearg=None):
    namespace = random_safe_word()
    name = random_safe_word()
    version = '.'.join([
        str(random.choice(range(0, 100))),
        str(random.choice(range(0, 100))),
        str(random.choice(range(0, 100)))
    ])
    spec = [namespace, name, version]
    # print(spec)
    return spec


def process_table(raw, table=None):

    cols = []

    lines = raw.split('\n')
    lines = [x for x in lines if '|' in x]
    lines = lines[1:]

    for line in lines:
        parts = line.split('|')
        parts = [x.strip() for x in parts]

        #if 'hstore' in parts[1]:
        #    continue

        if parts[1] == 'uuid' and parts[3] == 'not null':
            cols.append(f'{parts[0]} UUID NOT NULL')
            continue

        if parts[3] == 'not null':
            cols.append(f'{parts[0]} {parts[1]} NOT NULL')
        else:
            cols.append(f'{parts[0]} {parts[1]}')

    sql = [
        f'DROP TABLE IF EXISTS {table};',
        f'CREATE TABLE {table} ('
    ]
    for idc,col in enumerate(cols):
        if idc == len(cols) - 1:
            sql.append('    ' + col)
        else:
            sql.append('    ' + col + ',')

    # "ansible_collectionversion_namespace_name_version_96aacd81_uniq" UNIQUE CONSTRAINT, btree (namespace, name, version)
    if 'unique constraint' in raw.lower():
        lines = raw.split('\n')
        constraints = [x.strip() for x in lines if 'UNIQUE CONSTRAINT' in x]

        if constraints:
            sql[-1] += ','

        for idc, constraint in enumerate(constraints):
            constraint = constraint[constraint.index('('):]
            constraint_name = constraints[idc].split('"')[1]
            if idc == len(constraints) -1:
                sql.append(f'    CONSTRAINT {constraint_name} UNIQUE {constraint}')
            else:
                sql.append(f'    CONSTRAINT {constraint_name} UNIQUE {constraint},')

    sql.append(');')
    return '\n'.join(sql)


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



def make_ddl():

    TABLES = [
        'core_content',
        'core_repositorycontent',
        'core_repository',
        'core_repositoryversion',
        'ansible_collection',
        'ansible_collectionversion',
        'ansible_collectionversionsignature',
        'ansible_ansiblecollectiondeprecated'
    ]

    for table in TABLES:
        cmd = f"docker exec -t oci_env_pulp_1 /bin/bash -c 'rm -f /tmp/{table}.txt'"
        logger.info(cmd)
        pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

        # docker exec -it oci_env_pulp_1 psql -U pulp -c '\d ansible_collectionversion'
        cmd = f"docker exec -t oci_env_pulp_1 psql -U pulp -d pulp -L /tmp/{table}.txt -c \'\d {table}\'"
        logger.info(cmd)
        pid = subprocess.run(cmd, shell=True)
        #stdout = pid.stdout.decode('utf-8')
        #print(stdout)

        cmd = f"docker exec -t oci_env_pulp_1 /bin/bash -c 'cat /tmp/{table}.txt'"
        logger.info(cmd)
        pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
        stdout = pid.stdout.decode('utf-8')
        #print(stdout)

        sql = process_table(stdout, table=table)
        logger.info(sql)

        sqlfile = os.path.join("tables", table + '.sql')
        with open(sqlfile, 'w') as f:
            f.write(sql)


def make_database(reset=False):
    cname = "foobar"
    password = "foobar"

    cmd = f"docker inspect {cname}"
    pid = subprocess.run(cmd, shell=True)
    if pid.returncode == 0 and reset:

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


def make_specs(count=1000):

    specs = []

    fn = 'specs.json'
    if os.path.exists(fn):
        try:
            with open(fn, 'r') as f:
                specs = json.loads(f.read())
        except json.decoder.JSONDecodeError:
            pass

    if len(specs) > count:
        return specs[:count]

    print(f'making {count - len(specs)} new specs')
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
        for res in executor.map(random_spec, [x for x in range(0, count - len(specs))]):
            specs.append(res)

    logger.info('writing new specs to cache')
    with open(fn, 'w') as f:
        f.write(json.dumps(specs, indent=2))

    return specs



class PulpMocker:

    container_name = 'foobar'
    _connection = None

    def __init__(self):
        self._collectionmap = {}
        self._collectionversionmap = {}
        self._repomap = {}
        self._repocontentmap = {}

        cvmap = self.get_collectionversions()
        for k,v in cvmap.items():
            self._collectionversionmap[k] = v['content_ptr_id']

    def __del__(self):
        if self._connection is not None:
            self._connection.close()

    def reset_database(self):
        self._collectionmap = {}
        self._collectionversionmap = {}
        self._repomap = {}
        self._repocontentmap = {}
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        # make_ddl()
        make_database(reset=True)
        make_tables()

    def get_connection(self):
        if self._connection is None:
            self._connection = get_connection()
        return self._connection

    @property
    def namespace_count(self):
        cvmap = self.get_collectionversions(debug=False)
        cvkeys = list(cvmap.keys())
        ckeys = sorted(set([x[:1] for x in cvkeys]))
        return len(ckeys)

    @property
    def collection_count(self):
        cvmap = self.get_collectionversions(debug=False)
        cvkeys = list(cvmap.keys())
        ckeys = sorted(set([x[:2] for x in cvkeys]))
        return len(ckeys)

    @property
    def collection_version_count(self):
        cvmap = self.get_collectionversions(debug=False)
        return len(list(cvmap.keys()))

    def get_stats(self):
        nscount = self.namespace_count
        ccount = self.collection_count
        cvcount = self.collection_version_count
        return {
            'namespaces': nscount,
            'collections': ccount,
            'collection_versions': cvcount
        }

    def show_stats(self):
        nscount = self.namespace_count
        ccount = self.collection_count
        cvcount = self.collection_version_count
        logger.info('-' * 100)
        logger.info(f'CURRENT STATS - namespaces:{nscount} collections:{ccount} collection_versions:{cvcount}')
        logger.info('-' * 100)

    def make_content(self, ctype='ansible.collection_version'):

        conn = self.get_connection()
        cur = conn.cursor()

        pulp_id = str(uuid.uuid4())
        ts = datetime.datetime.now()
        labels = "'a' => 'a'"

        sql = 'INSERT INTO core_content '
        sql += '(pulp_id, pulp_created, pulp_last_updated, pulp_type, timestamp_of_interest)'
        sql += ' VALUES '
        sql += f"(%s, %s, %s, %s, %s);"
        cur.execute(sql, (pulp_id, ts, ts, ctype, ts,))
        conn.commit()
        # conn.close()

        return pulp_id

    def make_collection(self, namespace, name):

        if (namespace, name) in self._collectionmap:
            return self._collectionmap[(namespace, name)]

        conn = self.get_connection()
        cur = conn.cursor()

        sql = 'SELECT pulp_id FROM ansible_collection WHERE namespace=%s AND name=%s'
        cur.execute(sql, (namespace, name,))
        rows = cur.fetchall()
        if len(rows) > 0:
            pulp_id = rows[0][0]
            self._collectionmap[(namespace, name)] = pulp_id
            return pulp_id

        pulp_id = str(uuid.uuid4())
        ts = datetime.datetime.now()

        sql = 'INSERT INTO ansible_collection '
        sql += '(pulp_id, pulp_created, pulp_last_updated, namespace, name)'
        sql += ' VALUES '
        sql += f"(%s, %s, %s, %s, %s);"
        #logger.info(f'making collection: {sql}')
        cur.execute(sql, (pulp_id, ts, ts, namespace, name,))
        conn.commit()
        #conn.close()

        self._collectionmap[(namespace, name)] = pulp_id
        return pulp_id

    def make_collectionversion(self, spec):

        cvkey = tuple(spec)
        if cvkey in self._collectionversionmap:
            return self._collectionverisonmap[cvkey]

        #cvmap = self.get_collectionversions()
        #if cvkey in cvmap:
        #    return cvmap[ckey]['content_ptr_id']

        # make content first
        content_ptr_id = self.make_content()

        # make collection second
        collection_id = self.make_collection(spec[0], spec[1])

        # make cv thirds
        conn = self.get_connection()
        cur = conn.cursor()

        namespace = spec[0]
        name = spec[1]
        version = spec[2]

        sql = (
            "INSERT INTO ansible_collectionversion"
            + " (content_ptr_id, collection_id, namespace, name, version, is_highest, authors, repository,"
            + " homepage, issues, license, description, documentation, docs_blob, dependencies, contents, files, manifest, search_vector)"
            + " VALUES"
            + " ("
            +   f"'{content_ptr_id}',"
            +   f" '{collection_id}',"
            +   f" '{namespace}',"
            +   f" '{name}',"
            +   f" '{version}',"
            +   f"  false,"
            +   f" ARRAY['joe'],"
            +   " 'http://github.com/foo/bar',"
            +   " 'http://foobar.net',"
            +   " 'http://foobar.net/issues',"
            +   " ARRAY['agpl'],"
            +   " 'desc',"
            +   " 'docs',"
            +   " '{}',"
            +   " '{}',"
            +   " '{}',"
            +   " '{}',"
            +   " '{}',"
            +   " to_tsvector('english', 'foo bar')"
            + ")"
            + ";"
        )

        logger.info(f'INSERT {spec}')

        cur.execute(sql)
        conn.commit()
        #conn.close()

        return content_ptr_id

    def make_cvs_batch(self, specs=None):

        cname = 'foobar'

        collections = {}

        with open('cvs.sql', 'a') as f:
            for spec in specs:

                namespace = spec[0]
                name = spec[1]
                version = spec[2]

                if namespace not in collections:
                    collection_id = uuid.uuid4()
                else:
                    collection_id = collections[namespace]

                sql = (
                    "INSERT INTO ansible_collectionversion"
                    + " (content_ptr_id, collection_id, namespace, name, version, is_highest, authors, repository,"
                    + " homepage, issues, license, description, documentation, docs_blob, dependencies, contents,"
                    + " files, manifest, search_vector)"
                    + " VALUES"
                    + " ("
                    +   f"'{uuid.uuid4()}',"
                    +   f" '{collection_id}',"
                    +   f" '{namespace}',"
                    +   f" '{name}',"
                    +   f" '{version}',"
                    +   f"  false,"
                    +   f" ARRAY['joe'],"
                    +   " 'http://github.com/foo/bar',"
                    +   " 'http://foobar.net',"
                    +   " 'http://foobar.net/issues',"
                    +   " ARRAY['agpl'],"
                    +   " 'desc',"
                    +   " 'docs',"
                    +   " '{}',"
                    +   " '{}',"
                    +   " '{}',"
                    +   " '{}',"
                    +   " '{}',"
                    +   " to_tsvector('english', 'foo bar')"
                    + ")"
                    + ";"
                )
                #cmd = f'docker exec -t {cname} psql -U pulp -d pulp -c "{sql}"'
                #pid = subprocess.run(cmd, shell=True)
                #print(cmd)
                f.write(sql + '\n')

        src = 'cvs.sql'
        dst = '/tmp/sql'

        cmd = f'docker exec -t {cname} /bin/bash -c "rm -f {dst}"'
        subprocess.run(cmd, shell=True)

        cmd = f'docker cp {src} {cname}:{dst}'
        subprocess.run(cmd, shell=True)

        cmd = f'docker exec -t {cname} psql -U pulp -d pulp --file={dst}'
        pid = subprocess.run(cmd, shell=True)
        #if pid.returncode != 0:
        #    import epdb; epdb.st()

        #import epdb; epdb.st()


    def make_repo(self, reponame):

        if reponame in self._repomap:
            return self._repomap[reponame]

        conn = self.get_connection()
        cur = conn.cursor()

        sql = f"SELECT * FROM core_repository WHERE name='{reponame}'"
        cur.execute(sql)
        rows = cur.fetchall()

        if len(rows) > 0:
            #conn.close()
            return rows[0][0]

        pulp_id = str(uuid.uuid4())
        ts = datetime.datetime.now()
        labels = "'a' => 'a'"

        logger.info(f'make repo {reponame}')
        sql = 'INSERT INTO core_repository '
        sql += '(pulp_id, pulp_created, pulp_last_updated, name, next_version, pulp_type, user_hidden, pulp_labels)'
        sql += ' VALUES '
        sql += f"(%s, %s, %s, %s, %s, %s, %s, %s);"
        cur.execute(sql, (pulp_id, ts, ts, reponame, 1, 'ansible.ansible', False, labels,))
        conn.commit()
        #conn.close()

        self.make_new_repo_version(repoid=pulp_id, number=0)

        # TODO - increment next_version?

        self._repomap[reponame] = pulp_id
        return pulp_id

    def make_new_repo_version(self, repoid=None, reponame=None, number=None):

        conn = self.get_connection()
        cur = conn.cursor()

        sql = f"SELECT number FROM core_repositoryversion WHERE repository_id=%s"
        cur.execute(sql, (repoid,))
        current_versions = cur.fetchall()
        current_versions = [x[0] for x in current_versions]

        if number is None and not current_versions:
            number = 0
        elif number is None and current_versions:
            number = sorted(current_versions)[-1] + 1

        pulp_id = str(uuid.uuid4())
        ts = datetime.datetime.now()

        logger.info(f'make repoversion {repoid} v:{number}')
        sql = 'INSERT INTO core_repositoryversion '
        sql += '(pulp_id, pulp_created, pulp_last_updated, number, complete, repository_id, info)'
        sql += ' VALUES '
        sql += f"(%s, %s, %s, %s, %s, %s, %s);"
        cur.execute(sql, (pulp_id, ts, ts, number, True, repoid, '{}',))

        # update the next version of the repo ...
        sql = 'UPDATE core_repository SET next_version=%s WHERE pulp_id=%s'
        cur.execute(sql, (number + 1, repoid,))

        conn.commit()
        #conn.close()

        return pulp_id

    def get_collectionversions(self, debug=True):

        if debug:
            logger.info('get ALL collectionversions')

        conn = self.get_connection()
        cur = conn.cursor()

        sql = f"SELECT * FROM ansible_collectionversion"
        cur.execute(sql)
        rows = cur.fetchall()

        cvmap = {}
        for row in rows:
            ds = {
                'content_ptr_id': row[0],
                'version': row[1],
                'contents': row[2],
                'collection_id': row[3],
                'authors': row[4],
                'dependencies': row[5],
                'description': row[6],
                'docs_blob': row[7],
                'documentation': row[8],
                'homepage': row[9],
                'issues': row[10],
                'license': row[11],
                'name': row[12],
                'namespace': row[13],
                'repository': row[14],
                'search_vector': row[15],
                'is_highest': row[16],
                'files': row[17],
                'manifest': row[18],
                'requires_ansible': row[19],
            }
            cvkey = (ds['namespace'], ds['name'], ds['version'])
            cvmap[cvkey] = ds
            self._collectionversionmap[cvkey] = row[0]

        #conn.close()
        #import epdb; epdb.st()
        return cvmap

    def make_repositorycontent(self, repository_id, version_added_id, content_id):

        conn = self.get_connection()
        cur = conn.cursor()

        sql = f"SELECT pulp_id FROM core_repositorycontent WHERE "
        sql += "repository_id=%s AND version_added_id=%s AND content_id=%s"
        cur.execute(sql, (repository_id, version_added_id, content_id))
        rows = cur.fetchall()
        if len(rows) > 0:
            return rows[0][0]

        pulp_id = str(uuid.uuid4())
        ts = datetime.datetime.now()

        #logger.info('make repository_content')
        sql = 'INSERT INTO core_repositorycontent '
        sql += '(pulp_id, pulp_created, pulp_last_updated, content_id, repository_id, version_added_id)'
        sql += ' VALUES '
        sql += '(%s, %s, %s, %s, %s, %s)'
        cur.execute(sql, (pulp_id, ts, ts, content_id, repository_id, version_added_id,))

        #import epdb; epdb.st()
        conn.commit()
        #conn.close()
        return pulp_id

    def get_repositorycontent(self, repoid):
        conn = self.get_connection()
        cur = conn.cursor()

        sql = 'SELECT pulp_id,content_id,repository_id,version_added_id,version_removed_id from core_repositorycontent'
        sql += ' WHERE repository_id=%s'
        cur.execute(sql, (repoid,))
        rows = cur.fetchall()
        for idx,x in enumerate(rows):
            rows[idx] = {
                'pulp_id': x[0],
                'content_id': x[1],
                'repository_id': x[2],
                'version_added_id': x[3],
                'version_removed_id': x[4]
            }
        rows = [x for x in rows if not x.get('version_removed_id')]
        return [x['content_id'] for x in rows]

    def add_to_repo(self, specs, reponame='hub1'):
        cname = 'foobar'
        repoid = self.make_repo(reponame)

        # make a new repo version
        repo_version_id = self.make_new_repo_version(repoid=repoid, reponame=reponame)

        # map out what is already in the repo ...
        repo_content = self.get_repositorycontent(repoid)

        # map out what cvs are in the system already ...
        cvmap = self.get_collectionversions()

        logger.info(f'checking for {len(specs)} specs in {reponame}')
        for spec in specs:

            # logger.info(f'adding {spec} to {reponame}')

            ckey = tuple(spec)
            if ckey not in cvmap:
                cvid = self.make_collectionversion(spec)
            else:
                ds = cvmap[tuple(spec)]
                cvid  = ds['content_ptr_id']

            if cvid in repo_content:
                continue

            # make repocontent
            rcid = self.make_repositorycontent(repoid, repo_version_id, cvid)

        #import epdb; epdb.st()

    def benchmark_query(self, queryfile):
        '''
        bn = os.path.basename(queryfile)
        dst = os.path.join('/tmp', bn)
        cmd = f'docker cp {queryfile} {self.container_name}:{dst}'
        logger.info(cmd)
        subprocess.run(cmd, shell=True)
        '''

        with open(queryfile, 'r') as f:
            sql = f.read()

        conn = self.get_connection()
        cur = conn.cursor()

        ts1 = datetime.datetime.now()
        cur.execute(sql)
        rows = cur.fetchall()
        ts2 = datetime.datetime.now()

        if len(rows) > 1000:
            import epdb; epdb.st()

        delta = (ts2 - ts1).total_seconds()
        return delta, len(rows)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true', help='delete and recreate database')
    parser.add_argument('--count', dest='collection_version_count', type=int, default=10000, help='how many collectionversions to test with')
    parser.add_argument('--increment', dest='collection_version_increment', type=int, help='run tests with incrementing CV counts')
    parser.add_argument('--filter', dest='query_filter', help='limit queries to files that have this keyword')
    args = parser.parse_args()

    # redfine tables, kill database, make tables ...
    if args.reset:
        make_ddl()
        make_database(reset=True)
        make_tables()

    cv_increments = [args.collection_version_count]
    if args.collection_version_increment:
        cv_increments = list(range(
            1,
            args.collection_version_count + args.collection_version_increment,
            args.collection_version_increment
        ))

    # make the ORM
    pm = PulpMocker()

    results = []

    # iterate each increment and benchmark it ...
    for cv_count in cv_increments:

        # create the CV specifications for testing
        specs = make_specs(count=cv_count)

        stats = pm.get_stats()
        if stats['collection_versions'] > cv_count:
            pm.reset_database()

        # add (and create if needed) all the CVs to a repo ...
        pm.add_to_repo(specs, reponame='hub1')
        stats = pm.get_stats()

        # benchmark all the queries ...
        sql_query_files = sorted(glob.glob('queries/*.sql'))
        if args.query_filter:
            sql_query_files = [x for x in sql_query_files if args.query_filter in x]
        for sqf in sql_query_files:
            delta, row_count = pm.benchmark_query(sqf)
            ds = copy.deepcopy(stats)
            ds['query'] = sqf
            ds['duration'] = delta
            ds['rowcount'] = row_count
            results.append(ds)

        # store intermediate results on disk
        with open('benchmark_results.json', 'w') as f:
            f.write(json.dumps(results))

    import epdb; epdb.st()



if __name__ == "__main__":
    main()
