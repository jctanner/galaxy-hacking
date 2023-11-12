select
    rs.user_id,
    ac.username,
    sa.uid github_id,
    rs.docs,
    rs.ease_of_use,
    rs.does_what_it_says,
    rs.works_as_is,
    rs.used_in_production,
    rs.repository_id,
    mr.provider_namespace_id provider_ns_id,
    pn.name provider_ns_name,
    mn.name ns_name,
    mr.name repo_name
from main_repositorysurvey rs
left join accounts_customuser ac on ac.id=rs.user_id
left join socialaccount_socialaccount sa on sa.user_id=rs.user_id
left join main_repository mr on mr.id=rs.repository_id
left join main_providernamespace pn on pn.id=mr.provider_namespace_id
left join main_namespace mn on mn.id=pn.namespace_id
where sa.provider='github'
order by ac.username;
