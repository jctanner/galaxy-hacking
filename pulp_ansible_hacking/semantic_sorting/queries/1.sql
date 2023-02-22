DROP FUNCTION IF EXISTS parse_semantic_version;

CREATE OR REPLACE FUNCTION parse_semantic_version(text)
RETURNS record AS $$
DECLARE
  version text := $1;
  major int;
  minor int;
  patch int;
BEGIN
  IF substring(version, 1, 1) = 'v' THEN
    version := substring(version FROM 2);
  END IF;

  SELECT split_part(version, '.', 1)::int INTO major;
  SELECT split_part(version, '.', 2)::int INTO minor;
  SELECT split_part(split_part(version, '.', 3), '-', 1)::int INTO patch;
  RETURN (major, minor, patch);
END;
$$ LANGUAGE plpgsql;


select
	host,
	namespace,
	name,
	version,
	parse_semantic_version(version) as sv
FROM
	ansible_collectionversion
--ORDER BY sv
;
