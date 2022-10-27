## v3 namespace and owners sync
1. python fetch_upstream_namespaces.py
2. create_django_script.py
3. docker exec -it galaxy_ng_api_1 /bin/bash -c 'django-admin shell < /src/galaxy_ng/dev/standalone-community/userimport.py'
