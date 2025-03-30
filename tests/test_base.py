# -*- coding: utf-8 -*-


import functools
import itertools
import math
import operator
from collections import OrderedDict
from collections.abc import Callable
from contextlib import suppress
from copy import deepcopy
from typing import Any
from typing import Optional

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
from C41811.Config import Path
from C41811.Config import SequenceConfigData
from C41811.Config import StringConfigData
from C41811.Config.errors import ConfigDataReadOnlyError
from C41811.Config.errors import ConfigDataTypeError
from C41811.Config.errors import RequiredPathNotFoundError
from C41811.Config.errors import UnsupportedConfigFormatError
from C41811.Config.processor.Component import ComponentMetaParser
from C41811.Config.utils import Unset
from utils import safe_raises


def test_none_config_data():
    assert not NoneConfigData()

    with raises(ValueError):
        # noinspection PyTypeChecker
        NoneConfigData(NotImplemented)


class TestMappingConfigData:

    @staticmethod
    @fixture
    def odict():
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
    def data(odict) -> MappingConfigData:
        return ConfigData(odict)

    @staticmethod
    @fixture
    def readonly_odict(odict):
        return pmap(odict)

    @staticmethod
    @fixture
    def readonly_data(readonly_odict) -> MappingConfigData:
        return ConfigData(readonly_odict)

    # noinspection PyTestUnpassedFixture
    @staticmethod
    def test_init(odict, readonly_odict):
        data = ConfigData(odict)
        assert data.data is not odict
        assert data.data == odict

        assert MappingConfigData().data == dict()

        readonly_data = ConfigData(readonly_odict)
        assert readonly_data.data is not readonly_odict
        assert readonly_data.data == readonly_odict

    RetrieveTests = (
        "path,          value,                    ignore_excs,                  kwargs", (  # @formatter:off # noqa: E122, E501
        ("foo",         ConfigData({"bar": 123}), (),                           {}),  # noqa: E122
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
    def test_retrieve(data: MappingConfigData, path, value, ignore_excs, kwargs):
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs):
            assert data.retrieve(path, **kwargs) == value

    ModifyTests = (
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
    def test_modify(data: MappingConfigData, path, value, ignore_excs, kwargs):
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs) as info:
            data.modify(path, value, **kwargs)
        if info:
            return
        assert data.retrieve(path, return_raw_value=True) == value

    DeleteTests = (
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
    def test_delete(data: MappingConfigData, path, ignore_excs):
        with safe_raises(ignore_excs):
            data.delete(path)
        assert path not in data

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_unset(data: MappingConfigData, path, ignore_excs):
        ignore_excs = tuple(exc for exc in ignore_excs if not issubclass(exc, RequiredPathNotFoundError))
        with safe_raises(ignore_excs):
            data.unset(path)
        assert path not in data

    ExistsTests = (
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
    def test_exists(data, path, is_exist, ignore_excs, kwargs):
        with safe_raises(ignore_excs):
            assert data.exists(path, **kwargs) is is_exist

    GetTests = (
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
    def test_get(data, path, value, ignore_excs, kwargs):
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
            ("not exist",        "default value", (),                     {"default": "default value"}),
            ("foo\\.not exist",  "default value", (),                     {"default": "default value"}),
            ("foo2\\.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
        )  # @formatter:on
    )

    @staticmethod
    @mark.parametrize(*GetTests)
    def test_set_default(data, path, value, ignore_excs, kwargs):
        has_index_key = any(isinstance(k, IndexKey) for k in Path.from_str(path))
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
            ("foo", ConfigData({"bar": 123}),),
            ("foo1", 114,),
            ("foo2", ConfigData(["bar"]),),
        ))

    @staticmethod
    @mark.parametrize(*GetItemTests)
    def test_getitem(data, path, value):
        assert data[path] == value

    @staticmethod
    @mark.parametrize(*GetItemTests)
    def test_getattr(data, path, value):
        assert getattr(data, path) == value

    @staticmethod
    @mark.parametrize("path, new_value", (
            ("foo.bar", 456),
            ("foo2", {"test": "value"}),
            ("foo3", 789),
            ("foo4.bar", 101112),
    ))
    def test_setitem(data, path, new_value):
        data[path] = new_value
        assert path in data
        assert data[path].data == new_value if isinstance(data[path], ConfigData) else data[path] == new_value

    @staticmethod
    @mark.parametrize("path, ignore_excs", (
            ("foo", ()),
            ("foo1", ()),
            ("foo2", ()),
            ("foo2\\.bar", (KeyError,)),
            ("foo3", (KeyError,)),
    ))
    def test_delitem(data, path, ignore_excs):
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
    def test_contains(data, path, is_exist):
        assert (path in data) == is_exist

    IterTests = ("raw_dict", (
        {},
        {"foo": "bar"},
        {"foo": "bar", "foo\\.bar": "bar"},
        {"foo": "bar", "foo\\.bar": "bar", "foo1": "bar"},
        {"foo": "bar", "foo\\.bar": "bar", "foo1": "bar", "foo2": ["bar"]},
    ))

    @staticmethod
    @mark.parametrize(*IterTests)
    def test_iter(raw_dict):
        assert list(iter(ConfigData(raw_dict))) == list(iter(raw_dict))

    @staticmethod
    @mark.parametrize(*IterTests)
    def test_str(raw_dict):
        assert str(ConfigData(raw_dict)) == str(raw_dict)

    @staticmethod
    def test_data_readonly_attr(data, readonly_data):
        assert readonly_data.data_read_only
        assert not data.data_read_only

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            data.data_read_only = None

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            readonly_data.data_read_only = None

    @staticmethod
    def test_readonly_attr(data, readonly_data):
        assert readonly_data.read_only
        with raises(ConfigDataReadOnlyError):
            readonly_data.read_only = False

        assert not data.read_only
        data.read_only = True
        assert data.read_only
        with raises(ConfigDataReadOnlyError):
            data.modify("new_key", 123)

    @staticmethod
    def test_data_attr(data):
        last_data = data.data
        data["foo.bar"] = 456
        assert last_data != data.data

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            data.data = {}

    @classmethod
    @mark.parametrize(*RetrieveTests)
    def test_readonly_retrieve(cls, readonly_data, path, value, ignore_excs, kwargs):
        cls.test_retrieve(readonly_data, path, value, ignore_excs, kwargs)

    ReadOnlyModifyTests = (
        ','.join(arg for arg in ModifyTests[0].split(',') if "ignore_excs" not in arg),
        ((*x[:-2], x[-1]) for x in ModifyTests[1])
    )

    @classmethod
    @mark.parametrize(*ReadOnlyModifyTests)
    def test_readonly_modify(cls, readonly_data, path, value, kwargs):
        cls.test_modify(readonly_data, path, value, ConfigDataReadOnlyError, kwargs)

    ReadOnlyDeleteTests = (
        ', '.join(arg for arg in DeleteTests[0].split(', ') if "ignore_excs" not in arg),
        tuple(x[:-1] for x in DeleteTests[1])
    )

    @classmethod
    @mark.parametrize(*ReadOnlyDeleteTests)
    def test_readonly_delete(cls, readonly_data, path):
        cls.test_delete(readonly_data, path, ConfigDataReadOnlyError)

    @classmethod
    @mark.parametrize(*ReadOnlyDeleteTests)
    def test_readonly_unset(cls, readonly_data, path):
        cls.test_unset(readonly_data, path, (ConfigDataReadOnlyError,))

    @staticmethod
    def test_eq(data, readonly_data):
        assert data == data
        assert data == deepcopy(data)
        assert readonly_data == readonly_data
        assert readonly_data == deepcopy(readonly_data)
        assert data == readonly_data

    @staticmethod
    def test_deepcopy(data):
        last_data = deepcopy(data)
        data["foo.bar"] = 456
        assert last_data != data

    KeysTests = ("kwargs, keys", (
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
    def test_keys(data, kwargs, keys):
        assert set(data.keys(**kwargs)) == keys

    ValuesTests = (
        "kwargs, values",
        (
            ({},
             [
                 ConfigData({"bar": 123}),
                 114,
                 ["bar"],
                 ConfigData({'b': 1, 'c': {'d': 2, 'e': {'f': 3}}}),
                 None,
             ]),
            ({"return_raw_value": True}, [{"bar": 123}, 114, ["bar"], {'b': 1, 'c': {'d': 2, 'e': {'f': 3}}}, None]),
        )
    )

    @staticmethod
    @mark.parametrize(*ValuesTests)
    def test_values(data, kwargs, values):
        assert list(data.values(**kwargs)) == values

    ItemsTests = ("kwargs, items", (
        ({}, [
            ("foo", ConfigData({"bar": 123})),
            ("foo1", 114),
            ("foo2", ["bar"]),
            ("a", ConfigData({'b': 1, 'c': {'d': 2, 'e': {'f': 3}}})),
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
    def test_items(data, kwargs, items):
        assert list(data.items(**kwargs)) == items

    @staticmethod
    @mark.parametrize("data", (
            {123: {"abc", "zzz"}},
            {"key": "value"},
    ))
    def test_clear(data):
        data = ConfigData(data)
        data.clear()
        assert not data

    @staticmethod
    @mark.parametrize("data", (
            {"a": 1, "b": 2},
            {"a": 1, "b": 2, "c": 3},
    ))
    def test_popitem(data):
        data = ConfigData(data)
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
    def test_pop(dct, key, result, ignore_excs):
        data = ConfigData(dct)
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
    def test_pop_default(dct, key, default, result, ignore_excs):
        data = ConfigData(dct)
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
    def test_update(data, mapping, result):
        data = ConfigData(data)
        data.update(mapping)
        assert data == ConfigData(result)

    @staticmethod
    def test_repr(data):
        assert repr(data.data) in repr(data)
        assert repr({"a": 1, "b": 2}) in repr(ConfigData({"a": 1, "b": 2}))

    @staticmethod
    def test_format():
        assert repr(ConfigData({"a": 1, "b": 2})) == format(ConfigData({"a": 1, "b": 2}), 'r')
        with raises(TypeError):
            format(ConfigData({"a": 1, "b": 2}), 'not exists')

    MergeTests = (
        ({"a": 1, "b": 2}, {"a": -1, "b": 3}),
        ({"a": 1, "b": 2}, {"b": 3, "c": 4}),
        ({"a": 1, "b": 2}, {"b": 3}),
    )


class TestSequenceConfigData:
    @staticmethod
    @fixture
    def sequence() -> list:
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
    def readonly_sequence(sequence) -> tuple:
        return tuple(sequence)

    @staticmethod
    @fixture
    def data(sequence) -> SequenceConfigData[list]:
        return ConfigData(sequence)

    @staticmethod
    @fixture
    def readonly_data(readonly_sequence) -> SequenceConfigData[tuple]:
        return ConfigData(readonly_sequence)

    # noinspection PyTestUnpassedFixture
    @staticmethod
    def test_init(sequence, readonly_sequence):
        data = ConfigData(sequence)
        assert data.data is not sequence
        assert data.data == sequence

        assert SequenceConfigData().data == list()

        readonly_data = ConfigData(readonly_sequence)
        assert readonly_data.data is not readonly_sequence
        assert readonly_data.data == readonly_sequence

    RetrieveTests = (
        "path,           value,                        ignore_excs,                  kwargs", (  # @formatter:off # noqa: E122, E501
        (r"\[0\]",       1,                            (),                           {}),  # noqa: E122
        (r"\[0\]",       1,                            (),                           {"return_raw_value": True}),  # noqa: E122, E501
        (r"\[1\]",       2,                            (),                           {}),  # noqa: E122
        (r"\[2\]\.a",    ConfigData([3, 4]),           (),                           {}),  # noqa: E122
        (r"\[2\]\.a",    [3, 4],                       (),                           {"return_raw_value": True}),  # noqa: E122, E501
        (r"\[2\]\.b",    ConfigData({"c": 5, "d": 6}), (),                           {}),  # noqa: E122
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
    def test_retrieve(data: SequenceConfigData, path, value, ignore_excs, kwargs):
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs):
            assert data.retrieve(path, **kwargs) == value

    ModifyTests = (
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
    def test_modify(data: SequenceConfigData, path, value, ignore_excs, kwargs):
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs):
            data.modify(path, value, **kwargs)
            assert data.retrieve(path, return_raw_value=True) == value

    DeleteTests = (
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
    def test_delete(data: SequenceConfigData, path, ignore_excs):
        with safe_raises(ignore_excs):
            data.delete(path)
        assert path not in data

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_unset(data: SequenceConfigData, path, ignore_excs):
        ignore_excs = tuple(exc for exc in ignore_excs if not issubclass(exc, RequiredPathNotFoundError))
        with safe_raises(ignore_excs):
            data.unset(path)
        assert path not in data

    ExistsTests = (
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
    def test_exists(data, path, is_exist, ignore_excs, kwargs):
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
    def test_get(data, path, value, ignore_excs, kwargs):
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
    @mark.parametrize(*GetTests)
    def test_set_default(data, path, value, ignore_excs, kwargs):
        has_index_key = any(isinstance(k, IndexKey) for k in Path.from_str(path))
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
            (1, 2),
            (2, ConfigData({
                "a": [3, 4],
                "b": {
                    "c": 5,
                    "d": 6,
                },
            })),
            (3, ConfigData([7, 8])),
        ))

    @staticmethod
    @mark.parametrize(*GetItemTests)
    def test_getitem(data, path, value):
        assert data[path] == value

    @staticmethod
    @mark.parametrize("path, new_value", (
            (0, 456),
            (1, {"test": "value"}),
            (2, 789),
            (3, 101112),
    ))
    def test_setitem(data, path, new_value):
        data[path] = new_value
        assert data[path].data == new_value if isinstance(data[path], ConfigData) else data[path] == new_value

    @staticmethod
    @mark.parametrize("path, ignore_excs", (
            (1, ()),
            (2, ()),
            (3, ()),
            (4, (IndexError,)),
            (5, (IndexError,)),
    ))
    def test_delitem(data: SequenceConfigData, path, ignore_excs):
        with safe_raises(ignore_excs):
            last = data[path]
            del data[path]

        with suppress(IndexError):
            assert last != data[path]

    @staticmethod
    @mark.parametrize("path, is_exist", (
            (1, True),
            (888, False),
            (2, True),
            ([7, 8], True),
            ([999], False),
            (r"\[0\]", False),
            ("bar", False),
    ))
    def test_contains(data, path, is_exist):
        assert (path in data) == is_exist

    IterTests = ("raw_sequence", (
        [],
        [1, 2, 3],
        [1, {2: [3, 4]}, 5],
        [1, 2, [3, [4, 5]], 6],
        [{1: 2, 3: [4, 5, {6: 7}, 8]}, 9, {10: [11, 12]}, 13],
    ))

    @staticmethod
    @mark.parametrize(*IterTests)
    def test_iter(raw_sequence):
        assert list(iter(ConfigData(raw_sequence))) == list(iter(raw_sequence))

    @staticmethod
    @mark.parametrize(*IterTests)
    def test_str(raw_sequence):
        assert str(ConfigData(raw_sequence)) == str(raw_sequence)

    @staticmethod
    def test_data_readonly_attr(data, readonly_data):
        assert readonly_data.data_read_only
        assert not data.data_read_only

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            data.data_read_only = None

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            readonly_data.data_read_only = None

    @staticmethod
    def test_readonly_attr(data, readonly_data):
        assert readonly_data.read_only
        with raises(ConfigDataReadOnlyError):
            readonly_data.read_only = False

        assert not data.read_only
        data.read_only = True
        assert data.read_only
        with raises(ConfigDataReadOnlyError):
            data.modify(r"\[0\]", 123)

    @staticmethod
    def test_data_attr(data):
        last_data = data.data
        data[0] = 456
        assert last_data != data.data

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            data.data = {}

    @classmethod
    @mark.parametrize(*RetrieveTests)
    def test_readonly_retrieve(cls, readonly_data, path, value, ignore_excs, kwargs):
        cls.test_retrieve(readonly_data, path, value, ignore_excs, kwargs)

    ReadOnlyModifyTests = (
        ','.join(arg for arg in ModifyTests[0].split(',') if "ignore_excs" not in arg),
        ((*x[:-2], x[-1]) for x in ModifyTests[1])
    )

    @classmethod
    @mark.parametrize(*ReadOnlyModifyTests)
    def test_readonly_modify(cls, readonly_data, path, value, kwargs):
        cls.test_modify(readonly_data, path, value, ConfigDataReadOnlyError, kwargs)

    ReadOnlyDeleteTests = (
        ', '.join(arg for arg in DeleteTests[0].split(', ') if "ignore_excs" not in arg),
        tuple(x[:-1] for x in DeleteTests[1])
    )

    @classmethod
    @mark.parametrize(*ReadOnlyDeleteTests)
    def test_readonly_delete(cls, readonly_data, path):
        cls.test_delete(readonly_data, path, ConfigDataReadOnlyError)

    @classmethod
    @mark.parametrize(*ReadOnlyDeleteTests)
    def test_readonly_unset(cls, readonly_data, path):
        cls.test_unset(readonly_data, path, (ConfigDataReadOnlyError,))

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
    def test_methods(method, data, args, readonly):
        cfg = ConfigData(deepcopy(data))

        excs = (ConfigDataReadOnlyError,) if readonly else ()
        with safe_raises(excs) as info:
            result = getattr(cfg, method)(*args)
        if info:
            return
        assert result == getattr(data, method)(*args)
        assert cfg.data == data

    @staticmethod
    def test_reversed(data, readonly_data):
        assert list(reversed(data)) == list(reversed(data))

    @staticmethod
    def test_eq(data, readonly_data):
        assert data == data
        assert data == deepcopy(data)
        assert readonly_data == readonly_data
        assert readonly_data == deepcopy(readonly_data)

    @staticmethod
    def test_deepcopy(data):
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
    def test_repr(data):
        assert repr(data.data) in repr(data)
        assert repr({"a": 1, "b": 2}) in repr(ConfigData({"a": 1, "b": 2}))


class TestNumberConfigData:
    @staticmethod
    @fixture
    def number() -> int:
        return 0

    @staticmethod
    @fixture
    def data(number) -> NumberConfigData[int]:
        return ConfigData(number)

    @staticmethod
    @fixture
    def readonly_data(number) -> NumberConfigData[int]:
        cfg = ConfigData(number)
        cfg.freeze()
        return cfg

    @staticmethod
    def test_freeze(data, readonly_data):
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
    def test_init(data, readonly_data):
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
    def test_int(number):
        assert int(ConfigData(number)) == 0

    @staticmethod
    @mark.parametrize("number", (
            0,
            0.,
    ))
    def test_float(number):
        assert float(ConfigData(number)) == 0.

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
    def test_bool(number, value):
        assert bool(ConfigData(number)) == value

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
    def test_protocol(func, number, args):
        assert func(ConfigData(number), *args) == func(number, *args)


class TestBoolConfigData:
    @staticmethod
    def test_init():
        assert BoolConfigData().data is bool()


class TestStringConfigData:
    @staticmethod
    def test_init():
        assert StringConfigData().data == str()

    @staticmethod
    @mark.parametrize("string, format_spec", (
            ("test", "<5"),
            ("test", ">9"),
            ("test", "^7"),
    ))
    def test_format(string, format_spec):
        assert format(ConfigData(string), format_spec) == format(string, format_spec)

    @staticmethod
    @mark.parametrize("string, slice_obj", (
            ("test", slice(0, 2)),
            ("test", slice(None, None, -1)),
            ("test", slice(1)),
            ("test", slice(None, -2)),
            ("test", slice(None, None, 2)),
    ))
    def test_slice(string, slice_obj):
        assert ConfigData(string)[slice_obj] == string[slice_obj]
        cfg, cs = ConfigData(string), deepcopy(string)
        with raises(TypeError):
            # noinspection PyUnresolvedReferences
            cs[slice_obj] = "X"
        with raises(TypeError):
            cfg[slice_obj] = "X"
        with raises(TypeError):
            del cfg[slice_obj]
        with raises(TypeError):
            # noinspection PyUnresolvedReferences
            del cs[slice_obj]

    @staticmethod
    @mark.parametrize("string", (
            "test",
            "abba",
            "abcd",
    ))
    def test_reversed(string):
        assert list(reversed(ConfigData(string))) == list(reversed(string))

    @staticmethod
    @mark.parametrize("data, string, result", (
            ("test", "test", True),
            ("test", "TEST", False),
            ("test", "t", True),
            ("aabb", "ab", True),
    ))
    def test_contains(data, string, result):
        data = ConfigData(data)
        assert (string in data) is result

    @staticmethod
    @mark.parametrize("string", (
            "123456",
            "aabbcc",
    ))
    def test_iter(string):
        data = ConfigData(string)
        assert list(data) == list(string)

    @staticmethod
    @mark.parametrize("string", (
            "123456",
            "aabb",
    ))
    def test_len(string):
        data = ConfigData(string)
        assert len(data) == len(string)


def test_object_config_data():
    class MyClass:
        ...

    obj = MyClass()
    data = ConfigData(obj)
    assert isinstance(data, ObjectConfigData)
    assert data.data == obj
    assert data.data_read_only is False


def _ccd_from_members(members: dict[str, MappingConfigData]) -> ComponentConfigData:
    return ComponentConfigData(
        meta=ComponentMeta(members=[ComponentMember(fn) for fn in members.keys()]),
        members=members,
    )


def _ccd_from_meta(meta: dict[str, Any], members: dict[str, MappingConfigData]) -> ComponentConfigData:
    return ComponentConfigData(
        ComponentMetaParser().convert_config2meta(ConfigData(meta)),
        members
    )


class TestComponentConfigData:
    @staticmethod
    @fixture
    def empty_data() -> ComponentConfigData:
        return ComponentConfigData()

    @staticmethod
    @fixture
    def meta() -> ComponentMeta:
        return ComponentMeta(members=[ComponentMember("foo.json", alias="f"), ComponentMember("bar.json", alias="b")])

    @staticmethod
    @fixture
    def members() -> dict[str, MappingConfigData]:
        return {
            "foo.json": ConfigData({
                "key": {
                    "value": "foo",
                },
                "first": {
                    "second": 3,
                },
            }),
            "bar.json": ConfigData({
                "key": {
                    "value": "bar",
                    "extra": 0
                }
            }),
        }

    @staticmethod
    @fixture
    def data(meta, members) -> ComponentConfigData:
        return ComponentConfigData(meta, members)

    @staticmethod
    def test_empty_init(empty_data):
        assert not empty_data.members
        assert not empty_data.meta.config
        assert not empty_data.meta.members
        assert not empty_data.meta.orders.create
        assert not empty_data.meta.orders.read
        assert not empty_data.meta.orders.update
        assert not empty_data.meta.orders.delete

    @staticmethod
    def test_wrong_init():
        ccd = ComponentConfigData
        with raises(ValueError, match="repeat"):
            ccd(ComponentMeta(members=[*([ComponentMember("repeat")] * 3)]))

        with raises(ValueError, match="alias"):
            ccd(ComponentMeta(members=[ComponentMember("same", alias="same")]))

        with raises(ValueError, match="members"):
            ccd(members={"not in meta": ConfigData()})

        with raises(ValueError, match="members"):
            ccd(meta=ComponentMeta(members=[ComponentMember("not in members")]))

    @staticmethod
    def test_readonly_attr(empty_data):
        for attr in {"meta", "members", "filename2meta", "alias2filename"}:
            getattr(empty_data, attr)
            with raises(AttributeError):
                setattr(empty_data, attr, None)

    RetrieveTests = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": ConfigData({}), "b": ConfigData({}), "c": ConfigData({"key": "value"})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": ConfigData({"foo": {"bar": "value"}}), "b": ConfigData({}), "c": ConfigData({})},
            ), "foo\\.bar", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": ConfigData({}), "b": ConfigData({"foo": {"bar": "value"}}), "c": ConfigData({})},
            ), "foo\\.bar", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": ConfigData({}), "b": ConfigData({}), "c": ConfigData({"foo": {"bar": "value"}})},
            ), "foo\\.bar", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a", "c"]},
                {"a": ConfigData({}), "b": ConfigData({}), "c": ConfigData({"foo": {"bar": "value"}})},
            ), "foo", {"bar": "value"}, (), dict(return_raw_value=True)),
            (_ccd_from_meta(
                {"members": ["a", "c", "b"]},
                {"a": ConfigData({}), "b": ConfigData({"key": True}), "c": ConfigData({"key": "value"})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "c", "b"]},
                {
                    "a": ConfigData(pmap()),
                    "b": ConfigData(pmap({"key": True})),
                    "c": ConfigData(pmap({"key": "value"}))
                },
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": [dict(filename="a", alias="c"), "b"], "order": ["c"]},
                {"a": ConfigData({"a": "value"}), "b": ConfigData({"b": True})},
            ), "a", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": ConfigData({}), "b": ConfigData({"key": False}), "c": ConfigData({"key": None})},
            ), "\\{c\\}\\.key", None, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": ConfigData({"key": False}), "b": ConfigData({"key": None})},
            ), "\\{c\\}\\.key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": ConfigData({"key": False}), "b": ConfigData({"key": None})},
            ), "\\{z\\}\\.key", None, (RequiredPathNotFoundError,), {}),
            (_ccd_from_meta(
                {"order": ["z"]},
                {},
            ), "", None, (KeyError,), {}),
            (_ccd_from_meta(
                {"members": ["a", "c", "b"]},
                {
                    "a": ConfigData({"foo": "value"}),
                    "b": ConfigData({"foo": {"bar": "value"}}),
                    "c": ConfigData({"foo": {"bar": {"baz": "value"}}}),
                },
            ), "foo\\.bar\\.baz\\.qux", None, (ConfigDataTypeError,), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": ConfigData({"a": "value"}), "b": ConfigData({"b": True})},
            ), "key", None, (RequiredPathNotFoundError,), {}),
            (_ccd_from_meta(
                {"members": ["a"], "order": []},
                {"a": ConfigData()},
            ), "", None, (RequiredPathNotFoundError,), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*RetrieveTests)
    def test_retrieve(data, path, value, ignore_excs, kwargs):
        with safe_raises(ignore_excs):
            assert data.retrieve(path, **kwargs) == value

    ModifyTests = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": [dict(filename="a", alias="c"), "b"], "order": ["c"]},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({})},
            ), "key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({})},
            ), "key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({})},
            ), "key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "orders": {"read": ["a", "b"], "update": ["b", "a"]}},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({"key": None})},
            ), "key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": ConfigData({"foo": {"bar": "value"}}), "b": ConfigData({"foo": {"bar": None}})},
            ), "foo\\.bar", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": ConfigData({"foo": {"bar": "value"}}), "b": ConfigData({"foo": {"bar": None}})},
            ), "foo", {"bar": True}, (), dict(allow_create=False)),
            (_ccd_from_meta(
                {"members": ["c", "b", "a"]},
                {"a": ConfigData({}), "b": ConfigData({"key": False}), "c": ConfigData({"key": None})},
            ), "\\{a\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": ConfigData({"key": False}), "b": ConfigData({"key": None})},
            ), "\\{c\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": ConfigData({"key": False}), "b": ConfigData({"key": None})},
            ), "\\{z\\}\\.key", None, (RequiredPathNotFoundError,), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": ConfigData({"foo": {"bar": "value"}}), "b": ConfigData({"foo": {"bar": None}})},
            ), "quz", {"value": True}, (RequiredPathNotFoundError,), dict(allow_create=False)),
        )
    )

    @staticmethod
    @mark.parametrize(*ModifyTests)
    def test_modify(data, path, value, ignore_excs, kwargs):
        with safe_raises(ignore_excs) as info:
            data.modify(path, value, **kwargs)
        if info:
            return
        assert data.retrieve(path, return_raw_value=True) == value

    DeleteTests = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": ConfigData({"foo": {"bar": "value"}}), "b": ConfigData({"foo": {"bar": False}})},
            ), "foo\\.bar", False, (), {}),
            (_ccd_from_meta(
                {"members": [dict(filename="a", alias="c"), "b"], "order": ["c"]},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({"key": "value"})},
            ), "key", Unset, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "orders": {"delete": ["b", "a"], "read": ["a", "b"]}},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({"key": "value"})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": ConfigData({}), "b": ConfigData({"key": False}), "c": ConfigData({"key": None})},
            ), "\\{c\\}\\.key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": ConfigData({"key": False}), "b": ConfigData({"key": True})},
            ), "\\{c\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": ConfigData({"key": False}), "b": ConfigData({"key": None})},
            ), "\\{z\\}\\.key", Unset, (RequiredPathNotFoundError,), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "order": []},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({"key": "value"})},
            ), "key", Unset, (RequiredPathNotFoundError,), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": ConfigData({}), "b": ConfigData({})},
            ), "key", Unset, (RequiredPathNotFoundError,), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_delete(data, path, value, ignore_excs, kwargs):
        with safe_raises(ignore_excs) as info:
            data.delete(path, **kwargs)
        if info:
            return
        assert data.get(path, value) == value

    UnsetTests = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": ConfigData({"foo": {"bar": "value"}}), "b": ConfigData({"foo": {"bar": False}})},
            ), "foo\\.bar", False, (), {}),
            (_ccd_from_meta(
                {"members": [dict(filename="a", alias="c"), "b"], "order": ["c"]},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({"key": "value"})},
            ), "key", Unset, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "orders": {"delete": ["b", "a"], "read": ["a", "b"]}},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({"key": "value"})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "order": []},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({"key": "value"})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": ConfigData({}), "b": ConfigData({})},
            ), "key", "value", (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": ConfigData({}), "b": ConfigData({"key": False}), "c": ConfigData({"key": None})},
            ), "\\{c\\}\\.key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": ConfigData({"key": False}), "b": ConfigData({"key": True})},
            ), "\\{c\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": ConfigData({"key": False}), "b": ConfigData({"key": None})},
            ), "\\{z\\}\\.key", Unset, (), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*UnsetTests)
    def test_unset(data, path, value, ignore_excs, kwargs):
        with safe_raises(ignore_excs) as info:
            data.unset(path, **kwargs)
        if info:
            return
        assert data.get(path, value) == value

    ExistsTests = (
        "data, path, is_exists, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": ConfigData({"foo": {"bar": None}}), "b": ConfigData({"foo": {"bar": {"quz": None}}})},
            ), "foo\\.bar\\.quz", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": ConfigData({"foo": {"bar": None}}), "b": ConfigData({"foo": {"bar": {"quz": None}}})},
            ), "foo\\.bar\\.quz", True, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": ConfigData({}), "b": ConfigData({})},
            ), "key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({})},
            ), "key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": ConfigData({"key": "value"}), "b": ConfigData({})},
            ), "key", False, (), {}),
            (_ccd_from_meta(
                {},
                {},
            ), "key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": ConfigData({}), "b": ConfigData({"key": False}), "c": ConfigData({"key": None})},
            ), "\\{c\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b", "c"]},
                {"a": ConfigData({"key": False}), "b": ConfigData({}), "c": ConfigData({"key": None})},
            ), "\\{b\\}\\.key", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": ConfigData({"key": False}), "b": ConfigData({"key": True})},
            ), "\\{c\\}\\.key", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": ConfigData({"key": False}), "b": ConfigData({"key": True})},
            ), "\\{c\\}\\.any", False, (), {}),
            (_ccd_from_meta(
                {"members": ["b", dict(filename="a", alias="c")]},
                {"a": ConfigData({"key": False}), "b": ConfigData({"key": None})},
            ), "\\{z\\}\\.key", False, (), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*ExistsTests)
    def test_exists(data, path, is_exists, ignore_excs, kwargs):
        with safe_raises(ignore_excs):
            assert data.exists(path, **kwargs) is is_exists

    GetTests = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {},
                {},
            ), "value", None, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": ConfigData({"foo": {"bar": True}}), "b": ConfigData({"foo": {"bar": False}})},
            ), "foo\\.bar", True, (), {}),
            (_ccd_from_meta(
                {"members": ["b", "a"]},
                {"a": ConfigData({"foo": {"bar": True}}), "b": ConfigData({"foo": {"bar": False}})},
            ), "foo\\.bar", False, (), {}),
            (_ccd_from_meta(
                {},
                {},
            ), "value", None, (), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*GetTests)
    def test_get(data, path, value, ignore_excs, kwargs):
        with safe_raises(ignore_excs):
            assert data.get(path, value, **kwargs) == value

    SetDefaultTests = (
        "data, path, value, ignore_excs, kwargs", (
            (_ccd_from_meta(
                {"members": ["a", "b"]},
                {"a": ConfigData({}), "b": ConfigData({})}
            ), "test\\.path", None, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "orders": {"create": ["b", "a"], "read": ["a", "b"]}},
                {"a": ConfigData({}), "b": ConfigData({})}
            ), "test\\.path", True, (), {}),
            (_ccd_from_meta(
                {"members": ["a", "b"], "orders": {"create": ["b", "a"], "read": ["a", "b"]}},
                {"a": ConfigData({}), "b": ConfigData({"test": {"path": None}})}
            ), "test\\.path", False, (AssertionError,), {}),
            (_ccd_from_meta(
                {},
                {}
            ), "test\\.path", None, (RequiredPathNotFoundError,), {}),
        )
    )

    @staticmethod
    @mark.parametrize(*SetDefaultTests)
    def test_set_default(data, path, value, ignore_excs, kwargs):
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
    def test_eq(a, b):
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
    def test_str(members):
        assert str(members) in str(_ccd_from_members(members))

    @staticmethod
    @mark.parametrize("members", (
            {},
            {"a": MappingConfigData()},
            {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
    ))
    def test_repr(members):
        ccd = _ccd_from_members(members)
        assert repr(members) in repr(ccd)

    @staticmethod
    @mark.parametrize("members", (
            {},
            {"a": MappingConfigData()},
            {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
    ))
    def test_deepcopy(members):
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
    def test_contains(members, key):
        assert (key in _ccd_from_members(members)) is (key in members)

    @staticmethod
    @mark.parametrize("members", (
            {"a": MappingConfigData(), "b": MappingConfigData()},
            {"a": MappingConfigData({"foo": "bar"}), "b": MappingConfigData({"foo": "quz"})},
            {"a": MappingConfigData({"foo": {"extra": "value"}}), "b": MappingConfigData({"foo": {"key": "value"}})},
    ))
    def test_iter(members):
        assert list(_ccd_from_members(members)) == list(members.keys())

    @staticmethod
    @mark.parametrize("members", (
            {},
            {"a": MappingConfigData()},
            {"a": MappingConfigData(), "b": MappingConfigData()},
            {"a": MappingConfigData(), "b": MappingConfigData(), "c": MappingConfigData()},
    ))
    def test_len(members):
        assert len(_ccd_from_members(members)) == len(members)

    @staticmethod
    @mark.parametrize("members, key", (
            ({}, 'key'),
            ({"a": MappingConfigData({"key": "a"})}, "a"),
            ({"a": MappingConfigData({"key": "a"}), "b": MappingConfigData({"key": "b"})}, "b"),
    ))
    def test_getitem(members, key):
        ignore_excs = []
        if key not in members:
            ignore_excs.append(KeyError)

        with safe_raises(tuple(ignore_excs)):
            assert _ccd_from_members(members)[key] == members[key]

    @staticmethod
    @mark.parametrize("members, key, value", (
            ({}, 'key', MappingConfigData()),
            ({"a": MappingConfigData()}, "a", MappingConfigData({"key": "value"})),
            ({"a": MappingConfigData()}, "b", MappingConfigData()),
    ))
    def test_setitem(members, key, value):
        ccd = _ccd_from_members(members)
        ccd[key] = value
        assert ccd[key] == value

    @staticmethod
    @mark.parametrize("members, key", (
            ({}, "key"),
            ({"a": MappingConfigData()}, "a"),
            ({"a": MappingConfigData(), "b": MappingConfigData()}, "a"),
    ))
    def test_delitem(members, key):
        ccd = _ccd_from_members(members)
        ignore_excs = []
        if key not in members:
            ignore_excs.append(KeyError)

        with safe_raises(tuple(ignore_excs)):
            del ccd[key]
        assert key not in ccd


def _insert_operator(tests, op, iop: Optional[Callable] = None, *ext):
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
def test_unary_operator(a, op):
    assert (op(ConfigData(a)) == op(a)
            ), f"op({ConfigData(a):r}) != {op(a)}"


DyadicOperatorTests = (
    "a, b, op, iop, inplace_reverse_raw", (
        *_insert_operator(TestMappingConfigData.MergeTests, operator.or_, operator.ior, True),
        *_insert_operator(TestSequenceConfigData.RepeatTests, operator.mul, operator.imul, False),
        *_insert_operator(TestSequenceConfigData.ExtendTests, operator.add, operator.iadd, False),
    ),
)


@mark.parametrize(*DyadicOperatorTests)
def test_dyadic_operator(a, b, op, iop, inplace_reverse_raw):
    inplace_reverse_raw = (lambda _: _) if inplace_reverse_raw else ConfigData
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
    assert (iop(deepcopy(a), ConfigData(b)) == inplace_reverse_raw(iop(deepcopy(a), b))
            ), f"iop({deepcopy(a)}, {ConfigData(b):r}) != {inplace_reverse_raw(iop(deepcopy(a), b)):r}"
    assert (iop(ConfigData(deepcopy(a)), b) == ConfigData(iop(deepcopy(a), b))
            ), f"iop({ConfigData(deepcopy(a)):r}, {b}) != {ConfigData(iop(deepcopy(a), b)):r}"


def test_wrong_type_config_data():
    class EmptyTypesConfigData(ConfigData):
        TYPES = {}

    with raises(TypeError, match="Unsupported type"):
        EmptyTypesConfigData(type)


class TestConfigFile:
    @staticmethod
    @fixture
    def data():
        return ConfigData({
            "foo": {
                "bar": 123
            },
            "foo1": 114,
            "foo2": ["bar"]
        })

    @staticmethod
    @fixture
    def file(data):
        return ConfigFile(data, config_format="json")

    @staticmethod
    @fixture
    def pool(tmpdir):
        return ConfigPool(root_path=tmpdir)

    @staticmethod
    def test_attr_readonly(file, data):
        assert file.config == data
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.config = None

        assert file.config_format == "json"
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.config_format = None

    @staticmethod
    def test_wrong_save(data, pool):
        file = ConfigFile(data)
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: Unknown"):
            file.save(pool, '', ".json")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.save(pool, '', ".json", config_format="json")

    @staticmethod
    def test_wrong_load(file, pool):
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.load(pool, '', ".json", config_format="json")

    @staticmethod
    def test_wrong_initialize(file, pool):
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.initialize(pool, '', ".json", config_format="json")

    ExtraKwargs = (
        {"config_format": "json"},
    )

    CombExtraKwargs = []
    for i in range(1, len(ExtraKwargs) + 1):
        CombExtraKwargs.extend(
            functools.reduce(
                operator.or_,
                kwargs_tuple
            ) for kwargs_tuple in itertools.combinations(ExtraKwargs, i)
        )

    CombEQKwargs = tuple(d[0] | k for d, k in itertools.product(
        itertools.product((
            {"initial_config": {"foo": {"bar": 123}}},
            {"initial_config": {"foo": {"bar": 456}}},
        )),
        CombExtraKwargs
    ))

    EQTests = ("a, b, is_eq", tuple(
        ((ConfigFile(**a), ConfigFile(**b), a == b) for a, b in itertools.product(CombEQKwargs, CombEQKwargs))
    ))

    @staticmethod
    @mark.parametrize(*EQTests)
    def test_eq(a: ConfigFile, b: ConfigFile, is_eq: bool):
        assert (a == b) is is_eq

    @staticmethod
    def test_eq_diff_type(file):
        assert file != NotImplemented

    @staticmethod
    @mark.parametrize("raw_data, is_empty", (
            ({}, True),
            ({"foo": 123}, False),
    ))
    def test_bool(raw_data, is_empty):
        assert bool(ConfigFile(ConfigData(raw_data))) is not is_empty

    @staticmethod
    def test_repr(file, data):
        assert repr(file.config) in repr(file)
        assert repr(data) in repr(ConfigFile(data))
