import gzip
import json
# import os
# import django

from pprint import pprint

from django.contrib.auth import get_user_model

# from galaxy_ng.app.models import Namespace
# from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.tasks import legacy_sync_from_upstream
# from galaxy_ng.app.utils.namespaces import generate_v3_namespace_from_attributes
# from galaxy_ng.app.utils import rbac


User = get_user_model()


def do_check():

    '''
    checkmode = True
    if os.environ.get('CHECK_MODE') == "0":
        checkmode = False
    '''

    # compressed for size ...
    fn = 'old_mismatched_namespaces.json.gz'
    with gzip.open(fn, 'rb') as gz_file:
        raw = gz_file.read()
    rows = json.loads(raw)

    for idr, row in enumerate(rows):

        if 'painless' not in row['provider_namespace__name']:
            continue

        print('-' * 100)
        print(f'{len(rows)} | {idr}')
        pprint(row)

        # provider_namespace__name.role_name
        legacy_sync_from_upstream(
            github_user=row['provider_namespace__name'],
            role_name=row['role_name']
        )
        legacy_sync_from_upstream(
            github_user=row['namespace_name'],
            role_name=row['role_name']
        )

        # import epdb; epdb.st()


do_check()
