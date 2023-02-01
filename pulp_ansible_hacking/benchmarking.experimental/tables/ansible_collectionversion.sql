DROP TABLE IF EXISTS ansible_collectionversion;
CREATE TABLE ansible_collectionversion (
    content_ptr_id UUID NOT NULL,
    version character varying(128) NOT NULL,
    contents jsonb NOT NULL,
    collection_id UUID NOT NULL,
    authors character varying(64)[] NOT NULL,
    dependencies jsonb NOT NULL,
    description text NOT NULL,
    docs_blob jsonb NOT NULL,
    documentation character varying(2000) NOT NULL,
    homepage character varying(2000) NOT NULL,
    issues character varying(2000) NOT NULL,
    license character varying(32)[] NOT NULL,
    name character varying(64) NOT NULL,
    namespace character varying(64) NOT NULL,
    repository character varying(2000) NOT NULL,
    search_vector tsvector NOT NULL,
    is_highest boolean NOT NULL,
    files jsonb NOT NULL,
    manifest jsonb NOT NULL,
    requires_ansible character varying(255),
    CONSTRAINT ansible_collectionversion_namespace_name_version_96aacd81_uniq UNIQUE (namespace, name, version)
);