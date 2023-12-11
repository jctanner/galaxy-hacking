import logging
import requests

from django.contrib.contenttypes.models import ContentType
from pulpcore.app.models.role import UserRole
from pulp_ansible.app.models import Collection
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models import User
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.utils.rbac import add_user_to_v3_namespace

from galaxy_lib import get_old_owners
from github_lib import fetch_userdata_by_id
from github_lib import fetch_userdata_by_name


logger = logging.getLogger(__name__)


# map out the current users
usermap = dict((x.username, x) for x in User.objects.all())


# map out the provider namespaces
providers = {}
for lns in LegacyNamespace.objects.all():
    if not lns.namespace:
        continue
    provider = lns.namespace
    if provider not in providers:
        providers[provider] = []
    providers[provider].append(lns.name)


ct_map = dict((x.name,x) for x in ContentType.objects.all() if 'namespace' in x.name.lower())
ns_type_id = ct_map['namespace'].id
ns_roles = UserRole.objects.filter(content_type_id=ns_type_id)
owned_ns_ids = [int(x.object_id) for x in ns_roles]
orphaned_namespaces = Namespace.objects.exclude(id__in=owned_ns_ids)
orphaned_namespaces = sorted(orphaned_namespaces, key=lambda x: x.name)


total = len(orphaned_namespaces)
no_providers = []
no_owners = []

for ido,orphan in enumerate(orphaned_namespaces):

    names = [orphan.name]

    if orphan in providers:
        for lns in providers[orphan]:
            names.append(lns)
    else:
        no_providers.append(orphan)

    names = sorted(set(names))

    print(f'{total}|{ido} {names}')

    for ns in names:
        cols = Collection.objects.filter(namespace=ns)
        for col in cols:
            print(f'\t{col}')

    old_owners = get_old_owners(names)
    print(f'\told_owners: {[x["username"] for x in old_owners[1]]}')

    if not old_owners[1]:
        no_owners.append(orphan.name)

    if old_owners[1]:

        for owner in old_owners[1]:
            username = owner['username']
            usernames = [username]

            # what is the actual github login?
            if owner['github_id']:
                guser = fetch_userdata_by_id(owner['github_id'])
                if guser and guser.get('login'):
                    login = guser['login']
                    if login != username:
                        print(f'\t{username} -> {login}')
                        usernames.append(login)
                        #import epdb; epdb.st()

            for _un in usernames:

                if _un not in usermap:

                    print(f'\tcreate {_un} user')
                    user, _ = User.objects.get_or_create(username=_un)
                    usermap[_un] = user

                else:
                    user = usermap[_un]

                print(f'\tset user:{user} as owner of {orphan}...')
                add_user_to_v3_namespace(user, orphan)
                # import epdb; epdb.st()

    else:

        matched_github_users = []

        # is there a matching github user for this ns name(s) ?
        print(f'\tcheck github for {orphan.name}')
        udata = fetch_userdata_by_name(orphan.name)
        print(f'\t\t{udata}')
        if udata and not udata.get('message'):
            matched_github_users.append(udata)

        if orphan in providers:
            # print(providers[orphan])
            for lns in providers[orphan]:
                print(f'\tcheck github for {lns}')
                udata = fetch_userdata_by_name(lns)
                print(f'\t\t{udata}')

                if udata and not udata.get('message'):
                    matched_github_users.append(udata)

                #import epdb; epdb.st()

        if matched_github_users:
            for gdata in matched_github_users:
                login = gdata['login']
                if login in usermap:
                    user = usermap[login]
                else:
                    print(f'\tcreate {login} user')
                    user, _ = User.objects.get_or_create(username=login)
                    usermap[login] = user

                print(f'\tset user:{user} as owner of {orphan}...')
                add_user_to_v3_namespace(user, orphan)
                # import epdb; epdb.st()


print('total orphaned namespaces ...')
print(len(orphaned_namespaces))
print('total orphaned namespaces with no upstream owners ...')
print(len(no_owners))
print('total orphaned namespaces with no legacy namespaces attached ...')
print(len(no_providers))
