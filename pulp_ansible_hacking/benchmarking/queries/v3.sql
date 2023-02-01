WITH HighestVersionLookup AS
(
    SELECT
        MAX(number) as highest_version,
        repository_id as highest_version_repository_id
    FROM
        core_repositoryversion
    WHERE
        number>0
    GROUP BY
        repository_id
    ORDER BY
        repository_id
),

RepositoryVersionAddedLookup AS
(
    SELECT
        pulp_id as repository_version_added_id,
        --pulp_id as repository_version_removed_id,
        number as version_added_number
        --number as version_removed_number
    FROM
        core_repositoryversion
),

RepositoryVersionRemovedLookup AS
(
    SELECT
        pulp_id as repository_version_id,
        number as version_removed_number
    FROM
        core_repositoryversion
)

SELECT

    -- make a synthetic ID for uniqueness        
    concat(cr.pulp_id, ':', acv.content_ptr_id) AS id,

    crc.pulp_id as crc_pulp_id,
    crc.content_id as crc_content_id,
    crc.repository_id as crc_repository_id,
    crv.number as crv_version_number,
    crc.version_added_id as crc_version_added_id,
    rval.version_added_number as version_added_number,
    crc.version_removed_id as crc_version_removed_id,
    --cr.pulp_id as cr_pulp_id,
    cr.pulp_id as repository_id,
    --cr.name as cr_name,
    cr.name as reponame,
    cr.next_version as cr_next_version,
    --acv.content_ptr_id as collection_content_ptr_id,
    acv.content_ptr_id as collectionversion_id,
    acv.namespace as namespace,
    acv.name as name,
    acv.version as version,
    hvl.highest_version_repository_id as highest_version_repository_id,
    hvl.highest_version as highest_version,

    -- enumerate the version removed number
    (
        SELECT
            version_removed_number
        FROM
            RepositoryVersionRemovedLookup rvml
        WHERE
            rvml.repository_version_id=crc.version_removed_id
    ) as version_removed_number,

    -- count the number of deprecations for this namespace.name
    (
        SELECT
            COUNT(*)
        FROM
            ansible_ansiblecollectiondeprecated acd
        WHERE
            acd.namespace=acv.namespace
        AND
            acd.name=acv.name
    ) as deprecation_count,

    -- count the number of applicable signatures for this CV+repo
    (
        SELECT
            COUNT(*)
        FROM
            ansible_collectionversionsignature acvs
        WHERE
            acvs.signed_collection_id=acv.content_ptr_id
        AND
        (
            SELECT
                COUNT(*)
            FROM
                core_repositorycontent crc3
            WHERE
                crc3.repository_id=crc.repository_id
            AND
                crc3.content_id=acvs.content_ptr_id
        )>=1
    ) as sig_count

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
INNER JOIN
    RepositoryVersionAddedLookup rval ON rval.repository_version_added_id=crc.version_added_id
--INNER JOIN
--    RepositoryVersionAddedLookup rval2 ON rval2.repository_version_removed_id=crc.version_removed_id
--LEFT JOIN
--    RepositoryVersionRemovedLookup rvrl ON rvrl.repository_version_id=crc.version_removed_id
WHERE
    highest_version=crv.number
    AND
    (
        crc.version_removed_id is NULL
--        OR
--        (
--            SELECT DISTINCT
--                version_removed_number
--            FROM
--                RepositoryVersionRemovedLookup rvrl2
--            WHERE
--                rvrl2.repository_version_id=crc.version_removed_id
--        )<version_added_number
    )
--LIMIT 5
;
