DROP TABLE IF EXISTS ansible_ansiblecollectiondeprecated;
CREATE TABLE ansible_ansiblecollectiondeprecated (
    content_ptr_id UUID NOT NULL,
    namespace character varying(64) NOT NULL,
    name character varying(64) NOT NULL,
    CONSTRAINT ansible_ansiblecollectio_namespace_name_e1aa1c6d_uniq UNIQUE (namespace, name)
);