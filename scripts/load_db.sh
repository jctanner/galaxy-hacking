#!/bin/bash

function copy_dump {
    docker exec -it galaxy_ng_postgres_1 /bin/bash -c 'test -f /tmp/ah-dump'
    RC=$?
    if [[ $RC == 1 ]]; then
        echo "copying dumpfile"
        docker cp ah-dump.xz galaxy_ng_postgres_1:/tmp/.
        echo "extracting dumpfile"
        docker exec -it galaxy_ng_postgres_1 /bin/bash -c 'cd /tmp; xz -d ah-dump.xz'
    fi
}

function drop_tables {
    echo "generate drop script"
    docker exec -it galaxy_ng_postgres_1 /bin/bash -c 'rm -f /tmp/drop.sh'
    docker exec -it galaxy_ng_postgres_1 /bin/bash \
        -c 'psql -U galaxy_ng -d galaxy_ng -c "select '"'"'psql -U galaxy_ng -d galaxy_ng -c \"drop table if exists \\\"'"'"' || tablename || '"'"'\\\" cascade;\"'"'"' from pg_tables;" | grep drop >> /tmp/drop.sh'
    docker exec -it galaxy_ng_postgres_1 /bin/bash -c 'cd /tmp; chmod +x drop.sh; ./drop.sh'
}

function restore_dump {
    echo "restoring the dump"
    docker exec -it galaxy_ng_postgres_1 /bin/bash -c 'psql -U galaxy_ng -d galaxy_ng < /tmp/ah-dump'
}

function make_users {
    if [ ! -f /tmp/makeusers.sql ]; then
        echo "enumerating missing users"
        docker exec -u root -it galaxy_ng_postgres_1 /bin/bash \
            -c "psql -P pager=off -U galaxy_ng -c 'select distinct(user_id) from guardian_userobjectpermission ORDER BY user_id;'" \
            > /tmp/users.txt
        cat /tmp/users.txt | tr -d ' ' | egrep ^[0-9] > /tmp/userids.txt
        echo "generating user script"
        FINAL_ID=$(tail -n1 /tmp/userids.txt | tr -d '\r')
        rm -f /tmp/makeusers.sql
        for X in $(seq 1 ${FINAL_ID}); do
            new_user="user${X}"
            sql="INSERT INTO galaxy_user (id, username, first_name, last_name, email, password"
            sql="$sql, is_superuser, is_staff, is_active, date_joined)"
            sql="$sql VALUES (${X}, '${new_user}', 'foo', 'bar', 'foo@bar.com', 'redhat1234'"
            sql="$sql, false, false, false, current_timestamp);"
            echo "$sql" >> /tmp/makeusers.sql
        done
    fi
    echo "copy user script to container"
    docker cp /tmp/makeusers.sql galaxy_ng_postgres_1:/tmp/.
    echo "executing user script"
    docker exec -u root -it galaxy_ng_postgres_1 /bin/bash -c "psql -P pager=off -U galaxy_ng -f /tmp/makeusers.sql"
}

copy_dump
drop_tables
restore_dump
make_users
