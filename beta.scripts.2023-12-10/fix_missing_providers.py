import logging
import requests

from django.contrib.contenttypes.models import ContentType
from pulpcore.app.models.role import UserRole
from pulp_ansible.app.models import Collection
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models import User
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.utils.rbac import add_user_to_v3_namespace
from galaxy_ng.app.utils.rbac import get_v3_namespace_owners
from galaxy_ng.app.utils.namespaces import map_v3_namespace

from galaxy_lib import get_old_owners
from github_lib import fetch_userdata_by_id
from github_lib import fetch_userdata_by_name


logger = logging.getLogger(__name__)


# map out the current users
usermap = dict((x.username, x) for x in User.objects.all())

# map out the v3 namespaces
v3_map = dict((x.name, x) for x in Namespace.objects.all())


for lns in LegacyNamespace.objects.filter(namespace_id__isnull=True).order_by('name'):
    print(lns)
    for owner in lns.owners.all():
        print(f'\tv1_owner:{owner}')

    v3_name = map_v3_namespace(lns.name)
    if v3_name not in v3_map:
        ns,_ = Namespace.objects.get_or_create(name=v3_name)
        v3_map[v3_name] = ns

    v3 = v3_map.get(v3_name)
    print(f'\tV3 {v3_name} {v3}')

    if v3:
        v3_owners = get_v3_namespace_owners(v3)
        for v3_owner in v3_owners:
            print(f'\tv3_owner:{v3_owner}')

        for v1_owner in lns.owners.all():
            if v1_owner not in v3_owners:
                print(f'\tadd {v1_owner} to v3:{v3}')
                add_user_to_v3_namespace(v1_owner, v3)

        print(f'\tbind {lns} to {v3}')
        lns.namespace = v3
        lns.save()
