import getpass
import pathlib


from juturna.hub._utils import api_request

from juturna.meta import JUTURNA_HUB_TOKEN
from juturna.meta import JUTURNA_CACHE_DIR


_AUTH_PATH = pathlib.Path(JUTURNA_CACHE_DIR, 'credentials')


def login(
    email: str,
    password: str = '',
    store_credentials: bool = False,
):
    """
    Login to the hub with email and password

    Use credentials to login into the juturna registry with email and password.
    Obtain a token to store in the juturna cache folder. The token, and the
    user id, will be used for later requests to the registry.
    """
    if not password:
        password = getpass.getpass()

    response = api_request(
        'POST',
        'collections/users/auth-with-password',
        '',
        json={'identity': email, 'password': password},
    )

    auth_content = {
        'JT_HUB_TOKEN': response['token'],
        'JT_HUB_ID': response['record']['id'],
    }

    if store_credentials:
        auth_content['JT_HUB_EMAIL'] = email
        auth_content['JT_HUB_PASSWORD'] = password

    if not _AUTH_PATH.parent.exists():
        _AUTH_PATH.mkdir(exist_ok=True, parents=True)

    with open(_AUTH_PATH, 'w') as f:
        f.write('\n'.join([f'{k}={v}' for k, v in auth_content.items()]))

    print('token acquired')
    print(response)


def token() -> str:
    """Fetch the authentication token"""
    if JUTURNA_HUB_TOKEN:
        return JUTURNA_HUB_TOKEN

    if _AUTH_PATH.exists():
        with open(_AUTH_PATH) as f:
            for line in f:
                k, v = line.split('=')

                if k == 'JT_HUB_TOKEN':
                    return v[:-1]

    return ''


def user_id() -> str:
    """Fetch the current user id"""
    if _AUTH_PATH.exists():
        with open(_AUTH_PATH) as f:
            for line in f:
                k, v = line.split('=')

                if k == 'JT_HUB_ID':
                    return v

    return ''
