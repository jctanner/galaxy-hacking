DROP TABLE IF EXISTS ansible_collectionversion;
CREATE TABLE ansible_collectionversion (
    content_ptr_id UUID NOT NULL,
    host character varying(64) NOT NULL,
    namespace character varying(64) NOT NULL,
    name character varying(64) NOT NULL,
    version character varying(128) NOT NULL,
    CONSTRAINT ansible_collectionversion_namespace_name_version_96aacd81_uniq UNIQUE (host, namespace, name, version)
);
