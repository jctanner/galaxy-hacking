WITH
	AnsibleRepositoryContentVersions (repoid, reponame, cv_id, namespace, name, version, vadded, vremoved)
	AS
	(
		select
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
			cr.pulp_id, cr.name, acv.content_ptr_id, acv.namespace, acv.name, acv.version	
	)

SELECT
	concat(repoid, ':', cv_id) AS id,
	repoid as repository_id,
	cv_id as collectionversion_id,
	reponame,
	namespace,
	name,
	version,

    -- count the number of deprecations for this namespace.name
    (
        SELECT
            COUNT(*)
        FROM
            ansible_ansiblecollectiondeprecated acd
        WHERE
            acd.namespace=namespace
        AND
            acd.name=name
    ) as deprecation_count,

    -- count the number of applicable signatures for this CV+repo
    (
        SELECT
            COUNT(*)
        FROM
            ansible_collectionversionsignature acvs
        WHERE
            acvs.signed_collection_id=cv_id
            AND
            (
                SELECT
                    COUNT(*)
                FROM
                    core_repositorycontent crc3
                WHERE
                    crc3.repository_id=repoid
                AND
                    crc3.content_id=acvs.content_ptr_id
            )>=1
    ) as sig_count

from
	AnsibleRepositoryContentVersions

WHERE
	(
		vremoved is null
		OR
		vremoved < vadded
	)
;
