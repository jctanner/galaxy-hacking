from logzero import logger


def scrape_v3_namespaces(cacher, server=None):
    namespaces = []

    if server is None:
        baseurl = 'https://old-galaxy.ansible.com'
    else:
        baseurl = server

    next_page = f'{baseurl}/api/v3/namespaces/'
    while next_page:
        logger.info(next_page)
        ds = cacher.get(next_page)

        for ns in ds['data']:
            namespaces.append(ns)

        if not ds['links'].get('next'):
            break

        next_page = baseurl + ds['links']['next']

    return namespaces


def scrape_objects(object_name, cacher, api_version='v1', server=None):
    objects = []

    if server is None:
        baseurl = 'https://old-galaxy.ansible.com'
    else:
        baseurl = server

    next_page = f'{baseurl}/api/{api_version}/{object_name}/'
    while next_page:
        logger.info(next_page)
        ds = cacher.get(next_page)

        if 'results' in ds:
            for obj in ds['results']:
                objects.append(obj)
        elif 'data' in ds:
            for obj in ds['data']:
                objects.append(obj)

        #if object_name == 'collections' and api_version == 'v3':
        #    import epdb; epdb.st()

        if not ds.get('next') and not ds.get('next_link') and not ds.get('links'):
            break

        if ds.get('next_link'):
            next_page = baseurl + ds['next_link']
            continue

        if ds.get('links', {}).get('next'):
            next_page = baseurl + ds['links']['next']
            continue
        elif 'links' in ds and not ds['links']['next']:
            break

        next_page = ds['next']
        if 'http://' in next_page:
            next_page = next_page.replace('http://', 'https://')
        if not next_page.startswith(baseurl):
            next_page = baseurl + next_page

    return objects