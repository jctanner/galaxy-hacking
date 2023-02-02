SELECT

    cr.pulp_id,
    cr.name,
    acvs.content_ptr_id,
    acvs.signed_collection_id,

    MAX(crv1.number) as sig_vadded,
    coalesce(MAX(crv2.number), -1) as sig_vremoved,

    True as is_signed

from
    core_repositorycontent crc
left join
    ansible_collectionversionsignature acvs on acvs.content_ptr_id=crc.content_id
left join
    core_repository cr on cr.pulp_id=crc.repository_id
left join
    core_repositoryversion crv1 on crv1.pulp_id=crc.version_added_id
left join
    core_repositoryversion crv2 on crv2.pulp_id=crc.version_removed_id
left join
    ansible_collectionversion acv on acv.content_ptr_id=acvs.content_ptr_id
WHERE
    acvs.content_ptr_id is not null
GROUP BY
    cr.pulp_id, acvs.content_ptr_id
HAVING
    MAX(crv1.number) > coalesce(MAX(crv2.number), -1)
;
