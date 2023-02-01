DROP TABLE IF EXISTS core_repositoryversion;
CREATE TABLE core_repositoryversion (
    pulp_id UUID NOT NULL,
    pulp_created timestamp with time zone NOT NULL,
    pulp_last_updated timestamp with time zone,
    number integer NOT NULL,
    complete boolean NOT NULL,
    base_version_id uuid,
    repository_id UUID NOT NULL,
    info jsonb NOT NULL,
    CONSTRAINT core_repositoryversion_repository_id_number_3c54ce50_uniq UNIQUE (repository_id, number)
);