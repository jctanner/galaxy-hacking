#!/usr/bin/env python3

############################################################################
# 
# ghacktion - simulate github actions
#
#   EXAMPLE:
#       ./ghacktion --repo=jctanner/actions-testing --number=4 list
#       ./ghacktion --repo=jctanner/actions-testing --number=4 --local run \
#           --file=blank.yml --job=build
#
#   A directory structure will get laid out on disk like so ...
#       /tmp/ghacktion-XXXX/<user>/<repo>.checkout
#       /tmp/ghacktion-XXXX/<user>/<repo>
#
############################################################################

import argparse
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import yaml

from pprint import pprint

import docker
import jinja2
from jinja2 import Template
import requests


CONSTANTS = {
    'test': 'pulp',
    'PY_COLORS': '1',
    'ANSIBLE_FORCE_COLOR': '1',
    'GITHUB_PULL_REQUEST': '111',
    'GITHUB_PULL_REQUEST_BODY': 'stuff',
    'GITHUB_BRANCH': 'master',
    'GITHUB_REF': 'null',
    'GITHUB_REPO_SLUG': 'galaxy_ng',
    'GITHUB_CONTENT': 'https://github.com/test/test',
    'GITHUB_TOKEN': '1111',
    'GITHUB_EVENT_NAME': 'push',
    'GITHUB_WORKFLOW': 'foobar',
    'GITHUB_PR_COMMITS_URL': '',
    'START_COMMIT': '',
    'END_COMMIT': '',
    'BRANCH': 'master',
    'GITHUB_WORKSPACE': '/app/src/galaxy_ng',
    'GITHUB_ENV': '/app/.github_env',
    'APP_PATH': '/app',
    'GALAXY_PATH': '/app/src/galaxy_ng',
    'DEBIAN_FRONTEND': 'noninteractive',
    'SECRETS_CONTEXT': '{}'
}


class WorkflowJobStep:

    _name = None
    _ds = None
    _env = None
    _run = None
    _uses = None

    def __init__(self, ds, name=None, job=None, workflow=None):
        self._name = name
        self._ds = ds
        self._job = job
        self._workflow = workflow
        self.parse()

    def __repr__(self):
        return f'<WorkflowJobStep: {self._name or self._uses}>'

    @property
    def name(self):
        return self._name or self._uses

    def parse(self):
        """
        Set attrs from the data structure.
        """
        if 'name' in self._ds:
            self._name = self._ds['name']
        if 'env' in self._ds:
            self._env = self._ds['env']
        if 'run' in self._ds:
            self._run = self._ds['run']
        if 'uses' in self._ds:
            self._uses = self._ds['uses']

    def _fix_cryptography(self):
        """
        Fix pulp + pulpsmash (fubared) requirements.
        """

        # disabled for now?
        return

        cmd = "pip show cryptography | egrep ^Version | cut -d\: -f2 | tr -d ' '"
        pid = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        version = pid.stdout.decode('utf-8').strip()
        if version != '36.0.2':
            print('## FIXING CRYPTOGRAPY PACKAGE')
            cmd = 'pip uninstall -y cryptography'
            subprocess.run(cmd, shell=True)
            cmd = 'pip install cryptography==36.0.2'
            subprocess.run(cmd, shell=True)

    def _clean_intermediate_checkouts(self):
        """
        Cleanup all checkouts.
        """
        candidates = glob.glob('*.checkout')
        if candidates:
            for candidate in candidates:
                shutil.rmtree(candidate)

    def _ffwd_pulp_ci(self):
        """
        Enhance the pulp CI playbooks.
        """

        # ansible-playbook -v
        # .github/workflows/scripts/install.sh:ansible-playbook build_container.yaml
        # .github/workflows/scripts/install.sh:ansible-playbook start_container.yaml
        subprocess.run(
            "sed -i.bak 's|ansible-playbook build|ansible-playbook -v build|g' .github/workflows/scripts/install.sh",
            shell=True
        )
        subprocess.run(
            "sed -i.bak 's|ansible-playbook start|ansible-playbook -v start|g' .github/workflows/scripts/install.sh",
            shell=True
        )

        '''
        # do not constantly rebuild container
        #   .ci/ansible/build_container.yaml
        subprocess.run(
            "sed -i.bak 's#command: \"docker build #shell: \"docker image inspect pulp:ci_build || docker build#' .ci/ansible/build_container.yaml",
            shell=True
        )
        '''

        # temporary workaround for permission issues
        fn = '.ci/ansible/Containerfile.j2'
        if os.path.exists(fn):
            newline = 'RUN chmod -R 777 /etc/pulp /var/log /var/lib/pulp'
            with open(fn, 'r') as f:
                fdata = f.read()
            flines = fdata.split('\n')
            if newline not in flines:
                entrypoint = [x for x in flines if x.startswith('ENTRYPOINT')][0]
                flines = [x for x in flines if x != entrypoint]
                flines.append(newline)
                flines.append(entrypoint)
                with open(fn, 'w') as f:
                    f.write('\n'.join(flines))

        # use an older pulpci image tag?
        # BAD
        #   https://github.com/pulp/pulp-oci-images/pkgs/container/pulp-ci-centos/43695358?tag=https
        #   ghcr.io/pulp/pulp-ci-centos:https


    def _alter_pytest(self):
        """
        Add debuggable kwargs to pytest.
        """
        subprocess.run(
            "sed -i.bak 's|pytest -v|pytest --capture=no -v|g' .github/workflows/scripts/script.sh",
            shell=True
        )

    def before(self):
        """
        Kinda like unittest class before.
        Runs before each step.
        """
        self._clean_intermediate_checkouts()
        self._fix_cryptography()
        self._ffwd_pulp_ci()
        #self._alter_pytest()

    def after(self):
        """
        Kinda like unittest class after.
        Runs after each step.
        """
        self._fix_cryptography()

    def get_github_env(self):
        """
        Read the env from the saved file.
        """
        fname = '.github_env'
        env = {}
        if os.path.exists(fname):
            with open(fname, 'r') as f:
                fdata = f.read()
            lines = fdata.split('\n')
            lines = [x.strip() for x in lines if x.strip()]
            for line in lines:
                parts = line.split('=', 1)
                key = parts[0]
                val = parts[1]
                env[key] = val
        return env

    def update_github_env(self, newkey, newval):
        """
        Create or update a new env var in the stored file.
        """
        fname = '.github_env'
        env = {}
        if os.path.exists(fname):
            with open(fname, 'r') as f:
                fdata = f.read()
            lines = fdata.split('\n')
            lines = [x.strip() for x in lines if x.strip()]
            for line in lines:
                parts = line.split('=', 1)
                key = parts[0]
                val = parts[1]
                env[key] = val

        env[newkey] = newval
        with open(fname, 'w') as f:
            for k,v in env.items():
                f.write(f'{k}={v}\n')

    @property
    def secrets(self):
        """
        Return github secrets.
        """
        # We don't want to give any secrets in this setup.
        return {
            'GITHUB_TOKEN': ''
        }

    @property
    def github(self):
        env = self.get_github_env()

        # GITHUB_PR_COMMITS_URL: ${{ github.event.pull_request.commits_url }}
        pjson = json.loads(env['GITHUB_PR_JSON'])

        _before = env['GITHUB_SHA']
        _after = env['GITHUB_BASE_SHA']

        gh = {
            'event': {
                'before': _before,
                'after': _after,
                'pull_request': {
                    'user': pjson['user'],
                    'base': {
                        'sha': None
                    },
                    'commits_url': pjson['commits_url']
                }
            },
            'sha': env['GITHUB_SHA']
        }
        return gh

    def checkout_v2(self):
        self.checkout_v3()

    def checkout_v3(self):
        # https://github.com/actions/checkout/blob/main/src/main.ts
        # https://github.com/actions/checkout/blob/main/src/git-source-provider.ts

        # git init in the /home/runner/work/<reponame>/<reponame> dir
        # git remote add origin <repositoryurl>
        # get default branch
        # if fetchdepth <= 0
        #   refspec = refspecforallhistory
        #   git fetch refspec
        # else
        #   refspec = settings.commit
        #   git fetch refspec
        # git.checkout(checkoutInfo.ref, checkoutInfo.startPoint)

        env = self.get_github_env()
        repo = env['GITHUB_REPOSITORY']

        # We don't want to do anything in this step if it's being
        # run from a local checkout.
        if str(repo) == 'None':
            self.update_github_env('GITHUB_PR_JSON', json.dumps({
                'user': '',
                'commits_url': '',
            }))
            self.update_github_env('GITHUB_SHA', '')
            self.update_github_env('GITHUB_BASE_REF', '')
            self.update_github_env('GITHUB_BASE_SHA', '')
            self.update_github_env('GITHUB_HEAD_REF', '')
            self.update_github_env('GITHUB_HEAD_SHA', '')
            self.update_github_env('GITHUB_PR_COMMITS_URL', '')
            return

        repositoryurl = f'https://github.com/{repo}'

        # https://api.github.com/repos/jctanner/actions-testing/pulls/4
        pr_number = env['GITHUB_PR_NUMBER']
        api_url = f'https://api.github.com/repos/{repo}/pulls/{pr_number}'
        print(api_url)
        rr = requests.get(api_url)
        pprint(rr.json())
        self.update_github_env('GITHUB_PR_JSON', json.dumps(rr.json()))

        # THE merge commit? ... also github.sha!
        merge_commit_sha = rr.json()['merge_commit_sha']
        github_sha = rr.json()['merge_commit_sha']
        self.update_github_env('GITHUB_SHA', github_sha)

        default_branch = rr.json()['head']['repo']['default_branch']

        # main
        base_ref = rr.json()['base']['ref']
        self.update_github_env('GITHUB_BASE_REF', base_ref)
        base_sha = rr.json()['base']['sha']
        self.update_github_env('GITHUB_BASE_SHA', base_sha)

        # jctanner-patch-4
        head_ref = rr.json()['head']['ref']
        self.update_github_env('GITHUB_HEAD_REF', head_ref)
        head_sha = rr.json()['head']['sha']
        self.update_github_env('GITHUB_HEAD_SHA', head_sha)

        self.update_github_env('GITHUB_PR_COMMITS_URL', rr.json()['commits_url'])

        subprocess.run('git init .', shell=True)
        subprocess.run(f'git remote add origin {repositoryurl}', shell=True)
        subprocess.run(f'git fetch origin', shell=True)
        subprocess.run(f'git checkout {base_ref}', shell=True)
        subprocess.run(f'git fetch origin {github_sha}', shell=True)
        subprocess.run(f'git checkout {github_sha}', shell=True)

    def setup_python_v3(self):

        env = self.get_github_env()

        venv_path = os.path.expanduser('~/ghacktion.venv')

        # make a venv?
        if os.path.exists(venv_path):
            shutil.rmtree(venv_path)
        pid = subprocess.run(f'virtualenv {venv_path}', shell=True)
        assert pid.returncode == 0

        # need some packages?
        for pkg in ['pytest', 'epdb']:
            subprocess.run(f'{venv_path}/bin/pip install {pkg}', shell=True)

        # get current path ...
        PATH = env.get('PATH')
        if PATH is None:
            res = subprocess.run('echo $PATH', shell=True, env=env, stdout=subprocess.PIPE)
            PATH = res.stdout.decode('utf-8').strip()
        venv_bin_path = os.path.abspath(os.path.expanduser('.venv/bin'))
        venv_bin_path = os.path.join(venv_path, 'bin')
        if not PATH.startswith(f'{venv_bin_path}:'):
            PATH = f'{venv_bin_path}:{PATH}'

        # how to make it active for all future python commands?
        self.update_github_env('PATH', PATH)


    def execute(self, matrix=None, checkout=None, debug=False):

        print('#' * 50)
        print(f'# STEP: {self.name}')
        print('#' * 50)

        if self._uses is not None:
            method_name = self._uses
            method_name = method_name.replace('actions/', '')
            method_name = method_name.replace('@', '_')
            method_name = method_name.replace('-', '_')
            method = getattr(self, method_name)
            method()
            return

        self.before()

        env = os.environ.copy()
        # load the cached env vars ...
        env.update(self.get_github_env())
        if self._env:
            env.update(self._env)

        # need a custom filter
        #   REDIS_DISABLED: ${{ contains('', matrix.env.TEST) }}
        def jinja_contains(a,b):
            return b in a

        # need another custom filter
        #   SECRETS_CONTEXT: ${{ toJson(secrets) }}
        def to_json(data):
            return json.dumps(data)

        # template env vars ...
        for k,v in env.items():
            if '${{' not in v:
                continue

            jenv = jinja2.Environment()
            jenv.filters['contains'] = jinja_contains

            tval = v.replace('${{', '{{')

            '''
            t = Template(tval)
            try:
                env[k] = t.render(matrix=matrix, github=self.github, secrets=self.secrets)
            except Exception as e:
                print(e)
                import epdb; epdb.st()
            '''

            tmpl = jenv.from_string(tval)
            newval = tmpl.render(
                matrix=matrix,
                github=self.github,
                secrets=self.secrets,
                contains=jinja_contains,
                toJson=to_json
            )
            env[k] = newval


        # echo "TEST=${{ matrix.env.TEST }}" >> $GITHUB_ENV\n
        if '${{' in self._run:
            cmd = self._run
            cmd_t = cmd.replace('${{', '{{')
            t = Template(cmd_t)
            tkwargs = {
                'matrix': matrix,
                'github': self.github,
                'secrets': self.secrets
            }

            # these keys need to move to the top level if given
            if 'include' in matrix:
                tkwargs['matrix'] = matrix['include']

            try:
                cmd = t.render(**tkwargs)
            except Exception as e:
                print(e)
                raise Exception (e)
                import epdb; epdb.st()
        else:
            cmd = self._run

        print(f'# {cmd}')
        cwd = checkout or os.getcwd()
        pid = subprocess.run(cmd, shell=True, env=env, cwd=cwd)
        #pid = subprocess.run(cmd, shell=True, env=env)

        if pid.returncode != 0:
            print(f'==> STEP FAILED: {self.name}')
            if debug:
                import epdb; epdb.st()
            raise Exception(f'STEP FAILED: {self.name}')

        assert pid.returncode == 0

        print(f'==> STEP SUCCESS: {pid.returncode}')

        self.after()


class WorkflowJob:

    _name = None
    _ds = None
    _steps = None
    _matrix = None
    _cwd = None

    def __init__(self, ds, name=None, workflow=None):
        self._name = name
        self._ds = ds
        self._workflow = workflow
        self.parse()

    def __repr__(self):
        return f'<WorkflowJob: {self._name}>'

    def parse(self):

        self._steps = []
        for sdata in self._ds['steps']:
            stp = WorkflowJobStep(sdata, name=sdata.get('name'), job=self, workflow=self._workflow)
            self._steps.append(stp)

        # FIXME - only handles a matrix with a single list
        if 'strategy' in self._ds:
            if 'matrix' in self._ds['strategy']:
                matrix = []
                bits = self._ds['strategy']['matrix']
                if 'env' in bits:
                    for item in bits['env']:
                        key = list(item.keys())[0]
                        val = list(item.values())[0]
                        m = {'env': dict([(key, val)])}
                        matrix.append(m)

                elif 'include' in bits:
                    for ds in bits['include']:
                        # this is a dict of vars for templating
                        #import epdb; epdb.st()
                        #key = list(item.keys())[0]
                        #val = list(item.values())[0]
                        #m = {'env': dict([(key, val)])}
                        m = {'include': ds}
                        matrix.append(m)

                self._matrix = matrix

    @property
    def name(self):
        return self._name

    @property
    def steps(self):
        return self._steps

    def clean(self):

        # each job should have a fresh env?
        #if os.path.exists(CONSTANTS['GITHUB_ENV']):
        #    os.remove(CONSTANTS['GITHUB_ENV'])

        # .netrc is stupid
        if os.path.exists(os.path.expanduser('~/.netrc')):
            os.remove(os.path.expanduser('~/.netrc'))

        '''
        # pulp ci scripts assume everything is clean, so we have to cleanup everytime ...
        packages = [
            'galaxy-importer',
            'pulp_ansible',
            'pulp_container',
            'pulpcore',
            'pulp-openapi-generator',
            'pulp-smash'
        ]
        for pkg in packages:
            pkg_path = os.path.join(CONSTANTS['APP_PATH'], 'src', pkg)
            if os.path.exists(pkg_path):
                shutil.rmtree(pkg_path)
        '''

        psmash = os.path.join(os.path.expanduser('~'), '.config', 'pulp_smash')
        if os.path.exists(psmash):
            shutil.rmtree(psmash)

        local = os.path.join(os.path.expanduser('~'), '.local')
        if os.path.exists(local):
            shutil.rmtree(local)

        gem = os.path.join(os.path.expanduser('~'), '.gem')
        if os.path.exists(gem):
            shutil.rmtree(gem)

        cache = os.path.join(os.path.expanduser('~'), '.cache')
        if os.path.exists(cache):
            shutil.rmtree(cache)

        _docker = os.path.join(os.path.expanduser('~'), '.docker')
        if os.path.exists(_docker):
            shutil.rmtree(_docker)

        _ansible = os.path.join(os.path.expanduser('~'), '.ansible')
        if os.path.exists(_ansible):
            shutil.rmtree(_ansible)

    def execute(self, checkout=None, debug=False):

        print('#' * 50)
        print(f'# {self._name}')
        print('#' * 50)

        if self._matrix:

            for matrix in self._matrix:

                # skip the docs,azure,s3,stream tests
                if 'env' in matrix and matrix['env']['TEST'] != 'pulp':
                    continue

                self.clean()

                for wstep in self._steps:
                    wstep.execute(matrix=matrix, checkout=checkout, debug=debug)

        else:

            self.clean()

            for wstep in self._steps:
                wstep.execute(checkout=checkout, debug=debug)


class Workflow:

    _name = None
    _ds = None
    _jobs = None
    _job_names = None
    _cwd = None

    def __init__(self, filename, checkout_path=None, workspace=None):
        self.filename = filename
        self.checkout_path = checkout_path
        workspace = workspace
        self.parse()

    def __repr__(self):
        return f'<Workflow: {self.filename} {self._name}>'

    def parse(self):
        with open(self.filename, 'r') as f:
            self._ds = yaml.safe_load(f)
        self._name = self._ds.get('name')

        self._job_names = list(self._ds['jobs'].keys())

        self._jobs = []
        for jn in self._job_names:
            jdata = self._ds['jobs'][jn]
            job = WorkflowJob(jdata, name=jn, workflow=self)
            self._jobs.append(job)

    @property
    def jobs(self):
        return self._jobs

    @property
    def job_names(self):
        return self._job_names


class AbstractExecutor:

    _backend_method = None
    _repo = None
    _number = None
    _dclient = None
    _instance = None
    _workspace = None
    _workflow = None
    _job = None
    _checkout = None
    _debug = False
    _pause = False
    _temporary_checkout = False
    _noclean = False

    #_IMAGE = 'python:3'
    _IMAGE = 'ghacktion:3'

    _DOCKERFILE = '''
    FROM python:3
    RUN pip3 install --upgrade pyyaml
    RUN pip3 install --upgrade docker
    RUN pip3 install --upgrade jinja2

    RUN test -f docker-20.10.16.tgz || wget https://download.docker.com/linux/static/stable/x86_64/docker-20.10.16.tgz
    RUN test -d docker || tar xzvf docker-20.10.16.tgz
    RUN test -f /usr/local/bin/docker || cp docker/docker /usr/local/bin/.
    '''

    def __init__(
        self,
        backend='docker',
        repo=None,
        number=None,
        workspace=None,
        workflow=None,
        job=None,
        checkout=None,
        debug=False,
        pause=False,
        noclean=False
    ):

        self._backend_method = backend
        self._repo = repo
        self._number = number
        self._workflow = workflow
        self._job = job
        self._checkout = checkout
        self._workspace = workspace
        self._debug = debug
        self._pause = pause
        self._noclean = noclean

        self.GITHUB_REPOSITORY_OWNER = None
        if self._repo:
            self.GITHUB_REPOSITORY_OWNER = os.path.dirname(self._repo)
        else:
            self.GITHUB_REPOSITORY_OWNER = \
                self.get_github_checkout_repo_user(self._checkout)

        self.create_workspace()
        self.create_checkout()

        # make the container
        if self._backend_method == 'docker':
            self._dclient = docker.from_env()
            self.verify_docker_image()
            self._instance = self._dclient.containers.run(
                self._IMAGE,
                "tail -f /dev/null",
                detach=True,
                volumes=[
                    '/var/run/docker.sock:/var/run/docker.sock',
                    f'{self._workspace}:/workspace:rw'
                ]
            )

    def get_github_checkout_repo_user(self, checkout):
        pid = subprocess.run(
            "git remote -v | egrep -m1 ^origin | awk '{print $2}'",
            shell=True,
            cwd=checkout,
            stdout=subprocess.PIPE
        )
        ds = pid.stdout.decode('utf-8').strip()
        ds = ds.replace('git@github.com:', '')
        ds = ds.replace('https://github.com/', '')
        return ds.split('/')[0]

    def __del__(self):
        if not self._noclean:
            if self._backend_method == 'docker' and self._instance:
                print('STOP DOCKER')
                self._instance.stop()

        if not self._noclean:
            if self._workspace and os.path.exists(self._workspace):
                try:
                    shutil.rmtree(self._workspace)
                except Exception as e:
                    subprocess.run(f'sudo rm -rf {self._workspace}', shell=True)

    def verify_docker_image(self):
        '''Verify or build the required container'''

        #if self._dclient.images.get(self._IMAGE):
        #    return True

        dockerfile = self._DOCKERFILE
        dockerfile = dockerfile.split('\n')
        dockerfile = [x.lstrip() for x in dockerfile]
        dockerfile = '\n'.join(dockerfile)

        fn = os.path.join(self._workspace, 'Dockerfile')
        with open(fn, 'w') as f:
            f.write(dockerfile)

        cmd = f'docker build -t {self._IMAGE} .'
        pid = subprocess.run(cmd, shell=True, cwd=self._workspace)

    @property
    def instance(self):
        if self._instance:
            return self._instance

        # what to do if local? ...
        #import epdb; epdb.st()

    def create_workspace(self):
        '''We need a root dir to store all of the stuff'''

        if self._workspace is None:
            tdir = tempfile.mkdtemp(prefix='ghacktion-')
            if not self._repo and self._checkout:
                co_abs = os.path.abspath(self._checkout)
                co_bp = os.path.basename(self._checkout)
                self._workspace = os.path.join(
                    tdir,
                    self.GITHUB_REPOSITORY_OWNER,
                    co_bp
                )
                topdir = os.path.dirname(self._workspace)
                if not os.path.exists(topdir):
                    os.makedirs(topdir)
                pid = subprocess.run(f'ln -s {co_abs} {co_bp}', cwd=topdir, shell=True)
                assert pid.returncode == 0
            else:
                self._workspace = os.path.join(tdir, self._repo)
            if not os.path.exists(self._workspace):
                os.makedirs(self._workspace)

            env_file = os.path.join(self._workspace, '.github_env')
            if self._backend_method == 'docker':
                env_file = os.path.join('/workspace', self._repo, '.github_env')

            # preseed some info ...
            env = {
                'GITHUB_PR_NUMBER': self._number,
                'GITHUB_ENV': env_file,
                'GITHUB_HEAD_REF': None,
                'GITHUB_REF': None,
                'GITHUB_REF_NAME': None,
                'GITHUB_SHA': None,
                'GITHUB_EVENT_NAME': 'pull_request',
                'GITHUB_WORKSPACE': self._workspace,
                'GITHUB_WORKFLOW': 'CI', #FIXME
                'GITHUB_REPOSITORY': self._repo,
                'GITHUB_REPOSITORY_OWNER': self.GITHUB_REPOSITORY_OWNER
            }
            fn = os.path.join(self._workspace, '.github_env')
            with open(fn, 'w') as f:
                for k, v in env.items():
                    f.write(f'{k}={v}\n')

            if self._backend_method == 'local':
                os.chdir(self._workspace)

    def create_checkout(self):
        '''We need the checkout to be inside the workspace'''
        if self._backend_method == 'local' and self._checkout:
            dst = os.path.join(self._workspace, os.path.basename(self._checkout))
            if self._checkout != dst and not os.path.exists(dst):
                shutil.copytree(self._checkout, dst)

        elif self._backend_method in ['local', 'docker'] and not self._checkout:

            # make a checkout for FILE PARSING ONLY!!!????!!!!???
            #self._checkout = os.path.join(self._workspace, os.path.basename(self._repo) + '.checkout')
            self._checkout = os.path.join(
                os.path.dirname(self._workspace),
                os.path.basename(self._repo) + '.checkout'
            )
            cmd = f'git clone https://github.com/{self._repo} {self._checkout}'
            pid = subprocess.run(cmd, shell=True)
            assert pid.returncode == 0
            self._temporary_checkout = True

    def run(self, checkout=None):

        if self._backend_method == 'local':

            # cd into the checkout
            if not self._temporary_checkout and checkout is None and self._checkout:
                os.chdir(self._checkout)

            # load from the checkout
            workflow_files = glob.glob(f'{self._checkout}/.github/workflows/*.yml')
            workflow_files += glob.glob(f'{self._checkout}/.github/workflows/*.yaml')
            workflow_files = sorted(set(workflow_files))
            workflow_files = [x.replace(self._checkout + '/', '') for x in workflow_files]
            selected_workflow_files = [
                x for x in workflow_files if os.path.basename(x) == os.path.basename(self._workflow)
            ]

            if not selected_workflow_files:
                print('ERROR: no matching workflows found')
                print('valid names ...')
                for x in workflow_files:
                    print(f'\t{os.path.basename(x)}')
                sys.exit(1)
            workflows = [
                Workflow(os.path.join(self._checkout, x), workspace=self._workspace) for x
                in selected_workflow_files
            ]

            # ensure input jobname was correct
            if self._job:
                job_matches = [x for x in workflows for y in x.jobs if y.name == self._job]
                if not job_matches:
                    print('ERROR: no matching jobs found')
                    print('valid names ...')
                    for wf in workflows:
                        for job in wf.jobs:
                            print(f'\t{job.name}')
                    sys.exit(1)

            # CLEAN UP THE INTERMEDIATE CHECKOUT?
            if self._temporary_checkout and not self._noclean:
                shutil.rmtree(self._checkout)

            for workflow in workflows:

                #wfn = os.path.join(self._checkout, wf)
                #print(wfn)
                #workflow = Workflow(wfn, workspace=self._workspace)

                for job in workflow.jobs:
                    if self._job and job.name != self._job:
                        continue
                    print(f'RUN {job.name}')
                    #import epdb; epdb.st()
                    job.execute(debug=self._debug)

            print('DONE')
            sys.exit(0)

        if self._backend_method == 'docker':
            # copy this script to the workspace
            fn = __file__
            bn = os.path.basename(fn)
            dst = os.path.join(self._workspace, bn)
            shutil.copy(fn, dst)

            # point at the workflow file inside the container
            wfn = os.path.join(os.path.basename(self._checkout), '.github', 'workflows', self._workflow)

            # re-run this script inside the container
            cmd = f'./workspace/{bn}'
            if self._repo:
                cmd += f' --repo={self._repo}'
            if self._number:
                cmd += f' --number={self._number}'
            cmd += ' --local'
            cmd += ' run'
            cmd += f' --file={wfn}'
            if self._job:
                cmd += f' --job={self._job}'
            if self._debug:
                cmd += f' --debug'

            sdata = [
                '#!/bin/bash',
                f'mkdir -p /workspace/{self._repo}'
                f'cd /workspace/{self._repo}',
                cmd
            ]

            sfn = os.path.join(self._workspace, 'run.sh')
            with open(sfn, 'w') as f:
                f.write('\n'.join(sdata))
            subprocess.run(f'chmod +x {sfn}', shell=True)

            # run the script ...
            #sfn2 = os.path.join('/workspace', self._repo, 'run.sh')
            sfn2 = os.path.join('/workspace', 'run.sh')
            pid = subprocess.run(f'docker exec -it {self.instance.name} {sfn2}', shell=True)

            assert pid.returncode == 0


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', help='<user>/<repo>')
    parser.add_argument('--number', help='pr number [-1 == HEAD]')
    parser.add_argument('--local', action='store_true', help='run locally')
    parser.add_argument('--checkout', help='path to a local checkout')

    subparsers = parser.add_subparsers(dest='command')
    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('--file')
    list_parser.add_argument('--job', help='ignored')

    run_parser = subparsers.add_parser('run')
    run_parser.add_argument('--file')
    run_parser.add_argument('--job')
    run_parser.add_argument('--step')
    run_parser.add_argument('--pause', action='store_true', help='pause after each step')
    run_parser.add_argument('--debug', action='store_true')
    run_parser.add_argument('--noclean', action='store_true')

    args = parser.parse_args()


    if args.command == 'list':
        with tempfile.TemporaryDirectory(prefix='ghacktion-') as tdir:

            checkout = None

            if args.checkout:
                # work from the local checkout ... 
                checkout = args.checkout

            else:

                # make a checkout for enumeration ...

                if not args.repo:
                    raise Exception('A repo must be provided if not a local checkout')

                cbase = os.path.basename(args.repo) + '.checkout'
                checkout = os.path.join(tdir, cbase)

                # make a checkout first ...
                cmd = f'git clone https://github.com/{args.repo} {checkout}'
                pid = subprocess.run(cmd, shell=True)

            # enumerate workflow files ...
            workflow_files = glob.glob(f'{checkout}/.github/workflows/*.yml')
            workflow_files += glob.glob(f'{checkout}/.github/workflows/*.yaml')
            workflow_files = sorted(set(workflow_files))

            if args.file:
                workflow_files = [
                    x for x in workflow_files if os.path.basename(x) == os.path.basename(args.file)
                ]

            # parse
            workflows = [Workflow(x) for x in workflow_files]

            print('-' * 50)
            for wf in workflows:
                print(f'# {wf.filename}')
                for job in wf.jobs:
                    print(job.name)
                    for ids,step in enumerate(job.steps):
                        print(f'\t{ids}. {step.name}')
            sys.exit(0)

    if args.command == 'run':

        if args.local:
            backend = 'local'
        else:
            backend = 'docker'

        AbstractExecutor(
            backend=backend,
            repo=args.repo,
            number=args.number,
            #workspace=tdir,
            workflow=args.file,
            job=args.job,
            checkout=args.checkout,
            debug=args.debug,
            pause=args.pause,
            noclean=args.noclean
        ).run()


if __name__ == "__main__":
    main()
