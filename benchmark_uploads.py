#!/usr/bin/env python3

import datetime
import os
import requests
import subprocess
import tempfile

from requests.auth import HTTPBasicAuth


NAMESPACE = "asr"
FILENAME = "asr-linux-1.6.1.tar.gz"
MACHINES = ['galaxy-42', 'galaxy-44']
AUTH = HTTPBasicAuth('admin', 'admin')
TOKENS = {
    'galaxy-42': 'bdfb956970d54eedaaa6e9268e44a6de3860fb45',
    'galaxy-44': '6cc16aa820a2f9f5838fffe576791931490ea3ec'
}


def cfg_to_ansible_cfg(cfg):
    acfg = ''
    acfg += '[galaxy]\n'
    acfg += 'server_list = hub\n'
    acfg += '[galaxy_server.hub]\n'
    acfg += f"url=http://{cfg['ipaddress']}:8002/api/automation-hub/\n"
    acfg += f"token={cfg['token']}\n"
    return acfg


def main():

    cfg = {}

    # get the ips for each machine
    for MACHINE in MACHINES:
        pid = subprocess.run(
            f"vagrant ssh-config {MACHINE}" + " | fgrep HostName | awk '{print $2}'",
            shell=True,
            stdout=subprocess.PIPE
        )
        ipaddress = pid.stdout.decode('utf-8').strip()
        cfg[MACHINE] = {
            'ipaddress': ipaddress,
            'token': TOKENS[MACHINE],
            'headers': {'Authorization': f"token {TOKENS[MACHINE]}"},
            'durations': []
        }

    # opcheck the api
    for MACHINE in MACHINES:
        ip = cfg[MACHINE]['ipaddress']
        url = f'http://{ip}:8002/api/automation-hub/v3/collections/'
        print(url)
        rr = requests.get(url, headers=cfg[MACHINE]['headers'])
        assert rr.status_code == 200

    # make the required namespace
    for MACHINE in MACHINES:
        ip = cfg[MACHINE]['ipaddress']
        url = f'http://{ip}:8002/api/automation-hub/v3/namespaces/'
        print(url)
        rr = requests.get(url, headers=cfg[MACHINE]['headers'])
        existing = [x['name'] for x in rr.json()['data']]
        if NAMESPACE in existing:
            continue
        rr = requests.post(url, json={'name': NAMESPACE, 'groups': []}, headers=cfg[MACHINE]['headers'])
        assert rr.status_code == 201

    # make the workdirs and ansible.cfg files
    for MACHINE in MACHINES:
        tdir = tempfile.mkdtemp(prefix=f'gng-benchmark-{MACHINE}-')
        cfg[MACHINE]['workdir'] = tdir
        acfg = cfg_to_ansible_cfg(cfg[MACHINE])
        with open(os.path.join(tdir, 'ansible.cfg'), 'w') as f:
            f.write(acfg)

    # time a publish ...
    for MACHINE in MACHINES:
        fn = os.path.abspath(FILENAME)
        cmd = f'ansible-galaxy collection publish -vvvv {fn}'
        t0 = datetime.datetime.now()
        pid = subprocess.run(cmd, shell=True, cwd=cfg[MACHINE]['workdir'])
        tN = datetime.datetime.now()
        cfg[MACHINE]['durations'].append((tN - t0).total_seconds())

    import epdb; epdb.st()



if __name__ == "__main__":
    main()
