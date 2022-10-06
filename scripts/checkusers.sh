#!/bin/bash


for dUID in $(cat userids.txt); do
    echo ${dUID}
    docker exec -u root -it galaxy_ng_postgres_1 /bin/bash -c "psql -P pager=off -U galaxy_ng -c 'select * from galaxy_user where id=${dUID}'"
    echo $?
done
