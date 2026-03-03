import pathlib
import shutil

from juturna.hub._search import search
from juturna.hub._auth import token

from juturna.hub._utils import api_request


def download(name: str, version: str = '', extract: str = ''):
    plugins = search(name, all_versions=True, exact=True, show_results=False)
    targets = list(filter(lambda p: p['name'] == name, plugins))
    target = (
        targets[-1]
        if not version
        else next(filter(lambda p: p['version'] == version, targets))
    )

    if not target:
        print('requested plugin not found')

    target_id = target['id']
    target_file = target['content']
    target_version = target['version']

    file_pointer = api_request(
        'GET',
        f'files/plugin_nodes/{target_id}/{target_file}',
        token(),
        stream=True,
    )

    local_filename = (
        f'{name}_{target_version}{"".join(pathlib.Path(target_file).suffixes)}'
    )

    with open(local_filename, 'wb') as f:
        for chunk in file_pointer.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f'node downloaded to {local_filename}')

    if extract:
        pathlib.Path(extract).mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(local_filename, extract)
