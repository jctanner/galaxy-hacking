import copy
import os
import yaml
from pprint import pprint


CACHEDIR = '/data/galaxy.content'
ROLESDIR = os.path.join(CACHEDIR, 'roles')
COLLECTIONSDIR = os.path.join(CACHEDIR, 'collections')


class PackageModuleReference:

    module = None
    packages = None

    def __init__(self, taskmeta):
        self.taskmeta = taskmeta
        self.packages = []


def split_string_args(args):
    # url="https://files.phpmyadmin.net/phpMyAdmin/{{ phpmyadmin_version }}/phpMyAdmin-{{ phpmyadmin_version }}-all-languages.tar.gz" dest=/tmp/ validate_certs=no timeout=90
    # name=open-vm-tools state=present

    # print(f'SPLIT {args}')

    words = args.split()
    newargs = {}

    lastkey = None
    for idw,word in enumerate(words):
        if '=' not in word:
            newargs[lastkey] += ' ' + word
            continue

        parts = word.split('=')
        lastkey = parts[0]
        newargs[parts[0]] = parts[1]

    # if 'php' in args:
    #    import epdb; epdb.st()

    return newargs


def find_variable_definition_in_directory(rootdir, varname, exclude=None):

    # print(f'FIND {varname} in {rootdir}')

    values = []
    candidates = []

    for root, dirs, files in os.walk(rootdir):
        if '.git' in root:
            continue
        for filen in files:
            if filen.endswith('.swp'):
                continue
            if not filen.endswith('.yml') and not filen.endswith('.yaml'):
                continue
            filepath = os.path.join(root, filen)
            if exclude and filepath in exclude:
                continue
            if not os.path.exists(filepath):
                continue

            try:
                with open(filepath, 'r') as f:
                    raw = f.read()
            except FileNotFoundError:
                continue

            if varname not in raw:
                continue

            #print(filepath)

            if varname in raw:
                candidates.append(filepath)

            try:
                ds = yaml.safe_load(raw)
            except Exception as e:
                continue
            if not isinstance(ds, dict):
                continue

            for k,v in ds.items():
                if k.strip('_') == varname:
                    print(f'{filepath} {k}')
                    #print(k)

                    if isinstance(v, list):
                        values.extend(v)
                    else:
                        values.append(v)
            #import epdb; epdb.st()

    #import epdb; epdb.st()
    return values


def iterate_block(basemeta, blocks_ds):
    basemeta['yaml'] = None
    for block_ds in blocks_ds['block']:
        tmeta = copy.deepcopy(basemeta)
        tmeta['yaml'] = block_ds
        yield tmeta


def find_tasks():

    for root, dirs, files in os.walk(CACHEDIR):
        for filen in files:
            lfilen = filen.lower()
            if not lfilen.endswith('.yml') and not lfilen.endswith('.yaml'):
                continue
            filepath = os.path.join(root, filen)
            if filepath.endswith('/meta/main.yml') or filepath.endswith('/meta/main.yaml'):
                continue
            if filepath.endswith('/defaults/main.yml') or filepath.endswith('/defaults/main.yaml'):
                continue
            if filepath.endswith('/defautls/main.yml') or filepath.endswith('/defautls/main.yaml'):
                continue
            if filepath.endswith('/vars/main.yml') or filepath.endswith('/vars/main.yaml'):
                continue
            if filepath.endswith('/test/dependencies.yml') or filepath.endswith('/test/dependencies.yaml'):
                continue
            if filepath.endswith('/spec/inspec.yml') or filepath.endswith('/spec/inspec.yaml'):
                continue
            if filepath.endswith('/tests/test.yml') or filepath.endswith('/tests/test.yaml'):
                continue
            if filepath.endswith('/tests/cleanup.yml') or filepath.endswith('/tests/cleanup.yaml'):
                continue
            if filepath.endswith('/meta/ansigenome.yml') or filepath.endswith('/meta/ansigenome.yaml'):
                continue
            if filepath.endswith('/meta/preferences.yml') or filepath.endswith('/meta/preferences.yaml'):
                continue
            if filepath.endswith('/meta/argument_specs.yml') or filepath.endswith('/meta/argument_specs.yaml'):
                continue
            if filepath.endswith('/meta/exception.yml') or filepath.endswith('/meta/exception.yaml'):
                continue
            if filen == '.travis.yml':
                continue
            if '/meta/' in filepath:
                continue
            if '/defaults/' in filepath:
                continue
            if '.chglog' in filepath:
                continue
            if '.github/' in filepath:
                continue
            if 'test/integration' in filepath:
                continue
            if '/vars/' in filepath:
                continue
            if '/.builds/' in filepath:
                continue
            if '/tests/' in filepath:
                continue
            if '/test/' in filepath:
                continue
            if '/testcases/' in filepath:
                continue
            if '/files/' in filepath:
                continue
            if '/examples/' in filepath:
                continue
            if '/example/' in filepath:
                continue
            if '/vars_examples/' in filepath:
                continue
            if '/changelogs/' in filepath:
                continue
            if '/group_vars/' in filepath:
                continue
            if '/host_vars/' in filepath:
                continue
            if filen == 'yamllint.yml':
                continue
            if filen == 'requirements.yml':
                continue
            if filen.endswith('vars.yml'):
                continue
            #if filepath.endswith('/molecule.yml') or filepath.endswith('/molecule.yaml'):
            #    continue
            #if filen == '.pre-commit-config.yaml':
            #    continue
            print(filepath)

            rootdir = None
            relative_path = None
            ctype = None
            if ROLESDIR in filepath:
                ctype = 'role'
                relative_path = filepath.replace(ROLESDIR, '')
                paths = filepath.split('/')
                rpaths = ROLESDIR.split('/')
                rootdir = paths[:len(rpaths)+1]
                rootdir = '/'.join(rootdir)

            elif COLLECTIONSDIR in filepath:
                ctype = 'collection'
                relative_path = filepath.replace(COLLECTIONSDIR, '')
                paths = filepath.split('/')
                cpaths = COLLECTIONSDIR.split('/')
                rootdir = paths[:len(cpaths)+1]
                rootdir = '/'.join(rootdir)

            topdir = relative_path.lstrip('/')
            topdir = topdir.split('/')[0]
            relative_path = relative_path.replace('/' + topdir + '/', '')

            if ctype == 'role':
                rparts = relative_path.split('/')
                if len(rparts) == 1 and filen not in ['main.yml', 'main.yaml']:
                    continue

                if 'molecule' in rparts:
                    continue

            fqn = None
            if ctype == 'role':
                fqn = topdir
            elif ctype == 'collection':
                fparts = topdir.split('-')
                fqn = f"{fparts[0]}.{fparts[1]}"

            try:
                with open(filepath, 'r') as f:
                    raw = f.read()
            except FileNotFoundError:
                continue
            except Exception:
                continue

            try:
                ds = yaml.safe_load(raw)
            except yaml.scanner.ScannerError:
                ds = []
            except yaml.constructor.ConstructorError:
                ds = []
            except yaml.parser.ParserError:
                ds = []
            except Exception:
                ds = []

            if ds is None:
                continue

            #pprint(ds)

            taskmeta = {
                'fqn': fqn,
                'rootdir': rootdir,
                'filename': filen,
                'filepath': filepath,
                'relative_path': relative_path,
                'content_type': ctype,
                'yaml': None
            }

            taskmetas = []
            for section in ds:

                if section is None:
                    continue

                if isinstance(section, str):
                    continue

                if isinstance(section, bool):
                    continue

                if 'roles' in section:
                    continue

                if 'tasks' in section:

                    if section['tasks'] is None:
                        continue

                    for tds in section['tasks']:

                        if tds == 'fail':
                            import epdb; epdb.st()

                        if 'block' in tds:
                            for tm in iterate_block(copy.deepcopy(taskmeta), tds):
                                yield tm
                            continue

                        taskmeta = {
                            'fqn': fqn,
                            'rootdir': rootdir,
                            'filename': filen,
                            'filepath': filepath,
                            'relative_path': relative_path,
                            'content_type': ctype,
                            'yaml': tds
                        }
                        yield taskmeta

                    continue

                if 'block' in section:
                    for btask in section['block']:
                        if 'block' in btask:
                            for tm in iterate_block(copy.deepcopy(taskmeta), btask):
                                yield tm
                            continue
                        taskmeta = {
                            'fqn': fqn,
                            'rootdir': rootdir,
                            'filename': filen,
                            'filepath': filepath,
                            'relative_path': relative_path,
                            'content_type': ctype,
                            'yaml': btask
                        }
                        yield taskmeta
                    continue


                if 'block' in section:
                    import epdb; epdb.st()

                taskmeta = {
                    'fqn': fqn,
                    'rootdir': rootdir,
                    'filename': filen,
                    'filepath': filepath,
                    'relative_path': relative_path,
                    'content_type': ctype,
                    'yaml': section
                }
                yield taskmeta


def extract_package_tasks(taskmeta):

    ds = taskmeta['yaml']
    if ds is None:
        return

    package_modules = ['dnf', 'yum', 'apt', 'package']
    keywords = [
        'always_run',
        'args',
        'async',
        'become',
        'become_method',
        'become_user',
        'connection',
        'poll',
        'changed_when',
        'check_mode',
        'consul_addon',
        'delegate_to',
        'delegate_facts',
        'delay',
        'diff',
        'environment',
        'failed_when',
        'ignore_errors',
        'listen',
        'vars',
        'name',
        'no_log',
        'notify',
        'register',
        'remote_user',
        'retries',
        'run_once',
        'static',
        'sudo',
        'sudo_user',
        'su',
        'su_user',
        'tags',
        'throttle',
        'loop',
        'loop_control',
        'until',
        'warn',
        'when',
        'with_dict',
        'with_items',
        'with_indexed_items',
        'with_fileglob',
        'with_first_found',
        'with_flattened',
        'with_subelements',
        'with_together',
    ]

    no_split = [
        'ansible.builtin.meta',
        'meta',
        'ansible.builtin.command',
        'command',
        'ansible.builtin.shell',
        'shell',
        'ansible.builtin.import_tasks',
        'import_tasks',
        'ansible.builtin.include_tasks',
        'import_tasks',
        'include_tasks',
        'fail',
        'flush_handlers',
        'include',
        'include_vars',
        'ansible.builtin.include_vars',
        'raw',
        'ansible.builtin.setup',
        'setup',
    ]

    module_calls = []

    '''
    for task in ds:

        if isinstance(task, bool):
            import epdb; epdb.st()

        if 'block' in task:
            for btask in task['block']:
                tasks.append(btask)
        else:
            tasks.append(task)
    '''

    task = taskmeta['yaml']

    if isinstance(task, str):
        #import epdb; epdb.st()
        return
    if not isinstance(task, dict):
        #import epdb; epdb.st()
        return
    module_names = [x for x in task.keys() if x not in keywords]
    if len(module_names) == 1:
        module = module_names[0].strip()
        # print(f'MODULE: {module}')
        args = task[module]

        if isinstance(args, str) and module not in no_split:
            try:
                args = split_string_args(args)
            except AttributeError:
                pass
            except KeyError:
                pass

        if module == 'local_action' or module == 'action':
            if isinstance(args, dict) and 'module' in args:
                module = args['module']
                args.pop('module', None)
            else:
                module = str(args)
                args = {}
                #import epdb; epdb.st()

        elif module == 'raw' and 'dnf' in args:
            # dnf install -y python2-dnf
            #import epdb; epdb.st()
            pass

        #if isinstance(args, str) and module not in no_split:
        #    args = split_string_args(args)

        module_calls.append([module, args, task])
    else:
        # print(module_names)
        #import epdb; epdb.st()
        return

    references = []
    package_calls = [x for x in module_calls if x[0] in package_modules]
    if package_calls:
        for idx, x in enumerate(package_calls):
            if isinstance(x[1], str):
                continue
            if x[1] is None:
                continue

            pmr = PackageModuleReference(x[-1])
            pmr.module = x[0]
            references.append(pmr)


            if isinstance(x[1], list):
                names = x[1][0].get('name')
            else:
                names = x[1].get('name', [])
            if not names:
                continue

            if not isinstance(names, list):
                names = [names]

            if '{{' not in str(names):
                pmr.packages = names

            else:
                if 'with_items' in x[2]:
                    names = x[2]['with_items']
                    if '{{' not in str(names):
                        #package_calls[idx][1]['name'] = names
                        for px in names:
                            if isinstance(px, list):
                                for pn in px:
                                    pmr.packages.append(pn)
                            elif isinstance(px, bool):
                                continue
                            elif isinstance(px, dict):
                                if 'name' in px:
                                    pmr.packages.append(px['name'])
                                    continue
                                if 'version' in px:
                                    continue
                                #import epdb; epdb.st()
                                continue
                            else:
                                pmr.packages.append(px)
                    else:
                        varname = str(names).replace('{{', '').replace('}}', '').strip()
                        names = find_variable_definition_in_directory(
                            taskmeta['rootdir'],
                            varname,
                            exclude=[taskmeta['filepath']]
                        )
                        #package_calls[idx][1]['name'] = names
                        for px in names:
                            if isinstance(px, list):
                                for pn in px:
                                    pmr.packages.append(pn)
                            elif isinstance(px, bool):
                                continue
                            elif isinstance(px, dict):
                                if 'name' in px:
                                    pmr.packages.append(px['name'])
                                    continue
                                if 'version' in px:
                                    continue
                                #import epdb; epdb.st()
                                continue
                            else:
                                pmr.packages.append(px)

    #return package_calls
    return references
