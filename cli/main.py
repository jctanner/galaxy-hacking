#!/usr/bin/env python3

import argparse
import os

from cli.lib import GalaxyClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', default=os.environ.get("GALAXY_TOKEN"))
    parser.add_argument('--server', default=os.environ.get("GALAXY_TOKEN"))
    subparsers = parser.add_subparsers(dest='parser_name')

    namespaces_parser = subparsers.add_parser(
        'namespaces',
        help='namespaces'
    )
    namespaces_parser.add_argument('action', choices=['list', 'create'])
    namespaces_parser.add_argument('--name')

    collections_parser = subparsers.add_parser(
        'collections',
        help='collections'
    )
    collections_parser.add_argument('action', choices=['list', 'upload'])
    collections_parser.add_argument('--filepath')

    args = parser.parse_args()
    gc = GalaxyClient(token=args.token, server=args.server)

    kwargs = {}
    if hasattr(args, 'name'):
        kwargs['name'] = args.name
    if hasattr(args, 'filepath'):
        kwargs['filepath'] = args.filepath

    func_name = f'{args.parser_name}_{args.action}'
    func = getattr(gc, func_name)
    func(**kwargs)


if __name__ == "__main__":
    main()
