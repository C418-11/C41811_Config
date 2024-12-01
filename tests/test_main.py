# -*- coding: utf-8 -*-
from collections import OrderedDict
from collections.abc import Mapping
from copy import deepcopy
from typing import MutableMapping
from pytest import fixture, mark, raises
from pydantic import BaseModel, Field
import sys
import os.path

import importlib.util

try:
    if importlib.util.find_spec("C41811.Config") is None:
        raise ModuleNotFoundError
except ModuleNotFoundError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from C41811.Config import ConfigData
from C41811.Config import ConfigFile
from C41811.Config import RequiredPath
from C41811.Config.errors import ConfigDataTypeError
from C41811.Config.errors import RequiredPathNotFoundError


class ReadOnlyMapping(Mapping):
    def __init__(self, dictionary: MutableMapping):
        self._data = dictionary

    def __getitem__(self, __key):
        return self._data[__key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


class TestConfigData:

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
            })
        ))

    @staticmethod
    @fixture
    def data(odict):
        return ConfigData(odict)

    @staticmethod
    @fixture
    def readonly_odict(odict):
        return ReadOnlyMapping(odict)

    @staticmethod
    @fixture
    def readonly_data(readonly_odict):
        return ConfigData(readonly_odict)

    @staticmethod
    def test_init_deepcopy(odict, readonly_odict):
        data = ConfigData(odict)
        assert data.data is not odict
        assert data.data == odict

        readonly_data = ConfigData(readonly_odict)
        assert readonly_data.data is not readonly_odict
        assert readonly_data.data == readonly_odict

    RetrieveTests = (
        "path,       value,                    ignore_excs,                  kwargs", (  # @formatter:off # noqa: E122
        ("foo",      ConfigData({"bar": 123}), (),                           {}),
        ("foo",      {"bar": 123},             (),                           {"get_raw": True}),
        ("foo.bar",  123,                      (),                           {}),
        ("foo1",     114,                      (),                           {}),
        ("foo2",     ["bar"],                  (),                           {}),
        ("foo2.bar", None,                     (ConfigDataTypeError, ),      {}),
        ("foo3",     None,                     (RequiredPathNotFoundError,), {}),
    ))  # @formatter:on

    @staticmethod
    @mark.parametrize(*RetrieveTests)
    def test_retrieve(data, path, value, ignore_excs, kwargs):
        if kwargs is None:
            kwargs = {}
        if not ignore_excs:
            assert data.retrieve(path, **kwargs) == value
            return

        with raises(ignore_excs):
            assert data.retrieve(path, **kwargs) == value

    ModifyTests = (
        "path,       value,        ignore_excs,                  kwargs", (  # @formatter:off # noqa: E122
        ("foo",      {"bar": 456}, (),                           {}),
        ("foo.bar",  123,          (),                           {}),
        ("foo1",     114,          (),                           {}),
        ("foo2",     ["bar"],      (),                           {}),
        ("foo2.bar", None,         (ConfigDataTypeError,),       {}),
        ("foo3",     None,         (),                           {}),
        ("foo3",     None,         (RequiredPathNotFoundError,), {"allow_create": False}, ),
    ))  # @formatter:on

    @staticmethod
    @mark.parametrize(*ModifyTests)
    def test_modify(data, path, value, ignore_excs, kwargs):
        if kwargs is None:
            kwargs = {}
        if not ignore_excs:
            data.modify(path, value, **kwargs)
            assert data.retrieve(path, get_raw=True) == value
            return

        with raises(ignore_excs):
            data.modify(path, value, **kwargs)
            assert data.retrieve(path, get_raw=True) == value

    DeleteTests = (
        "path,       ignore_excs", (  # @formatter:off # noqa: E122
        ("foo.bar",  ()),
        ("foo1",     ()),
        ("foo2",     ()),
        ("foo2.bar", (ConfigDataTypeError, )),
        ("foo3",     (RequiredPathNotFoundError,)),
    ))  # @formatter:on

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_delete(data, path, ignore_excs):
        if not ignore_excs:
            data.delete(path)
            assert path not in data
            return

        with raises(ignore_excs):
            data.delete(path)
            assert path not in data

    ExistsTests = (
        "path,            is_exist, ignore_excs", (  # @formatter:off # noqa: E122
        ("foo",           True,     ()),
        ("foo.bar",       True,     ()),
        ("foo.not exist", False,    ()),
        ("foo1",          True,     ()),
        ("foo2",          True,     ()),
        ("foo2.bar",      None,    (ConfigDataTypeError,)),
        ("foo3",          False,    ()),
    ))  # @formatter:on

    @staticmethod
    @mark.parametrize(*ExistsTests)
    def test_exists(data, path, is_exist, ignore_excs):
        if not ignore_excs:
            assert data.exists(path) == is_exist
            return

        with raises(ignore_excs):
            assert data.exists(path) == is_exist

    GetTests = (
        RetrieveTests[0],
        (
            *RetrieveTests[1],  # @formatter:off
            # path             value            ignore_excs             kwargs
            ("not exist",      "default value", (),                     {"default": "default value"}),
            ("foo.not exist",  "default value", (),                     {"default": "default value"}),
            ("foo2.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
        )  # @formatter:on
    )

    @staticmethod
    @mark.parametrize(*GetTests)
    def test_get(data, path, value, ignore_excs, kwargs):
        if kwargs is None:
            kwargs = {}

        if any(issubclass(exc, KeyError) for exc in ignore_excs):
            ignore_excs = tuple(exc for exc in ignore_excs if not issubclass(exc, KeyError))
            value = None

        if not ignore_excs:
            assert data.get(path, **kwargs) == value
            return

        with raises(ignore_excs):
            assert data.get(path, **kwargs) == value

    SetDefaultTests = (
        RetrieveTests[0],
        (
            *((*x[:3], x[3] | {"get_raw": True}) for x in RetrieveTests[1]),  # @formatter:off
            # path             value            ignore_excs             kwargs
            ("not exist",      "default value", (),                     {"default": "default value"}),
            ("foo.not exist",  "default value", (),                     {"default": "default value"}),
            ("foo2.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
        )  # @formatter:on
    )

    @staticmethod
    @mark.parametrize(*GetTests)
    def test_set_default(data, path, value, ignore_excs, kwargs):
        ignore_excs = tuple(exc for exc in ignore_excs if not issubclass(exc, KeyError))
        if "default" in kwargs:
            value = [value, kwargs["default"]]
        else:
            value = value,

        if data.exists(path, ignore_wrong_type=True):
            value = *value, data.retrieve(path, get_raw=True)

        if not ignore_excs:
            assert data.set_default(path, **kwargs) in value
            assert path in data
            assert data.retrieve(path, get_raw=True) in value
            return

        with raises(ignore_excs):
            assert data.set_default(path, **kwargs) in value
            assert path in data
            assert data.retrieve(path, get_raw=True) in value

    @staticmethod
    @mark.parametrize(
        "path, value", (
                ("foo", ConfigData({"bar": 123}),),
                ("foo.bar", 123,),
                ("foo1", 114,),
                ("foo2", ["bar"],),
        ))
    def test_getitem(data, path, value):
        assert data[path] == value

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
    @mark.parametrize(*DeleteTests)
    def test_delitem(data, path, ignore_excs):
        if not ignore_excs:
            del data[path]
            assert path not in data
            return

        with raises(ignore_excs):
            del data[path]
            assert path not in data

    @staticmethod
    @mark.parametrize(*ExistsTests)
    def test_contains(data, path, is_exist, ignore_excs):
        if not ignore_excs:
            assert (path in data) == is_exist
            return

        with raises(ignore_excs):
            assert (path in data) == is_exist

    @staticmethod
    def test_readonly_attr(data, readonly_data):
        assert not data.read_only
        assert readonly_data.read_only

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
        cls.test_modify(readonly_data, path, value, TypeError, kwargs)

    ReadOnlyDeleteTests = (
        ', '.join(arg for arg in DeleteTests[0].split(', ') if "ignore_excs" not in arg),
        tuple(x[:-1] for x in DeleteTests[1])
    )

    @classmethod
    @mark.parametrize(*ReadOnlyDeleteTests)
    def test_readonly_delete(cls, readonly_data, path):
        cls.test_delete(readonly_data, path, TypeError)

    @staticmethod
    def test_eq(data, readonly_data):
        assert data == readonly_data

    @staticmethod
    def test_deepcopy(data):
        last_data = deepcopy(data)
        data["foo.bar"] = 456
        assert last_data != data

    KeysTests = ("kwargs, keys", (
        ({}, {"a", "foo", "foo1", "foo2"}),
        ({"recursive": True}, {"a.c.e.f", "a.c", 'a', "a.c.d", "foo.bar", "a.c.e", "foo", "foo1", "a.b", "foo2"}),
        ({"end_point_only": True}, {"foo1", "foo2"}),
        ({"recursive": True, "end_point_only": True}, {'a.c.d', 'foo.bar', 'foo2', 'a.b', 'a.c.e.f', 'foo1'})
    ))

    @staticmethod
    @mark.parametrize(*KeysTests)
    def test_keys(data, kwargs, keys):
        assert set(data.keys(**kwargs)) == keys

    ValuesTests = (
        "kwargs, values",
        (
            ({}, [ConfigData({"bar": 123}), 114, ["bar"], ConfigData({'b': 1, 'c': {'d': 2, 'e': {'f': 3}}})]),
            ({"get_raw": True}, [{"bar": 123}, 114, ["bar"], {'b': 1, 'c': {'d': 2, 'e': {'f': 3}}}]),
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
        ]),
        ({"get_raw": True}, [
            ("foo", {"bar": 123}),
            ("foo1", 114),
            ("foo2", ["bar"]),
            ("a", {'b': 1, 'c': {'d': 2, 'e': {'f': 3}}}),
        ]),
    ))

    @staticmethod
    @mark.parametrize(*ItemsTests)
    def test_items(data, kwargs, items):
        assert list(data.items(**kwargs)) == items


class TestRequiredKey:
    @staticmethod
    @fixture
    def data():
        return ConfigData({
            "foo": {"bar": 123, "bar1": 456},
            "foo1": 114,
            "foo2": ["bar"],
        })

    @staticmethod
    @fixture
    def readonly_data(data):
        return RequiredPath(data, "readonly")

    @staticmethod
    @fixture
    def pydantic_model():
        class Foo(BaseModel):
            bar: int = Field(123)
            bar1: int = Field(456)

        class Data(BaseModel):
            foo: Foo = Field(default_factory=Foo)
            foo1: int
            foo2: list[str]

        return Data

    PydanticTests = "path, value", (
        ("foo", ConfigData({"bar": 123, "bar1": 456})),
        ("foo.bar", 123),
        ("foo1", 114),
        ("foo2", ["bar"]),
    )

    # @classmethod
    # @fixture(autouse=True, scope="function")
    # def __preload(cls, data, pydantic_model):
    #     if hasattr(cls, "cached") and cls.cached:
    #         return
    #     cls.cached = True
    #
    #     def _arg_tool(tests: tuple[str, tuple[tuple, ...]]):
    #         keys = tests[0].replace(' ', '').split(',')
    #         for args in tests[1]:
    #             yield dict(zip(keys, args))
    #
    #     def _test_all(func, *args, tests):
    #         for kwargs in _arg_tool(tests):
    #             # noinspection PyBroadException
    #             try:
    #                 func(*(deepcopy(a) for a in args), **kwargs)
    #             except Exception:
    #                 pass
    #
    #     _test_all(cls.test_pydantic, data, pydantic_model, tests=cls.PydanticTests)
    #     _test_all(cls.test_pydantic_with_error, data, tests=('', ()))
    #     _test_all(cls.test_default_iterable, data, tests=cls.IterableTests)
    #     _test_all(cls.test_default_mapping, data, tests=cls.MappingTests)

    @staticmethod
    @mark.parametrize("path, value", (
            ("foo", ConfigData({"bar": 123, "bar1": 456})),
            ("foo.bar", 123),
            ("foo1", 114),
            ("foo2", ["bar"]),
    ))
    def test_pydantic(data, pydantic_model, path, value):

        data = RequiredPath(pydantic_model, "pydantic").filter(data)
        assert data[path] == value

    @staticmethod
    def test_pydantic_with_error(data):
        class NotExist(BaseModel):
            foo3: int

        with raises(RequiredPathNotFoundError):
            RequiredPath(NotExist, "pydantic").filter(data)

        class NotExist2(BaseModel):
            foo: NotExist

        with raises(RequiredPathNotFoundError):
            RequiredPath(NotExist2, "pydantic").filter(data)

        class WrongType(BaseModel):
            foo: str

        with raises(ConfigDataTypeError):
            RequiredPath(WrongType, "pydantic").filter(data)

        class WrongType2(BaseModel):
            foo2: list[int]

        with raises(ConfigDataTypeError):
            RequiredPath(WrongType2, "pydantic").filter(data)

    IterableTests = ("paths, values, kwargs, ignore_excs", (
        (
            ["foo", "foo1", "foo2"],
            [ConfigData({"bar": 123, "bar1": 456}), 114, ["bar"]],
            {}, ()
        ),
        (
            ["foo", "foo.bar"],
            [ConfigData({"bar": 123, "bar1": 456}), 123],
            {}, ()
        ),
        (
            ["foo.bar", "foo"],  # 无论顺序先后都应该在父路径单独存在时包含父路径下的所有子路径
            [123, ConfigData({"bar": 123, "bar1": 456})],
            {}, ()
        ),
        (
            ["foo2.bar"],
            [987],
            {}, (ConfigDataTypeError,)
        ),
        (
            ["foo.bar2"],
            [987],
            {}, (RequiredPathNotFoundError,)
        ),
        (
            ["foo.bar2"],
            [987],
            {"allow_create": True}, (RequiredPathNotFoundError,)  # 因为没有默认值所以即便allow_create=True也会报错
        ),
        (
            ["foo.bar2", "foo1"],
            [float("-inf"), 114],  # -inf是占位符,表示该值可以不存在
            {"ignore_missing": True}, ()
        ),
        (
            ["foo2.bar", "foo1"],
            [float("-inf"), 114],
            {"ignore_missing": True, "allow_create": True}, (ConfigDataTypeError,)
        )
    ))

    @staticmethod
    @mark.parametrize(*IterableTests)
    def test_default_iterable(data, paths, values, kwargs, ignore_excs):
        if ignore_excs:
            with raises(ignore_excs):
                RequiredPath(paths).filter(data, **kwargs)
            return

        data = RequiredPath(paths).filter(data, **kwargs)

        for path, value in zip(paths, values):
            if isinstance(value, float) and value == float("-inf"):
                assert path not in data
                continue
            assert data[path] == value

    MappingTests = ("mapping, result, kwargs, ignore_excs", (
        ({
             "foo": dict,
             "foo.bar": int,
             "foo1": int,
             "foo2": list[str],
         },
         {
             "foo": {"bar": 123, "bar1": 456},
             "foo1": 114,
             "foo2": ["bar"],
         }, {}, ()),
        ({
             "foo.bar": 111,
             "foo": dict,
             "foo1": 222,
             "foo2": [333],
             "foo3.bar": 789,
             "foo3.test.value": 101112,
             "foo4": {
                 "bar": 789,
                 "test": {
                     "value": 101112,
                 }
             }
         },
         {
             "foo": {"bar": 123, "bar1": 456},
             "foo1": 114,
             "foo2": ["bar"],
             "foo3": {
                 "bar": 789,
                 "test": {
                     "value": 101112,
                 }
             },
             "foo4": {
                 "bar": 789,
                 "test": {
                     "value": 101112,
                 }
             }
         }, {"allow_create": True}, ()),
        ({
             "foo.bar": int,
             "foo": dict,
             "foo1": int,
             "foo2": list[str],
             "foo3": {
                 "bar": int,
                 "test": {
                     "value": 101112,
                 }
             }
         },
         {
             "foo": {"bar": 123, "bar1": 456},
             "foo1": 114,
             "foo2": ["bar"],
             "foo3": {
                 "test": {
                     "value": 101112,
                 }
             }
         }, {"allow_create": True, "ignore_missing": True}, ()),
        ({
             "foo.bar.baz": int,
         },
         {},
         {"ignore_missing": True}, (ConfigDataTypeError,))
    ))

    @staticmethod
    @mark.parametrize(*MappingTests)
    def test_default_mapping(data, mapping, result, kwargs, ignore_excs):
        if ignore_excs:
            with raises(ignore_excs):
                RequiredPath(mapping).filter(data, **kwargs)
            return

        data = RequiredPath(mapping).filter(data, **kwargs)
        assert data.data == result


class TestConfigFile:
    @fixture
    def file(self):
        return ConfigFile(ConfigData({
            "foo": {
                "bar": 123
            },
            "foo1": 114,
            "foo2": ["bar"]
        }), namespace='ns', file_name='f')

    @staticmethod
    def test_attr_readonly(file):
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.namespace = None

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.data = None

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.file_name = None

        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.config_format = None

    @staticmethod
    @mark.parametrize("file, is_empty", (
            (ConfigFile(ConfigData({})), True),
            (ConfigFile(ConfigData({"foo": 123})), False),
    ))
    def test_bool(file, is_empty):
        assert bool(file) is not is_empty
