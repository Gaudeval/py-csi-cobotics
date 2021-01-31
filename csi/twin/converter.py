from typing import (
    Any,
    Iterable,
    Mapping,
    MutableMapping,
    Optional,
    Protocol,
    TypeVar,
    Union,
)


MessageType = TypeVar("MessageType", bound=MutableMapping[str, Any])


class FilterType(Protocol):
    def __call__(self, message: MessageType) -> bool:
        pass


class ConverterType(Protocol):
    def __call__(self, message: MessageType) -> Optional[MessageType]:
        pass


class DropTable(ConverterType):
    def __init__(self, *tables: Iterable[str]):
        self.dropped_tables = list(tables)

    def __call__(self, message: MessageType) -> Optional[MessageType]:
        if message["__table__"] in self.dropped_tables:
            return None
        else:
            return message


class DropKey(ConverterType):
    def __init__(self, *keys: str):
        self.dropped_keys = list(keys)

    def __call__(self, message: MessageType) -> Optional[MessageType]:
        for k in self.dropped_keys:
            if k in message:
                del message[k]
        if len(message) > 0:
            return message
        return None


class RegionConverter(ConverterType):
    def __init__(self, region_names: Mapping[str, str], default_value: Any):
        self.region_names = region_names
        self.default_value = default_value

    def __call__(self, message: MessageType) -> Optional[MessageType]:
        message["entity_id"] = message["entity"]
        message["position"] = {}
        message["position"][
            self.region_names.get(message["region"], None)
        ] = self.default_value
        return message


class ObstructionDetection(ConverterType):
    def __init__(self, target: str, authorised: Optional[Iterable[str]] = None):
        if authorised is None:
            authorised = frozenset()
        self.authorised = frozenset(authorised)
        self.target = target

    def __call__(self, message: MessageType) -> Optional[MessageType]:
        if message["region"] == self.target:
            entities = message.get("entities", [])
            if not isinstance(entities, list):
                entities = [entities]
            message["has_obstruction"] = len(set(entities) - self.authorised) > 0
        return message
