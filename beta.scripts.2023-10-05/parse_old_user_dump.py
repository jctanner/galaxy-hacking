#!/usr/bin/env python

import json


def parse_sql(fn):

    column_names = []
    rows = []

    with open(fn, 'r') as f:
        raw = f.read()
    lines = raw.split('\n')

    column_names = lines[0].split('|')
    column_names = [x.strip() for x in column_names if x.strip()]
    #import epdb; epdb.st()

    for line in lines[1:]:
        if line.startswith('-'):
            continue
        if not line.strip():
            continue
        if 'rows)' in line:
            continue

        #print(line)

        values = line.split('|')
        values = [x.strip() for x in values]

        row = {}
        for idx,x in enumerate(column_names):
            try:
                row[x] = values[idx]
            except IndexError:
                pass
        rows.append(row)

    #import epdb; epdb.st()
    return rows



def main():

    '''
    users = parse_sql('galaxy_user.txt')
    idmap = dict((x['id'], x) for x in users)
    username_map = dict((x['username'], x) for x in users)

    social = parse_sql('social_auth_usersocialauth.txt')
    for idx,x in enumerate(social):
        social[idx]['extra_data'] = json.loads(x['extra_data'])
    login_map = dict((x['extra_data']['login'], x) for x in social)

    for idx,x in enumerate(social):
        login = x['extra_data']['login']
        user_id = x['user_id']

        user = idmap[user_id]
        gusername = user['username']

        if gusername != login:
            print(f'social:{login} -> galaxy:{gusername}')
            import epdb; epdb.st()
    '''

    fn = 'old_users.txt'
    with open(fn, 'r') as f:
        raw = f.read()
    rows = parse_sql(raw)

    import epdb; epdb.st()


if __name__ == "__main__":
    main()
