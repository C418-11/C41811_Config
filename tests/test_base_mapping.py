from collections import OrderedDict
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import Mapping
from copy import deepcopy
from typing import Any
from typing import cast

from pyrsistent import PMap
from pyrsistent import pmap
from pytest import fixture
from pytest import mark
from pytest import raises
from utils import EE
from utils import safe_raises

from c41811.config import ConfigData
from c41811.config import IndexKey
from c41811.config import MappingConfigData
from c41811.config import Path as DPath
from c41811.config import SequenceConfigData
from c41811.config.errors import ConfigDataReadOnlyError
from c41811.config.errors import ConfigDataTypeError
from c41811.config.errors import CyclicReferenceError
from c41811.config.errors import RequiredPathNotFoundError
from c41811.config.utils import Unset

type OD = OrderedDict[str, Any]
type ROD = PMap[str, Any]
type M_MCD = MappingConfigData[Mapping[Any, Any]]
type R_MCD = MappingConfigData[ROD]


class TestMappingConfigData:
    @staticmethod
    @fixture
    def odict() -> OD:
        return OrderedDict(
            (
                ("foo", OrderedDict((("bar", 123),))),
                ("foo1", 114),
                ("foo2", ["bar"]),
                (
                    "a",
                    {
                        "b": 1,
                        "c": {
                            "d": 2,
                            "e": {
                                "f": 3,
                            },
                        },
                    },
                ),
                (r"\\.\[\]", None),
            )
        )

    @staticmethod
    @fixture
    def data(odict: OD) -> M_MCD:
        return MappingConfigData(odict)

    @staticmethod
    @fixture
    def readonly_odict(odict: OD) -> ROD:
        return pmap(odict)

    @staticmethod
    @fixture
    def readonly_data(readonly_odict: ROD) -> R_MCD:
        return MappingConfigData(readonly_odict)

    # noinspection PyTestUnpassedFixture
    @staticmethod
    def test_init(odict: OD, readonly_odict: ROD) -> None:
        data = MappingConfigData(odict)
        assert data.data is not odict
        assert data.data == odict

        assert MappingConfigData().data == {}

        readonly_data = MappingConfigData(readonly_odict)
        assert readonly_data.data is not readonly_odict
        assert readonly_data.data == readonly_odict

    RetrieveTests: tuple[str, tuple[tuple[str, Any, EE, dict[str, Any]], ...]] = (
        "path, value, ignore_excs, kwargs",
        (
            ("foo", MappingConfigData({"bar": 123}), (), {}),
            ("foo", {"bar": 123}, (), {"return_raw_value": True}),
            ("foo\\.bar", 123, (), {}),
            ("foo1", 114, (), {}),
            ("foo2", ["bar"], (), {"return_raw_value": True}),
            ("foo2\\[0\\]", "bar", (), {}),
            ("foo2\\.bar", None, (ConfigDataTypeError,), {}),
            ("foo3", None, (RequiredPathNotFoundError,), {}),
            ("foo2\\[1\\]", None, (RequiredPathNotFoundError,), {}),
            ("foo\\[0\\]", None, (ConfigDataTypeError,), {}),
            ("\\[0\\]", None, (ConfigDataTypeError,), {}),
        ),
    )

    @staticmethod
    @mark.parametrize(*RetrieveTests)
    def test_retrieve(data: M_MCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs):
            assert data.retrieve(path, **kwargs) == value

    ModifyTests: tuple[str, tuple[tuple[str, Any, EE, dict[str, Any]], ...]] = (
        "path, value, ignore_excs, kwargs",
        (
            ("foo", {"bar": 456}, (), {}),
            ("foo\\.bar", 123, (), {}),
            ("foo1", 114, (), {}),
            ("foo2", ["bar"], (), {}),
            ("foo2\\.bar", None, (ConfigDataTypeError,), {}),
            ("foo3", None, (), {}),
            (
                "foo3",
                None,
                (RequiredPathNotFoundError,),
                {"allow_create": False},
            ),
        ),
    )

    @staticmethod
    @mark.parametrize(*ModifyTests)
    def test_modify(data: M_MCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs) as info:
            data.modify(path, value, **kwargs)
        if info:
            return
        assert data.retrieve(path, return_raw_value=True) == value

    DeleteTests: tuple[str, tuple[tuple[str, EE], ...]] = (
        "path, ignore_excs",
        (
            ("foo\\.bar", ()),
            ("foo1", ()),
            ("foo2", ()),
            ("foo2\\[0\\]", ()),
            ("foo2\\[-1\\]", ()),
            ("\\[0\\]", (ConfigDataTypeError,)),
            ("foo\\[0\\]", (ConfigDataTypeError,)),
            ("foo2\\.bar", (ConfigDataTypeError,)),
            ("foo2\\[1\\]", (RequiredPathNotFoundError,)),
            ("foo2\\[-2\\]", (RequiredPathNotFoundError,)),
            ("foo3", (RequiredPathNotFoundError,)),
        ),
    )

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_delete(data: M_MCD, path: str, ignore_excs: EE) -> None:
        with safe_raises(ignore_excs):
            data.delete(path)
        assert path not in data

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_unset(data: M_MCD, path: str, ignore_excs: EE) -> None:
        if ignore_excs is None:
            ignore_excs = ()
        elif not isinstance(ignore_excs, Iterable):
            ignore_excs = (ignore_excs,)

        ignore_excs = tuple(exc for exc in ignore_excs if not issubclass(exc, RequiredPathNotFoundError))
        with safe_raises(ignore_excs):
            data.unset(path)
        assert path not in data

    ExistsTests: tuple[str, tuple[tuple[str, bool | None, EE, dict[str, Any]], ...]] = (
        "path, is_exist, ignore_excs, kwargs",
        (
            ("foo", True, (), {}),
            ("foo\\.bar", True, (), {}),
            ("foo\\.not exist", False, (), {}),
            ("foo1", True, (), {}),
            ("foo2", True, (), {}),
            ("foo3", False, (), {}),
            ("foo2\\[0\\]", True, (), {}),
            ("foo2\\[1\\]", False, (), {}),
            ("foo2\\[-1\\]", True, (), {}),
            ("foo2\\.bar", False, (), {"ignore_wrong_type": True}),
            ("\\[0\\]", False, (), {"ignore_wrong_type": True}),
            ("foo2\\.bar", None, (ConfigDataTypeError,), {}),
            ("foo\\[0\\]", False, (ConfigDataTypeError,), {}),
            ("\\[0\\]", False, (ConfigDataTypeError,), {}),
        ),
    )

    @staticmethod
    @mark.parametrize(*ExistsTests)
    def test_exists(data: M_MCD, path: str, is_exist: bool, ignore_excs: EE, kwargs: dict[str, Any]) -> None:  # noqa: FBT001
        with safe_raises(ignore_excs):
            assert data.exists(path, **kwargs) is is_exist

    GetTests: tuple[str, tuple[tuple[str, Any, EE, dict[str, Any]], ...]] = (
        RetrieveTests[0],
        (
            *RetrieveTests[1],
            # path               value            ignore_excs             kwargs
            ("not exist", "default value", (), {"default": "default value"}),
            ("foo.not exist", "default value", (), {"default": "default value"}),
            ("foo2\\.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
        ),
    )

    @staticmethod
    @mark.parametrize(*GetTests)
    def test_get(data: M_MCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
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

    SetDefaultTests: tuple[str, tuple[tuple[str, Any, EE, dict[str, Any]], ...]] = (
        RetrieveTests[0],
        (
            *((*x[:3], x[3] | {"return_raw_value": True}) for x in RetrieveTests[1]),
            # path               value            ignore_excs             kwargs
            ("not exist", "default value", (), {"default": "default value"}),
            ("foo\\.not exist", "default value", (), {"default": "default value"}),
            ("foo2\\.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
        ),
    )

    @staticmethod
    @mark.parametrize(*GetTests)
    def test_set_default(data: M_MCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        if ignore_excs is None:
            ignore_excs = ()
        elif not isinstance(ignore_excs, Iterable):
            ignore_excs = (ignore_excs,)

        has_index_key = any(isinstance(k, IndexKey) for k in DPath.from_str(path))
        ignore_config_data_type_error = any(issubclass(exc, ConfigDataTypeError) for exc in ignore_excs)

        if has_index_key and (not data.exists(path, ignore_wrong_type=ignore_config_data_type_error)):
            print(f"Skipping test because cannot set default value for non-existent index key: {path}")  # noqa: T201
            return

        ignore_excs = tuple(exc for exc in ignore_excs if not issubclass(exc, LookupError))
        value = [value, kwargs["default"]] if "default" in kwargs else (value,)

        if data.exists(path, ignore_wrong_type=True):
            value = *value, data.retrieve(path)

        with safe_raises(ignore_excs):
            assert data.setdefault(path, **kwargs) in value
            assert data.exists(path)
            assert data.retrieve(path) in value

    GetItemTests = (
        "path, value",
        (
            (
                "foo",
                MappingConfigData({"bar": 123}),
            ),
            (
                "foo1",
                114,
            ),
            (
                "foo2",
                SequenceConfigData(["bar"]),
            ),
        ),
    )

    @staticmethod
    @mark.parametrize(*GetItemTests)
    def test_getitem(data: M_MCD, path: str, value: Any) -> None:
        assert data[path] == value

    @staticmethod
    @mark.parametrize(*GetItemTests)
    def test_getattr(data: M_MCD, path: str, value: Any) -> None:
        assert getattr(data, path) == value

    @staticmethod
    @mark.parametrize(
        "path, new_value",
        (
            ("foo.bar", 456),
            ("foo2", {"test": "value"}),
            ("foo3", 789),
            ("foo4.bar", 101112),
        ),
    )
    def test_setitem(data: M_MCD, path: str, new_value: Any) -> None:
        data[path] = new_value
        assert path in data
        assert (
            cast(MappingConfigData[Any], data[path]).data == new_value
            if isinstance(data[path], ConfigData)
            else data[path] == new_value
        )

    @staticmethod
    @mark.parametrize(
        "path, ignore_excs",
        (
            ("foo", ()),
            ("foo1", ()),
            ("foo2", ()),
            ("foo2\\.bar", (KeyError,)),
            ("foo3", (KeyError,)),
        ),
    )
    def test_delitem(data: M_MCD, path: str, ignore_excs: EE) -> None:
        with safe_raises(ignore_excs):
            del data[path]
        assert path not in data

    @staticmethod
    @mark.parametrize(
        "path, is_exist",
        (
            ("foo", True),
            ("foo\\.bar", False),
            ("foo\\.not exist", False),
            ("foo1", True),
            ("foo2", True),
            ("foo2\\.bar", False),
            ("foo3", False),
        ),
    )
    def test_contains(data: M_MCD, path: str, is_exist: bool) -> None:  # noqa: FBT001
        assert (path in data) == is_exist

    IterTests: tuple[str, tuple[dict[str, Any], ...]] = (
        "raw_dict",
        (
            {},
            {"foo": "bar"},
            {"foo": "bar", "foo\\.bar": "bar"},
            {"foo": "bar", "foo\\.bar": "bar", "foo1": "bar"},
            {"foo": "bar", "foo\\.bar": "bar", "foo1": "bar", "foo2": ["bar"]},
        ),
    )

    @staticmethod
    @mark.parametrize(*IterTests)
    def test_iter(raw_dict: OD) -> None:
        assert list(iter(MappingConfigData(raw_dict))) == list(iter(raw_dict))

    @staticmethod
    @mark.parametrize(*IterTests)
    def test_str(raw_dict: OD) -> None:
        assert str(MappingConfigData(raw_dict)) == str(raw_dict)

    @staticmethod
    def test_data_readonly_attr(data: M_MCD, readonly_data: R_MCD) -> None:
        assert readonly_data.data_read_only
        assert not data.data_read_only

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            data.data_read_only = None  # type: ignore[misc, assignment]

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            readonly_data.data_read_only = None  # type: ignore[misc, assignment]

    @staticmethod
    def test_readonly_attr(data: M_MCD, readonly_data: R_MCD) -> None:
        assert readonly_data.read_only
        with raises(ConfigDataReadOnlyError):
            readonly_data.read_only = False

        assert not data.read_only
        data.read_only = True
        assert data.read_only
        with raises(ConfigDataReadOnlyError):
            data.modify("new_key", 123)

    @staticmethod
    def test_data_attr(data: M_MCD) -> None:
        last_data = data.data
        data["foo.bar"] = 456
        assert last_data != data.data

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            data.data = {}

    @classmethod
    @mark.parametrize(*RetrieveTests)
    def test_readonly_retrieve(
        cls,
        readonly_data: R_MCD,
        path: str,
        value: Any,
        ignore_excs: EE,
        kwargs: dict[str, Any],
    ) -> None:
        cls.test_retrieve(cast(M_MCD, readonly_data), path, value, ignore_excs, kwargs)

    ReadOnlyModifyTests: tuple[str, Generator[tuple[str, Any, dict[str, Any]], Any, None]] = (
        # 从中剔除ignore_excs参数
        ",".join(arg for arg in ModifyTests[0].split(",") if "ignore_excs" not in arg),
        ((*x[:-2], x[-1]) for x in ModifyTests[1]),
    )

    @classmethod
    @mark.parametrize(*ReadOnlyModifyTests)
    def test_readonly_modify(cls, readonly_data: R_MCD, path: str, value: Any, kwargs: dict[str, Any]) -> None:
        cls.test_modify(cast(M_MCD, readonly_data), path, value, ConfigDataReadOnlyError, kwargs)

    ReadOnlyDeleteTests: tuple[str, tuple[tuple[str], ...]] = (
        # 从中剔除ignore_excs参数
        ", ".join(arg for arg in DeleteTests[0].split(", ") if "ignore_excs" not in arg),
        tuple(x[:-1] for x in DeleteTests[1]),
    )

    @classmethod
    @mark.parametrize(*ReadOnlyDeleteTests)
    def test_readonly_delete(cls, readonly_data: R_MCD, path: str) -> None:
        cls.test_delete(cast(M_MCD, readonly_data), path, ConfigDataReadOnlyError)

    @classmethod
    @mark.parametrize(*ReadOnlyDeleteTests)
    def test_readonly_unset(cls, readonly_data: R_MCD, path: str) -> None:
        cls.test_unset(cast(M_MCD, readonly_data), path, (ConfigDataReadOnlyError,))

    @staticmethod
    def test_eq(data: M_MCD, readonly_data: R_MCD) -> None:
        assert data == data
        assert data == deepcopy(data)
        assert readonly_data == readonly_data
        assert readonly_data == deepcopy(readonly_data)
        assert data == readonly_data

    @staticmethod
    def test_deepcopy(data: M_MCD) -> None:
        last_data = deepcopy(data)
        data["foo.bar"] = 456
        assert last_data != data

    KeysTests: tuple[str, tuple[tuple[dict[Any, Any], set[str]], ...]] = (
        "kwargs, keys",
        (
            ({}, {"a", "foo", "foo1", "foo2", r"\\.\[\]"}),
            (
                {"recursive": True},
                {
                    r"a\.c\.e\.f",
                    r"a\.c",
                    "a",
                    r"a\.c\.d",
                    r"foo\.bar",
                    r"a\.c\.e",
                    "foo",
                    "foo1",
                    r"a\.b",
                    "foo2",
                    r"\\\\.\\[\\]",
                },
            ),
            ({"end_point_only": True}, {"foo1", "foo2", r"\\\\.\\[\\]"}),
            (
                {"recursive": True, "end_point_only": True},
                {r"a\.c\.d", r"foo\.bar", "foo2", r"a\.b", r"a\.c\.e\.f", "foo1", r"\\\\.\\[\\]"},
            ),
        ),
    )

    @staticmethod
    @mark.parametrize(*KeysTests)
    def test_keys(data: M_MCD, kwargs: dict[str, Any], keys: set[str]) -> None:
        assert set(data.keys(**kwargs)) == keys

    @staticmethod
    def cyclic_reference_datas() -> tuple[dict[str, Any], ...]:
        c: dict[str, Any] = {"A": None}
        b = {"C": c}
        d = {"C": c}
        a = {"B": b, "D": d}
        c["A"] = a
        return a, b, c, d

    CyclicReferenceTests: tuple[
        str,
        tuple[
            tuple[
                dict[Any, Any],
                dict[str, Any],
                set[str] | None,
                EE,
            ],
            ...,
        ],
    ] = (
        "data, kwargs, keys, ignore_excs",
        (
            (cyclic_reference_datas()[0], {}, {"B", "D"}, ()),
            (cyclic_reference_datas()[1], {}, {"C"}, ()),
            (cyclic_reference_datas()[2], {}, {"A"}, ()),
            (cyclic_reference_datas()[3], {}, {"C"}, ()),
            (cyclic_reference_datas()[0], {"end_point_only": True}, set(), ()),
            (
                cyclic_reference_datas()[0],
                {"recursive": True, "strict": False},
                {r"D\.C", r"D\.C\.A", r"B\.C", "D", "B", r"B\.C\.A"},
                (),
            ),
            (
                cyclic_reference_datas()[1],
                {"recursive": True, "strict": False},
                {r"C\.A", "C", r"C\.A\.D\.C", r"C\.A\.B", r"C\.A\.D"},
                (),
            ),
            (
                cyclic_reference_datas()[2],
                {"recursive": True, "strict": False},
                {r"A\.B\.C", r"A\.D", r"A\.B", r"A\.D\.C", "A"},
                (),
            ),
            (
                cyclic_reference_datas()[3],
                {"recursive": True, "strict": False},
                {r"C\.A", "C", r"C\.A\.B\.C", r"C\.A\.B", r"C\.A\.D"},
                (),
            ),
            (cyclic_reference_datas()[0], {"recursive": True, "strict": True}, None, (CyclicReferenceError,)),
            (cyclic_reference_datas()[0], {"recursive": True, "end_point_only": True}, None, (CyclicReferenceError,)),
            (cyclic_reference_datas()[0], {"recursive": True}, None, (CyclicReferenceError,)),
            (cyclic_reference_datas()[1], {"recursive": True}, None, (CyclicReferenceError,)),
            (cyclic_reference_datas()[2], {"recursive": True}, None, (CyclicReferenceError,)),
            (cyclic_reference_datas()[3], {"recursive": True}, None, (CyclicReferenceError,)),
        ),
    )

    @staticmethod
    @mark.parametrize(*CyclicReferenceTests)
    def test_cyclic_reference_keys(
        data: dict[str, Any], kwargs: dict[str, Any], keys: set[str], ignore_excs: EE
    ) -> None:
        data = MappingConfigData(data)
        with safe_raises(ignore_excs):
            assert set(data.keys(**kwargs)) == keys

    @staticmethod
    def test_keys_with_wrong_data() -> None:
        data: MappingConfigData[Any] = MappingConfigData({123: {}})
        with raises(TypeError):
            data.keys(recursive=True)

    ValuesTests: tuple[str, tuple[tuple[dict[Any, Any], list[Any]], ...]] = (
        "kwargs, values",
        (
            (
                {},
                [
                    MappingConfigData({"bar": 123}),
                    114,
                    ["bar"],
                    MappingConfigData({"b": 1, "c": {"d": 2, "e": {"f": 3}}}),
                    None,
                ],
            ),
            ({"return_raw_value": True}, [{"bar": 123}, 114, ["bar"], {"b": 1, "c": {"d": 2, "e": {"f": 3}}}, None]),
        ),
    )

    @staticmethod
    @mark.parametrize(*ValuesTests)
    def test_values(data: M_MCD, kwargs: dict[str, Any], values: Any) -> None:
        assert list(data.values(**kwargs)) == values

    ItemsTests: tuple[str, tuple[tuple[dict[Any, Any], list[tuple[Any, Any]]], ...]] = (
        "kwargs, items",
        (
            (
                {},
                [
                    ("foo", MappingConfigData({"bar": 123})),
                    ("foo1", 114),
                    ("foo2", ["bar"]),
                    ("a", MappingConfigData({"b": 1, "c": {"d": 2, "e": {"f": 3}}})),
                    (r"\\.\[\]", None),
                ],
            ),
            (
                {"return_raw_value": True},
                [
                    ("foo", {"bar": 123}),
                    ("foo1", 114),
                    ("foo2", ["bar"]),
                    ("a", {"b": 1, "c": {"d": 2, "e": {"f": 3}}}),
                    (r"\\.\[\]", None),
                ],
            ),
        ),
    )

    @staticmethod
    @mark.parametrize(*ItemsTests)
    def test_items(data: M_MCD, kwargs: dict[str, Any], items: list[tuple[str, Any]]) -> None:
        assert list(data.items(**kwargs)) == items

    @staticmethod
    @mark.parametrize(
        "data",
        (
            {123: {"abc", "zzz"}},
            {"key": "value"},
        ),
    )
    def test_clear(data: dict[Any, Any]) -> None:
        data = MappingConfigData(data)
        data.clear()
        assert not data

    @staticmethod
    @mark.parametrize(
        "data",
        (
            {"a": 1, "b": 2},
            {"a": 1, "b": 2, "c": 3},
        ),
    )
    def test_popitem(data: dict[Any, Any]) -> None:
        data = MappingConfigData(data)
        items = data.items()
        popped = data.popitem()
        assert popped in items
        assert popped not in data.items()

    @staticmethod
    @mark.parametrize(
        "dct, key, result, ignore_excs",
        (
            ({"a": 1}, "a", 1, ()),
            ({"a": 1, "b": 2}, "b", 2, ()),
            ({"a": 1}, "b", Unset, (RequiredPathNotFoundError,)),
        ),
    )
    def test_pop(dct: dict[Any, Any], key: str, result: Any, ignore_excs: EE) -> None:
        data = MappingConfigData(dct)
        with safe_raises(ignore_excs) as info:
            assert data.pop(key) == result
        if info:
            return
        assert key not in data

    @staticmethod
    @mark.parametrize(
        "dct, key, default, result, ignore_excs",
        (
            ({"a": 1}, "a", 2, 1, ()),
            ({"a": 1, "b": 2}, "b", 3, 2, ()),
            ({"a": 1}, "b", 2, 2, ()),
            ({"a": 1}, "c", 5, 5, ()),
        ),
    )
    def test_pop_default(dct: dict[str, Any], key: str, default: Any, result: Any, ignore_excs: EE) -> None:
        data = MappingConfigData(dct)
        with safe_raises(ignore_excs) as info:
            assert data.pop(key, default) == result
        if info:
            return
        assert key not in data

    @staticmethod
    @mark.parametrize(
        "data, mapping, result",
        (
            ({"a": 1}, {"a": 2}, {"a": 2}),
            ({"a": 1}, {"b": 2}, {"a": 1, "b": 2}),
            ({"a": 1, "d": 4}, {"a": 2, "b": 3}, {"a": 2, "b": 3, "d": 4}),
        ),
    )
    def test_update(data: dict[str, Any], mapping: Mapping[str, Any], result: Any) -> None:
        cfg = MappingConfigData(data)
        cfg.update(**mapping)
        assert cfg == MappingConfigData(result)

        cfg = MappingConfigData(data)
        cfg.update(mapping)
        assert cfg == MappingConfigData(result)

    @staticmethod
    def test_repr(data: M_MCD) -> None:
        assert repr(data.data) in repr(data)
        assert repr({"a": 1, "b": 2}) in repr(MappingConfigData({"a": 1, "b": 2}))

    @staticmethod
    def test_format() -> None:
        assert repr(MappingConfigData({"a": 1, "b": 2})) == format(MappingConfigData({"a": 1, "b": 2}), "r")
        with raises(TypeError):
            format(MappingConfigData({"a": 1, "b": 2}), "not exists")
