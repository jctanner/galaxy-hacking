from galaxy_ng.app.models.auth import Group, User
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.utils import rbac

from pulpcore.plugin.util import (
    assign_role,
    get_groups_with_perms_attached_roles,
    get_users_with_perms_attached_roles,
    get_objects_for_user,
    remove_role
)


for namespace in Namespace.objects.all():

    current_groups = get_groups_with_perms_attached_roles(
        namespace,
        include_model_permissions=False
    )

    '''
    current_users = get_users_with_perms_attached_roles(
        namespace,
        include_model_permissions=False
    )
    '''

    for cgroup in current_groups:

        if not cgroup.name.startswith('namespace:'):
            continue

        for guser in cgroup.user_set.all():
            '''
            if guser not in current_users:
                print(f'Add {guser} to {namespace}')
                rbac.add_user_to_v3_namespace(guser, namespace)
            '''
            print(f'Add {guser} to {namespace}')
            rbac.add_user_to_v3_namespace(guser, namespace)

        print(f'Delete {cgroup}')
        cgroup.delete()
