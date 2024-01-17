#!/usr/bin/env python

from pprint import pprint
import sys
import time
import django_guid

from galaxy_ng.app.models import Namespace
from pulp_ansible.app.models import AnsibleRepository
from pulp_ansible.app.models import AnsibleNamespace
from pulp_ansible.app.models import AnsibleNamespaceMetadata
from pulp_ansible.app.models import CollectionVersion

from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES
from pulpcore.plugin.tasking import dispatch, add_and_remove


# Set logging_uid, this does not seem to get generated when task called via management command
django_guid.set_guid(django_guid.utils.generate_guid())

# map out which namespaces+meta have made it into the published repo ...
published = AnsibleRepository.objects.filter(name='published').first()
published_content = published.content.all()
content_namespaces = {}
for pc in published_content:
    if str(pc.pulp_type) != 'ansible.namespace':
        continue
    ns = pc.cast()
    content_namespaces[ns.name] = pc.pulp_id

# Make a list of collection namespaces ...
content_collection_namespaces = {}
for cv in CollectionVersion.objects.values('namespace', 'name'):
    content_collection_namespaces[cv['namespace']] = None

print('---------------------------------------------------')
print('CURRENT CONTENT NAMESPACES IN THE PUBLISHED REPO')
print('---------------------------------------------------')
pprint(len(list(content_namespaces.keys())))

# map out all the -ansible- namespace and metadata objects by name ...
anamespaces = AnsibleNamespace.objects.values('pulp_id', 'name')
anamespaces_metadatas = AnsibleNamespaceMetadata.objects.values('pulp_id', 'name')
anmap = dict((x['name'], {'name': x['name'], 'namespace_id': x['pulp_id'], 'metadata': None}) for x in anamespaces)
for metadata in AnsibleNamespaceMetadata.objects.order_by('pulp_created').values('pulp_id', 'name', 'pulp_created'):
    anmap[metadata['name']]['metadata'] = metadata['pulp_id']

# figure out which ones didn't get added to the repo ...
content_namespaces_to_add = {}
content_namespaces_to_make = {}
for gnamespace in Namespace.objects.order_by('name').values('id', 'name'):
    gname = gnamespace['name']

    # this namespace is already content in the repo ...
    if gname in content_namespaces:
        continue

    # this will limit to just namespaces with collections ...
    #if gname not in content_collection_namespaces:
    #    continue

    # does the namespace have related content objects?
    if gname not in anmap:
        content_namespaces_to_make[gname] = None
        continue

    # does the namespace have related metadata content objects?
    if not anmap[gname].get('metadata'):
        content_namespaces_to_make[gname] = None
        continue

    content_namespaces_to_add[gname] = [anmap[gname]['namespace_id'], anmap[gname]['metadata']]


print('------------------------------------------------')
print('TOTAL NAMESPACES TO MAKE CONTENT FOR')
print('------------------------------------------------')
print(len(list(content_namespaces_to_make.keys())))

print('------------------------------------------------')
print('TOTAL NAMESPACES TO ADD TO THE PUBLISHED REPO')
print('------------------------------------------------')
print(len(list(content_namespaces_to_add.keys())))


# now add them all ... ?
chunk_size = 200
names = sorted(list(content_namespaces_to_add.keys()))
chunks = [names[i:i + chunk_size] for i in range(0, len(names), chunk_size)]
for idc,chunk in enumerate(chunks):
    print('---------------')
    print(f'{len(chunks)} | {idc}')
    print('---------------')

    print(sorted(chunk))

    new_content = []
    for name in chunk:
        new_content.append(str(anmap[name]['namespace_id']))
        new_content.append(str(anmap[name]['metadata']))

    # def add_and_remove(repository_pk, add_content_units, remove_content_units, base_version_pk=None):
    kwargs = {
        'repository_pk': str(published.pulp_id),
        'add_content_units': new_content,
        'remove_content_units': []

    }
    print(kwargs)

    task = dispatch(add_and_remove, kwargs=kwargs, exclusive_resources=[published])
    print(task.pulp_id)
    task_id = str(task.pulp_id)

    while task.state not in TASK_FINAL_STATES:
        task.refresh_from_db()
        print(f'\t{task.state}')
        time.sleep(1)

    if task.state in TASK_STATES.FAILED:
        raise Exception('task failed')

    # sys.exit(0)


