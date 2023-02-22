DROP VIEW IF EXISTS repository_collection_version;
DROP VIEW IF EXISTS repository_collectionsignatures;
DROP VIEW IF EXISTS repository_collectiondeprecations;

CREATE OR REPLACE VIEW repository_collectionsignature AS
SELECT

    cr.pulp_id as repository_id,
    cr.name,
    acvs.content_ptr_id,
    acvs.signed_collection_id as collectionversion_id,

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


CREATE OR REPLACE VIEW repository_collectiondeprecations AS
SELECT

    cr.pulp_id as deprecated_repository_id,
    cr.name as deprecated_repository_name,

    acd.content_ptr_id as deprecation_ptr_id,
    acd.namespace as deprecated_namespace,
    acd.name as deprecated_name,

    CONCAT(cr.name, ':', acd.namespace, ':', acd.name) as deprecated_fqn,

    MAX(crv1.number) as deprecation_vadded,
    coalesce(MAX(crv2.number), -1) as deprecation_vremoved,

    True as is_deprecated

from
    core_repositorycontent crc
left join
    ansible_ansiblecollectiondeprecated acd on acd.content_ptr_id=crc.content_id
left join
    core_repository cr on cr.pulp_id=crc.repository_id
left join
    core_repositoryversion crv1 on crv1.pulp_id=crc.version_added_id
left join
    core_repositoryversion crv2 on crv2.pulp_id=crc.version_removed_id
GROUP BY
    cr.pulp_id, acd.content_ptr_id
HAVING
    acd.content_ptr_id is not NULL
    AND
    MAX(crv1.number) > coalesce(MAX(crv2.number), -1)
;

CREATE OR REPLACE VIEW repository_collection_version AS
SELECT

    CONCAT(cr.pulp_id, '-', acv.content_ptr_id) as id,

    cr.pulp_id as repository_id,
    cr.name as reponame,
    acv.content_ptr_id as collectionversion_id,
    acv.namespace as namespace,
    acv.name as name,
    acv.version as version,

    CONCAT(cr.name, ':', acv.namespace, ':', acv.name) as cv_fqn,

    MAX(crv1.number) as vadded,
    coalesce(MAX(crv2.number), -1) as vremoved,

    core_content.pulp_created as cv_created_at,
    core_content.pulp_last_updated as cv_updated_at,
    acv.requires_ansible as cv_requires_ansible,
    acv.dependencies as cv_dependencies,

    coalesce((
        SELECT
            rcd.is_deprecated
        FROM
            repository_collectiondeprecations rcd
        WHERE
            CONCAT(cr.name, ':', acv.namespace, ':', acv.name)=rcd.deprecated_fqn
    ), False) as is_deprecated,

    coalesce((
        SELECT
            rcvs.is_signed
        FROM
            repository_collectionsignature rcvs
        WHERE
            cr.pulp_id=rcvs.repository_id
            AND
            acv.content_ptr_id=rcvs.collectionversion_id
    ), False) as is_signed

from
    core_repositorycontent crc
left join
    ansible_collectionversion acv on acv.content_ptr_id=crc.content_id
left join
    core_content on acv.content_ptr_id=core_content.pulp_id
left join
    core_repository cr on cr.pulp_id=crc.repository_id
left join
    core_repositoryversion crv1 on crv1.pulp_id=crc.version_added_id
left join
    core_repositoryversion crv2 on crv2.pulp_id=crc.version_removed_id
WHERE
    acv.content_ptr_id is not null
GROUP BY
    cr.pulp_id, acv.content_ptr_id, core_content.pulp_id
HAVING
   MAX(crv1.number) > coalesce(MAX(crv2.number), -1)
;


SELECT reponame,namespace,name,version,is_signed,is_deprecated FROM repository_collection_version;
