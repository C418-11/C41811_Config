

from collections.abc import Iterable
from collections.abc import Sequence
from contextlib import suppress
from copy import deepcopy
from typing import Any
from typing import cast

from pyrsistent import pmap
from pytest import fixture
from pytest import mark
from pytest import raises
from utils import EE
from utils import safe_raises

from C41811.Config import ConfigData
from C41811.Config import IndexKey
from C41811.Config import MappingConfigData
from C41811.Config import Path as DPath
from C41811.Config import SequenceConfigData
from C41811.Config import StringConfigData
from C41811.Config.errors import ConfigDataReadOnlyError
from C41811.Config.errors import ConfigDataTypeError
from C41811.Config.errors import RequiredPathNotFoundError

type SCD = SequenceConfigData[Sequence[Any]]
# noinspection SpellCheckingInspection
type RSCD = SequenceConfigData[tuple[Any, ...]]


class TestSequenceConfigData:
    @staticmethod
    @fixture
    def sequence() -> list[Any]:
        return [
            1,
            2,
            {
                "a": [3, 4],
                "b": {
                    "c": 5,
                    "d": 6,
                },
            },
            [7, 8]
        ]

    @staticmethod
    @fixture
    def readonly_sequence(sequence: list[Any]) -> tuple[Any, ...]:
        return tuple(sequence)

    @staticmethod
    @fixture
    def data(sequence: list[Any]) -> SCD:
        return SequenceConfigData(sequence)

    @staticmethod
    @fixture
    def readonly_data(readonly_sequence: tuple[Any, ...]) -> RSCD:
        return SequenceConfigData(readonly_sequence)

    # noinspection PyTestUnpassedFixture
    @staticmethod
    def test_init(sequence: SCD, readonly_sequence: RSCD) -> None:
        data = SequenceConfigData(sequence)
        assert data.data is not sequence
        assert data.data == sequence

        assert SequenceConfigData().data == list()

        readonly_data = SequenceConfigData(readonly_sequence)
        assert readonly_data.data is not readonly_sequence
        assert readonly_data.data == readonly_sequence

    RetrieveTests: tuple[str, tuple[tuple[str, Any, EE, dict[str, Any]], ...]] = (
        "path,           value,                        ignore_excs,                  kwargs", (
        (r"\[0\]", 1, (), {}),
        (r"\[0\]", 1, (), {"return_raw_value": True}),
        (r"\[1\]", 2, (), {}),
        (r"\[2\]\.a", SequenceConfigData([3, 4]), (), {}),
        (r"\[2\]\.a", [3, 4], (), {"return_raw_value": True}),
        (r"\[2\]\.b", MappingConfigData({"c": 5, "d": 6}), (), {}),
        (r"\[2\]\.b", pmap({"c": 5, "d": 6}), (), {"return_raw_value": True}),
        (r"\[2\]\.b\.c", 5, (), {}),
        (r"\[2\]\.b\.c", 5, (), {}),
        (r"\[3\]\[0\]", 7, (), {}),
        (r"\[0\]\.bar", None, (ConfigDataTypeError,), {}),
        (r"\[4\]", None, (RequiredPathNotFoundError,), {}),
        (r"\[3\]\[2\]", None, (RequiredPathNotFoundError,), {}),
        (r"\[3\]\.0", None, (ConfigDataTypeError,), {}),
        (r"bar", None, (ConfigDataTypeError,), {}),
    ))

    @staticmethod
    @mark.parametrize(*RetrieveTests)
    def test_retrieve(data: SCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs):
            assert data.retrieve(path, **kwargs) == value

    ModifyTests: tuple[str, tuple[tuple[str, Any, EE, dict[str, Any]], ...]] = (
        "path, value, ignore_excs, kwargs", (
        (r"\[0\]", 99, (), {}),
        (r"\[2\]", {"z": 9}, (), {}),
        (r"\[1\]", 88, (), {}),
        (r"\[2\]\.a", [9, 0], (), {}),
        ("bar", None, (ConfigDataTypeError,), {}),
        (r"\[3\]", None, (), {}),
        (r"\[4\]", None, (RequiredPathNotFoundError,), {"allow_create": False},),
    ))

    @staticmethod
    @mark.parametrize(*ModifyTests)
    def test_modify(data: SCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs):
            data.modify(path, value, **kwargs)
            assert data.retrieve(path, return_raw_value=True) == value

    DeleteTests: tuple[str, tuple[tuple[str, EE], ...]] = (
        "path, ignore_excs", (
        (r"\[0\]", ()),
        (r"\[1\]", ()),
        (r"\[2\]", ()),
        (r"\[2\]\.a", ()),
        (r"\[2\]\.a\[1\]", ()),
        (r"\[2\]\.b\.c", ()),
        (r"\[3\]\[1\]", ()),
        ("abc", (ConfigDataTypeError,)),
        (r"\[0\]\.a", (ConfigDataTypeError,)),
        (r"\[2\]\[0\]", (ConfigDataTypeError,)),
        (r"\[9\]", (RequiredPathNotFoundError,)),
        (r"\[2\]\.z", (RequiredPathNotFoundError,)),
        (r"\[3\]\[-5\]", (RequiredPathNotFoundError,)),
    ))

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_delete(data: SCD, path: str, ignore_excs: EE) -> None:
        with safe_raises(ignore_excs):
            data.delete(path)
        assert path not in data

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_unset(data: SCD, path: str, ignore_excs: EE) -> None:
        if ignore_excs is None:
            ignore_excs = ()
        elif not isinstance(ignore_excs, Iterable):
            ignore_excs = (ignore_excs,)

        ignore_excs = tuple(exc for exc in ignore_excs if not issubclass(exc, RequiredPathNotFoundError))
        with safe_raises(ignore_excs):
            data.unset(path)
        assert path not in data

    ExistsTests: tuple[str, tuple[tuple[str, bool | None, EE, dict[str, Any]], ...]] = (
        "path, is_exist, ignore_excs, kwargs", (
        (r"\[0\]", True, (), {}),
        (r"\[2\]", True, (), {}),
        (r"\[9\]", False, (), {}),
        (r"\[3\]", True, (), {}),
        (r"\[3\]", True, (), {}),
        (r"\[-6\]", False, (), {}),
        (r"\[3\]\[1\]", True, (), {}),
        (r"\[3\]\[4\]", False, (), {}),
        (r"\[2\]\.b\.c", True, (), {}),
        ("abc", False, (), {"ignore_wrong_type": True}),
        (r"\[3\]\.abc", False, (), {"ignore_wrong_type": True}),
        (r"\[2\]\[1\]", None, (ConfigDataTypeError,), {}),
        (r"\[3\]\.abc", False, (ConfigDataTypeError,), {}),
        (r"abc", False, (ConfigDataTypeError,), {}),
    ))

    @staticmethod
    @mark.parametrize(*ExistsTests)
    def test_exists(data: SCD, path: str, is_exist: bool, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs):
            assert data.exists(path, **kwargs) is is_exist

    GetTests = (
        RetrieveTests[0],
        (
            *RetrieveTests[1],
            # path value ignore_excs kwargs
            (r"\[10\]", "default value", (), {"default": "default value"}),
            (r"\[3\]\[20\]", "default value", (), {"default": "default value"}),
            (r"foo2\\.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
        )
    )

    @staticmethod
    @mark.parametrize(*GetTests)
    def test_get(data: SCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        if ignore_excs is None:
            ignore_excs = ()
        elif not isinstance(ignore_excs, Iterable):
            ignore_excs = (ignore_excs,)

        if kwargs is None:
            kwargs = {}

        if any(issubclass(exc, LookupError) for exc in ignore_excs):
            ignore_excs = tuple(exc for exc in ignore_excs if not issubclass(exc, LookupError))
            value = None

        with safe_raises(ignore_excs):
            assert data.get(path, **kwargs) == value

    SetDefaultTests = (
        RetrieveTests[0],
        (
            *((*x[:3], x[3] | {"return_raw_value": True}) for x in RetrieveTests[1]),
            # path               value            ignore_excs             kwargs
            (r"\[10\]", "default value", (), {"default": "default value"}),
            (r"\[3\]\[20\]", "default value", (), {"default": "default value"}),
            (r"foo2\\.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
        )
    )

    @staticmethod
    @mark.parametrize(*SetDefaultTests)
    def test_set_default(data: SCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        if ignore_excs is None:
            ignore_excs = ()
        elif not isinstance(ignore_excs, Iterable):
            ignore_excs = (ignore_excs,)

        has_index_key = any(isinstance(k, IndexKey) for k in DPath.from_str(path))
        ignore_config_data_type_error = any(issubclass(exc, ConfigDataTypeError) for exc in ignore_excs)

        if has_index_key and (not data.exists(path, ignore_wrong_type=ignore_config_data_type_error)):
            print(f"Skipping test because cannot set default value for non-existent index key: {path}")
            return

        ignore_excs = tuple(exc for exc in ignore_excs if not issubclass(exc, LookupError))
        if "default" in kwargs:
            value = [value, kwargs["default"]]
        else:
            value = value,

        if data.exists(path, ignore_wrong_type=True):
            value = *value, data.retrieve(path)

        with safe_raises(ignore_excs):
            assert data.setdefault(path, **kwargs) in value
            assert data.exists(path)
            assert data.retrieve(path) in value

    GetItemTests: tuple[str, tuple[tuple[int, Any], ...]] = (
        "index, value", (
        (1, 2),
        (2, MappingConfigData({
            "a": [3, 4],
            "b": {
                "c": 5,
                "d": 6,
            },
        })),
        (3, SequenceConfigData([7, 8])),
    ))

    @staticmethod
    @mark.parametrize(*GetItemTests)
    def test_getitem(data: SCD, index: int, value: Any) -> None:
        assert data[index] == value

    @staticmethod
    @mark.parametrize("index, new_value", (
            (0, 456),
            (1, {"test": "value"}),
            (2, 789),
            (3, 101112),
    ))
    def test_setitem(data: SCD, index: int, new_value: Any) -> None:
        data[index] = new_value
        assert (
            cast(SequenceConfigData[Any], data[index]).data == new_value
            if isinstance(data[index], ConfigData) else data[index] == new_value
        )

    @staticmethod
    @mark.parametrize("index, ignore_excs", (
            (1, ()),
            (2, ()),
            (3, ()),
            (4, (IndexError,)),
            (5, (IndexError,)),
    ))
    def test_delitem(data: SCD, index: int, ignore_excs: EE) -> None:
        with safe_raises(ignore_excs):
            last = data[index]
            del data[index]

        with suppress(IndexError):
            assert last != data[index]

    @staticmethod
    @mark.parametrize("item, is_exist", (
            (1, True),
            (888, False),
            (2, True),
            ([7, 8], True),
            ([999], False),
            (r"\[0\]", False),
            ("bar", False),
    ))
    def test_contains(data: SCD, item: Any, is_exist: bool) -> None:
        assert (item in data) == is_exist

    IterTests: tuple[str, tuple[list[Any], ...]] = ("raw_sequence", (
        [],
        [1, 2, 3],
        [1, {2: [3, 4]}, 5],
        [1, 2, [3, [4, 5]], 6],
        [{1: 2, 3: [4, 5, {6: 7}, 8]}, 9, {10: [11, 12]}, 13],
    ))

    @staticmethod
    @mark.parametrize(*IterTests)
    def test_iter(raw_sequence: list[Any]) -> None:
        assert list(iter(SequenceConfigData(raw_sequence))) == list(iter(raw_sequence))

    @staticmethod
    @mark.parametrize(*IterTests)
    def test_str(raw_sequence: list[Any]) -> None:
        assert str(SequenceConfigData(raw_sequence)) == str(raw_sequence)

    @staticmethod
    def test_data_readonly_attr(data: SCD, readonly_data: RSCD) -> None:
        assert readonly_data.data_read_only
        assert not data.data_read_only

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            data.data_read_only = None  # type: ignore[misc, assignment]

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            readonly_data.data_read_only = None  # type: ignore[misc, assignment]

    @staticmethod
    def test_readonly_attr(data: SCD, readonly_data: RSCD) -> None:
        assert readonly_data.read_only
        with raises(ConfigDataReadOnlyError):
            readonly_data.read_only = False

        assert not data.read_only
        data.read_only = True
        assert data.read_only
        with raises(ConfigDataReadOnlyError):
            data.modify(r"\[0\]", 123)

    @staticmethod
    def test_data_attr(data: SCD) -> None:
        last_data = data.data
        data[0] = 456
        assert last_data != data.data

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            data.data = {}  # type: ignore[assignment]

    @classmethod
    @mark.parametrize(*RetrieveTests)
    def test_readonly_retrieve(
            cls,
            readonly_data: RSCD,
            path: str,
            value: Any,
            ignore_excs: EE,
            kwargs: dict[str, Any],
    ) -> None:
        cls.test_retrieve(readonly_data, path, value, ignore_excs, kwargs)

    ReadOnlyModifyTests = (
        ','.join(arg for arg in ModifyTests[0].split(',') if "ignore_excs" not in arg),
        ((*x[:-2], x[-1]) for x in ModifyTests[1])
    )

    @classmethod
    @mark.parametrize(*ReadOnlyModifyTests)
    def test_readonly_modify(cls, readonly_data: RSCD, path: str, value: Any, kwargs: dict[str, Any]) -> None:
        cls.test_modify(readonly_data, path, value, ConfigDataReadOnlyError, kwargs)

    ReadOnlyDeleteTests = (
        ', '.join(arg for arg in DeleteTests[0].split(', ') if "ignore_excs" not in arg),
        tuple(x[:-1] for x in DeleteTests[1])
    )

    @classmethod
    @mark.parametrize(*ReadOnlyDeleteTests)
    def test_readonly_delete(cls, readonly_data: RSCD, path: str) -> None:
        cls.test_delete(cast(SCD, readonly_data), path, ConfigDataReadOnlyError)

    @classmethod
    @mark.parametrize(*ReadOnlyDeleteTests)
    def test_readonly_unset(cls, readonly_data: RSCD, path: str) -> None:
        cls.test_unset(cast(SCD, readonly_data), path, (ConfigDataReadOnlyError,))

    @staticmethod
    @mark.parametrize("method, data, args, readonly", (
            ("append", [], (123,), False),
            ("append", [1, 2, 3], (123,), False),
            ("append", [1, {2: [3, 4]}, 5], (123,), False),
            ("append", (1, {2: [3, 4]}, 5), (123,), True),
            ("insert", [], (123, 0), False),
            ("insert", [1, 2, 3], (123, 0), False),
            ("insert", [1, 2, 3], (123, 2), False),
            ("insert", [1, {2: [3, 4]}, 5], (123, -1), False),
            ("insert", (1, {2: [3, 4]}, 5), (123, 0), True),
            ("extend", [], ([123],), False),
            ("extend", [1, 2, 3], ([123],), False),
            ("extend", [1, {2: [3, 4]}, 5], ([123],), False),
            ("extend", (1, {2: [3, 4]}, 5), ([123],), True),
            ("index", [1, 2, 3], (3,), False),
            ("index", [9, 10, 11, 12, 13], (12, 2, -1), False),
            ("index", (9, 10), (9,), False),
            ("count", [1, 2, 3, 2, 1], (2,), False),
            ("count", (3, 2, 1, 4, 3), (2,), False),
            ("pop", [1, 2, 3], (), False),
            ("pop", [1, 2, 3], (0,), False),
            ("pop", [1, 2, 3], (-2,), False),
            ("pop", (1, 2, 3), (), True),
            ("remove", [1, 2, 3], (2,), False),
            ("remove", (1, 2, 3), (2,), True),
            ("clear", [1, 2, 3], (), False),
            ("clear", (1, 2, 3), (), True),
            ("reverse", [1, 2, 3], (), False),
            ("reverse", (1, 2, 3), (), True),
    ))
    def test_methods(method: str, data: SCD, args: tuple[Any, ...], readonly: RSCD) -> None:
        cfg = SequenceConfigData(deepcopy(data))

        excs = (ConfigDataReadOnlyError,) if readonly else ()
        with safe_raises(excs) as info:
            result = getattr(cfg, method)(*args)
        if info:
            return
        assert result == getattr(data, method)(*args)
        assert cfg.data == data

    @staticmethod
    def test_reversed(data: SCD, readonly_data: RSCD) -> None:
        assert list(reversed(data)) == list(reversed(data))

    @staticmethod
    def test_eq(data: SCD, readonly_data: RSCD) -> None:
        assert data == data
        assert data == deepcopy(data)
        assert readonly_data == readonly_data
        assert readonly_data == deepcopy(readonly_data)

    @staticmethod
    def test_deepcopy(data: SCD) -> None:
        last_data = deepcopy(data)
        data[0] = 456
        assert last_data != data

    @staticmethod
    def test_repr(data: SCD) -> None:
        assert repr(data.data) in repr(data)
        assert repr({"a": 1, "b": 2}) in repr(MappingConfigData({"a": 1, "b": 2}))


class TestStringConfigData:
    @staticmethod
    def test_init() -> None:
        assert StringConfigData().data == ""

    @staticmethod
    @mark.parametrize("string, format_spec", (
            ("test", "<5"),
            ("test", ">9"),
            ("test", "^7"),
    ))
    def test_format(string: str, format_spec: str) -> None:
        assert format(StringConfigData(string), format_spec) == format(string, format_spec)

    @staticmethod
    @mark.parametrize("string, slice_obj", (
            ("test", slice(0, 2)),
            ("test", slice(None, None, -1)),
            ("test", slice(1)),
            ("test", slice(None, -2)),
            ("test", slice(None, None, 2)),
    ))
    def test_slice(string: str, slice_obj: slice) -> None:
        assert StringConfigData(string)[slice_obj] == string[slice_obj]
        cfg, cs = StringConfigData(string), deepcopy(string)

        with raises(TypeError):
            cs[slice_obj] = "X"  # type: ignore[index]
        with raises(TypeError):
            del cs[slice_obj]  # type: ignore[attr-defined]

        with raises(TypeError):
            cfg[slice_obj] = "X"
        with raises(TypeError):
            del cfg[slice_obj]

    @staticmethod
    @mark.parametrize("string", (
            "test",
            "abba",
            "abcd",
    ))
    def test_reversed(string: str) -> None:
        assert list(reversed(StringConfigData(string))) == list(reversed(string))

    @staticmethod
    @mark.parametrize("data, string, result", (
            ("test", "test", True),
            ("test", "TEST", False),
            ("test", "t", True),
            ("aabb", "ab", True),
    ))
    def test_contains(data: str, string: str, result: bool) -> None:
        data = StringConfigData(data)
        assert (string in data) is result

    @staticmethod
    @mark.parametrize("string", (
            "123456",
            "aabbcc",
    ))
    def test_iter(string: str) -> None:
        data = StringConfigData(string)
        assert list(data) == list(string)

    @staticmethod
    @mark.parametrize("string", (
            "123456",
            "aabb",
    ))
    def test_len(string: str) -> None:
        data = StringConfigData(string)
        assert len(data) == len(string)
