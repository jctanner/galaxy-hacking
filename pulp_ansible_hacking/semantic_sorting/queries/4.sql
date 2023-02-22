DROP VIEW IF EXISTS semantic_version_map_view;
DROP FUNCTION IF EXISTS parse_semantic_version;
DROP TYPE IF EXISTS parse_result;

CREATE TYPE parse_result AS (
  version int[],
  prerelease text,
  is_prerelease boolean
);

CREATE OR REPLACE FUNCTION parse_semantic_version(text)
RETURNS parse_result AS $$
DECLARE
  version text := $1;
  major int;
  minor int;
  patch int;
  prerelease text;
  is_prerelease boolean;
BEGIN
  IF substring(version, 1, 1) = 'v' THEN
    version := substring(version FROM 2);
  END IF;

  SELECT split_part(version, '.', 1)::int INTO major;
  SELECT split_part(version, '.', 2)::int INTO minor;
  SELECT split_part(version, '.', 3) INTO prerelease;

  IF POSITION('-' in prerelease) > 0 THEN
    SELECT split_part(prerelease, '-', 1)::int INTO patch;
    prerelease := split_part(prerelease, '-', 2);
  ELSE
    IF POSITION('+' in prerelease) > 0 THEN
        SELECT split_part(prerelease, '+', 1)::int INTO patch;
        prerelease := split_part(prerelease, '+', 2);
    ELSE
        SELECT prerelease::int INTO patch;
        SELECT '' INTO prerelease;
    END IF;
  END IF;

  IF prerelease = '' THEN
    is_prerelease := false;
  ELSE
    is_prerelease := true;
  END IF;

  RETURN (ARRAY[major::int, minor::int, patch::int], prerelease, is_prerelease);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE view semantic_version_map_view AS
SELECT
    DISTINCT
    version as oversion,
    (parsed_version).version as semver,
    (parsed_version).prerelease as prerelease,
    (parsed_version).is_prerelease as is_prerelease
FROM
	(
		SELECT
            DISTINCT
            version,
            parse_semantic_version(version) as parsed_version
        FROM
            ansible_collectionversion
	) as t
;


select
    acv.content_ptr_id,
    acv.host,
    acv.namespace,
    acv.name,
    acv.version,
    --parse_semantic_version(acv.version) as sver1
    svm.semver,
    --COALESCE(svm.prerelease, 'NO'),
    svm.prerelease,
    svm.is_prerelease
FROM
    ansible_collectionversion acv
JOIN
    semantic_version_map_view as svm on svm.oversion=acv.version
WHERE
    acv.namespace='bob'
ORDER BY
	svm.semver
;
