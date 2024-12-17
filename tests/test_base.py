# -*- coding: utf-8 -*-


import functools
import itertools
import operator
from collections import OrderedDict
from copy import deepcopy

from pyrsistent import pmap
from pytest import fixture
from pytest import mark
from pytest import raises

from C41811.Config import ConfigData
from C41811.Config import ConfigFile
from C41811.Config import ConfigPool
from C41811.Config.errors import ConfigDataTypeError
from C41811.Config.errors import RequiredPathNotFoundError
from C41811.Config.errors import UnsupportedConfigFormatError
from utils import safe_raises


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
            }),
            (r"\\.\[\]", None),
        ))

    @staticmethod
    @fixture
    def data(odict):
        return ConfigData(odict)

    @staticmethod
    @fixture
    def readonly_odict(odict):
        return pmap(odict)

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
        "path,         value,                      ignore_excs,                  kwargs", (  # @formatter:off # noqa: E122
        ("foo",        ConfigData({"bar": 123}),   (),                           {}),
        ("foo",        {"bar": 123},               (),                           {"get_raw": True}),
        ("foo\\.bar",  123,                        (),                           {}),
        ("foo1",       114,                        (),                           {}),
        ("foo2",       ["bar"],                    (),                           {}),
        ("foo2\\.bar", None,                       (ConfigDataTypeError, ),      {}),
        ("foo3",       None,                       (RequiredPathNotFoundError,), {}),
    ))  # @formatter:on

    @staticmethod
    @mark.parametrize(*RetrieveTests)
    def test_retrieve(data, path, value, ignore_excs, kwargs):
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs) as info:
            result = data.retrieve(path, **kwargs)
        if not info:
            assert result == value

    ModifyTests = (
        "path,         value,        ignore_excs,                  kwargs", (  # @formatter:off # noqa: E122
        ("foo",        {"bar": 456}, (),                           {}),
        ("foo\\.bar",  123,          (),                           {}),
        ("foo1",       114,          (),                           {}),
        ("foo2",       ["bar"],      (),                           {}),
        ("foo2\\.bar", None,         (ConfigDataTypeError,),       {}),
        ("foo3",       None,         (),                           {}),
        ("foo3",       None,         (RequiredPathNotFoundError,), {"allow_create": False}, ),
    ))  # @formatter:on

    @staticmethod
    @mark.parametrize(*ModifyTests)
    def test_modify(data, path, value, ignore_excs, kwargs):
        if kwargs is None:
            kwargs = {}

        with safe_raises(ignore_excs) as info:
            data.modify(path, value, **kwargs)
            result = data.retrieve(path, get_raw=True)
        if not info:
            assert result == value

    DeleteTests = (
        "path,         ignore_excs", (  # @formatter:off # noqa: E122
        ("foo\\.bar",  ()),
        ("foo1",       ()),
        ("foo2",       ()),
        ("foo2\\.bar", (ConfigDataTypeError, )),
        ("foo3",       (RequiredPathNotFoundError,)),
    ))  # @formatter:on

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_delete(data, path, ignore_excs):
        with safe_raises(ignore_excs):
            data.delete(path)
        assert path not in data

    @staticmethod
    @mark.parametrize(*DeleteTests)
    def test_unset(data, path, ignore_excs):
        ignore_excs = tuple(exc for exc in ignore_excs if not issubclass(exc, RequiredPathNotFoundError))
        with safe_raises(ignore_excs):
            data.unset(path)
        assert path not in data

    ExistsTests = (
        "path,              is_exist, ignore_excs", (  # @formatter:off # noqa: E122
        ("foo",             True,     ()),
        ("foo\\.bar",       True,     ()),
        ("foo\\.not exist", False,    ()),
        ("foo1",            True,     ()),
        ("foo2",            True,     ()),
        ("foo2\\.bar",      None,    (ConfigDataTypeError,)),
        ("foo3",            False,    ()),
    ))  # @formatter:on

    @staticmethod
    @mark.parametrize(*ExistsTests)
    def test_exists(data, path, is_exist, ignore_excs):
        with safe_raises(ignore_excs) as info:
            exists = data.exists(path)
        if not info:
            assert exists == is_exist

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

        if any(issubclass(exc, KeyError) for exc in ignore_excs):
            ignore_excs = tuple(exc for exc in ignore_excs if not issubclass(exc, KeyError))
            value = None

        with safe_raises(ignore_excs) as info:
            result = data.get(path, **kwargs)
        if not info:
            assert result == value

    SetDefaultTests = (
        RetrieveTests[0],
        (
            *((*x[:3], x[3] | {"get_raw": True}) for x in RetrieveTests[1]),  # @formatter:off
            # path               value            ignore_excs             kwargs
            ("not exist",        "default value", (),                     {"default": "default value"}),
            ("foo\\.not exist",  "default value", (),                     {"default": "default value"}),
            ("foo2\\.not exist", "default value", (ConfigDataTypeError,), {"default": "default value"}),
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

        with safe_raises(ignore_excs):
            assert data.set_default(path, **kwargs) in value
            assert data.exists(path)
            assert data.retrieve(path, get_raw=True) in value

    GetItemTests = (
        "path, value", (
            ("foo", ConfigData({"bar": 123}),),
            ("foo1", 114,),
            ("foo2", ["bar"],),
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
    def test_readonly_attr(data, readonly_data):
        assert readonly_data.read_only
        with raises(TypeError):
            readonly_data.read_only = False

        assert not data.read_only
        data.read_only = True
        assert data.read_only
        with raises(TypeError):
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
        cls.test_modify(readonly_data, path, value, TypeError, kwargs)

    ReadOnlyDeleteTests = (
        ', '.join(arg for arg in DeleteTests[0].split(', ') if "ignore_excs" not in arg),
        tuple(x[:-1] for x in DeleteTests[1])
    )

    @classmethod
    @mark.parametrize(*ReadOnlyDeleteTests)
    def test_readonly_delete(cls, readonly_data, path):
        cls.test_delete(readonly_data, path, TypeError)

    @classmethod
    @mark.parametrize(*ReadOnlyDeleteTests)
    def test_readonly_unset(cls, readonly_data, path):
        cls.test_unset(readonly_data, path, (TypeError,))

    @staticmethod
    def test_eq(data, readonly_data):
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
            ({"get_raw": True}, [{"bar": 123}, 114, ["bar"], {'b': 1, 'c': {'d': 2, 'e': {'f': 3}}}, None]),
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
        ({"get_raw": True}, [
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
        assert file.data == data
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.data = None

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
            {"config_data": {"foo": {"bar": 123}}},
            {"config_data": {"foo": {"bar": 456}}},
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
