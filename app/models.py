from os import environ
from base64 import b64encode
from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from typing import Self


class APIConfig(BaseModel):
    """Class that is used to hold environment variables.
    """

    model_config = ConfigDict(frozen=True)

    api_key:    str  = Field()
    host:       str  = Field()
    https:      bool = Field(True)
    verify_ssl: bool = Field(True)

    @classmethod
    def from_environment_variables(cls) -> Self:
        data = {key: environ.get(key.upper()) for key in cls.model_fields.keys()}
        instance = cls(**data)
        return instance

    @property
    def api_token(self) -> bytes:
        """Returns a b64 encoded api key for the authorization header
        """
        token = f'apikey:{self.api_key}'.encode()
        token = b64encode(token).decode()
        return token


class CustomFieldMixing(object):
    pass


class WorkPackageSchema(BaseModel):
    """Class that represents a schema for a work package.
    """

    model_config = ConfigDict(extra='allow')

    id: str = Field()
    links: str = Field(alias='_links')


class WorkPackage(BaseModel):

    model_config = ConfigDict(extra='allow')

    id:      int =  Field()
    type:    str =  Field(alias='_type')
    subject: str =  Field()
    links:   dict = Field(alias='_links')
    startDate:  date | None = Field(None)
    dueDate:    date | None = Field(None)
    schema:

    def __getitem__(self, key):
        """Used to make reading variables by name easy
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            pass

    def __setitem__(self, key, value):
        """Used to make writing variables by name easy
        """
        pass
