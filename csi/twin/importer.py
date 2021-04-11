from types import SimpleNamespace
from typing import Any, List, Generator, Mapping, Tuple, Union

from csi.transform import json_transform

MessageType = Mapping[str, Any]
PathType = Tuple[str, ...]


def as_items(element: Any, prefix: PathType = ()) -> Generator[Tuple, None, None]:
    """Convert nested structure into flat list with tuple capturing nested paths."""
    if isinstance(element, Mapping):
        for k, v in element.items():
            yield from as_items(v, prefix + (k,))
    if isinstance(element, list):
        for k, v in enumerate(element):
            yield from as_items(v, prefix + (k,))
    yield prefix, element


def from_table(db, *table):
    return map(as_object, db.flatten_messages(*table))


def as_object(element: Union[Mapping, Any]):
    if isinstance(element, Mapping):
        return SimpleNamespace(**{k: as_object(v) for k, v in element.items()})
    return element


def is_type(*types: List[str]):
    _types = set(types)

    def _filter(message: MessageType):
        return message.get("__table__", None) in _types

    return _filter


def has_key(*keys: List[Tuple[str]]):
    _keys = set(keys)

    def _filter(message: MessageType):
        return bool({k for k, _ in as_items(message)} & _keys)

    return _filter


def replace_key(key: str, replacement: str):
    def _transformer(message: MessageType):
        return json_transform(
            "$..[?(@.{})]".format(key),
            message,
            lambda d: {
                **{k: v for k, v in d.items() if k != key},
                **{replacement: d[key]},
            },
        )

    return _transformer
