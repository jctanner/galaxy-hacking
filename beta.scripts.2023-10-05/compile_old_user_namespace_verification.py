#!/usr/bin/env python3

import os
import json
import glob

from logzero import logger

from github_lib import fetch_userdata_by_id
from github_lib import fetch_userdata_by_name


def main():
    fn = 'user_namespace_map.json'
    with open(fn, 'r') as f:
        umap = json.loads(f.read())
    for k,v in umap.items():
        umap[k]['github_login_verified'] = False
        umap[k]['github_login_new'] = None
        umap[k]['github_login'] = None
        if v['extra_data']:
            umap[k]['github_login'] = v['extra_data'].get('login')

    uids = list(umap.keys())
    uids = sorted(uids, key=lambda x: int(x))
    for iduid, uid in enumerate(uids):
        udata = umap[uid]
        gusername = udata['galaxy_username']
        g_github_login = udata['github_login']

        logger.info(f"({len(uids)}|{iduid}) {uid}. {udata['galaxy_username']}")

        verified = False
        github_id = udata.get('github_id')
        if github_id:
            github_id = int(github_id)
            gdata = fetch_userdata_by_id(github_id)
            if gdata and gdata.get('id') == github_id and gdata.get('login') == gusername:
                umap[uid]['github_login_verified'] = True
                verified = True
            elif gdata and gdata.get('login'):
                if gdata['login'] != udata['github_login']:
                    umap[uid]['github_login_new'] = gdata['login']
                if gdata['login'].lower() == gusername.lower() or gdata['login'].lower() == g_github_login.lower():
                    umap[uid]['github_login_verified'] = True
                verified = True
            elif gdata and gdata.get('message') == 'Not Found':
                pass
            elif gdata:
                import epdb; epdb.st()

        if not github_id:
            gdata = fetch_userdata_by_name(gusername)
            if not gdata:
                continue
            if gdata.get('message') == 'Not Found':
                continue

            #if github_id:
            #    import epdb; epdb.st()

            if gdata.get('login') == gusername:
                umap[uid]['github_id'] = gdata['id']
                umap[uid]['github_login_verified'] = True
                verified = True
            elif gdata.get('login').lower() == gusername.lower():
                umap[uid]['github_id'] = gdata['id']
                umap[uid]['github_login_verified'] = True
                if not g_github_login:
                    umap[uid]['github_login'] = gdata['login']
                if gdata.get('login') != umap[uid].get('github_login'):
                    #if gdata['login'] == 'ccollicutt':
                    #    import epdb; epdb.st()
                    umap[uid]['github_login_new'] = gdata['login']
                verified = True
            else:
                import epdb; epdb.st()

    with open('user_namespace_map_validated.json', 'w') as f:
        f.write(json.dumps(umap, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
