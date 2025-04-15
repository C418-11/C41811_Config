# -*- coding: utf-8 -*-


import functools
import itertools
import math
import operator
from collections import OrderedDict
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import Sequence
from contextlib import suppress
from copy import deepcopy
from numbers import Number
from pathlib import Path as FPath
from typing import Any
from typing import ClassVar
from typing import Optional
from typing import cast

from pyrsistent import PMap
from pyrsistent import pmap
from pytest import fixture
from pytest import mark
from pytest import raises

from C41811.Config import BoolConfigData
from C41811.Config import ComponentConfigData
from C41811.Config import ComponentMember
from C41811.Config import ComponentMeta
from C41811.Config import ConfigData
from C41811.Config import ConfigFile
from C41811.Config import ConfigPool
from C41811.Config import IndexKey
from C41811.Config import MappingConfigData
from C41811.Config import NoneConfigData
from C41811.Config import NumberConfigData
from C41811.Config import ObjectConfigData
from C41811.Config import Path as DPath
from C41811.Config import SequenceConfigData
from C41811.Config import StringConfigData
from C41811.Config.abc import ABCIndexedConfigData
from C41811.Config.errors import ConfigDataReadOnlyError
from C41811.Config.errors import ConfigDataTypeError
from C41811.Config.errors import CyclicReferenceError
from C41811.Config.errors import RequiredPathNotFoundError
from C41811.Config.errors import UnsupportedConfigFormatError
from C41811.Config.processor.Component import ComponentMetaParser
from C41811.Config.utils import Unset
from utils import EE
from utils import safe_raises


def test_none_config_data() -> None:
    assert not NoneConfigData()

    with raises(ValueError):
        # noinspection PyTypeChecker
        NoneConfigData(NotImplemented)  # type: ignore[arg-type]


type OD = OrderedDict[str, Any]
type ROD = PMap[str, Any]
type M_MCD = MappingConfigData[Mapping[Any, Any]]
type R_MCD = MappingConfigData[ROD]


class TestMappingConfigData:

    @staticmethod
    @fixture
    def odict() -> OD:
        return OrderedDict((
            ("foo", OrderedDict((
                ("bar", 123),
            ))),
            ("foo1", 114),
            ("foo2", ["bar"]),
            ('a', {
                'b': 1,
                'c': {
                    'd': 2,
                    'e': {
                        'f': 3,
                    },
                }
            }),
            (r"\\.\[\]", None),
        ))

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

        assert MappingConfigData().data == dict()

        readonly_data = MappingConfigData(readonly_odict)
        assert readonly_data.data is not readonly_odict
        assert readonly_data.data == readonly_odict

    RetrieveTests: tuple[str, tuple[tuple[str, Any, EE, dict[str, Any]], ...]] = (
        "path,          value,                    ignore_excs,                  kwargs", (  # @formatter:off # noqa: E122, E501
        ("foo",         MappingConfigData({"bar": 123}), (),                           {}),  # noqa: E122
        ("foo",         {"bar": 123},             (),                           {"return_raw_value": True}),  # noqa: E122, E501
        ("foo\\.bar",   123,                      (),                           {}),  # noqa: E122
        ("foo1",        114,                      (),                           {}),  # noqa: E122
        ("foo2",        ["bar"],                  (),                           {"return_raw_value": True}),  # noqa: E122, E501
        ("foo2\\[0\\]", "bar",                    (),                           {}),  # noqa: E122
        ("foo2\\.bar",  None,                     (ConfigDataTypeError, ),      {}),  # noqa: E122
        ("foo3",        None,                     (RequiredPathNotFoundError,), {}),  # noqa: E122
        ("foo2\\[1\\]", None,                     (RequiredPathNotFoundError,), {}),  # noqa: E122
        ("foo\\[0\\]",  None,                     (ConfigDataTypeError,),       {}),  # noqa: E122
        ("\\[0\\]",     None,                     (ConfigDataTypeError,),       {}),  # noqa: E122
    ))  # @formatter:on # noqa: E122

    @staticmethod
    @mark.parametrize(*RetrieveTests)
    def test_retrieve(data: M_MCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs):
            assert data.retrieve(path, **kwargs) == value

    ModifyTests: tuple[str, tuple[tuple[str, Any, EE, dict[str, Any]], ...]] = (
        "path,         value,        ignore_excs,                  kwargs", (  # @formatter:off # noqa: E122
        ("foo",        {"bar": 456}, (),                           {}),  # noqa: E122
        ("foo\\.bar",  123,          (),                           {}),  # noqa: E122
        ("foo1",       114,          (),                           {}),  # noqa: E122
        ("foo2",       ["bar"],      (),                           {}),  # noqa: E122
        ("foo2\\.bar", None,         (ConfigDataTypeError,),       {}),  # noqa: E122
        ("foo3",       None,         (),                           {}),  # noqa: E122
        ("foo3",       None,         (RequiredPathNotFoundError,), {"allow_create": False}, ),  # noqa: E122
    ))  # @formatter:on # noqa: E122

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
        "path,           ignore_excs", (  # @formatter:off # noqa: E122
        ("foo\\.bar",    ()),  # noqa: E122
        ("foo1",         ()),  # noqa: E122
        ("foo2",         ()),  # noqa: E122
        ("foo2\\[0\\]",  ()),  # noqa: E122
        ("foo2\\[-1\\]", ()),  # noqa: E122
        ("\\[0\\]",      (ConfigDataTypeError,)),  # noqa: E122
        ("foo\\[0\\]",   (ConfigDataTypeError,)),  # noqa: E122
        ("foo2\\.bar",   (ConfigDataTypeError, )),  # noqa: E122
        ("foo2\\[1\\]",  (RequiredPathNotFoundError,)),  # noqa: E122
        ("foo2\\[-2\\]", (RequiredPathNotFoundError,)),  # noqa: E122
        ("foo3",         (RequiredPathNotFoundError,)),  # noqa: E122
    ))  # @formatter:on # noqa: E122

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
        "path,              is_exist, ignore_excs,            kwargs", (  # @formatter:off # noqa: E122
        ("foo",             True,     (),                     {}),  # noqa: E122
        ("foo\\.bar",       True,     (),                     {}),  # noqa: E122
        ("foo\\.not exist", False,    (),                     {}),  # noqa: E122
        ("foo1",            True,     (),                     {}),  # noqa: E122
        ("foo2",            True,     (),                     {}),  # noqa: E122
        ("foo3",            False,    (),                     {}),  # noqa: E122
        ("foo2\\[0\\]",     True,     (),                     {}),  # noqa: E122
        ("foo2\\[1\\]",     False,    (),                     {}),  # noqa: E122
        ("foo2\\[-1\\]",    True,     (),                     {}),  # noqa: E122
        ("foo2\\.bar",      False,    (),                     {"ignore_wrong_type": True}),  # noqa: E122
        ("\\[0\\]",         False,    (),                     {"ignore_wrong_type": True}),  # noqa: E122
        ("foo2\\.bar",      None,     (ConfigDataTypeError,), {}),  # noqa: E122
        ("foo\\[0\\]",      False,    (ConfigDataTypeError,), {}),  # noqa: E122
        ("\\[0\\]",         False,    (ConfigDataTypeError,), {}),  # noqa: E122
    ))  # @formatter:on  # noqa: E122

    @staticmethod
    @mark.parametrize(*ExistsTests)
    def test_exists(data: M_MCD, path: str, is_exist: bool, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs):
            assert data.exists(path, **kwargs) is is_exist

    GetTests: tuple[str, tuple[tuple[str, Any, EE, dict[str, Any]], ...]] = (
        RetrieveTests[0],
        (
            *RetrieveTests[1],  # @formatter:off
            # path               value            ignore_excs             kwargs
            ("not exist",        "default value", (),                     {"default": "default value"}),
            ("foo.not exist",    "default value", (),                     {"default": "default value"}),
            ("foo2\\.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
        )  # @formatter:on
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
            *((*x[:3], x[3] | {"return_raw_value": True}) for x in RetrieveTests[1]),  # @formatter:off
            # path               value            ignore_excs             kwargs
            ("not exist",        "default value", (),                     {"default": "default value"}),
            ("foo\\.not exist",  "default value", (),                     {"default": "default value"}),
            ("foo2\\.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
        )  # @formatter:on
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

    GetItemTests = (
        "path, value", (
            ("foo", MappingConfigData({"bar": 123}),),
            ("foo1", 114,),
            ("foo2", SequenceConfigData(["bar"]),),
        ))

    @staticmethod
    @mark.parametrize(*GetItemTests)
    def test_getitem(data: M_MCD, path: str, value: Any) -> None:
        assert data[path] == value

    @staticmethod
    @mark.parametrize(*GetItemTests)
    def test_getattr(data: M_MCD, path: str, value: Any) -> None:
        assert getattr(data, path) == value

    @staticmethod
    @mark.parametrize("path, new_value", (
            ("foo.bar", 456),
            ("foo2", {"test": "value"}),
            ("foo3", 789),
            ("foo4.bar", 101112),
    ))
    def test_setitem(data: M_MCD, path: str, new_value: Any) -> None:
        data[path] = new_value
        assert path in data
        assert (
            cast(MappingConfigData[Any], data[path]).data == new_value
            if isinstance(data[path], ConfigData) else data[path] == new_value
        )

    @staticmethod
    @mark.parametrize("path, ignore_excs", (
            ("foo", ()),
            ("foo1", ()),
            ("foo2", ()),
            ("foo2\\.bar", (KeyError,)),
            ("foo3", (KeyError,)),
    ))
    def test_delitem(data: M_MCD, path: str, ignore_excs: EE) -> None:
        with safe_raises(ignore_excs):
            del data[path]
        assert path not in data

    @staticmethod
    @mark.parametrize("path, is_exist", (
            ("foo", True),
            ("foo\\.bar", False),
            ("foo\\.not exist", False),
            ("foo1", True),
            ("foo2", True),
            ("foo2\\.bar", False),
            ("foo3", False),
    ))
    def test_contains(data: M_MCD, path: str, is_exist: bool) -> None:
        assert (path in data) == is_exist

    IterTests: tuple[str, tuple[dict[str, Any], ...]] = ("raw_dict", (
        {},
        {"foo": "bar"},
        {"foo": "bar", "foo\\.bar": "bar"},
        {"foo": "bar", "foo\\.bar": "bar", "foo1": "bar"},
        {"foo": "bar", "foo\\.bar": "bar", "foo1": "bar", "foo2": ["bar"]},
    ))

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
        ','.join(arg for arg in ModifyTests[0].split(',') if "ignore_excs" not in arg),
        ((*x[:-2], x[-1]) for x in ModifyTests[1])
    )

    @classmethod
    @mark.parametrize(*ReadOnlyModifyTests)
    def test_readonly_modify(cls, readonly_data: R_MCD, path: str, value: Any, kwargs: dict[str, Any]) -> None:
        cls.test_modify(cast(M_MCD, readonly_data), path, value, ConfigDataReadOnlyError, kwargs)

    ReadOnlyDeleteTests: tuple[str, tuple[tuple[str], ...]] = (
        # 从中剔除ignore_excs参数
        ', '.join(arg for arg in DeleteTests[0].split(', ') if "ignore_excs" not in arg),
        tuple(x[:-1] for x in DeleteTests[1])
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

    KeysTests: tuple[str, tuple[tuple[dict[Any, Any], set[str]], ...]] = ("kwargs, keys", (
        ({}, {'a', "foo", "foo1", "foo2", r"\\.\[\]"}),
        ({"recursive": True}, {
            r"a\.c\.e\.f", r"a\.c", 'a', r"a\.c\.d", r"foo\.bar",
            r"a\.c\.e", "foo", "foo1", r"a\.b", "foo2", r"\\\\.\\[\\]"
        }),
        ({"end_point_only": True}, {"foo1", "foo2", r"\\\\.\\[\\]"}),
        ({"recursive": True, "end_point_only": True}, {
            r"a\.c\.d", r"foo\.bar", "foo2", r"a\.b", r"a\.c\.e\.f", "foo1", r"\\\\.\\[\\]"
        })
    ))

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
        tuple[tuple[
            dict[Any, Any],
            dict[str, Any],
            set[str] | None,
            EE,
        ], ...]
    ] = ("data, kwargs, keys, ignore_excs", (
        (cyclic_reference_datas()[0],
         {}, {"B", "D"}, ()),
        (cyclic_reference_datas()[1],
         {}, {"C"}, ()),
        (cyclic_reference_datas()[2],
         {}, {"A"}, ()),
        (cyclic_reference_datas()[3],
         {}, {"C"}, ()),
        (cyclic_reference_datas()[0],
         {"end_point_only": True}, set(), ()),
        (cyclic_reference_datas()[0],
         {"recursive": True, "strict": False},
         {r"D\.C", r"D\.C\.A", r"B\.C", "D", "B", r"B\.C\.A"},
         ()),
        (cyclic_reference_datas()[1],
         {"recursive": True, "strict": False},
         {r"C\.A", "C", r"C\.A\.D\.C", r"C\.A\.B", r"C\.A\.D"},
         ()),
        (cyclic_reference_datas()[2],
         {"recursive": True, "strict": False},
         {r"A\.B\.C", r"A\.D", r"A\.B", r"A\.D\.C", "A"},
         ()),
        (cyclic_reference_datas()[3],
         {"recursive": True, "strict": False},
         {r"C\.A", "C", r"C\.A\.B\.C", r"C\.A\.B", r"C\.A\.D"},
         ()),
        (cyclic_reference_datas()[0],
         {"recursive": True, "strict": True}, None, (CyclicReferenceError,)),
        (cyclic_reference_datas()[0],
         {"recursive": True, "end_point_only": True}, None, (CyclicReferenceError,)),
        (cyclic_reference_datas()[0],
         {"recursive": True}, None, (CyclicReferenceError,)),
        (cyclic_reference_datas()[1],
         {"recursive": True}, None, (CyclicReferenceError,)),
        (cyclic_reference_datas()[2],
         {"recursive": True}, None, (CyclicReferenceError,)),
        (cyclic_reference_datas()[3],
         {"recursive": True}, None, (CyclicReferenceError,)),
    ))

    @staticmethod
    @mark.parametrize(*CyclicReferenceTests)
    def test_cyclic_reference_keys(
            data: dict[str, Any],
            kwargs: dict[str, Any],
            keys: set[str],
            ignore_excs: EE
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
            ({},
             [
                 MappingConfigData({"bar": 123}),
                 114,
                 ["bar"],
                 MappingConfigData({'b': 1, 'c': {'d': 2, 'e': {'f': 3}}}),
                 None,
             ]),
            ({"return_raw_value": True}, [{"bar": 123}, 114, ["bar"], {'b': 1, 'c': {'d': 2, 'e': {'f': 3}}}, None]),
        )
    )

    @staticmethod
    @mark.parametrize(*ValuesTests)
    def test_values(data: M_MCD, kwargs: dict[str, Any], values: Any) -> None:
        assert list(data.values(**kwargs)) == values

    ItemsTests: tuple[str, tuple[tuple[dict[Any, Any], list[tuple[Any, Any]]], ...]] = ("kwargs, items", (
        ({}, [
            ("foo", MappingConfigData({"bar": 123})),
            ("foo1", 114),
            ("foo2", ["bar"]),
            ("a", MappingConfigData({'b': 1, 'c': {'d': 2, 'e': {'f': 3}}})),
            (r"\\.\[\]", None),
        ]),
        ({"return_raw_value": True}, [
            ("foo", {"bar": 123}),
            ("foo1", 114),
            ("foo2", ["bar"]),
            ("a", {'b': 1, 'c': {'d': 2, 'e': {'f': 3}}}),
            (r"\\.\[\]", None),
        ]),
    ))

    @staticmethod
    @mark.parametrize(*ItemsTests)
    def test_items(data: M_MCD, kwargs: dict[str, Any], items: list[tuple[str, Any]]) -> None:
        assert list(data.items(**kwargs)) == items

    @staticmethod
    @mark.parametrize("data", (
            {123: {"abc", "zzz"}},
            {"key": "value"},
    ))
    def test_clear(data: dict[Any, Any]) -> None:
        data = MappingConfigData(data)
        data.clear()
        assert not data

    @staticmethod
    @mark.parametrize("data", (
            {"a": 1, "b": 2},
            {"a": 1, "b": 2, "c": 3},
    ))
    def test_popitem(data: dict[Any, Any]) -> None:
        data = MappingConfigData(data)
        items = data.items()
        popped = data.popitem()
        assert popped in items
        assert popped not in data.items()

    @staticmethod
    @mark.parametrize("dct, key, result, ignore_excs", (
            ({"a": 1}, "a", 1, ()),
            ({"a": 1, "b": 2}, "b", 2, ()),
            ({"a": 1}, "b", Unset, (RequiredPathNotFoundError,)),
    ))
    def test_pop(dct: dict[Any, Any], key: str, result: Any, ignore_excs: EE) -> None:
        data = MappingConfigData(dct)
        with safe_raises(ignore_excs) as info:
            assert data.pop(key) == result
        if info:
            return
        assert key not in data

    @staticmethod
    @mark.parametrize("dct, key, default, result, ignore_excs", (
            ({"a": 1}, "a", 2, 1, ()),
            ({"a": 1, "b": 2}, "b", 3, 2, ()),
            ({"a": 1}, "b", 2, 2, ()),
            ({"a": 1}, "c", 5, 5, ()),
    ))
    def test_pop_default(dct: dict[str, Any], key: str, default: Any, result: Any, ignore_excs: EE) -> None:
        data = MappingConfigData(dct)
        with safe_raises(ignore_excs) as info:
            assert data.pop(key, default) == result
        if info:
            return
        assert key not in data

    @staticmethod
    @mark.parametrize("data, mapping, result", (
            ({"a": 1}, {"a": 2}, {"a": 2}),
            ({"a": 1}, {"b": 2}, {"a": 1, "b": 2}),
            ({"a": 1, "d": 4}, {"a": 2, "b": 3}, {"a": 2, "b": 3, "d": 4}),
    ))
    def test_update(data: dict[str, Any], mapping: Mapping[str, Any], result: Any) -> None:
        data = MappingConfigData(data)
        data.update(mapping)
        assert data == MappingConfigData(result)

    @staticmethod
    def test_repr(data: M_MCD) -> None:
        assert repr(data.data) in repr(data)
        assert repr({"a": 1, "b": 2}) in repr(MappingConfigData({"a": 1, "b": 2}))

    @staticmethod
    def test_format() -> None:
        assert repr(MappingConfigData({"a": 1, "b": 2})) == format(MappingConfigData({"a": 1, "b": 2}), 'r')
        with raises(TypeError):
            format(MappingConfigData({"a": 1, "b": 2}), 'not exists')

    MergeTests = (
        ({"a": 1, "b": 2}, {"a": -1, "b": 3}),
        ({"a": 1, "b": 2}, {"b": 3, "c": 4}),
        ({"a": 1, "b": 2}, {"b": 3}),
    )


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
        "path,           value,                        ignore_excs,                  kwargs", (  # @formatter:off # noqa: E122, E501
        (r"\[0\]",       1,                            (),                           {}),  # noqa: E122
        (r"\[0\]",       1,                            (),                           {"return_raw_value": True}),  # noqa: E122, E501
        (r"\[1\]",       2,                            (),                           {}),  # noqa: E122
        (r"\[2\]\.a",    SequenceConfigData([3, 4]),           (),                           {}),  # noqa: E122
        (r"\[2\]\.a",    [3, 4],                       (),                           {"return_raw_value": True}),  # noqa: E122, E501
        (r"\[2\]\.b",    MappingConfigData({"c": 5, "d": 6}), (),                           {}),  # noqa: E122
        (r"\[2\]\.b",    pmap({"c": 5, "d": 6}),       (),                           {"return_raw_value": True}),  # noqa: E122, E501
        (r"\[2\]\.b\.c", 5,                            (),                           {}),  # noqa: E122
        (r"\[2\]\.b\.c", 5,                            (),                           {}),  # noqa: E122
        (r"\[3\]\[0\]",  7,                            (),                           {}),  # noqa: E122
        (r"\[0\]\.bar",  None,                         (ConfigDataTypeError, ),      {}),  # noqa: E122
        (r"\[4\]",       None,                         (RequiredPathNotFoundError,), {}),  # noqa: E122
        (r"\[3\]\[2\]",  None,                         (RequiredPathNotFoundError,), {}),  # noqa: E122
        (r"\[3\]\.0",    None,                         (ConfigDataTypeError,),       {}),  # noqa: E122
        (r"bar",         None,                         (ConfigDataTypeError,),       {}),  # noqa: E122
    ))  # @formatter:on # noqa: E122

    @staticmethod
    @mark.parametrize(*RetrieveTests)
    def test_retrieve(data: SCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs):
            assert data.retrieve(path, **kwargs) == value

    ModifyTests: tuple[str, tuple[tuple[str, Any, EE, dict[str, Any]], ...]] = (
        "path,         value,        ignore_excs,                  kwargs", (  # @formatter:off # noqa: E122
        (r"\[0\]",      99,           (),                           {}),  # noqa: E122
        (r"\[2\]",      {"z": 9},     (),                           {}),  # noqa: E122
        (r"\[1\]",      88,           (),                           {}),  # noqa: E122
        (r"\[2\]\.a",   [9, 0],       (),                           {}),  # noqa: E122
        ("bar",         None,         (ConfigDataTypeError,),       {}),  # noqa: E122
        (r"\[3\]",      None,         (),                           {}),  # noqa: E122
        (r"\[4\]",      None,         (RequiredPathNotFoundError,), {"allow_create": False}, ),  # noqa: E122
    ))  # @formatter:on # noqa: E122

    @staticmethod
    @mark.parametrize(*ModifyTests)
    def test_modify(data: SCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs):
            data.modify(path, value, **kwargs)
            assert data.retrieve(path, return_raw_value=True) == value

    DeleteTests: tuple[str, tuple[tuple[str, EE], ...]] = (
        "path,             ignore_excs", (  # @formatter:off # noqa: E122
        (r"\[0\]",         ()),  # noqa: E122
        (r"\[1\]",         ()),  # noqa: E122
        (r"\[2\]",         ()),  # noqa: E122
        (r"\[2\]\.a",      ()),  # noqa: E122
        (r"\[2\]\.a\[1\]", ()),  # noqa: E122
        (r"\[2\]\.b\.c",   ()),  # noqa: E122
        (r"\[3\]\[1\]",    ()),  # noqa: E122
        ("abc",            (ConfigDataTypeError,)),  # noqa: E122
        (r"\[0\]\.a",      (ConfigDataTypeError,)),  # noqa: E122
        (r"\[2\]\[0\]",    (ConfigDataTypeError, )),  # noqa: E122
        (r"\[9\]",         (RequiredPathNotFoundError,)),  # noqa: E122
        (r"\[2\]\.z",      (RequiredPathNotFoundError,)),  # noqa: E122
        (r"\[3\]\[-5\]",   (RequiredPathNotFoundError,)),  # noqa: E122
    ))  # @formatter:on # noqa: E122

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
        "path,              is_exist, ignore_excs,            kwargs", (  # @formatter:off # noqa: E122
        (r"\[0\]",          True,     (),                     {}),  # noqa: E122
        (r"\[2\]",          True,     (),                     {}),  # noqa: E122
        (r"\[9\]",          False,    (),                     {}),  # noqa: E122
        (r"\[3\]",          True,     (),                     {}),  # noqa: E122
        (r"\[3\]",          True,     (),                     {}),  # noqa: E122
        (r"\[-6\]",         False,    (),                     {}),  # noqa: E122
        (r"\[3\]\[1\]",     True,     (),                     {}),  # noqa: E122
        (r"\[3\]\[4\]",     False,    (),                     {}),  # noqa: E122
        (r"\[2\]\.b\.c",    True,     (),                     {}),  # noqa: E122
        ("abc",             False,    (),                     {"ignore_wrong_type": True}),  # noqa: E122
        (r"\[3\]\.abc",     False,    (),                     {"ignore_wrong_type": True}),  # noqa: E122
        (r"\[2\]\[1\]",     None,     (ConfigDataTypeError,), {}),  # noqa: E122
        (r"\[3\]\.abc",     False,    (ConfigDataTypeError,), {}),  # noqa: E122
        (r"abc",            False,    (ConfigDataTypeError,), {}),  # noqa: E122
    ))  # @formatter:on  # noqa: E122

    @staticmethod
    @mark.parametrize(*ExistsTests)
    def test_exists(data: SCD, path: str, is_exist: bool, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs):
            assert data.exists(path, **kwargs) is is_exist

    GetTests = (
        RetrieveTests[0],
        (
            *RetrieveTests[1],  # @formatter:off
            # path               value            ignore_excs             kwargs
            (r"\[10\]",           "default value", (),                     {"default": "default value"}),
            (r"\[3\]\[20\]",      "default value", (),                     {"default": "default value"}),
            (r"foo2\\.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
        )  # @formatter:on
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
            *((*x[:3], x[3] | {"return_raw_value": True}) for x in RetrieveTests[1]),  # @formatter:off
            # path               value            ignore_excs             kwargs
            (r"\[10\]",           "default value", (),                     {"default": "default value"}),
            (r"\[3\]\[20\]",      "default value", (),                     {"default": "default value"}),
            (r"foo2\\.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
        )  # @formatter:on
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

    RepeatTests = (
        ([1, 2, 3], 3),
        ([7], 4),
        ([9, 4, 2, 6], 8),
    )

    ExtendTests = (
        ([1, 2, 3], [4, 5, 6]),
        ([7], [8, 9, 10]),
        ([9, 4, 2, 6], [8, 7, 6, 5]),
    )

    @staticmethod
    def test_repr(data: SCD) -> None:
        assert repr(data.data) in repr(data)
        assert repr({"a": 1, "b": 2}) in repr(MappingConfigData({"a": 1, "b": 2}))


class TestNumberConfigData:
    @staticmethod
    @fixture
    def number() -> int:
        return 0

    @staticmethod
    @fixture
    def data[N: Number](number: N) -> NumberConfigData[N]:
        return NumberConfigData(number)

    @staticmethod
    @fixture
    def readonly_data[N: Number](number: N) -> NumberConfigData[N]:
        cfg = NumberConfigData(number)
        cfg.freeze()
        return cfg

    @staticmethod
    def test_freeze(
            data: NumberConfigData[int],  # type: ignore[type-var]
            readonly_data: NumberConfigData[int]  # type: ignore[type-var]
    ) -> None:
        data.freeze()
        readonly_data.freeze()
        assert data.read_only is True
        assert readonly_data.read_only is False
        data.freeze(True)
        readonly_data.freeze(True)
        assert data.read_only is True
        assert readonly_data.read_only is True
        data.freeze(False)
        readonly_data.freeze(False)
        assert data.read_only is False
        assert readonly_data.read_only is False

    @staticmethod
    def test_init(data: NumberConfigData[int], readonly_data: NumberConfigData[int]) -> None:  # type: ignore[type-var]
        assert data.data == 0
        assert data.read_only is False

        assert NumberConfigData().data == int()

        assert readonly_data.data == 0
        assert readonly_data.read_only is True

    @staticmethod
    @mark.parametrize("number", (
            0,
            0.,
    ))
    def test_int(number: Number) -> None:
        assert int(NumberConfigData(number)) == 0

    @staticmethod
    @mark.parametrize("number", (
            0,
            0.,
    ))
    def test_float(number: Number) -> None:
        assert float(NumberConfigData(number)) == 0.

    @staticmethod
    @mark.parametrize("number, value", (
            (0, False),
            (0., False),
            (1, True),
            (.1, True),
            (0j, False),
            (1j, True),
            (0.j, False),
            (.1j, True),
    ))
    def test_bool(number: Number, value: bool) -> None:
        assert bool(NumberConfigData(number)) == value

    InvertTests = (
        (0,),
        (2,),
        (4562,),
    )
    IndexTests = InvertTests
    RoundTests = (
        (0,),
        (2,),
        (4562,),
        (9.2,),
    )
    NegTests = (
        (0,),
        (2,),
        (4562,),
        (9.2,),
        (1.2j,)
    )
    PosTests = NegTests
    AbsTests = NegTests

    @staticmethod
    @mark.parametrize("func, number, args", (
            (round, 0.55, ()),
            (round, 0.55, (2,)),
            (round, 0.55, (1,)),
            (math.trunc, -0.55, ()),
            (math.trunc, 0.55, ()),
            (math.trunc, 1.55, ()),
            (math.ceil, 0, ()),
            (math.ceil, 0.5, ()),
            (math.ceil, 0.4, ()),
            (math.ceil, 1.5, ()),
            (math.ceil, 1.4, ()),
            (math.floor, 0, ()),
            (math.floor, 0.5, ()),
            (math.floor, 0.4, ()),
            (math.floor, 1.5, ()),
            (math.floor, 1.4, ()),
    ))
    def test_protocol(func: Callable[..., Any], number: Number, args: Any) -> None:
        assert func(NumberConfigData(number), *args) == func(number, *args)


class TestBoolConfigData:
    @staticmethod
    def test_init() -> None:
        assert BoolConfigData().data is bool()


class TestStringConfigData:
    @staticmethod
    def test_init() -> None:
        assert StringConfigData().data == str()

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


def test_object_config_data() -> None:
    class MyClass:
        ...

    obj = MyClass()
    data = ConfigData(obj)
    assert isinstance(data, ObjectConfigData)
    assert data.data == obj
    assert data.data_read_only is False


type D_MCD = MappingConfigData[dict[Any, Any]]
type M = dict[str, ABCIndexedConfigData[Any]]
type CCD = ComponentConfigData[ABCIndexedConfigData[dict[Any, Any]], ComponentMeta[D_MCD]]


def _ccd_from_members(members: M) -> CCD:
    return ComponentConfigData(
        meta=ComponentMeta(members=[ComponentMember(fn) for fn in members.keys()]),
        members=members,
    )


def _ccd_from_meta(meta: dict[str, Any], members: M) -> CCD:
    return ComponentConfigData(
        ComponentMetaParser().convert_config2meta(MappingConfigData(meta)),  # type: ignore[arg-type]
        members
    )


class TestComponentConfigData:
    @staticmethod
    @fixture
    def empty_data() -> CCD:
        return ComponentConfigData()

    @staticmethod
    @fixture
    def meta() -> ComponentMeta[Any]:
        return ComponentMeta(members=[ComponentMember("foo.json", alias="f"), ComponentMember("bar.json", alias="b")])

    @staticmethod
    @fixture
    def members() -> M:
        return {
            "foo.json": MappingConfigData({
                "key": {
                    "value": "foo",
                },
                "first": {
                    "second": 3,
                },
            }),
            "bar.json": MappingConfigData({
                "key": {
                    "value": "bar",
                    "extra": 0
                }
            }),
        }

    @staticmethod
    @fixture
    def data(meta: ComponentMeta[D_MCD], members: M) -> CCD:
        return ComponentConfigData(meta, members)

    @staticmethod
    def test_empty_init(empty_data: CCD) -> None:
        assert not empty_data.members
        assert not empty_data.meta.config
        assert not empty_data.meta.members
        assert not empty_data.meta.orders.create
        assert not empty_data.meta.orders.read
        assert not empty_data.meta.orders.update
        assert not empty_data.meta.orders.delete

    @staticmethod
    def test_wrong_init() -> None:
        ccd = ComponentConfigData
        with raises(ValueError, match="repeat"):
            ccd(ComponentMeta(members=[*([ComponentMember("repeat")] * 3)]))

        with raises(ValueError, match="alias"):
            ccd(ComponentMeta(members=[ComponentMember("same", alias="same")]))

        with raises(ValueError, match="members"):
            ccd(members={"not in meta": MappingConfigData()})

        with raises(ValueError, match="members"):
            ccd(meta=ComponentMeta(members=[ComponentMember("not in members")]))

    @staticmethod
    def test_readonly_attr(empty_data: CCD) -> None:
        for attr in {"meta", "members", "filename2meta", "alias2filename"}:
            getattr(empty_data, attr)
            with raises(AttributeError):
                setattr(empty_data, attr, None)

    RetrieveTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": MappingConfigData(), "b": MappingConfigData(), "c": MappingConfigData({"key": "value"})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": MappingConfigData({"foo": {"bar": "value"}}), "b": MappingConfigData(),
                 "c": MappingConfigData()},
            ), "foo\\.bar", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": MappingConfigData(), "b": MappingConfigData({"foo": {"bar": "value"}}),
                 "c": MappingConfigData()},
            ), "foo\\.bar", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": MappingConfigData(), "b": MappingConfigData(),
                 "c": MappingConfigData({"foo": {"bar": "value"}})},
            ), "foo\\.bar", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a", "c"]},
                {"a": MappingConfigData(), "b": MappingConfigData(),
                 "c": MappingConfigData({"foo": {"bar": "value"}})},
            ), "foo", {"bar": "value"}, (), dict(return_raw_value=True)),
            (_ccd_from_meta(
                {"members": ["a", "c", "b"]},
                {"a": MappingConfigData(), "b": MappingConfigData({"key": True}),
                 "c": MappingConfigData({"key": "value"})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "c", "b"]},
                {
                    "a": MappingConfigData(pmap()),
                    "b": MappingConfigData(pmap({"key": True})),
                    "c": MappingConfigData(pmap({"key": "value"}))
                },
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": [dict(filename="a", alias="c"), "b"], "order": ["c"]},
                {"a": MappingConfigData({"a": "value"}), "b": MappingConfigData({"b": True})},
            ), "a", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": SequenceConfigData([{"key": False}]), "b": SequenceConfigData([{"key": True}])},
            ), "\\[0\\]\\.key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": SequenceConfigData([{"key": False}]), "b": SequenceConfigData([{"key": True}])},
            ), "\\{b\\}\\[0\\]\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": MappingConfigData(), "b": MappingConfigData({"key": False}),
                 "c": MappingConfigData({"key": None})},
            ), "\\{c\\}\\.key", None, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
            ), "\\{c\\}\\.key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
            ), "\\{z\\}\\.key", None, (RequiredPathNotFoundError,), {}),
            (_ccd_from_meta(
                {"order": ["z"]},
                {},
            ), "", None, (KeyError,), {}),
            (_ccd_from_meta(
                {"members": ["a", "c", "b"]},
                {
                    "a": MappingConfigData({"foo": "value"}),
                    "b": MappingConfigData({"foo": {"bar": "value"}}),
                    "c": MappingConfigData({"foo": {"bar": {"baz": "value"}}}),
                },
            ), "foo\\.bar\\.baz\\.qux", None, (ConfigDataTypeError,), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": MappingConfigData({"a": "value"}), "b": MappingConfigData({"b": True})},
            ), "key", None, (RequiredPathNotFoundError,), {}),
            (_ccd_from_meta(
                {"members": ["a"], "order": []},
                {"a": NoneConfigData()},  # type: ignore[dict-item]
            ), "", None, (RequiredPathNotFoundError,), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*RetrieveTests)
    def test_retrieve(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs):
            assert data.retrieve(path, **kwargs) == value

    ModifyTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": [dict(filename="a", alias="c"), "b"], "order": ["c"]},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
            ), "key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
            ), "key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
            ), "key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "orders": {"read": ["a", "b"], "update": ["b", "a"]}},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": None})},
            ), "key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": MappingConfigData({"foo": {"bar": "value"}}), "b": MappingConfigData({"foo": {"bar": None}})},
            ), "foo\\.bar", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": SequenceConfigData([{"foo": {"bar": "value"}}]),
                 "b": SequenceConfigData([{"foo": {"bar": None}}])},
            ), "\\[0\\]\\.foo\\.bar", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": SequenceConfigData([{"foo": {"bar": "value"}}]),
                 "b": SequenceConfigData([{"foo": {"bar": None}}])},
            ), "\\{a\\}\\[0\\]\\.foo\\.bar", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": MappingConfigData({"foo": {"bar": "value"}}), "b": MappingConfigData({"foo": {"bar": None}})},
            ), "foo", {"bar": True}, (), dict(allow_create=False)),
            (_ccd_from_meta(
                {"members": ["c", "b", "a"]},
                {"a": MappingConfigData(), "b": MappingConfigData({"key": False}),
                 "c": MappingConfigData({"key": None})},
            ), "\\{a\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
            ), "\\{c\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
            ), "\\{z\\}\\.key", None, (RequiredPathNotFoundError,), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": MappingConfigData({"foo": {"bar": "value"}}), "b": MappingConfigData({"foo": {"bar": None}})},
            ), "quz", {"value": True}, (RequiredPathNotFoundError,), dict(allow_create=False)),
        )
    )

    @staticmethod
    @mark.parametrize(*ModifyTests)
    def test_modify(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs) as info:
            data.modify(path, value, **kwargs)
        if info:
            return
        assert data.retrieve(path, return_raw_value=True) == value

    DeleteTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": MappingConfigData({"foo": {"bar": "value"}}), "b": MappingConfigData({"foo": {"bar": False}})},
            ), "foo\\.bar", False, (), {}),
            (_ccd_from_meta(
                {"members": [dict(filename="a", alias="c"), "b"], "order": ["c"]},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
            ), "key", Unset, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "orders": {"delete": ["b", "a"], "read": ["a", "b"]}},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {
                    "a": MappingConfigData(),
                    "b": MappingConfigData({"key": False}),
                    "c": MappingConfigData({"key": None})},
            ), "\\{c\\}\\.key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": True})},
            ), "\\{c\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": SequenceConfigData([{"key": False}]), "b": SequenceConfigData([{"key": True}])},
            ), "\\[0\\]\\.key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": SequenceConfigData([{"key": False}]), "b": SequenceConfigData([{"key": True}])},
            ), "\\{a\\}\\[0\\]\\.key", Unset, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
            ), "\\{z\\}\\.key", Unset, (RequiredPathNotFoundError,), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "order": []},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
            ), "key", Unset, (RequiredPathNotFoundError,), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": MappingConfigData(), "b": MappingConfigData()},
            ), "key", Unset, (RequiredPathNotFoundError,), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_delete(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs) as info:
            data.delete(path, **kwargs)
        if info:
            return
        assert data.get(path, value) == value

    UnsetTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": MappingConfigData({"foo": {"bar": "value"}}), "b": MappingConfigData({"foo": {"bar": False}})},
            ), "foo\\.bar", False, (), {}),
            (_ccd_from_meta(
                {"members": [dict(filename="a", alias="c"), "b"], "order": ["c"]},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
            ), "key", Unset, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "orders": {"delete": ["b", "a"], "read": ["a", "b"]}},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "order": []},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData({"key": "value"})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": MappingConfigData(), "b": MappingConfigData()},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": MappingConfigData(), "b": MappingConfigData({"key": False}),
                 "c": MappingConfigData({"key": None})},
            ), "\\{c\\}\\.key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": True})},
            ), "\\{c\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
            ), "\\{z\\}\\.key", Unset, (), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*UnsetTests)
    def test_unset(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs) as info:
            data.unset(path, **kwargs)
        if info:
            return
        assert data.get(path, value) == value

    ExistsTests: tuple[str, tuple[tuple[CCD, str, bool, EE, dict[str, Any]], ...]] = (
        "data, path, is_exists, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": MappingConfigData({"foo": {"bar": None}}),
                 "b": MappingConfigData({"foo": {"bar": {"quz": None}}})},
            ), "foo\\.bar\\.quz", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": MappingConfigData({"foo": {"bar": None}}),
                 "b": MappingConfigData({"foo": {"bar": {"quz": None}}})},
            ), "foo\\.bar\\.quz", True, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": MappingConfigData(), "b": MappingConfigData()},
            ), "key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
            ), "key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": MappingConfigData({"key": "value"}), "b": MappingConfigData()},
            ), "key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": SequenceConfigData([{"key": "value"}]), "b": SequenceConfigData([{}])},
            ), "\\[0\\]\\.key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": SequenceConfigData([{"key": "value"}]), "b": SequenceConfigData([{}])},
            ), "\\{a\\}\\[0\\]\\.key", True, (), {}),
            (_ccd_from_meta(
                {},
                {},
            ), "key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {
                    "a": MappingConfigData(),
                    "b": MappingConfigData({"key": False}),
                    "c": MappingConfigData({"key": None})
                },
            ), "\\{c\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {
                    "a": MappingConfigData({"key": False}),
                    "b": MappingConfigData(),
                    "c": MappingConfigData({"key": None})
                },
            ), "\\{b\\}\\.key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": True})},
            ), "\\{c\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": True})},
            ), "\\{c\\}\\.any", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": MappingConfigData({"key": False}), "b": MappingConfigData({"key": None})},
            ), "\\{z\\}\\.key", False, (), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*ExistsTests)
    def test_exists(data: CCD, path: str, is_exists: bool, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs):
            assert data.exists(path, **kwargs) is is_exists

    GetTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {},
                {},
            ), "value", None, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {
                    "a": MappingConfigData({"foo": {"bar": True}}),
                    "b": MappingConfigData({"foo": {"bar": False}})
                },
            ), "foo\\.bar", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {
                    "a": MappingConfigData({"foo": {"bar": True}}),
                    "b": MappingConfigData({"foo": {"bar": False}})
                },
            ), "foo\\.bar", False, (), {}),
            (_ccd_from_meta(
                {},
                {},
            ), "value", None, (), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*GetTests)
    def test_get(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs):
            assert data.get(path, value, **kwargs) == value

    SetDefaultTests: tuple[str, tuple[tuple[CCD, str, Any, EE, dict[str, Any]], ...]] = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": MappingConfigData(), "b": MappingConfigData()}
            ), "test\\.path", None, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "orders": {"create": ["b", "a"], "read": ["a", "b"]}},
                {"a": MappingConfigData(), "b": MappingConfigData()}
            ), "test\\.path", True, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "orders": {"create": ["b", "a"], "read": ["a", "b"]}},
                {"a": MappingConfigData(), "b": MappingConfigData({"test": {"path": None}})}
            ), "test\\.path", False, (AssertionError,), {}),
            (_ccd_from_meta(
                {},
                {}
            ), "test\\.path", None, (RequiredPathNotFoundError,), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*SetDefaultTests)
    def test_set_default(data: CCD, path: str, value: Any, ignore_excs: EE, kwargs: dict[str, Any]) -> None:
        with safe_raises(ignore_excs) as info:
            assert data.setdefault(path, value, **kwargs) == value
        if info:
            return
        assert data.retrieve(path, return_raw_value=True) == value

    @staticmethod
    @mark.parametrize("a, b", (
            ({}, {}),
            (
                    {},
                    {"a": MappingConfigData()},
            ),
            (
                    {"a": MappingConfigData()},
                    {"a": MappingConfigData()},
            ),
            (
                    {},
                    {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
            ),
            (
                    {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
                    {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
            ),
    ))
    def test_eq(a: M, b: M) -> None:
        is_eq = a == b
        a, b = _ccd_from_members(a), _ccd_from_members(b)

        assert (a == b) is is_eq
        assert (not a != b) is is_eq
        assert not a == {}
        assert b != {}

    @staticmethod
    @mark.parametrize("members", (
            {},
            {"a": MappingConfigData()},
            {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
    ))
    def test_str(members: M) -> None:
        assert str(members) in str(_ccd_from_members(members))

    @staticmethod
    @mark.parametrize("members", (
            {},
            {"a": MappingConfigData()},
            {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
    ))
    def test_repr(members: M) -> None:
        ccd = _ccd_from_members(members)
        assert repr(members) in repr(ccd)

    @staticmethod
    @mark.parametrize("members", (
            {},
            {"a": MappingConfigData()},
            {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
    ))
    def test_deepcopy(members: M) -> None:
        ccd = _ccd_from_members(members)
        copied = deepcopy(ccd)

        assert copied == ccd
        assert copied is not ccd

    @staticmethod
    @mark.parametrize("members, key", (
            ({"a": MappingConfigData()}, "a"),
            ({"a": MappingConfigData()}, "b"),
            ({"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})}, "b"),
    ))
    def test_contains(members: M, key: str) -> None:
        assert (key in _ccd_from_members(members)) is (key in members)

    @staticmethod
    @mark.parametrize("members", (
            {"a": MappingConfigData(), "b": MappingConfigData()},
            {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
            {"a": MappingConfigData({"foo": {"extra": "value"}}), "b": MappingConfigData({"foo": {"key": "value"}})},
    ))
    def test_iter(members: M) -> None:
        assert list(_ccd_from_members(members)) == list(members.keys())

    @staticmethod
    @mark.parametrize("members", (
            {},
            {"a": MappingConfigData()},
            {"a": MappingConfigData(), "b": MappingConfigData()},
            {"a": MappingConfigData(), "b": MappingConfigData(), "c": MappingConfigData()},
    ))
    def test_len(members: M) -> None:
        assert len(_ccd_from_members(members)) == len(members)

    @staticmethod
    @mark.parametrize("members, key", (
            ({}, 'key'),
            ({"a": MappingConfigData({"key": "a"})}, "a"),
            ({"a": MappingConfigData({"key": "a"}), "b": MappingConfigData({"key": "b"})}, "b"),
    ))
    def test_getitem(members: M, key: str) -> None:
        ignore_excs = []
        if key not in members:
            ignore_excs.append(KeyError)

        with safe_raises(tuple(ignore_excs)):
            assert _ccd_from_members(members)[key] == members[key]

    @staticmethod
    @mark.parametrize("members, key, value", (
            ({}, "key", MappingConfigData()),
            ({"a": MappingConfigData()}, "a", MappingConfigData({"key": "value"})),
            ({"a": MappingConfigData()}, "b", MappingConfigData()),
    ))
    def test_setitem(members: M, key: str, value: MappingConfigData[dict[Any, Any]]) -> None:
        ccd = _ccd_from_members(members)
        ccd[key] = value
        assert ccd[key] == value

    @staticmethod
    @mark.parametrize("members, key", (
            ({}, "key"),
            ({"a": MappingConfigData()}, "a"),
            ({"a": MappingConfigData(), "b": MappingConfigData()}, "a"),
    ))
    def test_delitem(members: M, key: str) -> None:
        ccd = _ccd_from_members(members)
        ignore_excs = []
        if key not in members:
            ignore_excs.append(KeyError)

        with safe_raises(tuple(ignore_excs)):
            del ccd[key]
        assert key not in ccd


def _insert_operator(
        tests: tuple[Any, ...],
        op: Callable[[Any], Any] | Callable[[Any, Any], Any],
        iop: Optional[Callable[[Any], Any] | Callable[[Any, Any], Any]] = None,
        *ext: Any
) -> Iterable[tuple[Any, Any, Any]]:
    yield from ((*test, *((op,) if iop is None else (op, iop)), *ext) for test in tests)


UnaryOperatorTests = (
    "a, op", (
        *_insert_operator(TestNumberConfigData.InvertTests, operator.invert),
        *_insert_operator(TestNumberConfigData.NegTests, operator.neg),
        *_insert_operator(TestNumberConfigData.PosTests, operator.pos),
        *_insert_operator(TestNumberConfigData.AbsTests, operator.abs),
        *_insert_operator(TestNumberConfigData.RoundTests, round),
        *_insert_operator(TestNumberConfigData.IndexTests, operator.index),
    )
)


@mark.parametrize(*UnaryOperatorTests)
def test_unary_operator(a: Any, op: Callable[[Any], Any]) -> None:
    assert (op(ConfigData(a)) == op(a)
            ), f"op({ConfigData(a):r}) != {op(a)}"


DyadicOperatorTests = (
    "a, b, op, iop, convert_raw", (
        *_insert_operator(TestMappingConfigData.MergeTests, operator.or_, operator.ior, True),
        *_insert_operator(TestSequenceConfigData.RepeatTests, operator.mul, operator.imul, False),
        *_insert_operator(TestSequenceConfigData.ExtendTests, operator.add, operator.iadd, False),
    ),
)


@mark.parametrize(*DyadicOperatorTests)
def test_dyadic_operator(
        a: ConfigData,
        b: ConfigData,
        op: Callable[[Any, Any], Any],
        iop: Callable[[Any, Any], Any],
        convert_raw: bool,
) -> None:
    converter: Callable[[Any], Any] = (lambda _: _) if convert_raw else ConfigData
    assert (op(ConfigData(a), ConfigData(b)) == ConfigData(op(a, b))
            ), f"op({ConfigData(a):r}, {ConfigData(b):r}) != {ConfigData(op(a, b)):r}"
    assert (op(a, ConfigData(b)) == ConfigData(op(a, b))
            ), f"op({a}, {ConfigData(b):r}) != {ConfigData(op(a, b)):r}"
    assert (op(ConfigData(a), b) == ConfigData(op(a, b))
            ), f"op({ConfigData(a):r}, {b}) != {ConfigData(op(a, b)):r}"

    assert (op(ConfigData(b), ConfigData(a)) == ConfigData(op(b, a))
            ), f"op({ConfigData(b):r}, {ConfigData(a):r}) != {ConfigData(op(b, a)):r}"
    assert (op(b, ConfigData(a)) == ConfigData(op(b, a))
            ), f"op({b}, {ConfigData(a):r}) != {ConfigData(op(b, a)):r}"
    assert (op(ConfigData(b), a) == ConfigData(op(b, a))
            ), f"op({ConfigData(b):r}, {a}) != {ConfigData(op(b, a)):r}"

    assert (iop(ConfigData(deepcopy(a)), ConfigData(b)) == ConfigData(iop(deepcopy(a), b))
            ), f"iop({ConfigData(deepcopy(a)):r}, {ConfigData(b):r}) != {ConfigData(iop(deepcopy(a), b)):r}"
    assert (iop(deepcopy(a), ConfigData(b)) == converter(iop(deepcopy(a), b))
            ), f"iop({deepcopy(a)}, {ConfigData(b):r}) != {converter(iop(deepcopy(a), b)):r}"
    assert (iop(ConfigData(deepcopy(a)), b) == ConfigData(iop(deepcopy(a), b))
            ), f"iop({ConfigData(deepcopy(a)):r}, {b}) != {ConfigData(iop(deepcopy(a), b)):r}"


def test_wrong_type_config_data() -> None:
    class EmptyTypesConfigData(ConfigData):
        TYPES: ClassVar[OrderedDict[tuple[type, ...], Callable[[Any], Any] | type]] = OrderedDict()

    with raises(TypeError, match="Unsupported type"):
        EmptyTypesConfigData(type)


type P = ConfigPool


class TestConfigFile:
    @staticmethod
    @fixture
    def data() -> D_MCD:
        return cast(D_MCD, MappingConfigData({
            "foo": {
                "bar": 123
            },
            "foo1": 114,
            "foo2": ["bar"]
        }))

    @staticmethod
    @fixture
    def file(data: D_MCD) -> ConfigFile[D_MCD]:
        return ConfigFile(data, config_format="json")

    @staticmethod
    @fixture
    def pool(tmpdir: FPath) -> P:
        return cast(P, ConfigPool(root_path=str(tmpdir)))

    @staticmethod
    def test_attr_readonly(file: ConfigFile[D_MCD], data: D_MCD) -> None:
        assert file.config == data
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.config = None  # type: ignore[misc, assignment]

        assert file.config_format == "json"
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.config_format = None  # type: ignore[misc]

    @staticmethod
    def test_wrong_save(data: D_MCD, pool: P) -> None:
        file: ConfigFile[D_MCD] = ConfigFile(data)
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: Unknown"):
            file.save(pool, '', ".json")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.save(pool, '', ".json", config_format="json")

    @staticmethod
    def test_wrong_load(file: ConfigFile[D_MCD], pool: P) -> None:
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.load(pool, '', ".json", config_format="json")

    @staticmethod
    def test_wrong_initialize(file: ConfigFile[D_MCD], pool: P) -> None:
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.initialize(pool, '', ".json", config_format="json")

    ExtraKwargs = (
        {"config_format": "json"},
    )

    CombExtraKwargs: list[dict[str, str]] = []
    for i in range(1, len(ExtraKwargs) + 1):
        CombExtraKwargs.extend(
            functools.reduce(
                operator.or_,
                kwargs_tuple
            ) for kwargs_tuple in itertools.combinations(ExtraKwargs, i)
        )

    CombEQKwargs: tuple[
        dict[
            str,
            dict[
                str,
                dict[str, int]
            ] | str
        ], ...,
    ] = tuple(d[0] | k for d, k in itertools.product(
        itertools.product((
            {"initial_config": {"foo": {"bar": 123}}},
            {"initial_config": {"foo": {"bar": 456}}},
        )),
        CombExtraKwargs
    ))

    EQTests: tuple[
        str,
        tuple[tuple[
            ConfigFile[D_MCD],
            ConfigFile[D_MCD],
            bool
        ], ...]
    ] = ("a, b, is_eq", tuple(((
        ConfigFile(**cast(dict[str, Any], a)), ConfigFile(**cast(dict[str, Any], b)), a == b
    ) for a, b in itertools.product(CombEQKwargs, CombEQKwargs)
    )))

    @staticmethod
    @mark.parametrize(*EQTests)
    def test_eq(a: ConfigFile[D_MCD], b: ConfigFile[D_MCD], is_eq: bool) -> None:
        assert (a == b) is is_eq

    @staticmethod
    def test_eq_diff_type(file: ConfigFile[D_MCD]) -> None:
        assert file != NotImplemented

    @staticmethod
    @mark.parametrize("raw_data, is_empty", (
            ({}, True),
            ({"foo": 123}, False),
    ))
    def test_bool(raw_data: D_MCD, is_empty: bool) -> None:
        assert bool(ConfigFile(ConfigData(raw_data))) is not is_empty

    @staticmethod
    def test_repr(file: ConfigFile[D_MCD], data: D_MCD) -> None:
        assert repr(file.config) in repr(file)
        assert repr(data) in repr(ConfigFile(data))
