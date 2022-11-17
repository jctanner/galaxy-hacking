## v1 roles

1. export HUB_TOKEN=
2. export HUB_USERNAME=
3. export HUB_PASSWORD=
4. export GALAXY_DOWNSTREAM_BASEURL=
5. export GALAXY_UPSTREAM_BASEURL=
6. python sync_roles.py

## v2 collections

1. export HUB_TOKEN=
2. export HUB_USERNAME=
3. export HUB_PASSWORD=
4. export GALAXY_DOWNSTREAM_BASEURL=
5. export GALAXY_UPSTREAM_BASEURL=
6. python import_galaxy_collections_with_sync.py

## v3 namespace and owners sync
1. python fetch_upstream_namespaces.py
2. create_django_script.py
3. docker exec -it galaxy_ng_api_1 /bin/bash -c 'django-admin shell < /src/galaxy_ng/dev/standalone-community/userimport.py'

## v1 namespace and roles sync

```
curl -u admin:admin -H 'Content-Type: application/json' -X POST -d '{"baseurl": "http://192.168.122.99:8080/api/v1/roles"}' http://localhost:5001/api/v1/sync/
```
