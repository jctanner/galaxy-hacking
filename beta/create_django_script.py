#!/usr/bin/env python3


import json


with open('data.json', 'r') as f:
    ds = json.loads(f.read())

SCRIPT1 = '''#!/usr/bin/env python3
import json
from pulpcore.plugin.util import (
    assign_role,
    get_groups_with_perms_attached_roles,
    get_users_with_perms_attached_roles,
    remove_role
)
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models.auth import Group, User
from galaxy_ng.app.utils import rbac
'''

SCRIPT2 = '''

def unbind_namespace(namespace):
    current_groups = get_groups_with_perms_attached_roles(
        namespace,
        include_model_permissions=False
    )
    for cg in current_groups:
        rbac.remove_group_from_v3_namespace(cg, namespace)
    current_users = get_users_with_perms_attached_roles(
        namespace,
        include_model_permissions=False
    )
    for cu in current_users:
        remove_role('galaxy.collection_namespace_owner', cu, namespace)


# create all users
print('Creating users ...')
for username in data['usernames']:
    user, _ = User.objects.get_or_create(username=username)


# create and sync v1 namespace
for ids,ns in enumerate(data['namespaces']):
    print(f"V1 {len(data['namespaces'])}|{ids} {ns['name']}")
    legacy_namespace, _ = LegacyNamespace.objects.get_or_create(name=ns['name'])
    owners = []
    for username in ns['owners']:
        user = User.objects.filter(username=username).first()
        owners.append(user)
    legacy_namespace.owners.set(owners)


# create and sync v3 namespace
for ids,ns in enumerate(data['namespaces']):

    if not ns['has_collections']:
        continue

    print(f"V3 {len(data['namespaces'])}|{ids} {ns['name']}")

    name = ns['name']
    namespace, _ = Namespace.objects.get_or_create(name=ns['name'])
    unbind_namespace(namespace)

    # has a group?
    gn = f'namespace:{name}'
    group, _ = Group.objects.get_or_create(name=gn)

    # put all owners in the group
    for username in ns['owners']:
        rbac.add_username_to_groupname(username, gn)

    # bind group to namespace
    rbac.add_group_to_v3_namespace(group, namespace)

'''


with open('userimport.py', 'w') as f:
    f.write(SCRIPT1)
    f.write('\n')
    f.write(f"data = '{json.dumps(ds)}'")
    f.write('\n')
    f.write('data = json.loads(data)')
    f.write('\n')
    f.write(SCRIPT2)


#import epdb; epdb.st()
