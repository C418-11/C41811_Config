# -*- coding: utf-8 -*-

from pytest import fixture
from pytest import mark

from C41811.Config import EnvironmentConfigData
from C41811.Config import MappingConfigData

type ECD = EnvironmentConfigData
type DIFF = tuple[set[str], set[str]]


class TestEnvironmentConfigData:
    @staticmethod
    def test_init() -> None:
        env = EnvironmentConfigData({"test": "value"})
        assert isinstance(env, MappingConfigData)
        assert not env.updated_keys
        assert not env.removed_keys

    @staticmethod
    @fixture
    def data() -> ECD:
        return EnvironmentConfigData({
            "always": "environ",
        })

    @staticmethod
    @mark.parametrize("path, value, diff", (
            ("test", "value", ({"test"}, set())),
            ("always", "value", ({"always"}, set())),
            ("always", "environ", (set(), set())),
    ))
    def test_modify(data: ECD, path: str, value: str, diff: DIFF) -> None:
        data.modify(path, value)
        assert data.updated_keys == diff[0]
        assert data.removed_keys == diff[1]

    @staticmethod
    @mark.parametrize("path, diff", (
            ("always", (set(), {"always"})),
    ))
    def test_delete(data: ECD, path: str, diff: DIFF) -> None:
        data.delete(path)
        assert data.updated_keys == diff[0]
        assert data.removed_keys == diff[1]

    @staticmethod
    @mark.parametrize("path, diff", (
            ("test", (set(), set())),
            ("always", (set(), {"always"})),
    ))
    def test_unset(data: ECD, path: str, diff: DIFF) -> None:
        data.unset(path)
        assert data.updated_keys == diff[0]
        assert data.removed_keys == diff[1]

    @staticmethod
    @mark.parametrize("path, value, diff", (
            ("test", "value", ({"test"}, set())),
            ("always", "value", (set(), set())),
            ("always", "environ", (set(), set())),
    ))
    def test_setdefault(data: ECD, path: str, value: str, diff: DIFF) -> None:
        data.setdefault(path, value)
        assert data.updated_keys == diff[0]
        assert data.removed_keys == diff[1]

    @staticmethod
    @mark.parametrize("diff", (
            (set(), {"always"}),
    ))
    def test_clear(data: ECD, diff: DIFF) -> None:
        data.clear()
        assert data.updated_keys == diff[0]
        assert data.removed_keys == diff[1]

    @staticmethod
    @mark.parametrize("path, diff", (
            ("always", (set(), {"always"})),
    ))
    def test_pop(data: ECD, path: str, diff: DIFF) -> None:
        data.pop(path)
        assert data.updated_keys == diff[0]
        assert data.removed_keys == diff[1]

    @staticmethod
    @mark.parametrize("diff", (
            (set(), {"always"}),
    ))
    def test_popitem(data: ECD, diff: DIFF) -> None:
        data.popitem()
        assert data.updated_keys == diff[0]
        assert data.removed_keys == diff[1]

    @staticmethod
    @mark.parametrize("value, diff", (
            ({"always": "environ"}, (set(), set())),
            ({"always": "value"}, ({"always"}, set())),
            ({"test": "value", "always": "environ"}, ({"test"}, set())),
            ({"test": "value", "always": "value"}, ({"test", "always"}, set())),
            ({"test": "value"}, ({"test"}, set())),
    ))
    def test_update(data: ECD, value: dict[str, str], diff: DIFF) -> None:
        data.update(value)
        assert data.updated_keys == diff[0]
        assert data.removed_keys == diff[1]

    @staticmethod
    @mark.parametrize("key, value, diff", (
            ("test", "value", ({"test"}, set())),
            ("always", "value", ({"always"}, set())),
            ("always", "environ", (set(), set())),
    ))
    def test_setitem(data: ECD, key: str, value: str, diff: DIFF) -> None:
        data[key] = value
        assert data.updated_keys == diff[0]
        assert data.removed_keys == diff[1]

    @staticmethod
    @mark.parametrize("key, diff", (
            ("always", (set(), {"always"})),
    ))
    def test_delitem(data: ECD, key: str, diff: DIFF) -> None:
        del data[key]
        assert data.updated_keys == diff[0]
        assert data.removed_keys == diff[1]

    @staticmethod
    @mark.parametrize("value, diff", (
            ({"always": "environ"}, (set(), set())),
            ({"always": "value"}, ({"always"}, set())),
            ({"test": "value", "always": "environ"}, ({"test"}, set())),
            ({"test": "value", "always": "value"}, ({"test", "always"}, set())),
            ({"test": "value"}, ({"test"}, set())),
    ))
    def test_ior(data: ECD, value: dict[str, str], diff: DIFF) -> None:
        data |= value
        assert data.updated_keys == diff[0]
        assert data.removed_keys == diff[1]
