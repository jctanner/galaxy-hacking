#!/usr/bin/env pyton3

import io
import os
import json
import subprocess
import time

import flask
from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect
from flask import send_file

from pprint import pprint

import requests
import requests_cache

app = Flask(__name__)
api_prefix = "/api/automation-hub"
upstream_baseurl = 'https://beta-galaxy.ansible.com'
upstream_apiurl = upstream_baseurl + '/api/'
upstream_repo = 'community'
downstream_repo = 'published'

ARTIFACTS_DIR = '/vagrant/artifacts'
SERVER_ADDRESS = 'http://192.168.122.170:8080'


def get_sha256(fn):
    pid = subprocess.run(f'sha256sum {fn}', shell=True, stdout=subprocess.PIPE)
    sha = pid.stdout.decode('utf-8').strip().split()[0].strip()
    return sha


def add_url_args(incoming_request):
    url = ''
    if incoming_request.args:
        url += '?'
        to_append = []
        for k,v in incoming_request.args.items():
            to_append.append(f'{k}={v}')
        url += '&'.join(to_append)
    return url


@app.route(f'{api_prefix}/', methods=['GET'])
def api_root():
    return jsonify({
        'available_versions': {
            'v3': 'v3/'
        }
    })


@app.route(f'{api_prefix}/v3', methods=['GET'])
def v3_redirect():
    return redirect(f'{api_prefix}/v3/')


@app.route(f'{api_prefix}/v3/excludes/')
def excludes():
    return jsonify({})


@app.route(f'{api_prefix}/v3/collections/all/')
def collections_all():
    return jsonify({}), 404


@app.route(f'{api_prefix}/v3/collections/')
def collections_root():
    url = f'{api_prefix}/v3/plugin/ansible/content/published/collections/index/'
    url += add_url_args(request)
    return redirect(url)


@app.route(f'{api_prefix}/v3/plugin/ansible/content/published/collections/index/')
def published_collections_index():

    url = upstream_apiurl + f'v3/plugin/ansible/content/{upstream_repo}/collections/index/'
    url += add_url_args(request)
    print('UPSTREAM', url)
    rr = requests.get(url)
    resp = json.dumps(rr.json())
    resp = resp.replace('/api/v3', '/api/automation-hub/v3')
    resp = resp.replace('/community/', '/published/')
    resp = json.loads(resp)

    '''
    # trim down to just 1 collection
    resp['meta']['count'] = 10
    resp['links']['next'] = None
    resp['links']['last'] = resp['links']['first']
    resp['data'] = resp['data'][:10]
    '''

    resp['data'] = [x for x in resp['data'] if 'oracle' in json.dumps(x)]

    return jsonify(resp)


@app.route(f'{api_prefix}/v3/collections/<namespace>/<name>')
def collection(namespace, name):
    url = f'{api_prefix}/v3/collections/{namespace}/{name}/'
    url += add_url_args(request)
    return redirect(url)


@app.route(f'{api_prefix}/v3/collections/<namespace>/<name>/')
def collection_detail(namespace, name):
    url = upstream_apiurl + f'v3/collections/{namespace}/{name}/'
    url += add_url_args(request)
    print('UPSTREAM', url)
    rr = requests.get(url)
    resp = json.dumps(rr.json())
    resp = resp.replace('/api/v3', '/api/automation-hub/v3')
    resp = resp.replace('/community/', '/published/')
    resp = json.loads(resp)
    #pprint(resp)
    return jsonify(resp)


@app.route(f'{api_prefix}/v3/collections/<namespace>/<name>/versions/')
def collection_versions_redirect(namespace, name):
    url = f'{api_prefix}/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/versions/'
    url += add_url_args(request)
    return redirect(url)


@app.route(f'{api_prefix}/v3/collections/<namespace>/<name>/versions/<version>/')
def collection_version_short_redirect(namespace, name, version):
    url = f'{api_prefix}/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/versions/{version}/'
    url += add_url_args(request)
    return redirect(url)


@app.route(f'{api_prefix}/v3/collections/<namespace>/<name>/versions/<version>/docs-blob/')
def collection_version_docs(namespace, name, version):
    url = upstream_apiurl + f'v3/plugin/ansible/content/{upstream_repo}/collections/index/{namespace}/{name}/versions/'
    url += f'{version}/docs-blob/'
    url += add_url_args(request)
    print('UPSTREAM', url)
    rr = requests.get(url)
    resp = rr.json()
    pprint(resp)
    return jsonify(resp)


@app.route(f'{api_prefix}/v3/plugin/ansible/content/published/collections/index/<namespace>/<name>/versions/')
def collection_versions(namespace, name):
    url = upstream_apiurl + f'v3/plugin/ansible/content/{upstream_repo}/collections/index/{namespace}/{name}/versions/'
    url += add_url_args(request)
    print('UPSTREAM', url)
    rr = requests.get(url)
    resp = json.dumps(rr.json())
    resp = resp.replace('/api/v3', '/api/automation-hub/v3')
    resp = resp.replace('/community/', '/published/')
    resp = json.loads(resp)
    #pprint(resp)
    return jsonify(resp)


@app.route(f'{api_prefix}/v3/plugin/ansible/content/published/collections/index/<namespace>/<name>/versions/<version>')
def collection_version_redirect():
    url = f'{api_prefix}/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/versions/{version}/'
    url += add_url_args(request)
    return redirect(url)


@app.route(f'{api_prefix}/v3/plugin/ansible/content/published/collections/index/<namespace>/<name>/versions/<version>/')
def collection_version(namespace, name, version):
    url = upstream_apiurl + f'v3/plugin/ansible/content/{upstream_repo}/collections/index/{namespace}/{name}/versions/{version}/'
    url += add_url_args(request)
    rr = requests.get(url)
    ds = rr.json()
    download_url = ds['download_url']
    sha_bak = ds['artifact']['sha256']
    dldir = '/tmp/artifacts/'
    if not os.path.exists(ARTIFACTS_DIR):
        os.makedirs(ARTIFACTS_DIR)
    fn = os.path.basename(download_url)
    fp = os.path.join(ARTIFACTS_DIR, fn)
    lf = os.path.join(ARTIFACTS_DIR, fn + '.lock')
    if not os.path.exists(fp) and not os.path.exists(lf):
        with open(lf, 'w') as f:
            f.write('')
        cmd = f'curl -L -o {fp} {download_url}'
        subprocess.run(cmd, shell=True)
        os.remove(lf)
    sha = get_sha256(fp)
    if sha != sha_bak:
        raise Exception('BAD sha!?')

    resp = json.dumps(ds)
    resp = resp.replace('/api/v3', '/api/automation-hub/v3')
    resp = resp.replace('/community/', '/published/')
    resp = json.loads(resp)

    # fix the download url
    resp['download_url'] = SERVER_ADDRESS + f'/downloads/{fn}'
    resp['artifact']['sha256'] = sha

    #pprint(resp)
    return jsonify(resp)


@app.route('/downloads/<artifact>')
def download(artifact):
    fn = os.path.join(ARTIFACTS_DIR, artifact)
    lf = os.path.join(ARTIFACTS_DIR, artifact + '.lock')
    while os.path.exists(lf):
        time.sleep(.01)

    # have to send the file this way so that pulp doesn't fail
    # digest validation on whatever way the download occurs
    return send_file(
        io.BytesIO(open(fn, 'rb').read()),
        mimetype='application/tar+gzip'
    )


if __name__ == "__main__":
    # app.run(host='0.0.0.0', port=8080, debug=True, ssl_context='adhoc')
    app.run(host='0.0.0.0', port=8080, debug=True)
