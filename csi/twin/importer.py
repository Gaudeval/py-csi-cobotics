import datetime
import math
import pathlib
import re
import typing

from csi.monitor import Trace
from csi.twin.orm import DataBase
from csi.transform import json_transform

from typing import List, Mapping, Optional, Tuple
from .converter import ConverterType, FilterType


class DBMessageImporter:
    def __init__(
        self,
        entity_aliases: Optional[Mapping[str, str]] = None,
        converters: Optional[List[Tuple[Optional[FilterType], ConverterType]]] = None,
    ):
        if entity_aliases is None:
            entity_aliases = {}
        if converters is None:
            converters = []
        self.entity_aliases = entity_aliases
        self.converters = converters

    def import_messages(self, trace: Trace, db: typing.Union[DataBase, str]):
        # Open target database
        if isinstance(db, str):
            assert pathlib.Path(db).exists()
            db = DataBase(db)
        for message in db.messages():
            # Remove indexing by foreign table primary id
            message = json_transform(
                "$[*]..[?(@.__table__)]", message, self.reduce_foreign_dictionary
            )
            # Flatten foreign tables with a single element
            message = json_transform(
                "$..[?(@.length() = 1 and @[0][?(@.__table__ and @.__pk__)])]",
                message,
                lambda d: d[0],
            )
            # Flatten tables containing only data
            message = json_transform(
                "$..[?(@.data and @.keys().length() = 1)]", message, lambda d: d["data"]
            )
            # Convert terms to snake_case
            message = json_transform(
                "$..[?(@.keys().length() > 0)]", message, self.keys_to_snake_case
            )
            # Apply custom converters
            for convert_condition, convert_op in self.converters:
                if convert_condition is None or convert_condition(message):
                    message = convert_op(message)
                    if message is None:
                        break
            if message is None:
                continue
            # Normalise entity names
            message = json_transform(
                "$.entity_id", message, lambda d: d.replace("-", "_")
            )
            # Replace entity names with specified mapping
            message = json_transform(
                "$.entity_id", message, lambda d: self.entity_aliases.get(d, d)
            )
            # Prefix data with entity name
            message = json_transform(
                "$[?(@.entity_id)]",
                message,
                lambda d: {d["entity_id"] if d["entity_id"] else d["__table__"]: d},
            )
            trace.record(message, timestamp=_safety_timestamp)

    @staticmethod
    def to_snake_case(name):
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    @staticmethod
    def reduce_foreign_dictionary(contents):
        return {k: v for k, v in contents.items() if k not in ["__table__", "__pk__"]}

    @staticmethod
    def keys_to_snake_case(contents):
        if isinstance(contents, dict):
            return {DBMessageImporter.to_snake_case(k): v for k, v in contents.items()}
        else:
            return contents


def _parse_timestamp(row: typing.Mapping):
    v = next(iter(row.values()))
    return int(
        datetime.datetime.strptime(v["unix_toi"], "%Y-%m-%d %H:%M:%S").timestamp()
    )


def _safety_timestamp(row: typing.Mapping):
    v = next(iter(row.values()))
    if "timestamp" in v:
        return int(math.floor(v.get("timestamp") * 1000))
    return None
