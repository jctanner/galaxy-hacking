DROP VIEW IF EXISTS ansible_cross_repository_collection_versions_viewx;
DROP VIEW IF EXISTS ansible_cross_repository_collection_version_signatures_viewx;
DROP VIEW IF EXISTS ansible_cross_repository_collection_deprecations_viewx;
DROP VIEW IF EXISTS highest_acv_by_repo;

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

  IF substring(version, 1, 1) = 'v' THEN
    version := substring(version FROM 2);
  END IF;

  this_section = version;
  FOR i IN 1..3 LOOP

    if i = 3 THEN
        sections := array_append(sections, this_section);
    ELSE
        this_section_index := POSITION('.' in this_section);

        IF this_section_index = 0 THEN
          new_section := this_section;
        ELSE
          new_section = substring(this_section, 0, this_section_index);
          this_section := substring(this_section, this_section_index + 1);
        END IF;

        sections := array_append(sections, new_section);
    END IF;

  END LOOP;

  SELECT sections[1]::int INTO major;
  SELECT sections[2]::int INTO minor;
  SELECT sections[3]::text INTO prerelease;

  IF POSITION('-' in prerelease) > 0 THEN
    SELECT split_part(prerelease, '-', 1)::int INTO patch;
    this_section_index := POSITION('-' in prerelease);
    prerelease := substring(prerelease, this_section_index + 1);
  ELSE
    IF POSITION('+' in prerelease) > 0 THEN
        SELECT split_part(prerelease, '+', 1)::int INTO patch;
        this_section_index := POSITION('+' in prerelease);
        prerelease := substring(prerelease, this_section_index + 1);
    ELSE
        IF POSITION('.' in prerelease) > 0 THEN
            SELECT split_part(prerelease, '.', 1)::int INTO patch;
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


CREATE OR REPLACE view highest_acv_by_repo AS
SELECT
    repository_id,
    --content_id,
    acv.namespace as namespace,
    acv.name as name,
    --acv.version as version,
    MAX(svm.semver) as highest_semver
    --svm.is_prerelease
FROM
    core_repositorycontent crc
inner join 
    ansible_collectionversion acv on acv.content_ptr_id=crc.content_id
left join
    semantic_version_map_view svm
    on
    (
        svm.namespace=acv.namespace
        AND
        svm.name=acv.name
        AND
        svm.oversion=acv.version
    )
WHERE
    svm.is_prerelease is false
GROUP BY
    crc.repository_id,
    acv.namespace,
    acv.name
--HAVING
--    svm.is_prerelease is false
;


--
-- OLD STUFF
--

CREATE OR REPLACE VIEW ansible_cross_repository_collection_version_signatures_viewx AS
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

CREATE OR REPLACE VIEW ansible_cross_repository_collection_deprecations_viewx AS
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

CREATE OR REPLACE VIEW ansible_cross_repository_collection_versions_viewx AS
SELECT

    CONCAT(cr.pulp_id, '-', acv.content_ptr_id) as id,

    cd.pulp_id as distribution_id,
    cd.pulp_id as dist_id,
    cd.name as distribution_name,
    cd.base_path as base_path,

    cr.pulp_id as repository_id,
    cr.pulp_id as repo_id,
    cr.name as reponame,

    acv.content_ptr_id as collectionversion_id,
    acv.namespace as namespace,
    acv.name as name,
    acv.version as version,

    svm.semver as semver,
    svm.prerelease as prerelease,
    svm.is_prerelease as is_prerelease,

    core_content.pulp_created as cv_created_at,
    core_content.pulp_last_updated as cv_updated_at,
    acv.requires_ansible as cv_requires_ansible,
    acv.dependencies as cv_dependencies,

    coalesce((rcd.is_deprecated), False) as is_deprecated,
    coalesce((rcvs.is_signed), False) as is_signed,

    MAX(habr.highest_semver) as highest_semver

from
    core_repositorycontent crc
left join
    ansible_collectionversion acv on acv.content_ptr_id=crc.content_id
left join
    semantic_version_map_view svm
    on
    (
        svm.namespace=acv.namespace
        AND
        svm.name=acv.name
        AND
        svm.oversion=acv.version
    )
left join
    highest_acv_by_repo habr
    on
    (
        habr.repository_id=crc.repository_id
        AND
        habr.namespace=acv.namespace
        AND
        habr.name=acv.name
    )
left join
    core_content on acv.content_ptr_id=core_content.pulp_id
left join
    core_repository cr on cr.pulp_id=crc.repository_id
left join
    core_distribution cd on cd.repository_id=cr.pulp_id
left join
    core_repositoryversion crv1 on crv1.pulp_id=crc.version_added_id
left join
    core_repositoryversion crv2 on crv2.pulp_id=crc.version_removed_id
left join
    ansible_cross_repository_collection_version_signatures_viewx rcvs on
    (
        cr.pulp_id=rcvs.repository_id
        AND
        acv.content_ptr_id=rcvs.collectionversion_id
    )
left join ansible_cross_repository_collection_deprecations_viewx rcd on
    CONCAT(cr.name, ':', acv.namespace, ':', acv.name)=rcd.deprecated_fqn
WHERE
    acv.content_ptr_id is not null
GROUP BY
    cd.pulp_id,
    cr.pulp_id,
    acv.content_ptr_id,
    svm.semver,
    svm.prerelease,
    svm.is_prerelease,
    core_content.pulp_id,
    rcvs.is_signed,
    rcd.is_deprecated
HAVING
   cd.pulp_id is not null
   AND
   MAX(crv1.number) > coalesce(MAX(crv2.number), -1)
;

SELECT
    reponame,namespace,name,version,semver,prerelease,is_prerelease, highest_semver
from ansible_cross_repository_collection_versions_viewx;
--SELECT
--    repository_id,
--    namespace,
--    name,
--    highest_semver
--FROM
--    highest_acv_by_repo
--;
