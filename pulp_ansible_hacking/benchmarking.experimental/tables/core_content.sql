DROP TABLE IF EXISTS core_content;
CREATE TABLE core_content (
    pulp_id UUID NOT NULL,
    pulp_created timestamp with time zone NOT NULL,
    pulp_last_updated timestamp with time zone,
    pulp_type text NOT NULL,
    upstream_id uuid,
    timestamp_of_interest timestamp with time zone NOT NULL
);