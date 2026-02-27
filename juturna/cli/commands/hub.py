"""
Interact with the juturna plugin registry

This command offers all the basic functionalities to interact with the plugin
registry. This includes:

- authentication
- searching, by name, or author
- downloading, for latest version or specific versions
- publishing new plugins, or updating existing plugins (when a plugin is updated
  any existing previous versions will not be deleted)
"""

from juturna.hub._auth import login
from juturna.hub._search import search
from juturna.hub._get import download
from juturna.hub._publish import publish


_HUB_CMDS = {
    'login': login,
    'search': search,
    'get': download,
    'publish': publish,
}


def setup_parser(subparsers):  # noqa: D103
    parser = subparsers.add_parser(
        'hub', help='interact with the juturna plugin registry'
    )
    hub_subparsers = parser.add_subparsers(
        help='juturna hub CLI entrypoint', dest='hub_command'
    )

    login_parser = hub_subparsers.add_parser(
        'login',
        help='fetch auth credentials from the registry',
    )

    login_parser.add_argument(
        '--email',
        '-e',
        required=True,
        type=str,
        help='registered email address',
    )

    login_parser.add_argument('--password', '-p', type=str, help='password')
    login_parser.add_argument(
        '--store-credentials',
        '-s',
        action='store_true',
        help='save authorisation credentials to juturna cache folder',
    )

    search_parser = hub_subparsers.add_parser(
        'search', help='query the registry for plugins'
    )

    search_parser.add_argument('name', type=str, help='plugin name to search')

    search_parser.add_argument(
        '--author', '-a', action='store_true', help='search for plugin author'
    )
    search_parser.add_argument(
        '--all-versions',
        '-A',
        action='store_true',
        help='show all results and versions',
    )

    get_parser = hub_subparsers.add_parser(
        'get', help='download plugins from the registry'
    )

    get_parser.add_argument('name', type=str, help='plugin name to download')
    get_parser.add_argument(
        '--version', '-v', type=str, help='specific version to download'
    )
    get_parser.add_argument(
        '--extract', '-e', type=str, help='extract the download plugin archive'
    )

    publish_parser = hub_subparsers.add_parser(
        'publish', help='publish a plugin or update an existing plugin'
    )

    publish_parser.add_argument(
        'directory', type=str, help='directory of the plugin to publish'
    )

    publish_parser.add_argument(
        '--name',
        '-n',
        type=str,
        required=True,
        help='name of the plugin to publish',
    )
    publish_parser.add_argument(
        '--type',
        '-t',
        type=str,
        choices=['source', 'proc', 'sink'],
        required=True,
        help='type of the plugin to publish',
    )
    publish_parser.add_argument(
        '--version',
        '-v',
        type=str,
        required=True,
        help='semantic version of the plugin to publish',
    )
    publish_parser.add_argument(
        '--url', '-u', type=str, help='url of the plugin repository'
    )
    publish_parser.add_argument(
        '--description', '-d', type=str, help='plugin description'
    )
    publish_parser.add_argument('--about', '-a', type=str, help='plugin about')
    publish_parser.add_argument(
        '--contact', '-c', type=str, help='reference contact'
    )


def _execute(args):
    if command := args.hub_command:
        delattr(args, 'hub_command')

        _HUB_CMDS[command](**args.__dict__)
