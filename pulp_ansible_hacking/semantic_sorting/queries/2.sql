DROP FUNCTION IF EXISTS parse_semantic_version;
DROP VIEW IF EXISTS semantic_version_map_view;

CREATE OR REPLACE FUNCTION parse_semantic_version(text)
RETURNS record AS $$
DECLARE
  version text := $1;
  major int;
  minor int;
  patch int;
  prerelease text;
BEGIN
  IF substring(version, 1, 1) = 'v' THEN
    version := substring(version FROM 2);
  END IF;

  SELECT split_part(version, '.', 1)::int INTO major;
  SELECT split_part(version, '.', 2)::int INTO minor;
  SELECT split_part(version, '.', 3) INTO prerelease;
  SELECT split_part(prerelease, '-', 1)::int INTO patch;
  prerelease := split_part(prerelease, '-', 2);

  RETURN (major, minor, patch, prerelease);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE view semantic_version_map_view AS
SELECT
    cv.version oversion,
    parse_semantic_version(cv.version) as sversion
FROM
    ansible_collectionversion cv
;


select
	acv.host,
	acv.namespace,
	acv.name,
	acv.version,
	--parse_semantic_version(acv.version) as sver1
FROM
	ansible_collectionversion acv
LEFT JOIN
    semantic_version_map_view as sview ON sview.oversion=acv.version
;
