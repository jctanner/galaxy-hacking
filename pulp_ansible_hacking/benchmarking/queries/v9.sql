WITH
    AnsibleRepositoryContentVersions (repoid, reponame, cv_id, namespace, name, version, vadded, vremoved)
    AS
    (
        select
            distinct
            cr.pulp_id as repoid,
            cr.name as reponame,
            acv.content_ptr_id as cv_id,
            acv.namespace as namespace,
            acv.name as name,
            acv.version as version,
            MAX(crv1.number) as vadded,
            MAX(crv2.number) as vremoved
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
            cr.pulp_id, acv.content_ptr_id, acv.namespace, acv.name, acv.version
    )

SELECT
    concat(repoid, ':', cv_id) AS id,
    repoid as repository_id,
    cv_id as collectionversion_id,
    reponame,
    --namespace,
    --name,
    --version,
    MAX(namespace) as namespace,
    MAX(name) as name,
    MAX(version) as version,
    MAX(vadded) as added,
    MAX(vremoved) as removed


from
    AnsibleRepositoryContentVersions

GROUP BY
    repoid,reponame,cv_id

--WHERE
--    (namespace='pink' AND name='panther' AND version='2.0.0')
;
