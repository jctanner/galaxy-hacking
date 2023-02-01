DROP TABLE IF EXISTS core_repository;
CREATE TABLE core_repository (
    pulp_id UUID NOT NULL,
    pulp_created timestamp with time zone NOT NULL,
    pulp_last_updated timestamp with time zone,
    name text NOT NULL,
    description text,
    next_version integer NOT NULL,
    pulp_type text NOT NULL,
    remote_id uuid,
    retain_repo_versions integer,
    user_hidden boolean NOT NULL,
    pulp_labels hstore NOT NULL,
    CONSTRAINT core_repository_name_key UNIQUE (name)
);