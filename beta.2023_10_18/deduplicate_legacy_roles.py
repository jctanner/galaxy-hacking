import csv
import json
import os
import requests

from pprint import pprint

from galaxy_ng.app.utils import rbac
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole


CHECK_MODE = os.environ.get('CHECK_MODE') != '0'


def load_csv(fn):

    colnames = []
    rows = []

    with open(fn, newline='') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=';')
        for row in spamreader:
            if not colnames:
                colnames = row[:]
                continue

            try:
                ds = {}
                for idx, x in enumerate(row):
                    ds[colnames[idx]] = x
                rows.append(ds)
            except ValueError:
                pass

    if 'rows' in str(rows[-1]):
        rows = rows[:-1]
    #import epdb; epdb.st()

    return rows


class RoleScore:

    role = None
    expected_owners = None
    expected_versions = None
    missing_versions = None
    missing_owners = None
    upstream = None
    score = None
    fixes = None

    def __init__(self, upstream_data, expected_versions, role, owners=None):
        self.score = 100
        self.role = role
        self.upstream = upstream_data
        self.expected_versions = expected_versions
        self.expected_owners = owners

        self.fixes = {}
        self.missing_versions = []
        self.missing_owners = []

        urole = upstream_data

        # should have been bound to a v3 namespace ...
        if not role.namespace.namespace:
            self.fixes['bind_v3_namespace'] = True
            SELf.score -= 20
        else:
            current_owners = rbac.get_v3_namespace_owners(role.namespace.namespace)
            for expected_owner in self.expected_owners:
                if expected_owner not in current_owners:
                    self.missing_owners.append(expected_owner)
                    #self.score -= 5
                    #self.fixes['add_owners'] = True
            if self.missing_owners:
                self.fixes['add_owners'] = True
                self.score -= 20

        #import epdb; epdb.st()
        if role.namespace.name != urole['repository__provider__namespace__name']:
            current = role.namespace.name
            new_ns = urole['repository__provider__namespace__name']
            #print(f'FIX - set {role.id} namespace.name from {current} to {new_ns}')
            self.score -= 50
            self.fixes['namespace.name'] = new_ns

        # in old galaxy, github_user == repository.github_user == provider_namespace.name
        if role.full_metadata.get('github_user') != urole['provider_namespace__name']:
            current = role.full_metadata.get('github_user')
            new_user = urole['provider_namespace__name']
            #print(f'FIX - set {role.id} github_user from {current} to {new_user}')
            self.score -= 10
            self.fixes['github_user'] = new_user

        #if role.full_metadata.get('github_repo') != urole['repository__name']:
        if role.full_metadata.get('github_repo') != urole['repository_original_name']:
            current = role.full_metadata.get('github_repo')
            new_repo = urole['repository_original_name']
            #print(f'FIX - set {role.id} github_repo from {current} to {new_repo}')
            self.score -= 10
            self.fixes['github_repo'] = new_repo

        if role.full_metadata.get('versions') != expected_versions:

            current_versions = role.full_metadata.get('versions')

            for ev in self.expected_versions:
                if ev not in current_versions:
                    print(f'FIX - {role.id} missing {ev["name"]}')
                    self.score -= 10
                    self.fixes['add_versions'] = True
                    self.missing_versions.append(ev)

    def log(self, msg):
        msg = str(self.role.id) + ": " + msg
        with open('changes.log', 'a') as f:
            f.write(msg + '\n')

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f'{self.role}({self.role.id}):{self.score}%'

    def validate(self):
        # search old galaxy how the CLI does it ...
        # https://github.com/ansible/ansible/blob/devel/lib/ansible/galaxy/api.py#L525C24-L525C52
        #    "?owner__username=%s&name=%s" % (user_name, role_name)
        fqn = self.role.namespace.name + '.' + self.role.name
        ns_name = self.role.namespace.name
        role_name = self.role.name
        url = f'https://old-galaxy.ansible.com/api/v1/roles/?owner__username={ns_name}&name={role_name}'
        rr = requests.get(url)
        assert rr.status_code == 200
        ds = rr.json()
        assert ds['count'] == 1
        rdata = ds['results'][0]
        assert rdata['id'] == int(self.upstream['id'])

        if 'github_user' in self.fixes:
            assert self.fixes['github_user'] == rdata['github_user']
        if 'github_repo' in self.fixes:
            assert self.fixes['github_repo'] == rdata['github_repo']

        assert self.role.namespace.name == rdata['summary_fields']['namespace']['name']
        assert self.role.name == rdata['name']
        #import epdb; epdb.st()

    def do_fixes(self):
        for k,v in self.fixes.items():
            if k == 'add_owners':
                for missing_owner in self.missing_owners:
                    self.log(f'add {missing_owner} to {self.role.namespace.namespace}')
                    rbac.add_user_to_v3_namespace(missing_owner, self.role.namespace.namespace)
            elif k == 'github_user':
                self.log(f'set {self.role} github_user to {v}')
                self.role.full_metadata['github_user'] = v
                self.role.save()
            elif k == 'github_repo':
                self.log(f'set {self.role} github_repo to {v}')
                self.role.full_metadata['github_repo'] = v
                self.role.save()
            elif k == 'add_versions':
                import epdb; epdb.st()


upstream_roles = {}
upstream_data = load_csv('old_role_namespace_details.csv')
for ud in upstream_data:
    if 'id' in ud:
        uuid = int(ud['id'])
        ud['role_id'] = ud['id']
    else:
        uuid = int(ud['role_id'])

    if 'provider_namespace__name' not in ud:
        ud['provider_namespace__name'] = ud['provider_name']
        #import epdb; epdb.st()

    if 'repository__name' not in ud:
        ud['repository__name'] = ud['repository_name']
        #import epdb; epdb.st()

    upstream_roles[uuid] = ud


rmap = {}
lrvals = LegacyRole.objects.values_list('id', 'full_metadata__upstream_id')
for lrval in lrvals:
    uuid = lrval[1]
    rid = lrval[0]
    if uuid is None:
        continue
    if uuid not in rmap:
        rmap[uuid] = []
    rmap[uuid].append(rid)


# trim out non-duplicated roles ...
urids = list(rmap.keys())
for urid in urids:
    if len(rmap.get(urid)) < 2:
        rmap.pop(urid)


# handle de-dupe
urids = list(rmap.keys())
for urid in urids:

    if urid not in upstream_roles:
        continue

    print('-' * 50)

    # need the upstream data ...
    urole = upstream_roles[urid]
    pprint(urole)

    # what is the "right" fqn ...?
    # https://old-galaxy.ansible.com/einfachit/ssh_tor
    #   ansible-galaxy install einfachit.ssh_tor

    # https://old-galaxy.ansible.com/testing/ansible_testing_content
    #   mazer install testing.ansible_testing_content

    # https://old-galaxy.ansible.com/chip0k/ansible_role_ufw
    #   ansible-galaxy install chip0k.ansible_role_ufw

    namespace_names = [
        urole['namespace_name'],
        urole['provider_name'],
        urole['provider_namespace__name'],
        urole['repository__provider__namespace__name'],
    ]
    namespace_names = sorted(set(namespace_names))
    #import epdb; epdb.st()

    # sigh ... this is hard!
    # {namespace_name}.{role_name} == fqn
    # {provider_namespace__name}/{reository__name} == clone url
    role_fqn = f"{urole['repository__provider__namespace__name']}.{urole['role_name']}"
    print(f'FQN: {role_fqn}')
    ui_url = f"https://old-galaxy.ansible.com/{urole['namespace_name']}/{urole['role_name']}/"
    print(f'URL: {ui_url}')

    # https://old-galaxy.ansible.com/don_rumata/ansible_role_install_liberica_java
    # https://github.com/don-rumata/ansible-role-install-liberica-java

    # https://github.com/OT-OSM/Percona-PostgreSQL
    guser = urole['provider_name']
    grepo = urole['repository_original_name']
    clone_url = f'https://github.com/{guser}/{grepo}'
    print(f'GH: {clone_url}')
    #import epdb; epdb.st()

    # what are the grouped role ids ...
    rkeys = rmap[urid]
    print(rkeys)

    # get the role objects ...
    roles = [LegacyRole.objects.get(id=x) for x in rkeys]
    print(roles)

    # get ALL the owners ...
    all_owners = set()
    for role in roles:
        v3ns = role.namespace.namespace
        if v3ns:
            owners = rbac.get_v3_namespace_owners(v3ns)
            for owner in owners:
                all_owners.add(owner)

    # get the longest list of versions ...
    versions = [x.full_metadata.get('versions') for x in roles]
    versions = [(len(x), x) for x in versions]
    versions = sorted(versions, key=lambda x: x[0])
    versions = versions[-1][1]

    # score each role ...
    scores = [RoleScore(urole, versions, x, owners=all_owners) for x in roles]
    print(scores)

    #if any([x.missing_versions for x in scores]):
    #    import epdb; epdb.st()

    best = sorted(scores, reverse=True, key=lambda x: x.score)[0]

    '''
    #if best.missing_versions:
    #    import epdb; epdb.st()
    if best.score < 80:
        print(f'ns names: {namespace_names}')
        #pprint(best.fixes)
        #import epdb; epdb.st()
        #continue
    '''

    # validate lower scores ...
    if best.score < 80:
        try:
            best.validate()
        except Exception as e:
            print(e)
            continue

    if not CHECK_MODE:
        to_delete = [x for x in roles if x != best.role]
        for td in to_delete:
            td.delete()
        best.do_fixes()
