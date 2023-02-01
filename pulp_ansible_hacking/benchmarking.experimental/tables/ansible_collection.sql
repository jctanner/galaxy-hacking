DROP TABLE IF EXISTS ansible_collection;
CREATE TABLE ansible_collection (
    pulp_id UUID NOT NULL,
    pulp_created timestamp with time zone NOT NULL,
    pulp_last_updated timestamp with time zone,
    namespace character varying(64) NOT NULL,
    name character varying(64) NOT NULL,
    CONSTRAINT ansible_collection_namespace_name_8676eeb2_uniq UNIQUE (namespace, name)
);