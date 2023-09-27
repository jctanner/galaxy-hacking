import yaml

from pulp_ansible.app.models import CollectionRemote
from pulp_ansible.app.models import CollectionVersion
from pulp_ansible.app.models import AnsibleDistribution
from pulp_ansible.app.models import AnsibleRepository

from pulpcore.plugin.tasking import enqueue_with_reservation
from pulp_ansible.app.tasks.collections import sync as sync_collections


# Need the published repo
print('GET REPO')
community_repo, _ = AnsibleRepository.objects.get_or_create(name='community')

# Need the published distro
print('GET DISTRO')
community_distro, _ = AnsibleDistribution.objects.get_or_create(name='community', base_path="community")

# Link them ...
print('LINK REPO+DISTRO')
community_distro.repository = community_repo
community_distro.save()

# Need a remote
print('GET REMOTE')
community_remote, _ = CollectionRemote.objects.get_or_create(name='community')

requirements = {
    'collections': [
        'geerlingguy.mac'
    ]
}
requirements_string = yaml.dump(requirements)
community_remote.requirements_file = requirements_string
# community_remote.url = 'https://beta-galaxy.ansible.com'
community_remote.url = 'http://172.20.0.1:5001'
community_remote.save()


# need to dispatch with remote_pk and repository_pk ...
locks = []
locks.append(community_repo)
kwargs = {
    'repository_pk': community_repo.pk,
    'remote_pk': community_remote.pk,
    'mirror': False
}
res = enqueue_with_reservation(sync_collections, locks, kwargs=kwargs)

# res.refresh()
# res.get_status()

import epdb; epdb.st()
