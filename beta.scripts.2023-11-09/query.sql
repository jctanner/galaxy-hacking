galaxy=> select
        sa.modified sa_modified,
        ln.created legacy_ns_created,
        ln.modified legacy_ns_modified,
        sa.uid,
        gu.username username,
        ln.name legacy_ns,
        gn.name v3_ns
from
        social_auth_usersocialauth sa
left join
        galaxy_user gu on gu.id=sa.user_id
left join
        galaxy_legacynamespace ln on ln.name=gu.username
left join
        galaxy_namespace gn on gn.id=ln.namespace_id
where
        ln.name not like '%0' and gn.name like '%0'
order by sa.modified desc
;
