DROP FUNCTION IF EXISTS split_version;

-- major,minor,patch,pre_release,build_metadata
CREATE OR REPLACE FUNCTION split_version(version_string text)
RETURNS text[] AS $$
DECLARE
  version_array text[];
BEGIN
  version_array := string_to_array(version_string, '.');
  RETURN version_array;
END;
$$ LANGUAGE plpgsql;

select
    arc.collectionversion_id,
    arc.reponame,
    arc.namespace,
    arc.name,
    arc.version,
    acv.is_highest,
    split_version(arc.version) as version_tuple,
	(
		SELECT
			split_version(MAX(version)) as max_version
		FROM
			ansible_cross_repository_collection_versions_view arc2
		WHERE
			arc2.reponame=arc.reponame
			AND
			arc2.namespace=arc.namespace
			AND
			arc2.name=arc.name
	)
from
    ansible_cross_repository_collection_versions_view as arc
inner join
    ansible_collectionversion acv on acv.content_ptr_id=arc.collectionversion_id
where
    arc.name='bellz'
order by
	arc.version
;
