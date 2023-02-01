WITH HighestVersionLookup AS
(
    SELECT
        MAX(number) as highest_version,
        repository_id as highest_version_repository_id
    FROM
        core_repositoryversion
    --WHERE
    --    number>0
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

    -- make a synthetic ID for uniqueness        
    --concat(cr.pulp_id, ':', acv.content_ptr_id) AS id,

    crc.pulp_id as crc_pulp_id,
    crc.content_id as crc_content_id,
    crc.repository_id as crc_repository_id,
    crc.version_added_id as crc_version_added_id,
    crc.version_removed_id as crc_version_removed_id,
    --crv.number as crv_version_number,
    --crc.version_added_id as crc_version_added_id,

    --rval.version_added_number as version_added_number,
    --crc.version_removed_id as crc_version_removed_id,
    --cr.pulp_id as repository_id,
    --cr.name as reponame,
    --cr.next_version as cr_next_version,

    --acv.content_ptr_id as collectionversion_id,
    acv.namespace as namespace,
    acv.name as name,
    acv.version as version,

    --hvl.highest_version_repository_id as highest_version_repository_id,
    --hvl.highest_version as highest_version

    (
        SELECT
            cr.name as repository_name
        FROM
            core_repository cr
        WHERE
            cr.pulp_id=crc.repository_id
    )

    --(
    --    SELECT
    --        number as version_added_number
    --    FROM
    --        core_repositoryversion crv
    --    WHERE
    --        crv.pulp_id=crc.version_added_id
    --) as version_added_number,

    --(
    --    SELECT
    --        number as version_removed_number
    --    FROM
    --        core_repositoryversion crv
    --    WHERE
    --        crv.pulp_id=crc.version_removed_id
    --) as version_removed_number



FROM
    core_repositorycontent crc

INNER JOIN
    ansible_collectionversion acv ON acv.content_ptr_id=crc.content_id

--INNER JOIN
--    core_repository cr ON cr.pulp_id=crc.repository_id

--INNER JOIN
--    core_repositoryversion crv ON crv.repository_id=cr.pulp_id

--INNER JOIN
--    HighestVersionLookup hvl ON hvl.highest_version_repository_id=crv.repository_id

WHERE
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
                    --rvalx.repository_version_added_id=crc.version_added_id
                    rvalx.repository_version_id=crc.version_added_id
            )
        )
    )


--WHERE
--    (
--        version_removed_id is NULL
--        OR
--        version_added_number>version_removed_number
--    )

;
