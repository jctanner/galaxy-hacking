import json

from django.contrib.auth import get_user_model
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.models.survey import CollectionSurvey
from galaxy_ng.app.models.survey import LegacyRoleSurvey
from pulp_ansible.app.models import Collection


User = get_user_model()

question_props = [
    'docs',
    'does_what_it_says',
    'ease_of_use',
    'used_in_production',
    'works_as_is'
]


def sync_collections():
    with open('old_collection_surveys.json', 'r') as f:
        old_collection_surveys = json.loads(f.read())
    for csurvey in old_collection_surveys:
        gid = csurvey['github_id']
        username = csurvey['username']
        user,_ = User.objects.get_or_create(username=username)

        col_namespace = csurvey['namespace']
        col_name = csurvey['name']
        collection = Collection.objects.filter(
            namespace=col_namespace,
            name=col_name
        ).first()
        if not collection:
            continue

        print(f'\t{user}')
        print(f'\t{collection}')
        nsurvey,_ = CollectionSurvey.objects.get_or_create(
            user=user,
            collection=collection
        )
        for qp in question_props:
            current_val = getattr(nsurvey, qp)
            new_val = csurvey[qp]
            if not new_val:
                continue
            new_val = int(new_val)
            setattr(nsurvey, qp, new_val)
        nsurvey.save()


def sync_roles():
    with open('old_role_surveys.json', 'r') as f:
        old_role_surveys = json.loads(f.read())
    for rsurvey in old_role_surveys:
        gid = rsurvey['github_id']
        username = rsurvey['username']
        user,_ = User.objects.get_or_create(username=username)

        print(rsurvey)
        r_id = int(rsurvey['repository_id'])
        print(f'\t{r_id}')

        role = LegacyRole.objects.filter(full_metadata__upstream_id=r_id).first()
        if not role:
            rnamespace = rsurvey['provider_ns_name']
            rname = rsurvey['repo_name']
            role = LegacyRole.objects.filter(
                namespace__name=rnamespace,
                name=rname
            ).first()
        if not role:
            continue

        print(f'\t{user}')
        print(f'\t{role}')
        nsurvey,_ = LegacyRoleSurvey.objects.get_or_create(
            user=user,
            role=role
        )
        for qp in question_props:
            current_val = getattr(nsurvey, qp)
            new_val = rsurvey[qp]
            if not new_val:
                continue
            new_val = int(new_val)
            setattr(nsurvey, qp, new_val)
        nsurvey.save()


sync_collections()
sync_roles()
