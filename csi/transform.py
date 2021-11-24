from jsonpath2 import Path

# TODO Comment all methods for usage and check usage


def json_parse(path: str):
    return Path.parse_str(path)


def extract_subscript(node):
    from jsonpath2.nodes.subscript import SubscriptNode
    from jsonpath2.nodes.terminal import TerminalNode

    n = node
    while not isinstance(n := n.next_node, TerminalNode):
        if isinstance(n, SubscriptNode):
            assert len(n.subscripts) == 1
            yield n.subscripts[0].tojsonpath().strip('"')


def json_map(path, contents, function, *args):
    """Apply the specified function to all elements in contents matching path."""
    has_changed = True
    while (
        (match := json_match(path, contents)) and contents is not None and has_changed
    ):
        has_changed = False
        for m in match:
            subscripts = list(extract_subscript(m.node))
            element = contents
            if len(subscripts) > 0:
                for key in subscripts[:-1]:
                    if key not in element:
                        element = None
                        break
                    element = element[key]
                if element is None or subscripts[-1] not in element:
                    break
                assert isinstance(element, dict)
                element_changed, _ = function(element, subscripts[-1], *args)
            else:
                element_changed, contents = function(contents, None, *args)
            has_changed = has_changed | element_changed
    return contents


def json_map_removal(element, subscript):
    if subscript is None:
        return (element is None, None)
    elif subscript in element:
        del element[subscript]
        return (True, None)
    else:
        return (False, None)


def json_remove(path, contents):
    """Remove elements specified in path from contents"""
    return json_map(path, contents, json_map_removal)


def json_map_transform(element, subscript, transform):
    if subscript is None:
        transformed = transform(element)
        return (element != transformed, transformed)
    elif subscript in element:
        transformed = transform(element[subscript])
        original = element[subscript]
        element[subscript] = transformed
        return (original != transformed, transformed)
    else:
        return (False, None)


def json_transform(path, contents, transform):
    """Apply secified transform for path-matching elements in contents"""
    return json_map(path, contents, json_map_transform, transform)


def json_get(path, contents):
    """Retrieve elements specified by path in contents"""
    return [m.current_value for m in json_match(path, contents)]


def json_match(path, contents):
    if isinstance(path, str):
        return [m for m in Path.parse_str(path).match(contents)]
    else:
        return [m for m in path.match(contents)]


if __name__ == "__main__":
    import copy
    from csi.twin.orm import DataBase

    x = Path.parse_str("$..[?(@.data and @.label and @.entries().length() = 2)]")
    db = DataBase("../tests/fixtures/csi-large.db")
    for e in sorted(db.messages(), key=lambda m: m["unix_toi"]):
        print(json_get(str(x), e))
        f = copy.deepcopy(e)
        print(f)
        json_transform(str(x), f, lambda d: d["data"])
        print(f)
        f = copy.deepcopy(e)
        print(f)
        json_remove(str(x), f)
        print(f)
        break
