#!/usr/bin/env python


import json
import subprocess


def test_role_install(namespace_name, role_name):
    cmd [
        'ansible-galaxy',
        'role',
        'install',
        '-s', 'https://old-galaxy.ansible.com',
        '-p', '/tmp/testroles'
        f'{namespace_name}.{role_name}'
    ]
    pid = subprocess.run(" ".join(cmd), shell=True)
    return pid


def main():
    with open('old_roles.json', 'r') as f:
        roles = json.loads(f.read())
    print(f'TOTAL ROLES: {len(roles)}')

    byid = {}
    for role in roles:
        byid[role['id']] = role

    bykey = {}
    for role in roles:
        thiskey = (role['github_user'].lower(), role['github_repo'])
        if thiskey not in bykey:
            bykey[thiskey] = []
        bykey[thiskey].append(role['id'])

    print(f'TOTAL UNIQUE BY github_user+github_repo: {len(list(bykey.keys()))}')
    non_unique = len(roles) - len(list(bykey.keys()))
    print(f'TOTAL !UNIQUE BY github_user+github_repo: {non_unique}')

    keys = sorted(list(bykey.keys()))
    count = 0
    for idk,key in enumerate(keys):
        role_ids = bykey[key]
        if len(role_ids) == 1:
            continue

        count += 1
        print(f'{count}. {key}')
        for role_id in role_ids:
            this_role = byid[role_id]
            fqn = this_role['summary_fields']['namespace']['name'] + '.' + this_role['name']
            print(f'\tid:{role_id} fqn:{fqn} github_user:{this_role["github_user"]} github_repo:{this_role["github_repo"]}')
        #import epdb; epdb.st()


    print('-' * 100)

    # how many github_user's don't match namespace.name ?
    mismatched = []
    for role in roles:
        github_user = role['github_user']
        namespace_name = role['summary_fields']['namespace']['name']
        if namespace_name is None:
            # import epdb; epdb.st()
            continue

        if github_user.lower() != namespace_name.lower():
            mismatched.append([role['id'], namespace_name, github_user])


    import epdb; epdb.st()


if __name__ == "__main__":
    main()