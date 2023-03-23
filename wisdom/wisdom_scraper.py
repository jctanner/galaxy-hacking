#!/usr/bin/env python


import requests


def main():
    username = 'admin'
    password = 'admin'

    host = 'http://localhost:5001'
    search_path = '/api/automation-hub/v3/plugin/ansible/search/collection-versions/'

    # next_url = host + search_path + '?' + 'order_by=collection_version.updated_at'
    next_url = host + search_path
    rr = requests.get(next_url, auth=(username, password))
    import epdb; epdb.st()


if __name__ == "__main__":
    main()
