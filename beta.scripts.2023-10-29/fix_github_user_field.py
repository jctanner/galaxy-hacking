from galaxy_ng.app.api.v1.models import LegacyRole


for lrole in LegacyRole.objects.all():
    github_user = lrole.full_metadata.get('github_user')
    if github_user:
        continue
    new_github_user = lrole.namespace.name
    print(f'{lrole} {github_user} -> {new_github_user}')
    lrole.full_metadata['github_user'] = new_github_user
    lrole.save()




