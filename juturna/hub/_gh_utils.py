import requests

import juturna as jt


def _gh_node_list(url: str, authenticate: bool = False) -> dict:
    node_type_folders = _gh_dir_content(url, authenticate)

    if node_type_folders is None:
        return None

    node_types = node_type_folders['dirs']
    content = dict()

    while len(node_types) > 0:
        d = node_types.pop()
        all_nodes = _gh_dir_content(d[1], authenticate)['dirs']

        content[d[0]] = [n[0] for n in all_nodes]

    return content


def _gh_download_file(file_url: str, authenticate: bool):
    file_content = _get_req(file_url, authenticate).text

    return file_content


def _gh_node_content_list(node_url: str, authenticate: bool = False) -> list:
    content = _gh_dir_content(node_url, authenticate)

    if content is None:
        return None

    all_files = content['files']
    all_dirs = content['dirs']

    while len(all_dirs) > 0:
        d = all_dirs.pop()

        content = _gh_dir_content(d[1])
        all_files += content['files']
        all_dirs += content['dirs']

    return all_files


def _gh_dir_content(url: str, authenticate: bool = False) -> list | None:
    dir_content = _get_req(url, authenticate).json()

    if isinstance(dir_content, dict) and dir_content['status'] == '404':
        return None

    return {
        'dirs': [
            (i['path'], i['url']) for i in dir_content if i['type'] == 'dir'
        ],
        'files': [
            (i['path'], i['download_url'])
            for i in dir_content
            if i['type'] == 'file'
        ],
    }


def _get_req(url: str, authenticate: bool):
    headers = dict()

    if authenticate:
        headers['Authorization'] = f'token {jt.meta.JUTURNA_HUB_TOKEN}'

    return requests.get(url, headers=headers)
