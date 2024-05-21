import json
import asyncio
import aiohttp
import logging
from os import environ
from base64 import b64encode
from typing import ClassVar, Self, Optional
from pydantic import BaseModel, Field, ConfigDict


# ————————————————————————— Module Scoped Variables —————————————————————————

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


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
    port:       Optional[int]  = Field(None)

    @classmethod
    def from_env(cls) -> Self:
        """Reads the configs from environment variables on the first call
        subsequent calls return the originally parsed values to avoid bugs
        related to environment variables changing during runtime either by
        mistake or malice.
        """
        if cls._instance is None:
            data = {key: environ.get(key.upper()) for key in cls.model_fields.keys()}
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

def build_url(config: APIConfig, endpoint: str) -> str:
    """Returns a url for the endpoint using the apps configs.
    """
    prefix = 'https' if config.https else 'http'
    url = f'{prefix}://{config.host}/{endpoint}'
    return url


async def query_projects(filters: Optional[dict]=None, config: APIConfig=APIConfig.from_env()) -> dict:
    """Returns a list of projects using the filters provided
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, 'api/v3/projects')
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
        url = build_url(config, f'api/v3/projects/{project_id}/types')
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
        url = build_url(config, f'api/v3/work_packages/schemas/{project_id}-{work_package_type_id}')
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/hal+json',
            'Authorization': f'Basic {config.api_token}',
        }
        async with session.get(url, headers=headers) as response:
            data: dict = await response.json()
            return data


async def query_work_packages(offset: int=1, page_size: int=1000, filters: Optional[dict]=None, config: APIConfig=APIConfig.from_env()) -> dict:
    """Returns a list of work packages using the filters provided.
    Results are limited to the page_size specified.
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, 'api/v3/work_packages')
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
            return data


async def query_work_package_relations(filters: Optional[dict]=None, config: APIConfig=APIConfig.from_env()) -> dict:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, f'api/v3/relations')
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {config.api_token}',
        }
        params = {}
        if filters is not None:
            params['filters'] = filters if isinstance(filters, str) else json.dumps(filters)
        async with session.get(url, headers=headers, params=params) as response:
            data: dict = await response.json()
            return data


async def create_work_package(project_id: int, payload: dict, notify: bool=True, config: APIConfig=APIConfig.from_env()) -> dict:
    """Creates a work package in the given project and returns the newly created work package
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, f'api/v3/projects/{project_id}/work_packages')
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {config.api_token}',
        }
        params = {
            'notify': int(notify)
        }
        payload = json.dumps(payload, default=str)
        async with session.post(url, data=payload, headers=headers, params=params) as response:
            data: dict = await response.json()
            return data


async def create_relation(work_package_id: int, payload: dict, config: APIConfig=APIConfig.from_env()) -> dict:
    """Creates a relation between two work packages
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, f'api/v3/work_packages/{work_package_id}/relations')
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {config.api_token}',
        }
        payload = json.dumps(payload, default=str)
        async with session.post(url, data=payload, headers=headers) as response:
            data: dict = await response.json()
            return data

