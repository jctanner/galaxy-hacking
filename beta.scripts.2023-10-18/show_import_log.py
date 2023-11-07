from pulpcore.plugin.models import Task
from galaxy_ng.app.utils.galaxy import int_to_uuid


v1id = 2053706321136235841224340602491325788
this_uuid = int_to_uuid(v1id)

task = Task.objects.filter(pk=this_uuid).first()



curl -H 'Authorization: token <TOKEN>' https://galaxy.ansible.com/api/_ui/v1/me/ | jq .username




(galaxydev) [jtanner@p1 beta.scripts.2023-10-18]$ ansible-galaxy role import --token=<TOKEN> -vvvvvv haufe-it ansible-role-multissh
ansible-galaxy [core 2.15.3]
  config file = /etc/ansible/ansible.cfg
  configured module search path = ['/home/jtanner/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
  ansible python module location = /home/jtanner/venvs/galaxydev/lib64/python3.11/site-packages/ansible
  ansible collection location = /home/jtanner/.ansible/collections:/usr/share/ansible/collections
  executable location = /home/jtanner/venvs/galaxydev/bin/ansible-galaxy
  python version = 3.11.6 (main, Oct  3 2023, 00:00:00) [GCC 13.2.1 20230728 (Red Hat 13.2.1-1)] (/home/jtanner/venvs/galaxydev/bin/python3)
  jinja version = 3.1.2
  libyaml = True
Using /etc/ansible/ansible.cfg as config file
Initial connection to galaxy_server: https://galaxy.ansible.com
Opened /home/jtanner/.ansible/galaxy_token
Calling Galaxy at https://galaxy.ansible.com/api/
Found API version 'v3, pulp-v3, v1' with Galaxy server default (https://galaxy.ansible.com/api/)
Calling Galaxy at https://galaxy.ansible.com/api/v1/imports/
Successfully submitted import request 2053790683390280560371105338281559867
Calling Galaxy at https://galaxy.ansible.com/api/v1/imports?id=2053790683390280560371105338281559867
running
Calling Galaxy at https://galaxy.ansible.com/api/v1/imports?id=2053790683390280560371105338281559867
role imported successfully
