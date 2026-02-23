import pathlib
import shutil

from juturna.hub._utils import api_request
from juturna.hub._auth import token
from juturna.hub._auth import user_id


def publish(
    directory: str,
    name: str,
    type: str,
    version: str,
    url: str,
    description: str,
    about: str,
    contact: str,
):
    publish_data = {
        'created_by': user_id(),
        'name': name,
        'type': type,
        'version': version,
        'repository': url,
        'description': description,
        'about': about,
        'contact': contact,
    }

    zip_path = f'{pathlib.Path(directory).name}_{version}'

    shutil.make_archive(
        zip_path,
        'zip',
        pathlib.Path(directory).parent,
        pathlib.Path(directory).name,
    )

    with open(f'{zip_path}.zip', 'rb') as f:
        res = api_request(
            'POST',
            'collections/plugin_nodes/records',
            token(),
            data=publish_data,
            files={'content': f},
        )

    pathlib.Path.unlink(pathlib.Path(f'{zip_path}.zip'))

    if res.get('name', '') == name and res.get('version', '') == version:
        print('plugin successfully uploaded!')
    else:
        print('impossible to publish plugin, please check your data')

    # print(res)
