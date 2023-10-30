import gzip
import json

from django.contrib.auth import get_user_model
from galaxy_ng.app.utils import rbac
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole


User = get_user_model()


# cache
user_map = {}
ns_map = {}
lns_map = {}

# Make v1+v3 namespaces
with open('legacy_namespaces.json', 'r') as f:
    legacy_namespaces_data = json.loads(f.read())
for lns_data in legacy_namespaces_data:
    lns_name = lns_data['legacy_namespace_name']
    ns_name = lns_data['namespace_name']

    print(f'v1:{lns_name} <> v3:{ns_name}')

    # make v3
    if ns_name not in ns_map:
        ns,_ = Namespace.objects.get_or_create(name=ns_name)
        ns_map[ns_name] = ns

    # make v1
    if lns_name not in lns_map:
        lns,_ = LegacyNamespace.objects.get_or_create(name=lns_name)
        lns_map[lns_name] = lns

    # bind v1 to v3
    if lns.namespace != ns:
        lns.namespace = ns
        lns.save()


# set v3 ns owners
with open('new_v3_namespace_owners.json', 'r') as f:
    namespace_owners_data = json.loads(f.read())
total = len(namespace_owners_data)
for idr,ns_data in enumerate(namespace_owners_data):

    ns_name = ns_data['namespace_name']
    username = ns_data['username']

    print(f'{total}|{idr} {username} -> {ns_name}')

    if ns_name not in ns_map:
        ns,_ = Namespace.objects.get_or_create(name=ns_name)
        ns_map[ns_name] = ns
    else:
        ns = ns_map[ns_name]

    if username not in user_map:
        user,_ = User.objects.get_or_create(username=username)
    else:
        user = user_map[username]

    rbac.add_user_to_v3_namespace(user, ns)


# make roles
with gzip.open('new_roles.json.gz', 'rb') as gzip_file:
    roles_data = json.loads(gzip_file.read().decode('utf-8'))
total = len(roles_data)
for idr,role_data in enumerate(roles_data):

    print(f"{total}|{idr} {role_data['namespace_name']}.{role_data['role_name']}")

    ns_name = role_data['namespace_name']
    if ns_name not in lns_map:
        ns,_ = LegacyNamespace.objects.get_or_create(name=ns_name)
        lns_map[ns_name] = ns
    else:
        ns = lns_map[ns_name]

    #import epdb; epdb.st()

    role,created = LegacyRole.objects.get_or_create(
        namespace=ns,
        name=role_data['role_name'],
        full_metadata=role_data['full_metadata']
    )
    print(f'\t{created}')
    #import epdb; epdb.st()
