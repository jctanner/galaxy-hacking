import uuid

from ansible.module_utils.compat.version import LooseVersion
import semantic_version

from galaxy_ng.app.api.v1.utils import parse_version_tag
from galaxy_ng.app.api.v1.models import LegacyRole


def normalize_versions(versions):

    removed = []

    # convert old integer based IDs to uuid
    for vix, version in enumerate(versions):
        if isinstance(version.get('id', ''), int):
            versions[vix]['upstream_id'] = version['id']
            versions[vix]['id'] = str(uuid.uuid4())

    # Normalize keys
    for vix, version in enumerate(versions):
        if not version.get('tag'):
            if version.get('name'):
                versions[vix]['tag'] = version['name']
            else:
                versions[vix]['tag'] = version['version']

    # if looseversion can't make a numeric version from this tag
    # it's not going to work later. This also should cover the case
    # where previous galaxy_ng import code mistakenly thought
    # the branch+commit should be a version instead of only tags.
    for version in versions[:]:
        if not version.get('tag'):
            versions.remove(version)
            removed.append(version)
            continue
        lver = LooseVersion(version['tag'].lower())
        if not any(isinstance(x, int) for x in lver.version):
            versions.remove(version)
            removed.append(version)

    return versions, removed


count = 0
#for role in LegacyRole.objects.filter(full_metadata__versions__len__gt=0):
for role in LegacyRole.objects.all().order_by('-modified'):

    #print(role)

    old_versions = role.full_metadata.get('versions', [])
    if not old_versions:
        continue

    cleaned_versions, removed_versions = normalize_versions(old_versions)
    if not removed_versions:
        continue

    print(f'{count} {role}')
    for rv in removed_versions:
        print(f'\tREMOVE name:{rv.get("name")} version:{rv.get("version")} tag:{rv.get("tag")}')
        print(f'\t\t{rv.get("download_url")}')

    role.full_metadata['versions'] = cleaned_versions
    role.save()

    count += 1
    if count > 1000:
        break


