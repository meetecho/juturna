import requests

from juturna.meta import JUTURNA_HUB_URL


def api_request(method: str, endpoint: str, token: str, **kwargs):
    headers = dict()

    if token:
        headers['Authorization'] = token

    url = f'{JUTURNA_HUB_URL}/api/{endpoint}'
    res = requests.request(method, url, headers=headers, **kwargs)

    if res.status_code == 401:
        print('unauthorised request')

    try:
        return res.json()
    except Exception:
        return res
