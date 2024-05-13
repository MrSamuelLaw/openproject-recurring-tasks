import re
import json
import asyncio
import aiohttp
import logging


from models import (APIConfig,
                    Project,
                    WorkPackageType,
                    WorkPackageSchema,
                    WorkPackageStatus,
                    WorkPackageRelation,
                    SharedContext,
                    WorkPackage,
                    project_id,
                    schema_id)


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def build_url(config: APIConfig, endpoint: str) -> str:
    """Returns a url for the endpoint using the apps configs.
    """
    prefix = 'https' if config.https else 'http'
    url = f'{prefix}://{config.host}/{endpoint}'
    return url


def build_work_package_payload(work_package: WorkPackage, schema: WorkPackageSchema) -> dict:
    """Builds the payload to create a workpackage from a given work package model
    """
    payload = work_package.model_dump(by_alias=True)
    schema_data = schema.model_dump(by_alias=True)

    for key, obj in schema_data.items():
        if isinstance(obj, dict) and obj.get('writable') == False:
            if key in payload.keys():
                del payload[key]
            elif key in payload['_links'].keys():
                del payload['_links'][key]
    return payload


async def query_projects(config: APIConfig, filters: dict = None) -> list[Project]:
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
        if filters is not None: params['filters'] = filters;
        async with session.get(url, headers=headers, params=params) as response:
            data = await response.json()
            projects = [Project(**obj) for obj in data['_embedded']['elements']]
            return projects


async def query_project_types(config: APIConfig, id: project_id) -> list[WorkPackageType]:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, f'api/v3/projects/{id}/types')
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/hal+json',
            'Authorization': f'Basic {config.api_token}',

        }
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            work_package_types = [WorkPackageType(**obj) for obj in data['_embedded']['elements']]
            return work_package_types


async def query_work_package_statuses(config: APIConfig) -> list[WorkPackageStatus]:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, 'api/v3/statuses')
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/hal+json',
            'Authorization': f'Basic {config.api_token}',

        }
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            work_package_status = [WorkPackageStatus(**obj) for obj in data['_embedded']['elements']]
            return work_package_status


async def query_work_packages(config: APIConfig, offset: int=1, page_size: int=1000, filters: dict | None =None) -> list[WorkPackage]:
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
        # if filters is not None: params['filters'] = json.dumps(filters)
        if filters is not None: params['filters'] = filters;
        async with session.get(url, headers=headers, params=params) as response:
            data = await response.json()
            work_packages = [WorkPackage(**obj) for obj in data['_embedded']['elements']]
            return work_packages


async def query_work_package_schema(config: APIConfig, id: schema_id) -> WorkPackageSchema:
    """Queries the work package schema for a project id given the workpackage type id
    also has the side effect of updating the WorkPackage model field map
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, f'api/v3/work_packages/schemas/{id[0]}-{id[1]}')
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/hal+json',
            'Authorization': f'Basic {config.api_token}',
        }
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            schema = WorkPackageSchema(**data)
            return schema


async def query_work_package_relations(config: APIConfig, filters: dict | None =None) -> list[WorkPackageRelation]:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, f'api/v3/relations')
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {config.api_token}',
        }
        params = {}
        if filters is not None: params['filters'] = filters;
        async with session.get(url, headers=headers, params=params) as response:
            data = await response.json()
            relations = [WorkPackageRelation(**obj) for obj in data['_embedded']['elements']]
            return relations


async def build_shared_context(config: APIConfig):
    # get a list of the projects for the global context
    projects = await query_projects(APIConfig.from_env())
    SharedContext.projects.update({p.id: p for p in projects})

    # get a list of types for the global context & compute needed schemas
    async def build_project_type_map(project: Project):
        work_package_types = await query_project_types(config, project.id)
        SharedContext.work_package_types.update({wpt.id: wpt for wpt in work_package_types})
        SharedContext.work_package_schemas.update({(project.id, wpt.id): None for wpt in work_package_types})

    await asyncio.gather(*[build_project_type_map(p) for p in projects])

    # get a list of schemas
    schema_ids = [k for k, v in SharedContext.work_package_schemas.items() if v is None]
    schemas = await asyncio.gather(*[query_work_package_schema(config, id_) for id_ in schema_ids])
    SharedContext.work_package_schemas.update({s.id: s for s in schemas})


async def create_work_package(config: APIConfig, project: Project, schema: WorkPackageSchema, work_package: WorkPackage) -> WorkPackage:
    """Creates a work package in the given project and returns the newly created work package
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, f'api/v3/projects/{project.id}/work_packages')
        payload = build_work_package_payload(work_package, schema)
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {config.api_token}',
        }
        params = {
            'notify': 'true'
        }
        payload = json.dumps(payload, default=str)
        async with session.post(url, data=payload, headers=headers, params=params) as response:
            data = await response.json()
            new_work_package = WorkPackage(**data)
            return new_work_package


async def create_relation(config: APIConfig, work_package_id: int, work_package_relation: WorkPackageRelation) -> WorkPackageRelation:
    """Creates a relation between two work packages
    """
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.verify_ssl)) as session:
        url = build_url(config, f'api/v3/work_packages/{work_package_id}/relations')
        headers = {
            'Accept': 'application/hal+json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {config.api_token}',
        }
        payload = work_package_relation.model_dump_json(exclude_none=True, by_alias=True)
        async with session.post(url, data=payload, headers=headers) as response:
            data = await response.json()
            relation = WorkPackageRelation(**data)
            return relation