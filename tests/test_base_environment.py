from typing import Any

from pytest import fixture
from pytest import mark
from utils import EE
from utils import safe_raises

from C41811.Config import EnvironmentConfigData
from C41811.Config import MappingConfigData
from C41811.Config.basic.environment import Difference

type ECD = EnvironmentConfigData
type DIFF = tuple[set[str], set[str]]


class TestDifference:
    @staticmethod
    @fixture
    def diff() -> Difference:
        return Difference({"updated"}, {"removed"})

    @staticmethod
    def test_clear(diff: Difference) -> None:
        diff.clear()
        assert not diff.updated
        assert not diff.removed

    @staticmethod
    def test_bool(diff: Difference) -> None:
        assert diff
        diff.clear()
        assert not diff

    @staticmethod
    @mark.parametrize(
        "other, result, ignore_excs",
        (
            ({"added"}, ({"added", "updated"}, {"removed"}), ()),
            ({"updated"}, ({"updated"}, {"removed"}), ()),
            ({"removed"}, ({"updated", "removed"}, set()), ()),
            (None, (set(), set()), (TypeError,)),
        ),
    )
    def test_iadd(diff: Difference, other: Any, result: DIFF, ignore_excs: EE) -> None:
        with safe_raises(ignore_excs) as info:
            diff += other
        if info:
            return
        assert diff == Difference(*result)

    @staticmethod
    @mark.parametrize(
        "other, result, ignore_excs",
        (
            ({"deleted"}, ({"updated"}, {"removed", "deleted"}), ()),
            ({"removed"}, ({"updated"}, {"removed"}), ()),
            ({"updated"}, (set(), {"removed", "updated"}), ()),
            (None, (set(), set()), (TypeError,)),
        ),
    )
    def test_isub(diff: Difference, other: Any, result: DIFF, ignore_excs: EE) -> None:
        with safe_raises(ignore_excs) as info:
            diff -= other
        if info:
            return
        assert diff == Difference(*result)


class TestEnvironmentConfigData:
    @staticmethod
    def test_init() -> None:
        env = EnvironmentConfigData({"test": "value"})
        assert isinstance(env, MappingConfigData)
        assert not env.difference

    @staticmethod
    @fixture
    def data() -> ECD:
        return EnvironmentConfigData(
            {
                "always": "environ",
            }
        )

    @staticmethod
    @mark.parametrize(
        "path, value, diff",
        (
            ("test", "value", ({"test"}, set())),
            ("always", "value", ({"always"}, set())),
            ("always", "environ", (set(), set())),
        ),
    )
    def test_modify(data: ECD, path: str, value: str, diff: DIFF) -> None:
        diff = Difference(*diff)
        data.modify(path, value)
        assert data.difference == diff

    @staticmethod
    @mark.parametrize("path, diff", (("always", (set(), {"always"})),))
    def test_delete(data: ECD, path: str, diff: DIFF) -> None:
        diff = Difference(*diff)
        data.delete(path)
        assert data.difference == diff

    @staticmethod
    @mark.parametrize(
        "path, diff",
        (
            ("test", (set(), set())),
            ("always", (set(), {"always"})),
        ),
    )
    def test_unset(data: ECD, path: str, diff: DIFF) -> None:
        diff = Difference(*diff)
        data.unset(path)
        assert data.difference == diff

    @staticmethod
    @mark.parametrize(
        "path, value, diff",
        (
            ("test", "value", ({"test"}, set())),
            ("always", "value", (set(), set())),
            ("always", "environ", (set(), set())),
        ),
    )
    def test_setdefault(data: ECD, path: str, value: str, diff: DIFF) -> None:
        diff = Difference(*diff)
        data.setdefault(path, value)
        assert data.difference == diff

    @staticmethod
    @mark.parametrize("diff", ((set(), {"always"}),))
    def test_clear(data: ECD, diff: DIFF) -> None:
        diff = Difference(*diff)
        data.clear()
        assert data.difference == diff

    @staticmethod
    @mark.parametrize("path, diff", (("always", (set(), {"always"})),))
    def test_pop(data: ECD, path: str, diff: DIFF) -> None:
        diff = Difference(*diff)
        data.pop(path)
        assert data.difference == diff

    @staticmethod
    @mark.parametrize("diff", ((set(), {"always"}),))
    def test_popitem(data: ECD, diff: DIFF) -> None:
        diff = Difference(*diff)
        data.popitem()
        assert data.difference == diff

    @staticmethod
    @mark.parametrize(
        "value, diff",
        (
            ({"always": "environ"}, (set(), set())),
            ({"always": "value"}, ({"always"}, set())),
            ({"test": "value", "always": "environ"}, ({"test"}, set())),
            ({"test": "value", "always": "value"}, ({"test", "always"}, set())),
            ({"test": "value"}, ({"test"}, set())),
        ),
    )
    def test_update(data: ECD, value: dict[str, str], diff: DIFF) -> None:
        diff = Difference(*diff)
        data.update(value)
        assert data.difference == diff

    @staticmethod
    @mark.parametrize(
        "key, value, diff",
        (
            ("test", "value", ({"test"}, set())),
            ("always", "value", ({"always"}, set())),
            ("always", "environ", (set(), set())),
        ),
    )
    def test_setitem(data: ECD, key: str, value: str, diff: DIFF) -> None:
        diff = Difference(*diff)
        data[key] = value
        assert data.difference == diff

    @staticmethod
    @mark.parametrize("key, diff", (("always", (set(), {"always"})),))
    def test_delitem(data: ECD, key: str, diff: DIFF) -> None:
        diff = Difference(*diff)
        del data[key]
        assert data.difference == diff

    @staticmethod
    @mark.parametrize(
        "value, diff",
        (
            ({"always": "environ"}, (set(), set())),
            ({"always": "value"}, ({"always"}, set())),
            ({"test": "value", "always": "environ"}, ({"test"}, set())),
            ({"test": "value", "always": "value"}, ({"test", "always"}, set())),
            ({"test": "value"}, ({"test"}, set())),
        ),
    )
    def test_ior(data: ECD, value: dict[str, str], diff: DIFF) -> None:
        diff = Difference(*diff)
        data |= value
        assert data.difference == diff
