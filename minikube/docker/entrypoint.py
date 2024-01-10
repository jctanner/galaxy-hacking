#!/usr/bin/env python

import datetime
import os
import shutil
import subprocess
import sys
import time
import threading


API_SCRIPT = '''
#!/bin/bash

set -o errexit
set -o nounset

export PULP_SETTINGS=/etc/pulp/settings.py

readonly GUNICORN='/usr/local/bin/gunicorn'
readonly GUNICORN_FORWARDED_ALLOW_IPS="${GUNICORN_FORWARDED_ALLOW_IPS:-}"
readonly GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"
readonly GUNICORN_LOGGER_CLASS="${GUNICORN_LOGGER_CLASS:-}"
readonly GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-60}"

readonly BIND_HOST='0.0.0.0'
readonly BIND_PORT=${GUNICORN_PORT:-8000}
readonly APP_MODULE='pulpcore.app.wsgi:application'


GUNICORN_OPTIONS=(
  --bind "${BIND_HOST}:${BIND_PORT}"
  --workers "${GUNICORN_WORKERS}"
  --access-logfile -
  --limit-request-field_size 32768
  --timeout "${GUNICORN_TIMEOUT}"
)

if [[ -n "${GUNICORN_FORWARDED_ALLOW_IPS}" ]]; then
    GUNICORN_OPTIONS+=(--forwarded-allow-ips "${GUNICORN_FORWARDED_ALLOW_IPS}")
fi

if [[ -n "${GUNICORN_LOGGER_CLASS}" ]]; then
    GUNICORN_OPTIONS+=(--logger-class "${GUNICORN_LOGGER_CLASS}")
fi

exec "${GUNICORN}" "${GUNICORN_OPTIONS[@]}" "${APP_MODULE}"
'''


CONTENT_SCRIPT = '''
#!/bin/bash

set -o errexit
set -o nounset

export PULP_SETTINGS=/etc/pulp/settings.py

readonly GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}

readonly BIND_HOST='0.0.0.0'
readonly BIND_PORT="${GUNICORN_PORT:-24816}"
readonly WORKER_CLASS='aiohttp.GunicornWebWorker'
readonly APP_MODULE='pulpcore.content:server'


exec gunicorn \
  --bind "${BIND_HOST}:${BIND_PORT}" \
  --worker-class "${WORKER_CLASS}" \
  --workers "${GUNICORN_WORKERS}" \
  --access-logfile - \
  "${APP_MODULE}"
'''


WORKER_SCRIPT = '''
#!/bin/bash

set -o errexit
set -o nounset

export PULP_SETTINGS=/etc/pulp/settings.py

exec pulpcore-worker
'''


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

    pg_server = os.environ.get('PULP_DB_HOST', 'postgres')
    pg_user = os.environ.get('POSTGRES_USER')
    pg_pass = os.environ.get('POSTGRES_PASSWORD')

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

    pg_server = os.environ.get('PULP_DB_HOST', 'postgres')
    pg_admin_user = os.environ.get('POSTGRES_USER')
    pg_admin_pass = os.environ.get('POSTGRES_PASSWORD')

    pg_db = os.environ.get('PULP_DB_NAME', 'pulp')
    pg_user = os.environ.get('PULP_DB_USER', 'pulp')
    pg_pass = os.environ.get('PULP_DB_PASSWORD', 'pulp')

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

    pg_server = os.environ.get('PULP_DB_HOST', 'postgres')
    pg_admin_user = os.environ.get('POSTGRES_USER')
    pg_admin_pass = os.environ.get('POSTGRES_PASSWORD')

    pg_db = os.environ.get('PULP_DB_NAME', 'pulp')
    pg_user = os.environ.get('PULP_DB_USER', 'pulp')
    pg_pass = os.environ.get('PULP_DB_PASSWORD', 'pulp')

    if not os.path.exists('/etc/pulp/certs/'):
        os.makedirs('/etc/pulp/certs')

    if not os.path.exists('/etc/pulp/certs/database_fields.symmetric.key'):
        cmd = 'openssl rand -base64 32 > /etc/pulp/certs/database_fields.symmetric.key'
        pid = subprocess.run(cmd, shell=True)
        assert pid.returncode == 0

    cfg = [
        # THIS DOESN'T TAKE EFFECT? ...
        # "API_PREFIX = '/api/automation-hub'",
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
    ]

    settings_file = os.path.join('/etc', 'pulp', 'settings.py')
    settings_dir = os.path.dirname(settings_file)
    if not os.path.exists(settings_dir):
        os.makedirs(settings_dir)
    with open(settings_file, 'a') as f:
        f.write('\n'.join(cfg) + '\n')

    return


def install_galaxy_ng():
    print('#' * 50)
    print('INSTALL GALAXY_NG')
    print('#' * 50)

    subprocess.run(f'which git', shell=True)
    if not os.path.exists('/app'):
        os.makedirs('/app')
    if not os.path.exists('/app/galaxy_ng'):
        subprocess.run(f'git clone https://github.com/ansible/galaxy_ng /app/galaxy_ng', shell=True)

    if os.environ.get('GALAXY_BRANCH'):
        subprocess.run(
            f"git checkout {os.environ['GALAXY_BRANCH']}",
            cwd='/app/galaxy_ng',
            shell=True
        )

    pid = subprocess.run(f'pip install -e /app/galaxy_ng', shell=True)
    assert pid.returncode == 0


def make_paths():
    print('#' * 50)
    print('MAKE PATHS')
    print('#' * 50)

    paths = [
        '/var/lib/pulp/tmp',
        '/var/lib/pulp/artifact',
        '/var/lib/pulp/assets',
        '/var/lib/pulp/scripts',
    ]
    for path in paths:
        if not os.path.exists(path):
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

    # if scaling the pod this will probably fail ...
    # assert pid.returncode == 0

    if pid.returncode == 0:

        # on 4.2 you may have to run pulpcore-manager reset-admin-password
        cmd = 'PULP_SETTINGS=/etc/pulp/settings.py pulpcore-manager reset-admin-password -p admin'
        pid = subprocess.run(cmd, shell=True)
        assert pid.returncode == 0


def run_services():
    print('#' * 50)
    print('RUN SERVICES')
    print('#' * 50)

    commands = [
        'PULP_SETTINGS=/etc/pulp/settings.py pulpcore-manager runserver',
        'PULP_SETTINGS=/etc/pulp/settings.py pulpcore-worker'
    ]

    if not os.path.exists('/usr/local/bin/pulpcore-worker'):
        # the worker
        commands[1] = (
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


def run_api():
    print('#' * 50)
    print('RUN API')
    print('#' * 50)

    cmd = '/usr/bin/start-api'
    with open(cmd, 'w') as f:
        f.write(API_SCRIPT.lstrip())

    subprocess.run(f'chmod +x {cmd}', shell=True)
    subprocess.run(cmd, shell=True)


def run_content():
    print('#' * 50)
    print('RUN CONTENT')
    print('#' * 50)

    cmd = '/usr/bin/start-content'
    with open(cmd, 'w') as f:
        f.write(CONTENT_SCRIPT.lstrip())

    subprocess.run(f'chmod +x {cmd}', shell=True)

    while True:
        ts = datetime.datetime.now().isoformat()
        print(ts)
        subprocess.run(cmd, shell=True)
        time.sleep(10)


def run_worker():
    print('#' * 50)
    print('RUN WORKER')
    print('#' * 50)

    cmd = '/usr/bin/start-worker'
    with open(cmd, 'w') as f:
        f.write(WORKER_SCRIPT.lstrip())

    subprocess.run(f'chmod +x {cmd}', shell=True)

    while True:
        ts = datetime.datetime.now().isoformat()
        print(ts)
        subprocess.run(cmd, shell=True)
        time.sleep(5)


def main():

    service = 'api'
    if len(sys.argv) > 1:
        service = sys.argv[1]

    print(f'SERVICE: {service}')

    install_ldap()
    install_psql()
    install_galaxy_ng()

    if service == 'install':
        return 0

    make_paths()

    if service == 'api':
        create_database()
        build_settings()
        run_migrations()
        create_admin()
        run_api()

    elif service == 'worker':
        wait_for_database()
        build_settings()
        run_worker()

    elif service == 'content':
        wait_for_database()
        build_settings()
        run_content()

    while True:
        ts = datetime.datetime.now().isoformat()
        print(ts)
        time.sleep(10)


if __name__ == "__main__":
    main()
