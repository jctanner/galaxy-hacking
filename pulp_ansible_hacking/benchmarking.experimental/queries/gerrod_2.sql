SELECT

    crc.pulp_id as crc_pulp_id,
    crc.content_id as crc_content_id,
    crc.repository_id as crc_repository_id,
    crc.version_added_id as crc_version_added_id,
    crc.version_removed_id as crc_version_removed_id,
    crc.version_added_id as crc_version_added_id,

    cr.pulp_id as repository_id,
    cr.name as reponame,

    crv.number as crv_version_number,

    acv.namespace,
    acv.name,
    acv.version

FROM
    core_repositorycontent crc

INNER JOIN
    ansible_collectionversion acv ON acv.content_ptr_id=crc.content_id

INNER JOIN
    core_repository cr ON cr.pulp_id=crc.repository_id
INNER JOIN
    core_repositoryversion crv ON crv.repository_id=cr.pulp_id

ORDER BY
    acv.namespace, acv.name, acv.version, cr.name
;
