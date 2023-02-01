DROP VIEW IF EXISTS repository_collection_version;

CREATE OR REPLACE VIEW repository_collection_version AS

-- make a map for highest version
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
)

SELECT

    crc.pulp_id as crc_pulp_id,
    crc.content_id as crc_content_id,
    crc.repository_id as crc_repository_id,
    crv.number as crv_version_number,
    crc.version_added_id as crc_version_added_id,
    crc.version_removed_id as crc_version_removed_id,
    cr.pulp_id as cr_pulp_id,

    cr.next_version as cr_next_version,
    acv.content_ptr_id as collectionversion_id,

    hvl.highest_version_repository_id as highest_version_repository_id,
    hvl.highest_version as highest_version,

    -- make a synthetic ID for uniqueness        
    concat(cr.pulp_id, ':', acv.content_ptr_id) AS id,

    -- used by the model
    cr.pulp_id as repository_id,

    -- used by the model
    cr.name as reponame,

    -- used by the model
    acv.namespace as namespace,

    -- used by the model
    acv.name as name,

    -- used by the model
    acv.version as version,

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
WHERE
    highest_version=crv.number
ORDER BY
    reponame,
    namespace,
    name,
    version
;
