""" Dataclass-based JSON-formatted configuration management. """
from __future__ import annotations

import abc
import dataclasses
import datetime
import json
import typing

from pathlib import Path
from typing import (
    Any,
    Iterator,
    Iterable,
    Mapping,
    Optional,
    Type,
    TypeVar,
    Union,
    Protocol,
    Generic,
)


# https://github.com/python/typing/issues/182
JSONValue = Union[str, int, float, bool, None, "JSONObject", "JSONArray"]


# Mapping with string as keys, and JSONValue as values
class JSONObject(Protocol):
    def __setitem__(self, k: str, v: JSONValue) -> None:
        ...

    def __delitem__(self, v: str) -> None:
        ...

    def __getitem__(self, k: str) -> JSONValue:
        ...

    def __iter__(self) -> Iterator[str]:
        ...


# Array is List with keys of type `int`
class JSONArray(Protocol):
    def insert(self, index: int, value: JSONValue) -> None:
        ...

    def __getitem__(self, i: int) -> JSONValue:
        ...

    def __setitem__(self, i: int, o: JSONValue) -> None:
        ...

    def __delitem__(self, i: int) -> None:
        ...


# TODO Declare Configuration type to identify configuration items and distinguish from serialised


class JsonSerializable(abc.ABC):
    """Json-serializable class"""

    @classmethod
    @abc.abstractmethod
    def from_json(cls: Type[_S], obj: JSONObject) -> _S:
        """Create instance from json-compatible dictionary"""

    @abc.abstractmethod
    def to_json(self) -> JSONObject:
        """Encode instance into json-compatible dictionary"""


_S = TypeVar("_S", bound=JsonSerializable)


class ConfigurationEncoder(json.JSONEncoder):
    """Json encoder for Configuration objects."""

    @staticmethod
    def rename_encoded(
        values: JSONObject,
        encoded_fieldnames: Optional[Mapping[str, str]] = None,
    ) -> JSONObject:
        """Rename keys in Json dictionary from configuration field names to Json names."""
        if encoded_fieldnames is None:
            encoded_fieldnames = {}
        renamed_values = {}
        for field in values:
            field_value = values[field]
            field_name = encoded_fieldnames.get(field, field)
            renamed_values[field_name] = field_value
        return renamed_values

    def default(self, o: Any) -> JSONValue:
        """Encode object `o` into Json-compatible structure."""
        if isinstance(o, datetime.datetime):
            return o.strftime("%m/%d/%Y %H:%M:%S")
        if isinstance(o, Path):
            return str(o)
        # FIXME Add case for enum-types
        if isinstance(o, JsonSerializable):
            # Encode Json-serializable object
            encoded = o.to_json()
        elif dataclasses.is_dataclass(o):
            # Automatically encode dataclasses using declared field names
            encoded = {f.name: getattr(o, f.name) for f in dataclasses.fields(o)}
        elif hasattr(o, "__dict__"):
            # Automatically encode object by collecting __dict__ attribute
            encoded = dict(getattr(o, "__dict__").items())
        else:
            # Fallback to default json encoder
            try:
                encoded = json.JSONEncoder.default(self, o)
            except TypeError:
                encoded = o
            return encoded
        # Rename dict keys to Json field names
        return self.rename_encoded(encoded, getattr(o, "_encoded_fieldnames", {}))


T = TypeVar("T")
U = TypeVar("U")


class ConfigurationManager(Generic[T]):
    """Json-serializable configuration file manager."""

    def load(self, path: Union[str, Path]) -> T:
        """Load configuration from file."""
        with Path(path).open() as configuration_file:
            configuration = self.decode(json.load(configuration_file))
        return configuration

    def save(self, data: T, path: Union[str, Path]) -> None:
        """Save configuration to file"""
        with Path(path).open("w") as output_file:
            output_file.write(self.encode(data))

    def encode(self, value: T) -> str:
        """Encode configuration to Json string"""
        return json.dumps(value, indent=4, cls=ConfigurationEncoder)

    @classmethod
    def decode(cls, encoded_value: JSONValue) -> T:
        """Decode configuration from Json object"""
        return cls._decode(encoded_value, typing.get_args(cls)[0])

    @classmethod
    def _decode(cls, encoded_value: JSONValue, root_type: Type) -> Any:
        if isinstance(encoded_value, dict):
            # Rename field from Json encoding to local names
            decoded_value = cls.rename_decoded(
                encoded_value, getattr(root_type, "_encoded_fieldnames", {})
            )
            # Rename fields and load from root dataclass declaration
            if dataclasses.is_dataclass(root_type):
                for field in dataclasses.fields(root_type):
                    if field.name in decoded_value:
                        decoded_value[field.name] = cls._decode(
                            decoded_value[field.name], field.type
                        )
            # Create object from serialisation primitive or default constructor
            if issubclass(root_type, JsonSerializable):
                return root_type.from_json(encoded_value)
            else:
                return root_type(**{k: encoded_value[k] for k in encoded_value})
        elif isinstance(encoded_value, list):
            return [cls._decode(i, root_type) for i in encoded_value]
        elif isinstance(encoded_value, root_type):
            return encoded_value
        return encoded_value

    @classmethod
    def rename_decoded(
        cls,
        encoded_value: JSONObject,
        encoded_fieldnames: Mapping[str, str],
    ) -> JSONObject:
        """Rename keys in dictionary from Json names to configuration field names."""
        for local_name, encoded_name in encoded_fieldnames.items():
            if encoded_name in encoded_value:
                assert local_name not in encoded_value
                encoded_value[local_name] = encoded_value[encoded_name]
                del encoded_value[encoded_name]
        return encoded_value
