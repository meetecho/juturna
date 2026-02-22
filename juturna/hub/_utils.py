import requests

from juturna.meta._constants import JUTURNA_HUB_TOKEN
from juturna.meta._constants import JUTURNA_HUB_URL


def api_request(
    method: str, endpoint: str, body: dict, authenticate: bool = True
):
    headers = dict()

    if authenticate and JUTURNA_HUB_TOKEN:
        headers['Authorization'] = JUTURNA_HUB_TOKEN

    print(body)
    print(headers)

    url = f'{JUTURNA_HUB_URL}/api/{endpoint}'
    print(url)
    res = requests.request(method, url, headers=headers, json=body)

    print(res.status_code)

    if res.status_code == 401:
        print('unauthorised request')

    return res.json()
