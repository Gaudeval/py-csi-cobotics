import copy

from csi.transform import json_get, json_match, json_transform, json_remove


class TestJsonGet:
    pass


class TestJsonMatch:
    pass


class TestJsonRemove:
    test_data = {
        "animals": ["cow", "dog", "cat"],
        "countries": {
            "fr": {"name": "France", "continent": "Europe"},
            "mx": {"name": "Mexico", "continent": "America"},
            "jp": {"name": "Japan", "continent": "Asia"},
            "uk": {"name": "United Kingdom", "continent": "Europe"},
        },
        "empty": {"a": {}, "b": {}},
    }

    # single root list
    # single nested list
    # multiple subscripts list
    # recursive removal conflicts (first search returns a deleted element)

    def test_root(self):
        d = copy.deepcopy(self.test_data)
        e = json_remove("$", d)
        assert e is None

    def test_single_root_key(self):
        d = copy.deepcopy(self.test_data)
        json_remove("$.animals", d)
        assert len(d) == len(self.test_data) - 1
        assert "animals" not in d

    def test_single_nested_key(self):
        d = copy.deepcopy(self.test_data)
        json_remove("$.countries.uk", d)
        assert len(d["countries"]) == len(self.test_data["countries"]) - 1
        assert "uk" not in d["countries"]

    def test_multiple_subscripts_keys(self):
        d = copy.deepcopy(self.test_data)
        json_remove("$.countries[*].name", d)
        assert len(d["countries"]) == len(self.test_data["countries"])
        assert all("name" not in d["countries"][c] for c in d["countries"])
        assert all(
            len(d["countries"][c]) == len(self.test_data["countries"][c]) - 1
            for c in d["countries"]
        )

    def test_recursive(self):
        d = copy.deepcopy(self.test_data)
        json_remove("$..[?(@.keys().length() = 0)]", d)
        assert len(d) == len(self.test_data) - 1

    def test_recursive_conflicts(self):
        d = copy.deepcopy(self.test_data)
        json_remove("$[*]..[?(@.keys().length() != 3)]", d)
        assert len(d) == 1


class TestJsonTransform:
    pass
