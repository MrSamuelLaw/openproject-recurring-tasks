import aiohttp
from models import APIConfig, WorkPackage


def build_url(config: APIConfig, endpoint: str) -> str:
    """Builds a url for the endpoint using the apps configs.

    Returns: complete url for the endpoint.
    """
    prefix = 'https' if config.https else 'http'
    url = f'{prefix}://{config.host}/api/v3/{endpoint}'
    return url


async def query_work_packages(config: APIConfig, offset: int=1, page_size: int=1000, filters: dict=None) -> list[WorkPackage]:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, 'work_packages')
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/hal+json',
            'Authorization': f'Basic {config.api_token}',

        }
        params = {
            'offset': offset,
            'pageSize': page_size,
        }
        if filters is not None: params['filters'] = filters;
        async with session.get(url, headers=headers, params=params) as response:
            data = await response.json()
            work_packages = [WorkPackage(**obj) for obj in data['_embedded']['elements']]
            return work_packages

