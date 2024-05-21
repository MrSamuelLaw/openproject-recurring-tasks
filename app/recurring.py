import logging
import asyncio
from re import fullmatch
from itertools import chain
from collections import defaultdict
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Self, ClassVar, Any, Optional
from pydantic import BaseModel, ConfigDict, Field
import common as com


logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


# ————————————————————————— Decorators —————————————————————————

def cache_async(async_func):
    _cache = {}
    async def wrapper(*args, **kwargs):
        key = list(args)
        key.extend([(k, v) for k, v in kwargs.items()])
        key = hash(tuple(key))
        if key in _cache.keys():
            result = _cache[key]
        else:
            result = await async_func(*args, **kwargs)
            _cache[key] = result
        return result
    wrapper._cache = _cache
    return wrapper


# ————————————————————————— Models —————————————————————————

class WorkPackageType(BaseModel):

    model_config = ConfigDict(extra='ignore')

    id: int = Field()
    name: str = Field()

    def __hash__(self):
        return self.id


class Project(BaseModel):

    model_config = ConfigDict(extra='ignore')

    id: int =       Field()
    active: bool =  Field()
    name: str =     Field()

    def __hash__(self) -> int:
        return self.id

    @classmethod
    @cache_async
    async def query_projects(cls, filters: Optional[dict]=None) -> list[Self]:
        data = await com.query_projects(filters)
        projects = [cls(**obj) for obj in data['_embedded']['elements']]
        return projects

    @cache_async
    async def query_work_package_types(self) -> list[WorkPackageType]:
        data = await com.query_work_package_types(self.id)
        types = [WorkPackageType(**obj) for obj in data['_embedded']['elements']]
        return types


class WorkPackageSchema(BaseModel):
    """Class that represents a schema for a work package.
    Note, the schemas are made to sanitize the template when
    creating it.
    """

    model_config = ConfigDict(extra='allow')

    custom_field_name_map: ClassVar[dict] = {}

    links: dict = Field(alias='_links')

    def __hash__(self):
        return self.schema_id

    @property
    def schema_id(self) -> tuple[int, int]:
        project_id, type_id = self.links['self']['href'].split('/')[-1].split('-')
        return (int(project_id), int(type_id))

    @property
    def project_id(self) -> int:
        return self.schema_id[0]

    @property
    def type_id(self) -> int:
        return self.schema_id[1]

    @classmethod
    @cache_async
    async def query_work_package_schema(cls, project_id: int, work_package_type_id: int) -> Self:
        data = await com.query_work_package_schema(project_id, work_package_type_id)
        schema = cls(**data)
        schema._update_custom_field_name_map()
        return schema

    def _update_custom_field_name_map(self):
        pattern = r'customField\d+'
        custom_fields = {v['name']: k for k, v in self.model_dump().items() if fullmatch(pattern, k)}
        self.custom_field_name_map.update(custom_fields)

    def __getitem__(self, key: str):
        key = self.custom_field_name_map.get(key, key)
        return getattr(self, key)

    def get(self, key: str, fallback: Any=None) -> Any:
        key = self.custom_field_name_map.get(key, key)
        return getattr(self, key, fallback)


class WorkPackageRelation(BaseModel):

    model_config = ConfigDict(extra='allow')

    id: Optional[int] = Field(None)
    links: dict = Field(alias='_links')

    @property
    def to(self) -> int:
        return int(self.links['to']['href'].split('/')[-1])

    @to.setter
    def to(self, value) -> int:
        parts = self.links['to']['href'].split('/')
        parts[-1] = value
        self.link['to']['href'] = '/'.join(parts)

    @property
    def from_(self) -> int:
        return int(self.links['from']['href'].split('/')[-1])

    @from_.setter
    def from_(self, value) -> int:
        parts = self.links['from']['href'].split('/')
        parts[-1] = value
        self.link['from']['href'] = '/'.join(parts)

    @classmethod
    async def query_work_package_relations(cls, filters: Optional[dict]=None) -> list[Self]:
        data = await com.query_work_package_relations(filters=filters)
        relations = [cls(**obj) for obj in data['_embedded']['elements']]
        return relations

    def build_work_package_relation_payload(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


class WorkPackage(BaseModel):
    """Class that represents data for a work package
    """

    model_config = ConfigDict(extra='allow')

    id:      int =  Field()
    type:    str =  Field(alias='_type')
    subject: str =  Field()
    links:   dict = Field(alias='_links')
    date_:      date | None = Field(None, alias='date')
    startDate:  date | None = Field(None)
    dueDate:    date | None = Field(None)

    @property
    def type_id(self) -> int:
        return int(self.links['type']['href'].split('/')[-1])

    @property
    def project_id(self) -> int:
        return int(self.links['project']['href'].split('/')[-1])

    @property
    def schema_id(self) -> tuple[int, int]:
        return (self.project_id, self.type_id)

    def __getitem__(self, key: str):
        key = WorkPackageSchema.custom_field_name_map.get(key, key)
        if key in self.links.keys():
            return self.links[key]
        return getattr(self, key)

    def __setitem__(self, key: str, value):
        key = WorkPackageSchema.custom_field_name_map.get(key, key)
        if key in self.links.keys():
            self.links[key] = value
        setattr(self, key, value)

    def get(self, key: str, fallback: Any=None) -> Any:
        key = WorkPackageSchema.custom_field_name_map.get(key, key)
        if key in self.links.keys():
            return self.links[key]
        return getattr(self, key, fallback)

    @classmethod
    async def query_work_packages(cls, filters: Optional[dict]=None) -> list[Self]:
        data = await com.query_work_packages(filters=filters)
        work_packages = [cls(**obj) for obj in data['_embedded']['elements']]
        return work_packages

    def build_work_package_payload(self, schema: WorkPackageSchema) -> dict:
        payload = self.model_dump(by_alias=True, exclude_none=True)
        schema_data = schema.model_dump(by_alias=True)
        for key, obj in schema_data.items():
            if isinstance(obj, dict) and obj.get('writable') == False:  # noqa: E712
                if key in payload.keys():
                    del payload[key]
                elif key in payload['_links'].keys():
                    del payload['_links'][key]
        return payload


class WorkPackageCloneInfo(BaseModel):

    template: WorkPackage
    modifications: dict[str, Any]

    async def create_clone(self) -> WorkPackage:
        # create a copy of the template
        clone = self.template.model_copy()
        # apply the modifications
        for key, val in self.modifications.items():
            clone[key] = val
        # get the schema to build the work package payload
        projects = await Project.query_projects()
        project = [p for p in projects if p.name == clone['Target Project']['title']][0]
        schema = await WorkPackageSchema.query_work_package_schema(project.id, clone.type_id)
        payload = clone.build_work_package_payload(schema)
        # create the new work package
        data = await com.create_work_package(project.id, payload)
        new_work_package = WorkPackage(**data)
        relation = WorkPackageRelation(**{
            '_links': {
                'from': {'href': f'/api/v3/work_packages/{new_work_package.id}'},
                'to': {'href': f'/api/v3/work_packages/{self.template.id}'}
            },
            'name': 'duplicates',
            'type': 'duplicates',
            'reverseType': 'duplicated'
        })
        payload = relation.build_work_package_relation_payload()
        await com.create_relation(new_work_package.id, payload)
        return new_work_package


# ————————————————————————— Module Methods —————————————————————————

async def calculate_clone_infos():
    # query the projects and types to compute the schemas necessary
    projects = await Project.query_projects()
    types = await asyncio.gather(*[p.query_work_package_types() for p in projects])
    schema_ids = [(p.id, t.id) for p, l in zip(projects, types) for t in l]
    schemas = await asyncio.gather(*[WorkPackageSchema.query_work_package_schema(*sid) for sid in schema_ids])

    # filter to schemas that have things to schedule
    schemas = [s for s in schemas if s.get('Auto Scheduling Algorithm')]

    # get work packages using schemas
    filters = [
        {'status_id': {'operator': 'o', 'values': None}},
        {'project_id': {'operator': '=', 'values': list({s.project_id for s in schemas})}},
        {'type': {'operator': '=', 'values': list({s.type_id for s in schemas})}}
    ]
    templates = await WorkPackage.query_work_packages(filters=filters)


    data = await asyncio.gather(
        calculate_fixed_delay_clone_infos(templates),
        calculate_fixed_interval_clone_infos(templates),
        calculate_fixed_day_of_month_clone_infos(templates),
        calculate_weather_dependent_clone_infos(templates)
    )
    clone_infos: list[WorkPackageCloneInfo] = list(chain(*data))
    return clone_infos


async def calculate_fixed_delay_clone_infos(templates: list[WorkPackage]) -> list[WorkPackageCloneInfo]:
    templates = [t for t in templates if t['Auto Scheduling Algorithm']['title'] == 'Fixed Delay']

    # short circuit evaluation
    if not templates:
        return []

    # queries for duplicated so we can get the info on them
    filters = [
        {'status_id': {'operator': 'o', 'values': None}},
        {'duplicates': {'operator': '=', 'values': [t.id for t in templates]}}
    ]
    duplicates = await WorkPackage.query_work_packages(filters=filters)

    # query the relations so we can link duplicated to templates with short circuiting
    if not duplicates:
        relations = []
    else:
        filters = [
            {'to': {'operator': '=', 'values': [t.id for t in templates]}},
            {'from': {'operator': '=', 'values': [d.id for d in duplicates]}},
            {'type': {'operator': '=', 'values': ['duplicates']}}
        ]
        relations = await WorkPackageRelation.query_work_package_relations(filters=filters)

    # compute the clones from the mapping
    clones: list[WorkPackageCloneInfo] = []
    mapping = defaultdict(list)
    [mapping[r.to].append(r.from_)  for r in relations]
    for template in templates:
        if not mapping[template.id]:
            interval = template['Interval/Day Of Month']
            dueDate = date.today() + timedelta(days=interval)
            clone = WorkPackageCloneInfo(
                template=template,
                modifications = {
                    'date': dueDate,
                    'startDate': dueDate,
                    'dueDate': dueDate
                }
            )
            clones.append(clone)
    return clones


async def calculate_fixed_interval_clone_infos(templates: list[WorkPackage]) -> list[WorkPackageCloneInfo]:
    templates = [t for t in templates if t['Auto Scheduling Algorithm']['title'] == 'Fixed Interval']

    # short circuit evaluation
    if not templates:
        return []

    # calculate next occurrence date
    dates = {}
    for t in templates:
        try:
            start = t['startDate'] or t['date_']
            today = date.today()
            delta: timedelta = today - start
            interval = t['Interval/Day Of Month']
            remainder = timedelta(days = interval - (delta.days % interval))
            next_date = start + delta + remainder
            dates[t.id] = next_date
        except (TypeError, ValueError) as e:
            LOGGER.warning(f'Invalid recurring config for work package {t.id} with error {e}')

    if not dates:
        duplicates = []
    else:
        # queries for duplicated so we can get the info on them
        filters = [
            # {'status_id': {'operator': 'o', 'values': None}},
            {'duplicates': {'operator': '=', 'values': [t.id for t in templates]}},
            {'startDate': {'operator': '=d', 'values': [str(d) for d in dates.values()]}}
        ]
        duplicates = await WorkPackage.query_work_packages(filters=filters)


    # query the relations so we can link duplicated to templates with short circuiting
    if not duplicates:
        relations = []
    else:
        filters = [
            {'to': {'operator': '=', 'values': [t.id for t in templates]}},
            {'from': {'operator': '=', 'values': [d.id for d in duplicates]}},
            {'type': {'operator': '=', 'values': ['duplicates']}}
        ]
        relations = await WorkPackageRelation.query_work_package_relations(filters=filters)

    # compute the clones from the mapping
    clones: list[WorkPackageCloneInfo] = []
    mapping = defaultdict(list)
    [mapping[r.to].append(r.from_)  for r in relations]
    for template in templates:
        if not mapping[template.id]:
            try:
                dueDate = dates[template.id]
                clone = WorkPackageCloneInfo(
                    template=template,
                    modifications = {
                        'date': dueDate,
                        'startDate': dueDate,
                        'dueDate': dueDate
                    }
                )
                clones.append(clone)
            except KeyError as e:
                LOGGER.warning(f'Failed to create clone info for work package {template.id} with error {e}')
    return clones


async def calculate_fixed_day_of_month_clone_infos(templates: list[WorkPackage]) -> list[WorkPackageCloneInfo]:
    templates = [t for t in templates if t['Auto Scheduling Algorithm']['title'] == 'Fixed Day Of Month']

    # short circuit evaluation
    if not templates:
        return []

    # calculate next occurrence date
    dates = {}
    for t in templates:
        try:
            today = date.today()
            day = t['Interval/Day Of Month']
            # if day is in the past look to next months
            next_date = today.replace(day = day)
            if next_date <= today:
                next_date = next_date + relativedelta(months=1)
            dates[t.id] = next_date
        except (TypeError, ValueError) as e:
            LOGGER.warning(f'Invalid recurring config for work package {t.id} with error {e}')

    if not dates:
        duplicates = []
    else:
        # queries for duplicated so we can get the info on them
        filters = [
            # {'status_id': {'operator': 'o', 'values': None}},
            {'duplicates': {'operator': '=', 'values': [t.id for t in templates]}},
            {'startDate': {'operator': '=d', 'values': [str(d) for d in dates.values()]}}
        ]
        duplicates = await WorkPackage.query_work_packages(filters=filters)

    # query the relations so we can link duplicated to templates with short circuiting
    if not duplicates:
        relations = []
    else:
        filters = [
            {'to': {'operator': '=', 'values': [t.id for t in templates]}},
            {'from': {'operator': '=', 'values': [d.id for d in duplicates]}},
            {'type': {'operator': '=', 'values': ['duplicates']}}
        ]
        relations = await WorkPackageRelation.query_work_package_relations(filters=filters)

    # compute the clones from the mapping
    clones: list[WorkPackageCloneInfo] = []
    mapping = defaultdict(list)
    [mapping[r.to].append(r.from_)  for r in relations]
    for template in templates:
        if not mapping[template.id]:
            try:
                dueDate = dates[template.id]
                clone = WorkPackageCloneInfo(
                    template=template,
                    modifications = {
                        'date': dueDate,
                        'startDate': dueDate,
                        'dueDate': dueDate
                    }
                )
                clones.append(clone)
            except KeyError as e:
                LOGGER.warning(f'Failed to create clone info for work package {template.id} with error {e}')
    return clones


async def calculate_weather_dependent_clone_infos(templates: list[WorkPackage]) -> list[WorkPackageCloneInfo]:
    return []


async def async_main():
    clone_infos = await calculate_clone_infos()
    await asyncio.gather(*[ci.create_clone() for ci in clone_infos])


if __name__ == '__main__':
    asyncio.run(async_main())