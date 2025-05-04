import json
import aiohttp
import logging
from os import environ
from base64 import b64encode
from typing import ClassVar, Self, Optional
from pydantic import BaseModel, Field, ConfigDict


# ————————————————————————— Module Scoped Variables —————————————————————————
MAX_PAGE_SIZE = 1000


# ————————————————————————— Models —————————————————————————

class APIConfig(BaseModel):
    """Class that is used to hold environment variables.
    """

    _instance: ClassVar[Self | None] = None

    model_config = ConfigDict(frozen=True)

    api_key:    str  = Field()
    host:       str  = Field()
    https:      bool = Field(True)
    verify_ssl: bool = Field(True)
    notify_create:  bool = Field(True)  # notify when creating a new work package
    notify_update:  bool = Field(True)  # notify when update a template work package
    log_level:  int  = Field(logging.WARNING)
    port:       Optional[int]  =    Field(None)
    latitude:   Optional[float] =   Field(None)
    longitude:  Optional[float] =   Field(None)


    @classmethod
    def from_env(cls) -> Self:
        """Reads the configs from environment variables on the first call
        subsequent calls return the originally parsed values to avoid bugs
        related to environment variables changing during runtime either by
        mistake or malice.
        """
        if cls._instance is None:
            data = {key: environ.get(key.upper()) for key in cls.model_fields.keys()}
            data = {key: value for key, value in data.items() if value is not None}
            if 'log_level' in data.keys():
                data['log_level'] = getattr(logging, data['log_level'])
            cls._instance = cls(**data)
        return cls._instance

    @property
    def api_token(self) -> bytes:
        """Returns a b64 encoded api key for the authorization header
        """
        token = f'apikey:{self.api_key}'.encode()
        token = b64encode(token).decode()
        return token


# ————————————————————————— Functions —————————————————————————

def build_url(endpoint: str, config: APIConfig=APIConfig.from_env()) -> str:
    """Returns a url for the endpoint using the apps configs.
    """
    prefix = 'https' if config.https else 'http'
    port = f':{config.port}' if config.port else ''
    url = f'{prefix}://{config.host}{port}/{endpoint}'
    return url


async def query_forecast(num_days: int, config: APIConfig=APIConfig.from_env()):
    """Queries the forecast for the weather codes in 15 minute increments using the
    open-meteo api. The weather codes can then be used to generate work packages
    based on weather events.
    """
    if not (0 <= num_days <= 16):
        raise ValueError(f'num_days must be between 0 and 16 inclusive. Actual value = {num_days}')

    async with aiohttp.ClientSession() as session:
        url = 'https://api.open-meteo.com/v1/forecast'
        params = {
            'latitude': config.latitude,
            'longitude': config.longitude,
            'forecast_days': num_days,
            'minutely_15': ','.join(['precipitation', 'wind_speed_10m' ,'wind_gusts_10m'])
        }
        async with session.get(url, params=params) as response:
            data: dict = await response.json()
            return data


async def query_projects(filters: Optional[dict]=None, config: APIConfig=APIConfig.from_env()) -> dict:
    """Returns a list of projects using the filters provided
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url('api/v3/projects', config)
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/hal+json',
            'Authorization': f'Basic {config.api_token}',
        }
        params = {}
        if filters is not None:
            params['filters'] = filters if isinstance(filters, str) else json.dumps(filters)
        async with session.get(url, headers=headers, params=params) as response:
            data: dict = await response.json()
            return data


async def query_work_package_types(project_id: int, config: APIConfig=APIConfig.from_env()) -> dict:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(f'api/v3/projects/{project_id}/types', config)
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/hal+json',
            'Authorization': f'Basic {config.api_token}',

        }
        async with session.get(url, headers=headers) as response:
            data: dict = await response.json()
            return data


async def query_work_package_schema(project_id: int, work_package_type_id: int, config: APIConfig=APIConfig.from_env()) -> dict:
    """Queries the work package schema for a project id given the work package type id
    also has the side effect of updating the WorkPackage model field map
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(f'api/v3/work_packages/schemas/{project_id}-{work_package_type_id}', config)
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/hal+json',
            'Authorization': f'Basic {config.api_token}',
        }
        async with session.get(url, headers=headers) as response:
            data: dict = await response.json()
            return data


async def query_work_packages(offset: int=1, page_size: int=MAX_PAGE_SIZE, filters: Optional[dict]=None, config: APIConfig=APIConfig.from_env()) -> dict:
    """Returns a list of work packages using the filters provided.
    Results are limited to the page_size specified.
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url('api/v3/work_packages', config)
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/hal+json',
            'Authorization': f'Basic {config.api_token}',
        }
        params = {
            'offset': offset,
            'pageSize': page_size,
        }
        if filters is not None:
            params['filters'] = filters if isinstance(filters, str) else json.dumps(filters)
        async with session.get(url, headers=headers, params=params) as response:
            data: dict = await response.json()
            # recursively call until all data is loaded in
            if offset * page_size < data['total']:
                more_data = await query_work_packages(offset=offset+1, page_size=page_size, filters=filters, config=config)
                data['_embedded']['elements'].extend(more_data['_embedded']['elements'])
                data['count'] = data['count'] + more_data['count']
            return data


async def query_work_package_relations(offset: int=1, page_size: int=MAX_PAGE_SIZE, filters: Optional[dict]=None, config: APIConfig=APIConfig.from_env()) -> dict:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url('api/v3/relations', config)
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {config.api_token}',
        }
        params = {
            'offset': offset,
            'pageSize': page_size
        }
        if filters is not None:
            params['filters'] = filters if isinstance(filters, str) else json.dumps(filters)
        async with session.get(url, headers=headers, params=params) as response:
            data: dict = await response.json()
            # recursively call until all data is loaded in
            if offset * page_size < data['total']:
                more_data = await query_work_package_relations(offset=offset+1, page_size=page_size, filters=filters, config=config)
                data['_embedded']['elements'].extend(more_data['_embedded']['elements'])
                data['count'] = data['count'] + more_data['count']
            return data
            return data


async def create_work_package(project_id: int, payload: dict, notify: bool=None, config: APIConfig=APIConfig.from_env()) -> dict:
    """Creates a work package in the given project and returns the newly created work package
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(f'api/v3/projects/{project_id}/work_packages', config)
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {config.api_token}',
        }
        params = {
            'notify': int(config.notify_create) if notify is None else int(notify)
        }
        payload = json.dumps(payload, default=str)
        async with session.post(url, data=payload, headers=headers, params=params) as response:
            data: dict = await response.json()
            return data


async def create_relation(work_package_id: int, payload: dict, config: APIConfig=APIConfig.from_env()) -> dict:
    """Creates a relation between two work packages
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(f'api/v3/work_packages/{work_package_id}/relations', config)
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {config.api_token}',
        }
        payload = json.dumps(payload, default=str)
        async with session.post(url, data=payload, headers=headers) as response:
            data: dict = await response.json()
            return data


async def update_work_package(work_package_id: int, payload: dict, notify: bool=None, config: APIConfig=APIConfig.from_env()) -> dict:
    """Updates the attributes defined in payload for the work package with the id = work_package_id
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(f'api/v3/work_packages/{work_package_id}', config)
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {config.api_token}',
        }
        params = {
            'notify': int(config.notify_update) if notify is None else int(notify)
        }
        payload = json.dumps(payload, default=str)
        async with session.patch(url, data=payload, headers=headers, params=params) as response:
            data: dict = await response.json()
            return data