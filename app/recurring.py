import sys
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

    template: WorkPackage =         Field()
    modifications: dict[str, Any] = Field()

    async def create_clone(self) -> WorkPackage:
        logging.debug('creating clone from work package %d', self.template.id)
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


class WorkPackageTemplateInfo(BaseModel):

    template: WorkPackage =             Field()
    modifications: dict[str, Any] =     Field()

    async def update_template(self) -> WorkPackage:
        self.modifications['lockVersion'] = self.template.lockVersion
        logging.debug('updating template %d with modifications %s', self.template.id, self.modifications)
        data = await com.update_work_package(self.template.id, self.modifications)
        work_package = WorkPackage(**data)
        return work_package


class WorkPackageSchedulingInfo(BaseModel):

    clone_info: Optional[WorkPackageCloneInfo] =        Field(None)
    template_info: Optional[WorkPackageTemplateInfo] =  Field(None)


# ————————————————————————— Module Methods —————————————————————————

async def calculate_scheduling_infos() -> list[WorkPackageSchedulingInfo]:
    # query the projects and types to compute the schemas necessary
    projects = await Project.query_projects()
    types = await asyncio.gather(*[p.query_work_package_types() for p in projects])
    schema_ids = [(p.id, t.id) for p, lst in zip(projects, types) for t in lst]
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
        calculate_fixed_delay_scheduling_infos(templates),
        calculate_fixed_interval_scheduling_infos(templates),
        calculate_fixed_day_of_month_clone_infos(templates),
        calculate_fixed_day_of_year_clone_infos(templates),
        calculate_weather_dependent_clone_infos(templates)
    )
    scheduling_infos: list[WorkPackageSchedulingInfo] = list(chain(*data))
    return scheduling_infos


async def calculate_fixed_delay_scheduling_infos(templates: list[WorkPackage]) -> list[WorkPackageSchedulingInfo]:
    templates = [t for t in templates if t['Auto Scheduling Algorithm']['title'] == 'Fixed Delay']

    logging.debug('%d fixed delay schedule templates found', len(templates))
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
    scheduling_infos: list[WorkPackageSchedulingInfo] = []
    mapping = defaultdict(list)
    [mapping[r.to].append(r.from_)  for r in relations]
    for template in templates:
        if not mapping[template.id]:
            interval = template['Interval/Day Of Month']
            dueDate = date.today() + timedelta(days=interval)
            clone_info = WorkPackageCloneInfo(
                template=template,
                modifications = {
                    'date': dueDate,
                    'startDate': dueDate,
                    'dueDate': dueDate
                }
            )
            schedule_info = WorkPackageSchedulingInfo(clone_info=clone_info)
            scheduling_infos.append(schedule_info)

    logging.debug('%d fixed delay scheduling_infos calculated', len(scheduling_infos))
    return scheduling_infos


async def calculate_fixed_interval_scheduling_infos(templates: list[WorkPackage]) -> list[WorkPackageSchedulingInfo]:
    templates = {t.id: t for t in templates if t['Auto Scheduling Algorithm']['title'] == 'Fixed Interval'}

    # short circuit evaluation
    logging.debug('%d fixed interval schedule templates found', len(templates))
    if not templates:
        return []

    # calculate next occurrence date
    dates = {}
    for t in templates.values():
        try:
            start = t['startDate'] or t['date_']
            today = date.today()
            delta: timedelta = today - start
            interval = t['Interval/Day Of Month']
            remainder = timedelta(days = interval - (delta.days % interval))
            next_date = start + delta + remainder
            dates[t.id] = next_date
        except (TypeError, ValueError) as e:
            logging.warning('Invalid recurring config for work package %d with error %s', t.id, e)

    if not dates:
        duplicates = []
    else:
        # queries for duplicated so we can get the info on them
        filters = [{'duplicates': {'operator': '=', 'values': list(templates.keys())}}]
        duplicates = await WorkPackage.query_work_packages(filters=filters)
        duplicates = {d.id: d for d in duplicates if (d.startDate or d.dueDate or d.date_) in dates.values()}


    # query the relations so we can link duplicated to templates with short circuiting
    if not duplicates:
        relations = []
    else:
        filters = [
            {'to': {'operator': '=', 'values': list(templates.keys())}},
            {'from': {'operator': '=', 'values': list(duplicates.keys())}},
            {'type': {'operator': '=', 'values': ['duplicates']}}
        ]
        relations = await WorkPackageRelation.query_work_package_relations(filters=filters)

    # compute the clones from the mapping
    scheduling_infos: list[WorkPackageSchedulingInfo] = []
    mapping = defaultdict(list)
    for r in relations:
        d = duplicates[r.from_]
        if (d.startDate or d.dueDate or d.date_) == dates[r.to]:
            mapping[r.to].append(r.from_)
    for template in templates.values():
        if not mapping[template.id]:
            try:
                dueDate = dates[template.id]
                clone_info = WorkPackageCloneInfo(
                    template=template,
                    modifications = {
                        'date': dueDate,
                        'startDate': dueDate,
                        'dueDate': dueDate
                    }
                )
                scheduling_info = WorkPackageSchedulingInfo(clone_info = clone_info)
                scheduling_infos.append(scheduling_info)
            except KeyError as e:
                logging.warning('Failed to create clone info for work package %d with error %s', template.id, e)

    logging.debug('%d fixed interval scheduling_infos calculated', len(scheduling_infos))
    return scheduling_infos


async def calculate_fixed_day_of_month_clone_infos(templates: list[WorkPackage]) -> list[WorkPackageSchedulingInfo]:
    templates = {t.id: t for t in templates if t['Auto Scheduling Algorithm']['title'] == 'Fixed Day Of Month'}

    # short circuit evaluation
    logging.debug('%d fixed day of month schedule templates found', len(templates))
    if not templates:
        return []

    # calculate next occurrence date
    dates = {}
    for t in templates.values():
        try:
            today = date.today()
            day = t['Interval/Day Of Month']
            # if day is in the past look to next months
            next_date = today.replace(day=day)
            if next_date <= today:
                next_date = next_date + relativedelta(months=1)
            dates[t.id] = next_date
        except (TypeError, ValueError) as e:
            logging.warning('Invalid recurring config for work package %d with error %s', t.id, e)

    if not dates:
        duplicates = []
    else:
        # queries for duplicated so we can get the info on them
        filters = [{'duplicates': {'operator': '=', 'values': list(templates.keys())}}]
        duplicates = await WorkPackage.query_work_packages(filters=filters)
        duplicates = {d.id: d for d in duplicates if (d.startDate or d.dueDate or d.date_) in dates.values()}


    # query the relations so we can link duplicated to templates with short circuiting
    if not duplicates:
        relations = []
    else:
        filters = [
            {'to': {'operator': '=', 'values': list(templates.keys())}},
            {'from': {'operator': '=', 'values': list(duplicates.keys())}},
            {'type': {'operator': '=', 'values': ['duplicates']}}
        ]
        relations = await WorkPackageRelation.query_work_package_relations(filters=filters)

    # compute the clones from the mapping
    scheduling_infos: list[WorkPackageSchedulingInfo] = []
    mapping = defaultdict(list)
    for r in relations:
        d = duplicates[r.from_]
        if (d.startDate or d.dueDate or d.date_) == dates[r.to]:
            mapping[r.to].append(r.from_)
    for template in templates.values():
        if not mapping[template.id]:
            try:
                dueDate = dates[template.id]
                clone_info = WorkPackageCloneInfo(
                    template=template,
                    modifications = {
                        'date': dueDate,
                        'startDate': dueDate,
                        'dueDate': dueDate
                    }
                )
                scheduling_info = WorkPackageSchedulingInfo(clone_info=clone_info)
                scheduling_infos.append(scheduling_info)
            except KeyError as e:
                logging.warning('Failed to create clone info for work package %d with error %s', template.id, e)

    logging.debug('%d fixed day of month scheduling_infos calculated', len(scheduling_infos))
    return scheduling_infos


async def calculate_fixed_day_of_year_clone_infos(templates: list[WorkPackage]) -> list[WorkPackageSchedulingInfo]:
    templates = {t.id: t for t in templates if t['Auto Scheduling Algorithm']['title'] == 'Fixed Day Of Year'}

    # short circuit evaluation
    logging.debug('%d fixed day of year schedule templates found', len(templates))
    if not templates:
        return []

    # calculate next occurrence date
    dates = {}
    for t in templates.values():
        try:
            today = date.today()
            next_date = t.startDate or t.dueDate or t.date_
            next_date = next_date.replace(year=today.year)
            dates[t.id] = next_date
        except (TypeError, ValueError) as e:
            logging.warning('Invalid recurring config for work package %d with error %s', t.id, e)

    if not dates:
        duplicates = []
    else:
        # queries for duplicated so we can get the info on them
        filters = [{'duplicates': {'operator': '=', 'values': list(templates.keys())}}]
        duplicates = await WorkPackage.query_work_packages(filters=filters)
        duplicates = {d.id: d for d in duplicates if (d.startDate or d.dueDate or d.date_) in dates.values()}


    # query the relations so we can link duplicated to templates with short circuiting
    if not duplicates:
        relations = []
    else:
        filters = [
            {'to': {'operator': '=', 'values': list(templates.keys())}},
            {'from': {'operator': '=', 'values': list(duplicates.keys())}},
            {'type': {'operator': '=', 'values': ['duplicates']}}
        ]
        relations = await WorkPackageRelation.query_work_package_relations(filters=filters)

    # compute the clones from the mapping
    scheduling_infos: list[WorkPackageSchedulingInfo] = []
    mapping = defaultdict(list)
    for r in relations:
        d = duplicates[r.from_]
        if (d.startDate or d.dueDate or d.date_) == dates[r.to]:
            mapping[r.to].append(r.from_)
    for template in templates.values():
        if not mapping[template.id]:
            try:
                dueDate = dates[template.id]
                clone_info = WorkPackageCloneInfo(
                    template=template,
                    modifications = {
                        'date': dueDate,
                        'startDate': dueDate,
                        'dueDate': dueDate
                    }
                )
                scheduling_info = WorkPackageSchedulingInfo(clone_info=clone_info)
                scheduling_infos.append(scheduling_info)
            except KeyError as e:
                logging.warning('Failed to create clone info for work package %d with error %s', template.id, e)

    logging.debug('%d fixed day of year scheduling_infos calculated', len(scheduling_infos))
    return scheduling_infos



async def calculate_weather_dependent_clone_infos(templates: list[WorkPackage]) -> list[WorkPackageSchedulingInfo]:
    templates = [t for t in templates if t['Auto Scheduling Algorithm']['title'] == 'Weather Forecast']

    # short circuit evaluation
    logging.debug('%d weather dependent scheduling templates found', len(templates))
    if not templates:
        return []

    # get the number of days to query weather for
    num_days = max((t['Interval/Day Of Month'] for t in templates))
    weather_data = await com.query_forecast(num_days)
    forecast_codes = weather_data['minutely_15']['weather_code']

    def forecast_codes_in_work_package(forecast_codes: int | tuple[int, int], template: WorkPackage):
        """Checks if the forecast weather codes intersect with the templates
        weather codes and returns true if so.
        """
        days_out = template['Interval/Day Of Month']
        idx = days_out * 24 * 4 # days out * hours in a day * quarters in an hour
        idx = min((idx, len(forecast_codes)))
        codes = set(forecast_codes[: idx])
        t_codes = template['Weather Codes'].split(',')
        t_codes = [c.strip() for c in t_codes]
        flag = False
        for tc in t_codes:
            if '-' in tc:
                left, right = [int(v) for v in tc.split('-')]
                codes = [v for v in codes if left <= v <= right]
                if codes:
                    logging.debug('Matched the codes %s in expresion %s', codes, tc)
                    flag = True
            else:
                tc = int(tc)
                codes = [v for v in codes if tc == v]
                if codes:
                    logging.debug('Matched the codes %s in expresion %s', codes, tc)
                    flag = True
        return flag

    # create new clones when codes in forecast goes from false to true
    scheduling_infos = []
    fieldName = 'Weather Detected Status'
    for t in templates:
        scheduling_info = WorkPackageSchedulingInfo()
        previously_detected = t[fieldName]
        currently_detected = forecast_codes_in_work_package(forecast_codes, t)
        if currently_detected and (not previously_detected):
            dueDate = date.today()
            clone_info = WorkPackageCloneInfo(
                template=t,
                modifications = {
                    'date': dueDate,
                    'startDate': dueDate,
                    'dueDate': dueDate
                }
            )
            scheduling_info.clone_info = clone_info
        if currently_detected != previously_detected:
            customFieldId = WorkPackageSchema.custom_field_name_map[fieldName]
            modifications = {
                customFieldId: currently_detected
            }
            update_info = WorkPackageTemplateInfo(
                template=t,
                modifications=modifications
            )
            scheduling_info.template_info = update_info
            scheduling_infos.append(scheduling_info)

    logging.debug('%d weather dependent scheduling_infos calculated', len(scheduling_infos))
    return scheduling_infos


async def async_main():
    logging.info('Calculating scheduling infos...')
    scheduling_infos = await calculate_scheduling_infos()

    clone_infos = [si.clone_info for si in scheduling_infos if si.clone_info is not None]
    logging.info('Creating %d new work packages', len(clone_infos))
    await asyncio.gather(*[ci.create_clone() for ci in clone_infos])

    template_infos = [si.template_info for si in scheduling_infos if si.template_info is not None]
    logging.info('Update %d template work packages', len(template_infos))
    await asyncio.gather(*[ti.update_template() for ti in template_infos])


if __name__ == '__main__':
    try:
        # load in configs
        config = com.APIConfig.from_env()

        # setup the handlers
        console_handler = logging.StreamHandler(stream=sys.stdout)
        file_handler = logging.FileHandler('/app/logs/app.log')
        # format the logs
        format = '%(asctime)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(format)
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        # set the log levels
        console_handler.setLevel(config.log_level)
        file_handler.setLevel(logging.DEBUG)
        # get the root logger, setting it to level DEBUG so our handlers work
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        # add the handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        # run the app
        asyncio.run(async_main())
    
    except Exception as e:
        logging.exception('Exited with an exception')