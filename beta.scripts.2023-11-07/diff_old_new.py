#!/usr/bin/env python

import os
import uuid
import argparse

import json
import glob
import requests

from logzero import logger

from github_lib import fetch_userdata_by_id
from github_lib import fetch_userdata_by_name
from namespace_utils import map_v3_namespace
from namespace_utils import generate_v3_namespace_from_attributes
from cacher import Cacher
from scrapers import scrape_v3_namespaces
from scrapers import scrape_objects

GALAXY_TOKEN = os.environ.get('GALAXY_TOKEN')



class GalaxyComparator:

    # SCRAPED ...

    downstream_legacy_roles = None
    downstream_legacy_namespaces = None
    downstream_v3_namespaces = None
    downstream_v3_collections = None
    downstream_legacy_users = None

    upstream_legacy_namespaces = None
    upstream_legacy_roles = None
    upstream_legacy_users = None
    upstream_v2_collections = None

    # PROCESSED ...

    downstream_legacy_namespaces_by_name = None
    downstream_legacy_lowercase_namespace_name_map = None
    downstream_v3_namespaces_by_name = None
    downstream_v3_collections_by_fqcn = None
    downstream_legacyroles_by_fqrn = None
    downstream_legacyusers_by_github_id = None
    downstream_legacyusers_by_username = None

    upstream_collection_namespace_names = None
    upstream_legacyrole_namespace_names = None
    upstream_legacyroles_by_fqrn = None
    upstream_legacy_namespaces_by_name = None
    upstream_legacy_users_by_name = None


    def __init__(self, args):

        self.args = args

        # make cache
        self.cacher = Cacher()

        if self.args.refresh_downstream_cache:
            self.cacher.wipe_server(args.downstream)
            return
        # cacher.wipe_server('https://galaxy.ansible.com/api/v1/namespaces')

        # get all the data
        self.collect_data()
        self.process_data()

        #import epdb; epdb.st()
        self.compare_data()

    def collect_data(self):

        # get all old roles
        self.upstream_legacy_roles = scrape_objects(
            'roles',
            self.cacher,
            api_version='v1',
            server=self.args.upstream
        )

        # get all new roles
        self.downstream_legacy_roles = scrape_objects(
            'roles',
            self.cacher,
            api_version='v1',
            server=self.args.downstream
        )

        # get all old collections
        self.upstream_v2_collections = scrape_objects(
            'collections',
            self.cacher,
            api_version='v2',
            server=self.args.upstream
        )

        # get all new collections
        self.downstream_v3_collections = scrape_objects(
            'collections',
            self.cacher,
            api_version='v3',
            server=self.args.downstream
        )

        # get all users from new ...
        self.upstream_legacy_users = scrape_objects(
            'users',
            self.cacher,
            api_version='v1',
            server=self.args.upstream
        )

        # get all users from new ...
        self.downstream_legacy_users = scrape_objects(
            'users',
            self.cacher,
            api_version='v1',
            server=self.args.downstream
        )

        # get all v3 namespaces from new
        self.downstream_v3_namespaces = scrape_v3_namespaces(
            self.cacher,
            server=self.args.downstream
        )

        # get all namespaces from old
        self.upstream_legacy_namespaces = scrape_objects(
            'namespaces',
            self.cacher,
            api_version='v1',
            server=self.args.upstream
        )

        # get all namespace from new
        self.downstream_legacy_namespaces = scrape_objects(
            'namespaces',
            self.cacher,
            api_version='v1',
            server=self.args.downstream
        )

    def fuzzy_match_downstream_roles(self, fqrn):
        upstream = self.upstream_legacyroles_by_fqrn[fqrn]
        github_user = upstream['github_user']
        github_repo = upstream['github_repo']

        if fqrn in self.downstream_legacyroles_by_fqrn:
            return [self.downstream_legacyroles_by_fqrn[fqrn]]

        matches = []
        for dfqrn, role in self.downstream_legacyroles_by_fqrn.items():
            if role['github_user'].lower() == github_user.lower() and \
                    role['github_repo'].lower() == github_repo.lower():
                matches.append(dfqrn)
                continue

        #import epdb; epdb.st()
        return matches

    def bind_provider(self, server, v1_id, v3_id):
        """Set the provider namespace on a legacy namespace."""

        # get the legacy namespace first ...
        legacy_url = server + f'/api/v1/namespaces/{v1_id}/'
        rr = requests.get(legacy_url)
        v1_data = rr.json()

        # don't change if already set
        if v1_data['summary_fields']['provider_namespaces']:
            return

        # FIXME
        return

        payload = {
            'id': v3_id
        }
        post_url = legacy_url + 'providers/'
        prr = requests.put(
            post_url,
            headers={'Authorization': f'token {GALAXY_TOKEN}'},
            json=payload
        )
        logger.info(f'\t\tprovider update status code: {prr.status_code}')
        #import epdb; epdb.st()

    def process_data(self):

        self.upstream_legacy_namespaces_by_name = {}
        self.downstream_legacy_namespaces_by_name = {}

        self.downstream_v3_namespaces_by_name = {}

        # map out the downstream legacy namespace names as lowercase
        # so we can later check for duplication ...
        self.downstream_legacy_lowercase_namespace_name_map = {}

        self.upstream_users_by_username = {}
        for upstream_user in self.upstream_legacy_users:
            self.upstream_users_by_username[upstream_user['username']] = upstream_user

        for upstream_legacy_namespace in self.upstream_legacy_namespaces:
            self.upstream_legacy_namespaces_by_name[upstream_legacy_namespace['name']] = upstream_legacy_namespace

        for new_namespace in self.downstream_legacy_namespaces:
            self.downstream_legacy_namespaces_by_name[new_namespace['name']] = new_namespace

            lowercase_name = new_namespace['name'].lower()
            if lowercase_name not in self.downstream_legacy_lowercase_namespace_name_map:
                self.downstream_legacy_lowercase_namespace_name_map[lowercase_name] = []
            self.downstream_legacy_lowercase_namespace_name_map[lowercase_name].append(new_namespace['name'])

        for v3_ns in self.downstream_v3_namespaces:
            self.downstream_v3_namespaces_by_name[v3_ns['name']] = v3_ns

        self.upstream_collection_namespace_names = set()
        for upstream_collection in self.upstream_v2_collections:
            self.upstream_collection_namespace_names.add(upstream_collection['namespace']['name'])

        self.upstream_legacyrole_namespace_names = set()
        for old_role in self.upstream_legacy_roles:
            self.upstream_legacyrole_namespace_names.add(old_role['summary_fields']['namespace']['name'])

        self.downstream_v3_collections_by_fqcn = {}
        for col in self.downstream_v3_collections:
            fqcn = (col['namespace'], col['name'])
            self.downstream_v3_collections_by_fqcn[fqcn] = col

        self.downstream_legacyroles_by_fqrn = {}
        for role in self.downstream_legacy_roles:
            fqrn = (role['summary_fields']['namespace']['name'], role['name'])
            self.downstream_legacyroles_by_fqrn[fqrn] = role

        self.upstream_legacyroles_by_fqrn = {}
        for role in self.upstream_legacy_roles:
            ns_name = role['summary_fields']['namespace']['name']
            if not ns_name:
                continue
            name = role['name']
            fqrn = (ns_name, name)
            self.upstream_legacyroles_by_fqrn[fqrn] = role
            #import epdb; epdb.st()

        self.downstream_legacyusers_by_github_id = {}
        self.downstream_legacyusers_by_username = {}
        for duser in self.downstream_legacy_users:

            self.downstream_legacyusers_by_username[duser['username']] = duser

            github_id = duser.get('github_id')
            if not github_id:
                continue
            self.downstream_legacyusers_by_github_id[github_id] = duser


    def get_content_for_upstream_namespace(self, ns_name, case_insensitive=True):
        content = []
        for role in self.upstream_legacy_roles:
            role_ns = role['summary_fields']['namespace']['name']

            # bad role ...
            if role_ns is None:
                continue

            if role_ns == ns_name:
                content.append(['role', role_ns, role['name']])
                continue
            if case_insensitive and role_ns.lower() == ns_name.lower():
                content.append(['role', role_ns, role['name']])
                continue

        for collection in self.upstream_v2_collections:
            col_ns = collection['namespace']['name']

            if col_ns == ns_name:
                content.append(['collection', col_ns, collection['name']])
                continue
            if case_insensitive and col_ns.lower() == ns_name.lower():
                content.append(['collection', col_ns, collection['name']])
                continue

        return content

    def get_content_for_downstream_namespace(self, ns_name, case_insensitive=True):
        content = []
        for role in self.downstream_legacy_roles:
            role_ns = role['summary_fields']['namespace']['name']

            # bad role ...
            if role_ns is None:
                continue

            if role_ns == ns_name:
                content.append(['role', role_ns, role['name']])
                continue
            if case_insensitive and role_ns.lower() == ns_name.lower():
                content.append(['role', role_ns, role['name']])
                continue

        for collection in self.downstream_v3_collections:

            col_ns = collection['namespace']

            if col_ns == ns_name:
                content.append(['collection', col_ns, collection['name']])
                continue
            if case_insensitive and col_ns.lower() == ns_name.lower():
                content.append(['collection', col_ns, collection['name']])
                continue

        return content

    def compare_data(self):

        missing_v1_namespaces = []
        missing_provider = []
        missing_owners = []

        missing_roles = []
        missing_collections = []

        upstream_namespaces_without_content = set()

        for ucol in self.upstream_v2_collections:
            fqcn = (ucol['namespace']['name'], ucol['name'])
            if fqcn not in self.downstream_v3_collections_by_fqcn:
                missing_collections.append(fqcn)
        missing_collections = sorted(missing_collections)

        for urole in self.upstream_legacy_roles:
            if not urole['summary_fields']['namespace']['name']:
                continue
            fqrn = (urole['summary_fields']['namespace']['name'], urole['name'])
            if fqrn not in self.downstream_legacyroles_by_fqrn:

                # transformed?
                #matches = self.fuzzy_match_downstream_roles(fqrn)
                #if matches:
                #    import epdb; epdb.st()
                missing_roles.append(fqrn)
        missing_roles = sorted(missing_roles)

        old_names = sorted(list(self.upstream_legacy_namespaces_by_name.keys()))
        for old_name in old_names:

            has_old_collections = old_name in self.upstream_collection_namespace_names
            has_old_roles = old_name in self.upstream_legacyrole_namespace_names
            has_old_content = has_old_collections or has_old_roles

            if not has_old_content:
                upstream_namespaces_without_content.add(old_name)

            if old_name not in self.downstream_legacy_namespaces_by_name:

                # we don't care if the namespace is missing if it doesn't have content ...
                if has_old_roles:
                    missing_v1_namespaces.append(old_name)

                continue

            old_ns = self.upstream_legacy_namespaces_by_name.get(old_name)
            new_ns = self.downstream_legacy_namespaces_by_name.get(old_name)

            if not new_ns['summary_fields']['provider_namespaces']:
                missing_provider.append(old_name)
                continue

            if not old_ns['summary_fields']['owners']:
                continue

            old_owners = [x['username'] for x in old_ns['summary_fields']['owners']]
            new_owners = [x['username'] for x in new_ns['summary_fields']['owners']]

            if sorted(old_owners) == sorted(new_owners):
                continue

            _missing_owners = []
            for old_owner in old_owners:
                if old_owner not in new_owners:

                    old_owner_data = self.upstream_users_by_username[old_owner]
                    old_owner_gh_id = old_owner_data['github_id']
                    old_owner_gh_data = fetch_userdata_by_id(old_owner_gh_id)
                    if old_owner_gh_data:
                        old_owner_gh_login_current = old_owner_gh_data['login']
                    else:
                        old_owner_gh_login_current = None

                    #if old_owner == '888jonno':
                    #    import epdb; epdb.st()

                    # if they changed their username and the new username is an owner,
                    # they're not missing ...
                    if old_owner_gh_login_current and \
                            old_owner_gh_login_current in new_owners:
                        continue

                    # If we have their githubid as another username, that's good enough ...
                    if old_owner_gh_id and \
                            old_owner_gh_id in self.downstream_legacyusers_by_github_id and \
                            self.downstream_legacyusers_by_github_id[old_owner_gh_id]['username'] in new_owners:
                        continue

                    _missing_owners.append(old_owner)

            if not _missing_owners:
                continue

            missing_owners.append([old_name, _missing_owners])
            #import epdb; epdb.st()

        logger.info('')
        logger.info('==== STATS ====')
        with_content = len(self.upstream_legacy_namespaces) - len(list(upstream_namespaces_without_content))
        logger.warning(f'upstream namespaces with content: {with_content}')
        logger.warning(f'upstream namespaces without content: {len(list(upstream_namespaces_without_content))}')
        logger.warning(f'downstream legacy namespaces total: {len(self.downstream_legacy_namespaces)}')
        logger.warning(f'downstream missing collections: {len(missing_collections)}')
        logger.warning(f'downstream missing roles: {len(missing_roles)}')
        logger.warning(f'downstream missing legacy namespaces: {len(missing_v1_namespaces)}')
        logger.warning(f'downstream legacy namespaces w/ missing provider namespace: {len(missing_provider)}')
        logger.warning(f'downstream legacy namespaces w/ missing owner(s): {len(missing_owners)}')
        logger.warning(f'downstream users: {len(self.downstream_legacy_users)}')
        logger.warning(f'downstream users with github_ids: {len(self.downstream_legacyusers_by_github_id.keys())}')

        logger.info('')
        logger.info('==== MISSING PROVIDERS ====')
        for nid,ns_name in enumerate(missing_provider):
            nsdata = self.downstream_legacy_namespaces_by_name[ns_name]
            logger.info(f'{nid}. {ns_name}')

            gh_data = fetch_userdata_by_name(ns_name)
            github_id = gh_data.get('id')

            # is there a v3 namespace?
            v3_name = generate_v3_namespace_from_attributes(username=ns_name, github_id=github_id)
            v3_ns = self.downstream_v3_namespaces_by_name.get(v3_name)
            if v3_ns:
                logger.info(f'\tfound v3: {v3_ns["name"]}')
                for owner in v3_ns['users']:
                    logger.info(f'\t\towner: {owner["name"]}')

                bind_provider(server, new_by_name[ns_name]['id'], v3_ns['id'])
                continue

            logger.warning(f'\tno matching v3 namespace for {v3_name}')

        logger.info('')
        logger.info('==== MISSING LEGACY NAMESPACES ====')
        for nid,ns_name in enumerate(missing_v1_namespaces):
            logger.warning(f'{nid}. {ns_name}')

            legacy_names = self.downstream_legacy_lowercase_namespace_name_map.get(ns_name.lower())
            if legacy_names:
                for ln in legacy_names:
                    logger.info(f'\t similar legacy namespace: {ln}')

            upstream_content = sorted(self.get_content_for_upstream_namespace(ns_name))
            for uc in upstream_content:
                logger.info(f'\tustream - {uc}')

            downstream_content = sorted(self.get_content_for_downstream_namespace(ns_name))
            for dc in downstream_content:
                logger.info(f'\tdstream - {dc}')

        logger.info('')
        logger.info('==== MISSING OWNERS ====')
        for nid,ns_tuple in enumerate(missing_owners):

            ns_name = ns_tuple[0]
            missing_owner_names = ns_tuple[1]

            logger.info(f'{nid}. {ns_name}')

            '''
            upstream = self.upstream_legacy_namespaces_by_name[ns_name]
            for upstream_owner in upstream['summary_fields']['owners']:
                username = upstream_owner['username']
                uudata = self.upstream_users_by_username[username]
                github_id = uudata['github_id']
                logger.info(f'\tu_owner: {username} ({github_id})')
            '''

            dstream = self.downstream_legacy_namespaces_by_name[ns_name]
            for dstream_owner in dstream['summary_fields']['owners']:
                username = dstream_owner['username']

                logger.info(f'\td_owner: {username}')

            for username in missing_owner_names:
                if username not in self.upstream_users_by_username:
                    import epdb; epdb.st()
                uudata = self.upstream_users_by_username[username]
                github_id = uudata['github_id']
                gdata = fetch_userdata_by_id(github_id) or {}
                real_login = gdata.get('login')

                logger.info(f'\tmissing: {username} [{real_login}] {github_id}')

                if github_id and github_id in self.downstream_legacyusers_by_github_id:
                    matched_user = self.downstream_legacyusers_by_github_id[github_id]
                    matched_username = matched_user['username']
                    logger.info(f'\t\tmatched user by gid {matched_username} {github_id}')

                else:

                    # match by name? ...
                    if username in self.downstream_legacyusers_by_username:
                        matched_user = \
                            self.downstream_legacyusers_by_username[username]
                        logger.info(f'\t\tmatched user by un {username} {matched_user["id"]}')

                    #import epdb; epdb.st()

            #import epdb; epdb.st()


        logger.info('')
        logger.info('==== MISSING COLLECTIONS ====')
        for idc,mc in enumerate(missing_collections):
            logger.warning(f'{idc}. {mc[0]}.{mc[1]}')

        logger.info('')
        logger.info('==== MISSING ROLES ====')
        for idc,fqrn in enumerate(missing_roles):
            logger.warning(f'{idc}. {fqrn[0]}.{fqrn[1]}')

            matches = self.fuzzy_match_downstream_roles(fqrn)
            for match in matches:
                logger.info(f'\tsimilar: {match}')
            #import epdb; epdb.st()

        # import epdb; epdb.st()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--upstream',
        default='https://old-galaxy.ansible.com',
        help='the source server'
    )
    parser.add_argument(
        '--downstream',
        default='https://galaxy.ansible.com',
        help='the destination server'
    )
    parser.add_argument(
        '--refresh-downstream-cache',
        action='store_true'
    )
    args = parser.parse_args()

    GalaxyComparator(args)



if __name__ == "__main__":
    main()
