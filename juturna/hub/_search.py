import shutil

from packaging.version import Version

from juturna.hub._auth import token
from juturna.hub._utils import api_request


def search(
    name: str,
    author: bool = False,
    exact: bool = False,
    all_versions: bool = False,
    show_results: bool = True,
) -> list:
    cmp = '=' if exact else '~'
    filter_by = f'contact {cmp} "{name}"' if author else f'name {cmp} "{name}"'
    response = api_request(
        'GET',
        'collections/plugin_nodes/records',
        token(),
        params={'filter': filter_by},
    )

    items = [
        sorted(
            response['items'],
            key=lambda r: (r.get('name', '').lower(), Version(r['version'])),
        )
    ][-1]

    if not all_versions:
        latest_plugins_dict = {}

        for plugin in items:
            name = plugin.get('name')
            latest_plugins_dict[name] = plugin

        items = list(latest_plugins_dict.values())

    if show_results:
        pretty_print_plugins(items)

    return items


def format_cell(text, width):
    text = str(text)

    if len(text) > width:
        return text[: width - 3] + '...'

    return f'{text:<{width}}'


def pretty_print_plugins(plugins):
    terminal_width = shutil.get_terminal_size(fallback=(80, 24)).columns - 2
    fixed_widths = {
        'name': 20,
        'type': 12,
        'version': 10,
        'contact': 22,
    }

    padding_spaces = 2 * 4
    space_used = sum(fixed_widths.values()) + padding_spaces
    desc_width = max(15, terminal_width - space_used)
    col_widths = {**fixed_widths, 'description': desc_width}

    header_row = '  '.join(
        format_cell(col.upper(), width) for col, width in col_widths.items()
    )

    print(header_row)
    print('-' * len(header_row))

    for plugin in plugins:
        row = '  '.join(
            format_cell(plugin.get(col, ''), width)
            for col, width in col_widths.items()
        )

        print(row)
