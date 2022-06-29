#!/usr/bin/env python3

import os
import shutil
import subprocess
import tempfile


def make_collection(namespace, name, version):
    tdir = tempfile.mkdtemp(prefix='colbuild-')
    pid = subprocess.run(
        f'ansible-galaxy collection init {namespace}.{name}',
        shell=True,
        cwd=tdir
    )

    basedir = os.path.join(tdir, namespace, name)
    galaxy_fn = os.path.join(basedir, 'galaxy.yml')

    cmd = f"sed -i.bak 's/tags\:\ \[\]/tags\:\ \[\"tools\"\]/g' {galaxy_fn}"
    subprocess.run(cmd, shell=True)

    cmd = f"sed -i.bak 's|version\:\ 1.0.0|version:\ {version}|g' {galaxy_fn}"
    subprocess.run(cmd, shell=True)

    # add runtime.yml
    os.mkdir(os.path.join(basedir, 'meta'))
    with open(os.path.join(basedir, 'meta', 'runtime.yml'), 'w') as f:
        f.write('requires_ansible: ">=2.10"\n')

    pid = subprocess.run('ansible-galaxy collection build .', shell=True, cwd=basedir, stdout=subprocess.PIPE)
    fn = pid.stdout.decode('utf-8').strip()
    fn = fn.split()[-1]
    return fn


def publish_artifact(artifact):
    tdir = tempfile.mkdtemp(prefix='colpub-')
    cfg = os.path.join(tdir, 'ansible.cfg')
    with open(cfg, 'w') as f:
        f.write('[galaxy]\n')
        f.write('server_list = hub\n')
        f.write('[galaxy_server.hub]\n')
        f.write('url=http://localhost:5001/api/automation-hub/\n')
        f.write('username=admin\n')
        f.write('password=admin\n')

    cmd = f'ansible-galaxy collection publish {artifact}'
    subprocess.run(cmd, shell=True, cwd=tdir)
    shutil.rmtree(tdir)

    atmp = os.path.dirname(os.path.dirname(os.path.dirname(artifact)))
    if atmp.startswith('/tmp'):
        shutil.rmtree(atmp)


def main():
    for x in range(99, 120):
        print(x)
        artifact = make_collection('autohubtest2', 'foobar', f'1.0.{x}')
        publish_artifact(artifact)


if __name__ == "__main__":
    main()
