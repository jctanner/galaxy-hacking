WITH HighestVersionLookup AS
(
    SELECT
        MAX(number) as highest_version,
        repository_id as highest_version_repository_id
    FROM
        core_repositoryversion
    GROUP BY
        repository_id
    ORDER BY
        repository_id
),

RepositoryVersionNumberLookup AS
(
    SELECT
        pulp_id as repository_version_id,
        number
    FROM
        core_repositoryversion
)

SELECT

    crc.pulp_id as crc_pulp_id,
    crc.content_id as crc_content_id,
    crc.repository_id as crc_repository_id,
    crv.number as crv_version_number,
    crc.version_added_id as crc_version_added_id,
    crc.version_removed_id as crc_version_removed_id,
    cr.pulp_id as repository_id,
    hvl.highest_version as highest_version,

    cr.name as reponame,
    acv.namespace as namespace,
    acv.name as name,
    acv.version as version

FROM
    core_repositorycontent crc
INNER JOIN
    core_repository cr ON cr.pulp_id=crc.repository_id
INNER JOIN
    core_repositoryversion crv ON crv.repository_id=cr.pulp_id
INNER JOIN
    ansible_collectionversion acv ON acv.content_ptr_id=crc.content_id
INNER JOIN
    HighestVersionLookup hvl ON hvl.highest_version_repository_id=crv.repository_id

WHERE
    highest_version=crv.number
    AND
    (
        crc.version_removed_id is NULL
        OR
        (
            (
                SELECT
                    number
                FROM
                    RepositoryVersionNumberLookup rvmlx
                WHERE
                    rvmlx.repository_version_id=crc.version_removed_id
            )
            <
            (
                SELECT
                    number
                FROM
                    RepositoryVersionNumberLookup rvalx
                WHERE
                    rvalx.repository_version_id=crc.version_added_id
            )
        )
    )

ORDER BY
    acv.namespace, acv.name, acv.version, cr.name
;
