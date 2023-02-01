DROP TABLE IF EXISTS core_repositorycontent;
CREATE TABLE core_repositorycontent (
    pulp_id UUID NOT NULL,
    pulp_created timestamp with time zone NOT NULL,
    pulp_last_updated timestamp with time zone,
    content_id UUID NOT NULL,
    repository_id UUID NOT NULL,
    version_added_id UUID NOT NULL,
    version_removed_id uuid,
    CONSTRAINT core_repositorycontent_repository_id_content_id_df902e11_uniq UNIQUE (repository_id, content_id, version_removed_id),
    CONSTRAINT core_repositorycontent_repository_id_content_id_fb06c181_uniq UNIQUE (repository_id, content_id, version_added_id)
);