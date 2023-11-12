select
    rs.user_id,
    ac.username,
    sa.uid github_id,
    rs.docs,
    rs.ease_of_use,
    rs.does_what_it_says,
    rs.works_as_is,
    rs.used_in_production,
    rs.collection_id,
    col.namespace_id,
    mn.name namespace,
    col.name
from main_collectionsurvey rs
left join accounts_customuser ac on ac.id=rs.user_id
left join socialaccount_socialaccount sa on sa.user_id=rs.user_id
left join main_collection col on col.id=rs.collection_id
left join main_namespace mn on mn.id=col.namespace_id
where sa.provider='github'
order by ac.username;
