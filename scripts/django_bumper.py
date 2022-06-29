#!/usr/bin/env python3

import datetime
import json
import os
import shutil
import subprocess
import tempfile
import threading

from threading import Thread
from pprint import pprint
from bs4 import BeautifulSoup


PACKAGES = ['pulpcore', 'pulp-ansible', 'pulp-container', 'django']
REPO = "git@github.com:jctanner/galaxy_ng"
UPSTREAM = "https://github.com/ansible/galaxy_ng"

PYPI_MAP = {
    'django': 'Django',
}

PYPI_CACHE = {}
IMAGE = 'pipcompiler:latest'
REQUIREMENTS_FILES = [
    ['requirements/requirements.txt'],
    ['requirements/requirements.common.txt'],
    ['requirements/requirements.insights.txt', 'requirements/requirements.insights.in'],
    ['requirements/requirements.standalone.txt', 'requirements/requirements.standalone.in']
]

PIP_COMPILE_EXTRA_ARGS = {
    #'5': '--annotation=line',
}

BRANCH_EXTRA_ARGS = {
    'stable-4.2': {
        #5: '--annotation-style=line',
        6: '--annotation-style=line',
    }
}


# https://github.com/jazzband/pip-tools/issues/794
# pip-tools>=3.6.5 -should- work with pip==19.1

# pip-tools==2.0.2
#   Error: No such option: --annotation-style (Possible options: --annotate, --no-annotate)
# pip-tools==4.5.1
#   AttributeError: module 'pip._internal.index' has no attribute 'PackageFinder'
# pip-tools==1.11.0
#   ModuleNotFoundError: No module named 'pip.req'
# pip-tools==3.9.0 && pip~=18.0 | pip~=10.0
#   pip._internal.exceptions.InstallationError: Command "python setup.py egg_info" failed with error code 1 in /tmp/tmp0nr7n4a1build/cryptography/
PIP_COMPILE_PIP_VERSION = {
    '6': 'pip~=22.1',
    '5': 'pip~=21.3',
    '4': 'pip~=19.3',
    '3': 'pip~=18.1',
    '2': 'pip~=18.1',
    '1': 'pip~=18.1',
}


def threaded_command(cmd):
    return subprocess.run(cmd, shell=True)


def make_baseimage():

    PYV = '3.8'
    #PYV = '3.9'

    tdir = tempfile.mkdtemp(prefix='pipcompile-docker-')
    fname = os.path.join(tdir, 'Dockerfile')
    with open(fname, 'w') as f:
        f.write(f'FROM python:{PYV}\n')
        f.write('RUN apt -y update\n')
        #f.write('RUN apt -y install python3-virtualenv python3-pip python3-wheel python3-cryptography\n')
        f.write('RUN apt -y install python3-virtualenv python3-pip\n')
        f.write(f'RUN python{PYV} -m venv /venv\n')
        f.write('RUN /venv/bin/pip install --upgrade pip wheel\n')
        #f.write('RUN /venv/bin/pip install cryptography\n')
        #f.write('RUN /venv/bin/pip install --upgrade pip wheel\n')

    pid = subprocess.run(f'docker build -t {IMAGE} .', shell=True, cwd=tdir)
    assert pid.returncode == 0

    shutil.rmtree(tdir)


def get_current_package_version(checkout, packagename):
    cmd = f"egrep ^{packagename}== requirements/*"
    cmd += " | awk '{print $1}'"
    pid = subprocess.run(cmd, shell=True, cwd=checkout, stdout=subprocess.PIPE)
    raw = pid.stdout.decode('utf-8')
    lines = raw.split('\n')
    lines = [x.strip() for x in lines if x.strip()]
    specs = [x.split(':')[-1] for x in lines]
    specs = sorted(set(specs))

    specs = sorted(specs)
    return specs[-1].split('==')[-1]


def get_pypi_versions(packagename, numeric=True):

    if packagename not in PYPI_CACHE:
        print('fetching versions ...')
        pid = subprocess.run(f"curl 'https://pypi.org/project/{packagename}/#history'", shell=True, stdout=subprocess.PIPE)
        html = pid.stdout.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        rvs = soup.find_all('p', {'class': 'release__version'})
        rvs = [x.text.strip() for x in rvs]
        PYPI_CACHE[packagename] = rvs[:]

    rvs = PYPI_CACHE[packagename][:]
    rvs = [x.split('.') for x in rvs]

    if numeric:
        _rvs = []
        for rv in rvs:
            try:
                _rv = [int(x) for x in rv]
                _rvs.append(_rv)
            except ValueError:
                pass
        rvs = _rvs[:]

    return rvs


def get_pypi_latest_majors(package_name):
    ptversions = get_pypi_versions(package_name)
    ptmajors = [x[0] for x in ptversions]
    ptmap = dict([(x, None) for x in ptmajors])
    for k,v in ptmap.items():
        for ptv in ptversions:
            if ptv[0] != k:
                continue
            if ptmap[k] is None:
                ptmap[k] = ptv
                continue
            if len(ptv) < len(ptmap[k]):
                continue
            if ptv[1] < ptmap[k][1]:
                continue
            if ptv[2] > ptmap[k][2]:
                ptmap[k] = ptv
    return ptmap


def get_latest_pypi_zstream(packagename, current_version):
    rvs = get_pypi_versions(packagename)

    parts = current_version.split('.')
    major = int(parts[0])
    minor = int(parts[1])
    z = int(parts[2])

    matched_versions = [x for x in rvs if x[0] == major and x[1] == minor]
    matched_versions = sorted(matched_versions)
    return '.'.join([str(x) for x in matched_versions[-1]])


def construct_checkout(checkout):

    # make the checkout
    pid = subprocess.run(f'git clone {REPO} {checkout}', shell=True)
    assert pid.returncode == 0

    # add upstream
    pid = subprocess.run(f'git remote add upstream {UPSTREAM}', shell=True, cwd=checkout)
    assert pid.returncode == 0

    # fetch
    pid = subprocess.run('git fetch -a && git fetch upstream', shell=True, cwd=checkout)
    assert pid.returncode == 0

    # rebase
    pid = subprocess.run('git pull --rebase upstream master', shell=True, cwd=checkout)
    assert pid.returncode == 0


def get_stable_branches(checkout):
    # find the stable branches
    pid = subprocess.run('git branch -a', shell=True, cwd=checkout, stdout=subprocess.PIPE)
    branches = pid.stdout.decode('utf-8').split('\n')
    branches = [x.strip() for x in branches if x.strip()]
    stable_branches = [x for x in branches if 'upstream/stable-' in x]
    stable_branches = [x.split('/')[-1] for x in stable_branches]
    return stable_branches


def main():

    tdir = tempfile.mkdtemp(prefix='galaxy-django-bump-')
    if not os.path.exists(tdir):
        os.makedirs(tdir)

    checkout = os.path.join(tdir, 'galaxy_ng')
    construct_checkout(checkout)
    stable_branches = get_stable_branches(checkout)
    stable_branches.append('master')

    # map out the current pinned versions ...
    pmap = {}
    for sb in stable_branches:

        pmap[sb] = {}

        pid = subprocess.run('git checkout master && git reset --hard', shell=True, cwd=checkout)
        pid = subprocess.run(f'git checkout upstream/{sb}', shell=True, cwd=checkout)

        for pname in PACKAGES:
            try:
                pv = get_current_package_version(checkout, pname)
                pmap[sb][pname] = {
                    'current': pv,
                    'latest': None
                }
            except Exception as e:
                pass

    for branch, packages in pmap.items():
        for package_name, details in packages.items():
            pypi_name = PYPI_MAP.get(package_name, package_name)
            latest = get_latest_pypi_zstream(pypi_name, details['current'])
            pmap[branch][package_name]['latest'] = latest

    make_baseimage()
    for branch, packages in pmap.items():

        if branch != 'stable-4.2':
            continue

        container_commands = []
        checkout_paths = {}

        # try every major version of pip-tools
        ptmap = get_pypi_latest_majors('pip-tools')
        for pmajor,pversion in ptmap.items():

            #if pmajor != 5:
            #    continue

            # make a new checkout for the updates ...
            tdir2 = f'/tmp/galaxy-django-bump-{branch}-{pmajor}'
            if os.path.exists(tdir2):
                try:
                    shutil.rmtree(tdir2)
                except Exception as e:
                    subprocess.run(f'sudo rm -rf {tdir2}', shell=True)
            if not os.path.exists(tdir2):
                os.makedirs(tdir2)
            checkout_branch = os.path.join(tdir2, 'galaxy_ng')
            checkout_paths[(branch, pmajor)] = checkout_branch
            construct_checkout(checkout_branch)
            pid = subprocess.run(f'git checkout upstream/{branch}', shell=True, cwd=checkout_branch)

            # make a new branch for the updates ...
            ts = datetime.datetime.now().isoformat().split('T')[0].replace('-', '_')
            pr_branch = f'BUMP_DEPS_{ts}_{branch}'.replace('-', '_').replace('.', '_')
            pid = subprocess.run(f'git checkout -b {pr_branch}', shell=True, cwd=checkout_branch)

            # cleanup ...
            pid = subprocess.run('git reset --hard', shell=True, cwd=checkout_branch)

            # assemble the container internal script
            pversion = '.'.join([str(x) for x in pversion])
            commands = ['source /venv/bin/activate']
            if str(pmajor) in PIP_COMPILE_PIP_VERSION:
                pip_version = PIP_COMPILE_PIP_VERSION[str(pmajor)]
                commands.append(f'/venv/bin/pip install --upgrade {pip_version}')
            commands.append(f'/venv/bin/pip install pip-tools=={pversion}')

            pceargs = PIP_COMPILE_EXTRA_ARGS.get(str(pmajor), '')

            beargs = ''
            if branch in BRANCH_EXTRA_ARGS:
                if pmajor in BRANCH_EXTRA_ARGS[branch]:
                    beargs = BRANCH_EXTRA_ARGS[branch][pmajor]

            for RF in REQUIREMENTS_FILES:
                if os.path.exists(os.path.join(checkout_branch, RF[0])):
                    commands.append(f'PYTHONPATH=. pip-compile {beargs} {pceargs} -o {" ".join(RF)} setup.py --upgrade-package django')
            script = ' && '.join(commands)
            cname = f'bumper_{branch}_{pmajor}'
            cmd = f'docker run --name="{cname}" -v {checkout_branch}:/app -w /app -it {IMAGE} /bin/bash -c "{script}"'
            container_commands.append(cmd)

        threads = []
        for cc in container_commands:
            threads.append(Thread(target=threaded_command, args=(cc,)))
        for thread in threads:
            thread.start()
        results = []
        for thread in threads:
            results.append(thread.join())

        # make the diffs
        for key, cp in checkout_paths.items():
            pmajor = key[1]
            patchfile = f'/tmp/galaxy_ng-{branch}-{pmajor}.diff'
            diff_pid = subprocess.run(f'git diff > {patchfile}', shell=True, cwd=cp)

        #import epdb; epdb.st()

        '''
        patchfile = f'/tmp/galaxy_ng-{branch}-{pversion}.diff'
        diff_pid = subprocess.run(f'git diff > {patchfile}', shell=True, cwd=checkout_branch)
        diff_file_map[branch][pversion] = patchfile
        #import epdb; epdb.st()

        print(f'DONE WITH {branch}')
        with open('/tmp/results.json', 'w') as f:
            f.write(json.dumps(diff_file_map, indent=2))
        '''

    #with open('/tmp/results.json', 'w') as f:
    #    f.write(json.dumps(diff_file_map, indent=2))



if __name__ == "__main__":
    main()
