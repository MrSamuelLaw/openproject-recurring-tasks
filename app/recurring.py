import json
import asyncio
import common
from itertools import chain
from collections import defaultdict
from datetime import date, timedelta
from models import (APIConfig,
                    SharedContext,
                    Project,
                    WorkPackage,
                    WorkPackageRelation,
                    WorkPackageCloneInfo)


async def build_shared_context(config: APIConfig):
    # get a list of the projects for the global context
    projects = await common.query_projects(APIConfig.from_env())
    SharedContext.projects.update({p.id: p for p in projects})

    # get a list of types for the global context & compute needed schemas
    async def build_project_type_map(project: Project):
        work_package_types = await common.query_project_types(config, project.id)
        SharedContext.work_package_types.update({wpt.id: wpt for wpt in work_package_types})
        SharedContext.work_package_schemas.update({(project.id, wpt.id): None for wpt in work_package_types})

    await asyncio.gather(*[build_project_type_map(p) for p in projects])

    # get a list of schemas
    schema_ids = [k for k, v in SharedContext.work_package_schemas.items() if v is None]
    schemas = await asyncio.gather(*[common.query_work_package_schema(config, id_) for id_ in schema_ids])
    SharedContext.work_package_schemas.update({s.id: s for s in schemas})


async def query_templates(config: APIConfig) -> list[WorkPackage]:

    # filter to schemas that have things to schedule
    schemas = [s for s in SharedContext.work_package_schemas.values() if s.get('Auto Scheduling Algorithm')]

    # query work packages using project and type filters
    filters = [
        {'status_id': {'operator': 'o', 'values': None}},
        {'project_id': {'operator': '=', 'values': list({s.project_id for s in schemas})}},
        {'type': {'operator': '=', 'values': list({s.type_id for s in schemas})}}
    ]
    templates = await common.query_work_packages(config, filters=json.dumps(filters))

    return templates


async def build_clone_info(config: APIConfig, templates: list[WorkPackage]) -> list[WorkPackageCloneInfo]:

    clones = await asyncio.gather(
        build_fixed_delay_clone_info(config, templates),
        build_fixed_interval_clone_info(config, templates),
        build_fixed_day_of_month_clone_info(config, templates)
    )
    clones = list(chain(*clones))
    return clones


async def build_fixed_delay_clone_info(config: APIConfig, templates: list[WorkPackage]) -> list[WorkPackageCloneInfo]:
    # filter to only fixed delay templates
    templates: dict[int, WorkPackage] = {t.id: t for t in templates if t['Auto Scheduling Algorithm']['title'] == 'Fixed Delay'}

    # short circuit evaluation
    if not templates:
        return []

    # queries for duplicated so we can get the info on them
    filters = [
        {'status_id': {'operator': 'o', 'values': None}},
        {'duplicates': {'operator': '=', 'values': list(templates.keys())}}
    ]
    duplicates = await common.query_work_packages(config, filters=json.dumps(filters))
    duplicates = {d.id: d for d in duplicates}

    # query the relations so we can link duplicated to templates with short circuiting
    if not duplicates:
        relations = []
    else:
        filters = [
            {'to': {'operator': '=', 'values': list(templates.keys())}},
            {'from': {'operator': '=', 'values': list(duplicates.keys())}},
            {'type': {'operator': '=', 'values': ['duplicates']}}
        ]
        relations = await common.query_work_package_relations(config, filters=json.dumps(filters))

    # compute the clones from the mapping
    clones: list[WorkPackageCloneInfo] = []
    mapping = defaultdict(list)
    [mapping[r.to].append(r.from_)  for r in relations]
    for template in templates.values():
        if not mapping[template.id]:
            interval = template['Interval/Day Of Month']
            clone = WorkPackageCloneInfo(
                template=template,
                modifications = {
                    'date': date.today() + timedelta(days=interval)
                }
            )
            clones.append(clone)
    return clones


async def build_fixed_interval_clone_info(config: APIConfig, templates: list[WorkPackage]) -> list[WorkPackageCloneInfo]:
    return []


async def build_fixed_day_of_month_clone_info(config: APIConfig, templates: list[WorkPackage]) -> list[WorkPackageCloneInfo]:
    return []


async def create_clone(config: APIConfig, clone_info: WorkPackageCloneInfo) -> WorkPackage:
    clone = clone_info.template.model_copy()
    for key, val in clone_info.modifications.items():
        clone[key] = val
    project = [p for p in SharedContext.projects.values() if p.name == clone['Target Project']['title']][0]
    schema = SharedContext.work_package_schemas[(project.id, clone.type_id)]
    new_work_package = await common.create_work_package(config, project, schema, clone)
    relation = WorkPackageRelation(**{
        '_links': {
            'from': {'href': f'/api/v3/work_packages/{new_work_package.id}'},
            'to': {'href': f'/api/v3/work_packages/{clone_info.template.id}'}
        },
        'name': 'duplicates',
        'type': 'duplicates',
        'reverseType': 'duplicated'
    })
    await common.create_relation(config, new_work_package.id, relation)
    return new_work_package