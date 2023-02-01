from django.contrib.postgres import search as psql_search
from django.db import migrations


#  A view that does a view things:
#   * cartesian product on collectionversions, content and repository_content
#   * reduce the product via a where clause down to combinations that have matching IDs
#   * subquery to make a count of signatures attached to the CV and the repo
#   * subquery to make a count of deprecations related to the CV
#   * The app code has an unmanaged model that makes this view look like any
#     other model and is compatible with filtersets and serializers.
#
# Why?
#   * The x-repo search requirements want the same CV listed N times per
#     repositories containing the CV.
#   * Many models and objects and concepts desired for cross repo search
#     filtering are not directly related to repositories.
#   * Using the queryset language to build the counts for signatures and
#     deprecations were drifting from wizardry into impossibility.
#   * Creating a real index model requires too many hooks in various
#     obscure workflows for CRUD and new devs will always make mistakes.

CREATE_REPOSITORY_COLLECTIONVERSION_VIEW = '''
CREATE OR REPLACE VIEW repository_collection_version AS
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
'''


DROP_REPOSITORY_COLLECTIONVERSION_VIEW = '''
DROP VIEW IF EXISTS repository_collection_version;
'''


class Migration(migrations.Migration):

    dependencies = [
        ('ansible', '0046_add_fulltext_search_fix'),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_REPOSITORY_COLLECTIONVERSION_VIEW,
            reverse_sql=DROP_REPOSITORY_COLLECTIONVERSION_VIEW,
        ),
    ]
