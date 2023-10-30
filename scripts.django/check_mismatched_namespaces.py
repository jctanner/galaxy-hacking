import gzip
import json
import os

# from pprint import pprint

from galaxy_ng.app.api.v1.models import LegacyRole


def do_check():

    checkmode = True
    if os.environ.get('CHECK_MODE') == "0":
        checkmode = False

    # compressed for size ...
    fn = 'old_mismatched_namespaces.json.gz'
    with gzip.open(fn, 'rb') as gz_file:
        raw = gz_file.read()
    rows = json.loads(raw)

    current_data = LegacyRole.objects.values_list(
        'id', 'full_metadata__upstream_id', 'full_metadata__github_user'
    )
    rmap = dict(
        (x[1], {'id': x[0], 'upstream_id': x[1], 'github_user': x[2]}) for x in current_data
    )

    for idr, row in enumerate(rows):

        upstream_id = int(row['role_id'])
        expected_github_user = row['provider_namespace__name']
        cdata = rmap.get(upstream_id)
        if not cdata:
            continue

        if cdata['github_user'] == expected_github_user:
            continue

        role = LegacyRole.objects.get(id=cdata['id'])
        current_github_user = role.full_metadata.get('github_user')
        print(
            f'FIX - ({len(rows)} | {idr}) set {role} github_user'
            + f' from {current_github_user} to {expected_github_user}'
        )
        if not checkmode:
            role.full_metadata['github_user'] = expected_github_user
            role.save()


do_check()
