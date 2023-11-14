#!/bin/bash

# create dump through the jumphost with ...
#   pg_dump -Fc -f beta_prod.dump -d galaxy -U galaxy -h localhost -p 5432


# start fresh ...
dropdb --user postgres galaxy
dropdb --user postgres pulp
su postgres -c "createdb --encoding=utf-8 --locale=en_US.UTF-8 -T template0 -O pulp galaxy"

# This will take a little while
pg_restore -d galaxy -U pulp beta-galaxy-2023-11-13.dump

# Switch the name for oci ...
su - postgres -c "psql -c 'ALTER DATABASE galaxy RENAME TO pulp'"
