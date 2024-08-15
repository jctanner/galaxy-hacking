#!/usr/bin/env python

import datetime
import os
import shutil
import subprocess
import sys
import time
import threading



def run_command_in_thread(command):

    if sys.version_info >= (3, 7):
        subprocess.run(
            command,
            shell=True,
            #stdout=subprocess.PIPE,
            #stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True,
        )
    else:
        subprocess.run(
            command,
            shell=True,
            #stdout=subprocess.PIPE,
            #stderr=subprocess.PIPE,
            #text=True,
            #universal_newlines=True,
        )


def run_commands_in_threads(commands):
    # Create and start a thread for each command
    threads = []
    for command in commands:
        thread = threading.Thread(target=run_command_in_thread, args=(command,))
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()


def install_time():
    print('#' * 50)
    print('INSTALL TIME')
    print('#' * 50)

    cmd = 'dpkg -l time || (apt -y update ; apt -y install time)'
    pid = subprocess.run(cmd, shell=True)
    assert pid.returncode == 0


def install_psql():
    print('#' * 50)
    print('INSTALL PSQL')
    print('#' * 50)

    cmd = 'dpkg -l postgresql-client || (apt -y update ; apt -y install postgresql-client)'
    pid = subprocess.run(cmd, shell=True)
    assert pid.returncode == 0


def install_ldap():
    print('#' * 50)
    print('INSTALL LDAP')
    print('#' * 50)

    cmd = 'DEBIAN_FRONTEND=noninteractive apt -y update'
    pid = subprocess.run(cmd, shell=True)
    assert pid.returncode == 0

    #cmd = 'DEBIAN_FRONTEND=noninteractive dpkg -l libldap-dev || (apt -y update ; apt -y install libldap-dev)'
    cmd = 'DEBIAN_FRONTEND=noninteractive apt -y install libldap-dev'
    pid = subprocess.run(cmd, shell=True)
    assert pid.returncode == 0

    #cmd = 'DEBIAN_FRONTEND=noninteractive dpkg -l libsasl2-dev || (apt -y update ; apt -y install libsasl2-dev)'
    cmd = 'DEBIAN_FRONTEND=noninteractive apt -y install libsasl2-dev'
    pid = subprocess.run(cmd, shell=True)
    assert pid.returncode == 0


def wait_for_database():
    print('#' * 50)
    print('CREATE DATABASE')
    print('#' * 50)

    pg_server = os.environ.get('PULP_DB_HOST')
    pg_user = os.environ.get('POSTGRES_ADMIN_USERNAME')
    pg_pass = os.environ.get('POSTGRES_ADMIN_PASSWORD')

    cmd = f'PGPASSWORD={pg_pass} psql -h {pg_server} -U {pg_user} -c "\l"'
    while True:
        pid = subprocess.run(cmd, shell=True)
        if pid.returncode == 0:
            break
        print(datetime.datetime.now(), "waiting 10 for database")
        time.sleep(10)


def create_database():
    print('#' * 50)
    print('CREATE DATABASE')
    print('#' * 50)

    pg_server = os.environ.get('PULP_DB_HOST')

    pg_admin_user = os.environ.get('POSTGRES_ADMIN_USERNAME')
    pg_admin_pass = os.environ.get('POSTGRES_ADMIN_PASSWORD')

    pg_db = os.environ.get('PULP_DB_NAME')
    pg_user = os.environ.get('PULP_DB_USER')
    pg_pass = os.environ.get('PULP_DB_PASSWORD')

    # need psql
    install_psql()

    # wait till can connect as admin user
    wait_for_database()

    '''
    # need hstore for 4.7+
    cmd = f"PGPASSWORD={pg_admin_pass} psql -h {pg_server} -U {pg_admin_user} -c 'CREATE EXTENSION hstore'"
    pid = subprocess.run(cmd, shell=True)
    assert pid.returncode == 0
    '''

    cmd = f"PGPASSWORD={pg_admin_pass} psql -h {pg_server} -U {pg_admin_user} -c '\l'" + " | awk '{print $1}' | grep ^[a-z]"
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    databases = [x.strip() for x in pid.stdout.decode('utf-8').split('\n') if x.strip()]
    print(f'CURRENT DATABASES: {databases}')

    if pg_db in databases:
        return

    sql = ""
    sql += f"create user {pg_user} with encrypted password \'{pg_pass}\';\n"
    sql += f"\set AUTOCOMMIT on\n"
    sql += f"CREATE database {pg_db} OWNER {pg_user};\n"
    sql += f"\set AUTOCOMMIT off\n"
    sql += f"grant all privileges on database {pg_db} to {pg_user};\n"

    print(sql)

    with open('create_database.sql', 'w') as f:
        f.write(sql)

    cmd = f"PGPASSWORD={pg_admin_pass} psql -h {pg_server} -U {pg_admin_user} < create_database.sql"
    print(cmd)
    pid = subprocess.run(cmd, shell=True)
    assert pid.returncode == 0

    # need hstore for 4.7+
    cmd = f"PGPASSWORD={pg_admin_pass} psql -h {pg_server} -U {pg_admin_user} -d {pg_db} -c 'CREATE EXTENSION hstore'"
    pid = subprocess.run(cmd, shell=True)
    assert pid.returncode == 0


def build_settings():
    print('#' * 50)
    print('BUILD SETTINGS')
    print('#' * 50)

    #pg_server = os.environ.get('POSTGRES_SERVER')
    pg_server = os.environ.get('PULP_DB_HOST')

    #pg_db = os.environ.get('POSTGRES_DATABASE')
    #pg_user = os.environ.get('POSTGRES_USERNAME')
    #pg_pass = os.environ.get('POSTGRES_PASSWORD')

    pg_db = os.environ.get('PULP_DB_NAME')
    pg_user = os.environ.get('PULP_DB_USER')
    pg_pass = os.environ.get('PULP_DB_PASSWORD')

    if not os.path.exists('/etc/pulp/certs/'):
        os.makedirs('/etc/pulp/certs')

    if not os.path.exists('/etc/pulp/certs/database_fields.symmetric.key'):
        cmd = 'openssl rand -base64 32 > /etc/pulp/certs/database_fields.symmetric.key'
        pid = subprocess.run(cmd, shell=True)
        assert pid.returncode == 0

    shutil.copy('/src/settings.py', '/etc/pulp/settings.py')

    return

    cmd = "pip show pulpcore | grep Location | awk '{print $2}'"
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert pid.returncode == 0
    pulpcore_path = pid.stdout.decode('utf-8').strip()
    pulpcore_path = os.path.join(pulpcore_path, 'pulpcore')
    settings_file = os.path.join(pulpcore_path, 'app', 'settings.py')

    #shutil.copy(settings_file, '/etc/pulp/settings.py')

    cfg = [
        #"ANALYTICS = False",
        "API_PREFIX = '/api/galaxy'",
        "CONTENT_ORIGIN = 'http://localhost:24816'",
        "DATABASES = {",
        "    'default': {",
        "        'ENGINE': 'django.db.backends.postgresql',",
        f"        'NAME': '{pg_db}',",
        f"        'USER': '{pg_user}',",
        f"        'PASSWORD': '{pg_pass}',",
        f"        'HOST': '{pg_server}',",
        "    }",
        "}",
        #"AUTHENTICATION_CLASSES: [",
        #"    'rest_framework.authentication.SessionAuthentication',",
        #"    'rest_framework.authentication.TokenAuthentication',",
        #"    'rest_framework.authentication.BasicAuthentication',",
        #"    'django.contrib.auth.backends.ModelBackend',",
        #"]",
    ]

    #with open('/etc/pulp/settings.py', 'a') as f:
    with open(settings_file, 'a') as f:
        f.write('\n'.join(cfg) + '\n')


def install_galaxy_ng():
    print('#' * 50)
    print('INSTALL GALAXY_NG')
    print('#' * 50)

    subprocess.run(f'which git', shell=True)
    os.makedirs('/app')
    subprocess.run(f'git clone https://github.com/ansible/galaxy_ng /app/galaxy_ng', shell=True)

    if os.environ.get('GALAXY_BRANCH'):
        subprocess.run(
            f"git checkout {os.environ['GALAXY_BRANCH']}",
            cwd='/app/galaxy_ng',
            shell=True
        )

    pid = subprocess.run(f'time pip install -e /app/galaxy_ng', shell=True)
    assert pid.returncode == 0


def make_paths():
    print('#' * 50)
    print('MAKE PATHS')
    print('#' * 50)

    paths = [
        '/var/lib/pulp/tmp',
        '/var/lib/pulp/artifact',
        '/var/lib/pulp/scripts',
    ]
    for path in paths:
        os.makedirs(path)


def run_migrations():
    print('#' * 50)
    print('RUN MIGRATIONS')
    print('#' * 50)

    cmd = 'PULP_SETTINGS=/etc/pulp/settings.py pulpcore-manager migrate'
    pid = subprocess.run(cmd, shell=True)
    assert pid.returncode == 0


def create_admin():
    print('#' * 50)
    print('CREATE ADMIN')
    print('#' * 50)

    cmd = "PULP_SETTINGS=/etc/pulp/settings.py DJANGO_SUPERUSER_PASSWORD=admin"
    cmd += " pulpcore-manager createsuperuser --noinput --username=admin --email=admin@localhost"
    pid = subprocess.run(cmd, shell=True)
    assert pid.returncode == 0

    # on 4.2 you may have to run pulpcore-manager reset-admin-password
    cmd = 'PULP_SETTINGS=/etc/pulp/settings.py pulpcore-manager reset-admin-password -p admin'
    pid = subprocess.run(cmd, shell=True)
    assert pid.returncode == 0


def run_services():
    print('#' * 50)
    print('RUN SERVICES')
    print('#' * 50)

    commands = []
    if shutil.which('pulpcore-api'):
        commands.append('PULP_SETTINGS=/etc/pulp/settings.py pulpcore-api')
    else:
        commands.append('PULP_SETTINGS=/etc/pulp/settings.py pulpcore-manager runserver')

    commands.append('PULP_SETTINGS=/etc/pulp/settings.py pulpcore-content')

    if shutil.which('pulpcore-worker'):
        commands.append('PULP_SETTINGS=/etc/pulp/settings.py pulpcore-worker')

    else:
        # the worker
        commands.append(
            'DJANGO_SETTINGS_MODULE=pulpcore.app.settings'
            + ' PULP_SETTINGS=/etc/pulp/settings.py'
            + ' rq worker -w pulpcore.tasking.worker.PulpWorker -c pulpcore.rqconfig'
        )

        # need a resource manager
        commands.append((
            'DJANGO_SETTINGS_MODULE=pulpcore.app.settings'
            + ' PULP_SETTINGS=/etc/pulp/settings.py'
            + ' rq worker -n resource-manager -w pulpcore.tasking.worker.PulpWorker -c pulpcore.rqconfig'
        ))

    run_commands_in_threads(commands)


def main():

    install_time()
    install_ldap()
    install_galaxy_ng()
    create_database()
    build_settings()
    make_paths()
    run_migrations()
    create_admin()
    run_services()

    while True:
        ts = datetime.datetime.now().isoformat()
        print(ts)
        time.sleep(10)


if __name__ == "__main__":
    main()
