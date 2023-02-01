SELECT
    --distinct
    cr.pulp_id as repository_id,
    cr.name as reponame,
    acv.content_ptr_id as collectionversion_id,
    acv.namespace as namespace,
    acv.name as name,
    acv.version as version,
    MAX(crv1.number) as vadded,
    coalesce(MAX(crv2.number), -1) as vremoved
from
    core_repositorycontent crc
left join
    ansible_collectionversion acv on acv.content_ptr_id=crc.content_id
left join
    core_repository cr on cr.pulp_id=crc.repository_id
left join
    core_repositoryversion crv1 on crv1.pulp_id=crc.version_added_id
left join
    core_repositoryversion crv2 on crv2.pulp_id=crc.version_removed_id
WHERE
    acv.content_ptr_id is not null
GROUP BY
    cr.pulp_id, acv.content_ptr_id
HAVING
   MAX(crv1.number) > coalesce(MAX(crv2.number), -1)
;
