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
  sections text[];
  new_section text;
  this_section text;
  this_section_index int;
  major int;
  minor int;
  patch int;
  prerelease text;
  is_prerelease boolean;
BEGIN

  --RAISE NOTICE 'VERSION: %', version;

  IF substring(version, 1, 1) = 'v' THEN
    version := substring(version FROM 2);
  END IF;

  --SELECT split_part(version, '.', 1)::int INTO major;
  --SELECT split_part(version, '.', 2)::int INTO minor;
  --SELECT split_part(version, '.', 3) INTO prerelease;

  this_section = version;
  FOR i IN 1..3 LOOP

    --RAISE NOTICE '%', i;
    --RAISE NOTICE '    TS: %', this_section;

    if i = 3 THEN
        sections := array_append(sections, this_section);
    ELSE
        this_section_index := POSITION('.' in this_section);
        --RAISE NOTICE '    IX: %', this_section_index;

        IF this_section_index = 0 THEN
          new_section := this_section;
        ELSE
          new_section = substring(this_section, 0, this_section_index);
          --RAISE NOTICE '    NEW_SECTION: %', new_section;
          this_section := substring(this_section, this_section_index + 1);
        END IF;

        --RAISE NOTICE '    THIS_SECTION: %', this_section;
        sections := array_append(sections, new_section);
    END IF;

  END LOOP;
  --RAISE NOTICE 'SECTIONS: %', sections;

  SELECT sections[1]::int INTO major;
  SELECT sections[2]::int INTO minor;
  SELECT sections[3]::text INTO prerelease;

  IF POSITION('-' in prerelease) > 0 THEN
    SELECT split_part(prerelease, '-', 1)::int INTO patch;
    --prerelease := split_part(prerelease, '-', 2);
    this_section_index := POSITION('-' in prerelease);
    prerelease := substring(prerelease, this_section_index + 1);
  ELSE
    IF POSITION('+' in prerelease) > 0 THEN
        SELECT split_part(prerelease, '+', 1)::int INTO patch;
        --prerelease := split_part(prerelease, '+', 2);
        this_section_index := POSITION('+' in prerelease);
        prerelease := substring(prerelease, this_section_index + 1);
    ELSE
        IF POSITION('.' in prerelease) > 0 THEN
            SELECT split_part(prerelease, '.', 1)::int INTO patch;
            --prerelease := split_part(prerelease, '+', 2);
            this_section_index := POSITION('.' in prerelease);
            prerelease := substring(prerelease, this_section_index + 1);
        ELSE
            SELECT prerelease::int INTO patch;
            SELECT '' INTO prerelease;
        END IF;
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
    namespace,
    name,
    version as oversion,
    (parsed_version).version as semver,
    (parsed_version).prerelease as prerelease,
    (parsed_version).is_prerelease as is_prerelease
FROM
	(
		SELECT
            --DISTINCT
            namespace,
            name,
            version,
            parse_semantic_version(version) as parsed_version
        FROM
            ansible_collectionversion
	) as t
GROUP BY
    t.namespace,t.name,t.version,t.parsed_version
;


select
    --acv.content_ptr_id,
    acv.host,
    acv.namespace,
    acv.name,
    acv.version,
    --parse_semantic_version(acv.version) as sver1
    svm.semver,
    --COALESCE(svm.prerelease, 'NO'),
    svm.prerelease,
    svm.is_prerelease,
    (
        SELECT
            MAX(semver)
        FROM
            semantic_version_map_view svm2
        WHERE
            svm2.is_prerelease=false
            AND
            svm2.namespace=acv.namespace
            AND
            svm2.name=acv.name
    )=svm.semver as max_semver
FROM
    ansible_collectionversion acv
LEFT JOIN
    semantic_version_map_view as svm on (svm.namespace=acv.namespace AND svm.name=acv.name AND svm.oversion=acv.version)
WHERE
    --acv.namespace='bob'
    svm.is_prerelease=false
    AND
    (
        SELECT
            MAX(semver)
        FROM
            semantic_version_map_view svm2
        WHERE
            svm2.is_prerelease=false
            AND
            svm2.namespace=acv.namespace
            AND
            svm2.name=acv.name
    )=svm.semver
ORDER BY
    acv.namespace,
    acv.name,
    acv.version
	--svm.semver
;
