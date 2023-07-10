#!/bin/bash

rm -f makeusers.sql

for X in $(seq 1 60000); do
    echo "INSERT INTO galaxy_user (id, username, first_name, last_name, email, password, is_superuser, is_staff, is_active, date_joined) VALUES (${X}, 'foobarz${X}', 'foo', 'bar', 'foo@bar.com', 'redhat1234', false, false, false, current_timestamp);" >> makeusers.sql
done

# docker cp makeusers.sql galaxy_ng_postgres_1:/tmp/.
# docker exec -u root -it galaxy_ng_postgres_1 /bin/bash -c "psql -P pager=off -U galaxy_ng -f /tmp/makeusers.sql"
