#!/usr/bin/env python

from pprint import pprint
import json
import sys
import time
import django_guid
import requests

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.tasks.namespaces import _create_pulp_namespace
from pulp_ansible.app.models import AnsibleRepository
from pulp_ansible.app.models import AnsibleNamespace
from pulp_ansible.app.models import AnsibleNamespaceMetadata
from pulp_ansible.app.models import CollectionVersion

from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES
from pulpcore.plugin.tasking import dispatch, add_and_remove


# Set logging_uid, this does not seem to get generated when task called via management command
django_guid.set_guid(django_guid.utils.generate_guid())


def build_old_avatar_cache():

    AVATAR_CACHE_FILE = '.avatar_cache.json'

    avatar_map = {
        'pages': [],
        'avatars': {}
    }

    if os.path.exists(AVATAR_CACHE_FILE):
        with open(AVATAR_CACHE_FILE, 'r') as f:
            avatar_map = json.loads(f.read())

    pagenum = 1
    if avatar_map['pages']:
        pagenum = avatar_map['pages'][-1]

    baseurl = 'https://old-galaxy.ansible.com'
    next_page = f'https://old-galaxy.ansible.com/api/v1/namespaces/?page={pagenum}'
    while next_page:
        print(next_page)
        rr = requests.get(next_page)
        ds = rr.json()

        pagenum = int(next_page.split('=')[-1])
        if pagenum not in avatar_map['pages']:
            avatar_map['pages'].append(pagenum)

        for result in ds['results']:
            avatar_map['avatars'][result['name']] = result['avatar_url']

        with open(AVATAR_CACHE_FILE, 'w') as f:
            f.write(json.dumps(avatar_map, indent=2))

        if not ds.get('next_link'):
            break

        next_page = baseurl + ds['next_link']

    return avatar_map


def set_namespace_avatars(content_logos_to_set):
    nsnames = sorted(list(content_logos_to_set.keys()))
    for nsname in nsnames:
        ndata = content_logos_to_set[nsname]
        nid = ndata['id']
        avatar_url = ndata['avatar_url']
        ns = Namespace.objects.get(id=nid)
        print(ns)
        ns.avatar_url = avatar_url
        ns.save()

    #if content_logos_to_set:
    #    import epdb; epdb.st()


def make_avatar_content(content_namespaces_to_make):
    nsnames = sorted(list(content_namespaces_to_make.keys()))
    for nsname in nsnames:
        print(f'create pulp objects for {nsname}')
        ns = Namespace.objects.get(name=nsname)
        _create_pulp_namespace(ns.pk, download_logo=True)
        #import epdb; epdb.st()


def add_namespaces_content_to_repo(content_namespaces_to_add, anmap, published):
    """For each namespace, add it's related content and metadata to the repo"""

    chunk_size = 200
    names = sorted(list(content_namespaces_to_add.keys()))
    chunks = [names[i:i + chunk_size] for i in range(0, len(names), chunk_size)]
    for idc,chunk in enumerate(chunks):
        print('-------------------------------------------')
        print(f'ADDING TO REPO ... {len(chunks)} | {idc}')
        print('-------------------------------------------')

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
        # continue

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



# make the old index ...
old_avatars = build_old_avatar_cache()

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


# Make a list of legacy namespaces and their avatar urls ...
legacy_map = {}
for lnamespace in LegacyNamespace.objects.values('id', 'name', 'namespace', 'avatar_url'):
    v3id = lnamespace['namespace']
    legacy_map[v3id] = lnamespace


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
content_logos_to_set = {}
for gnamespace in Namespace.objects.order_by('name').values('id', 'name', '_avatar_url'):

    gid = gnamespace['id']
    gname = gnamespace['name']

    # this namespace is already content in the repo ...
    if gname in content_namespaces:
        continue

    # does the namespace have an avatar url? ...
    if not gnamespace['_avatar_url']:
        legacy_name = None
        avatar_url = None
        if gid in legacy_map:
            legacy_name = legacy_map[gid]['name']
            if legacy_map[gid]['avatar_url']:
                avatar_url = legacy_map[gid]['avatar_url']

        if legacy_name:
            avatar_url = old_avatars['avatars'].get(legacy_name)
        else:
            avatar_url = old_avatars['avatars'].get(gname)

        print('\t' + str(avatar_url))
        if avatar_url != '' and avatar_url != 'null' and avatar_url is not None:
            content_logos_to_set[gname] = {'id': gid, 'avatar_url': avatar_url}

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
print('TOTAL NAMESPACES TO SET AVATARS FOR')
print('------------------------------------------------')
print(len(list(content_logos_to_set.keys())))
set_namespace_avatars(content_logos_to_set)
#import epdb; epdb.st()


print('------------------------------------------------')
print('TOTAL NAMESPACES TO MAKE CONTENT FOR')
print('------------------------------------------------')
print(len(list(content_namespaces_to_make.keys())))
make_avatar_content(content_namespaces_to_make)
#import epdb; epdb.st()


print('------------------------------------------------')
print('TOTAL NAMESPACES TO ADD TO THE PUBLISHED REPO')
print('------------------------------------------------')
print(len(list(content_namespaces_to_add.keys())))
#import epdb; epdb.st()


# now add them all ... ?
add_namespaces_content_to_repo(content_namespaces_to_add, anmap, published)
