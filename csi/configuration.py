""" Dataclass-based configuration management. """

import abc
import dataclasses
import datetime
import json

from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Type, TypeVar, Union


_S = TypeVar("_S")


class JsonSerializable(abc.ABC):
    """Json-serializable class"""

    @classmethod
    @abc.abstractmethod
    def from_json(cls: Type[_S], obj: Mapping[str, Any]) -> _S:
        """Create instance from json-compatible dictionary"""

    @abc.abstractmethod
    def to_json(self) -> Mapping[str, Any]:
        """Encode instance into json-compatible dictionary"""


class ConfigurationEncoder(json.JSONEncoder):
    """"Json encoder for Configuration objects."""

    @staticmethod
    def rename_encoded(
        values: Mapping[str, Any],
        encoded_fieldnames: Optional[Mapping[str, str]] = None,
    ) -> Mapping[str, Any]:
        """"Rename keys in Json dictionary from configuration field names to Json names."""
        if encoded_fieldnames is None:
            encoded_fieldnames = {}
        renamed_values = {}
        for field, field_value in values.items():
            field_name = encoded_fieldnames.get(field, field)
            renamed_values[field_name] = field_value
        return renamed_values

    def default(self, o: Any) -> Any:
        """"Encode object `o` into Json-compatible structure."""
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


class ConfigurationManager:
    """"Json-serializable configuration file manager."""

    def __init__(self, root_type: Type[Any] = dict):
        self.root_type = root_type

    def load(self, path: Union[str, Path]) -> Any:
        """Load configuration from file."""
        with Path(path).open() as configuration_file:
            configuration = self.decode(json.load(configuration_file))
        return configuration

    def save(self, data: Any, path: Union[str, Path]) -> None:
        """Save configuration to file"""
        with Path(path).open("w") as output_file:
            output_file.write(self.encode(data))

    def encode(self, value: Any) -> str:
        """Encode configuration to Json string"""
        return json.dumps(value, indent=4, cls=ConfigurationEncoder)

    def decode(self, encoded_value: Any, root_type: Optional[Type[Any]] = None) -> Any:
        """Decode configuration from Json object"""
        if root_type is None:
            root_type = self.root_type
        if isinstance(encoded_value, dict):
            # Rename field from Json encoding to local names
            encoded_value = self.rename_decoded(
                encoded_value, getattr(root_type, "_encoded_fieldnames", {})
            )
            # Rename fields and load from root dataclass declaration
            if dataclasses.is_dataclass(root_type):
                for field in dataclasses.fields(root_type):
                    if field.name in encoded_value:
                        encoded_value[field.name] = self.decode(
                            encoded_value[field.name], field.type
                        )
            # Create object from serialisation primitive or default constructor
            if issubclass(root_type, JsonSerializable):
                encoded_value = root_type.from_json(encoded_value)
            else:
                encoded_value = root_type(**encoded_value)
        elif isinstance(encoded_value, list):
            # Recursively decode list elements from root type
            encoded_value = [self.decode(i, root_type) for i in encoded_value]
        return encoded_value

    @classmethod
    def rename_decoded(
        cls,
        encoded_value: MutableMapping[str, Any],
        encoded_fieldnames: Mapping[str, str],
    ) -> MutableMapping[str, Any]:
        """"Rename keys in dictionary from Json names to configuration field names."""
        for local_name, encoded_name in encoded_fieldnames.items():
            if encoded_name in encoded_value:
                assert local_name not in encoded_value
                encoded_value[local_name] = encoded_value[encoded_name]
                del encoded_value[encoded_name]
        return encoded_value
