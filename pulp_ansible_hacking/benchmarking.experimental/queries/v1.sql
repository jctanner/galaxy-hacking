SELECT
	distinct
	concat(cr.pulp_id, ':', acv.content_ptr_id) AS id,
	cr.pulp_id as repository_id,
	acv.content_ptr_id as collectionversion_id,
	cc.pulp_id as content_id,
	cr.name as reponame,
	acv.namespace,
	acv.name,
	acv.version,
	(
		SELECT
			COUNT(*)
		FROM
			core_repositorycontent crc2
		WHERE
			crc2.content_id=cc.pulp_id
			AND
			crc2.repository_id=cr.pulp_id
			AND
			acv.content_ptr_id=crc2.content_id
	) as rc_count,
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
	) as sig_count,
	(
		SELECT
			COUNT(*)
		FROM
			ansible_ansiblecollectiondeprecated acd
		WHERE
			acd.namespace=acv.namespace
			AND
			acd.name=acv.name
	) as deprecation_count
FROM
	ansible_collectionversion acv,
	core_content cc,
	core_repositorycontent crc
inner join core_repository cr ON crc.repository_id=cr.pulp_id
WHERE
	cc.pulp_id=crc.content_id
	AND
	(
		SELECT
			COUNT(*)
		FROM
			core_repositorycontent crc2
		WHERE
			crc2.content_id=cc.pulp_id
			AND
			crc2.repository_id=cr.pulp_id
			AND acv.content_ptr_id=crc2.content_id
	)>=1
ORDER BY
	acv.namespace,
	acv.name,
	acv.version,
	reponame
;
