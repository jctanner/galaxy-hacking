DROP TABLE IF EXISTS ansible_collectionversionsignature;
CREATE TABLE ansible_collectionversionsignature (
    content_ptr_id UUID NOT NULL,
    digest character varying(64) NOT NULL,
    pubkey_fingerprint character varying(64) NOT NULL,
    signed_collection_id UUID NOT NULL,
    signing_service_id uuid,
    data text NOT NULL,
    CONSTRAINT ansible_collectionversio_pubkey_fingerprint_signe_da0af2db_uniq UNIQUE (pubkey_fingerprint, signed_collection_id)
);