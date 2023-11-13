import json

from django.contrib.auth import get_user_model
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.models.survey import CollectionSurvey
from galaxy_ng.app.models.survey import CollectionSurveyRollup
from galaxy_ng.app.models.survey import LegacyRoleSurvey
from galaxy_ng.app.models.survey import LegacyRoleSurveyRollup
from pulp_ansible.app.models import Collection

from galaxy_ng.app.utils.survey import calculate_survey_score


role_ids = sorted(set(list(LegacyRoleSurvey.objects.values_list("role", flat=True))))
for role_id in role_ids:
    this_role = LegacyRole.objects.get(id=role_id)
    print(this_role)

    this_role_surveys = LegacyRoleSurvey.objects.filter(role=this_role)
    print(this_role_surveys)

    score = calculate_survey_score(this_role_surveys)
    print(score)

    rollup,_ = LegacyRoleSurveyRollup.objects.get_or_create(role=this_role, defaults={'score': score})
    print(rollup)
    print(rollup.score)


collection_ids = sorted(set(list(CollectionSurvey.objects.values_list("collection", flat=True))))
for collection_id in collection_ids:
    this_collection = Collection.objects.get(pulp_id=collection_id)
    print(this_collection)

    this_collection_surveys = CollectionSurvey.objects.filter(collection=this_collection)
    print(this_collection_surveys)

    score = calculate_survey_score(this_collection_surveys)
    print(score)

    rollup,_ = CollectionSurveyRollup.objects.get_or_create(collection=this_collection, defaults={'score': score})
    print(rollup)
    print(rollup.score)
