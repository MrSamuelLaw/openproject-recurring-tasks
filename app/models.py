from os import environ
from re import fullmatch
from base64 import b64encode
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, computed_field
from typing import Self, ClassVar, Any, Optional, TypeAlias


# ————————————————— Type Aliases —————————————————
project_id: TypeAlias = int
type_id: TypeAlias = int
status_id: TypeAlias = int
schema_id: TypeAlias = tuple[project_id, type_id]



# ————————————————— Models —————————————————

class APIConfig(BaseModel):
    """Class that is used to hold environment variables.
    """

    _instance: ClassVar[Self | None] = None

    model_config = ConfigDict(frozen=True)

    api_key:    str  = Field()
    host:       str  = Field()
    https:      bool = Field(True)
    verify_ssl: bool = Field(True)

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


class Project(BaseModel):

    model_config = ConfigDict(extra='ignore')

    id: project_id =    Field()
    active: bool =      Field()
    name: str =         Field()
    links: Optional[dict] = Field(None, alias='_links')


class WorkPackageType(BaseModel):

    model_config = ConfigDict(extra='allow')

    id: type_id = Field()


class WorkPackageStatus(BaseModel):

    model_config = ConfigDict(extra='allow')

    id: status_id = Field()


class WorkPackageSchema(BaseModel):
    """Class that represents a schema for a work package.
    Note, the schemas are made to sanitize the template when
    creating it.
    """

    model_config = ConfigDict(extra='allow')

    links: dict = Field(alias='_links')

    @property
    def project_id(self) -> project_id:
        return self.id[0]

    @property
    def type_id(self) -> type_id:
        return self.id[1]

    @property
    def id(self) -> schema_id:
        id = self.links['self']['href'].split('/')[-1].split('-')
        return tuple([int(v) for v in id])

    def _map_key(self, key: str) -> str:
        key = SharedContext.custom_field_map.get(key, key)
        if not hasattr(self, key):
            pattern = r'customField\d+'
            custom_fields = {v['name']: k for k, v in self.model_dump().items() if fullmatch(pattern, k)}
            SharedContext.custom_field_map.update(**custom_fields)
            key = SharedContext.custom_field_map.get(key, key)
        return key

    def __getitem__(self, key: str):
        key = self._map_key(key)
        return getattr(self, key)

    def get(self, key: str, fallback=None):
        key = self._map_key(key)
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
        self.link['to']['href'] = '/'.join(parts)

    @property
    def from_(self) -> int:
        return int(self.links['from']['href'].split('/')[-1])

    @from_.setter
    def from_(self, value) -> int:
        parts = self.links['from']['href'].split('/')
        self.link['from']['href'] = '/'.join(parts)


class WorkPackage(BaseModel):
    """Class that represents data for a work package
    """

    model_config = ConfigDict(extra='allow')

    id:      int =  Field()
    type:    str =  Field(alias='_type')
    subject: str =  Field()
    links:   dict = Field(alias='_links')
    startDate:  date | None = Field(None)
    dueDate:    date | None = Field(None)

    @property
    def type_id(self) -> type_id:
        return int(self.links['type']['href'].split('/')[-1])

    @property
    def project_id(self) -> project_id:
        return int(self.links['project']['href'].split('/')[-1])

    @property
    def schema_id(self) -> schema_id:
        return (self.project_id, self.type_id)

    def __getitem__(self, key: str):
        key = SharedContext.custom_field_map.get(key, key)
        if key in self.links.keys():
            return self.links[key]
        return getattr(self, key)

    def __setitem__(self, key: str, value):
        key = SharedContext.custom_field_map.get(key, key)
        if key in self.links.keys():
            self.links[key] = value
        setattr(self, key, value)


class WorkPackageCloneInfo(BaseModel):

    template: WorkPackage
    modifications: dict[str, Any]
    clone: WorkPackage | None = None  # set once the template has been cloned


class SharedContext(BaseModel):
    """Class that acts similar to a cache for storing state that multiple classes/functions
    must references. This is very handy for async applications where each function might
    be updating a shared resource.
    """

    projects: ClassVar[dict[int, Project]] = {}
    work_package_types: ClassVar[dict[int, WorkPackageType]] = {}
    work_package_schemas: ClassVar[dict[tuple[int, int], WorkPackageSchema | None]] = {}
    work_package_status: ClassVar[dict[int, WorkPackageStatus]] = {}
    custom_field_map: ClassVar[dict[str, str]] = {}

    def __init__(self, *args, **kwargs):
        raise NotImplemented('Cannot instantiate SharedContext directly')


