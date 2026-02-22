import getpass


from juturna.hub._utils import api_request


def login(
    email: str,
    password: str = '',
    store_credentials: bool = False,
):
    if not password:
        password = getpass.getpass()

    token = api_request(
        'POST',
        'collections/users/auth-with-password',
        {'identity': email, 'password': password},
    )

    print('token acquired')
    print(token)


def token() -> str: ...
