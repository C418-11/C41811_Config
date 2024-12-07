# -*- coding: utf-8 -*-


import contextlib
import functools
import itertools
import operator
import time
from collections import OrderedDict
from collections.abc import Mapping
from copy import deepcopy
from decimal import Decimal
from typing import MutableMapping

from pydantic import BaseModel
from pydantic import Field
from pytest import fixture
from pytest import mark
from pytest import raises
from pytest import warns

from C41811.Config import AttrKey
from C41811.Config import ConfigData
from C41811.Config import ConfigFile
from C41811.Config import ConfigPool
from C41811.Config import IndexKey
from C41811.Config import Path
from C41811.Config import PathSyntaxParser
from C41811.Config import RequiredPath
from C41811.Config import ValidatorFactoryConfig
from C41811.Config.errors import ConfigDataPathSyntaxException
from C41811.Config.errors import ConfigDataTypeError
from C41811.Config.errors import RequiredPathNotFoundError
from C41811.Config.errors import UnknownTokenType


class ReadOnlyMapping(Mapping):
    def __init__(self, dictionary: MutableMapping):
        self._data = dictionary

    def __getitem__(self, __key):
        return self._data[__key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


@contextlib.contextmanager
def safe_raises(expected_exception, *args, **kwargs):
    if not expected_exception:
        yield None
        return

    with raises(expected_exception, *args, **kwargs) as err:
        yield err


@contextlib.contextmanager
def safe_warns(expected_warning, *args, **kwargs):
    if not expected_warning:
        yield None
        return

    with warns(expected_warning, *args, **kwargs) as warn:
        yield warn


class TestKey:
    @staticmethod
    @mark.parametrize("key, other", (
            (IndexKey(0), 0),
            (IndexKey(99), 99),
            (AttrKey("aaa"), "aaa"),
            (AttrKey("bcd"), "bcd"),
    ))
    def test_both(key, other):
        assert key.key == other
        assert hash(key) == hash(other)
        assert str(key) == str(other)
        assert key == deepcopy(key)
        assert key != NotImplemented

    @staticmethod
    @mark.parametrize("key, other", (
            (AttrKey("aaa"), "aaa"),
            (AttrKey("bcd"), "bcd"),
    ))
    def test_attr_key(key, other):
        assert len(key) == len(other)
        assert key == other


class TestPath:
    @staticmethod
    @fixture
    def path():
        return Path.from_str(r"\.aaa\.bbb\.ccc\[0\]\.ddd\.eee\[1\]")

    @staticmethod
    @mark.parametrize("locate, keys, ignore_excs", (
            (["aaa", 0, "bbb"], [AttrKey("aaa"), IndexKey(0), AttrKey("bbb")], ()),
            ([2, "aaa"], [IndexKey(2), AttrKey("aaa")], ()),
            ([4, 2, "aaa"], [IndexKey(4), IndexKey(2), AttrKey("aaa")], ()),
            (["a", 1, None], None, (ValueError,)),
    ))
    def test_from_locate(locate, keys, ignore_excs):
        with safe_raises(ignore_excs) as info:
            path = Path.from_locate(locate)
        if not info:
            assert path == Path(keys)

    @staticmethod
    @mark.parametrize("index, value", (
            (0, AttrKey("aaa")),
            (1, AttrKey("bbb")),
            (2, AttrKey("ccc")),
            (3, IndexKey(0)),
            (4, AttrKey("ddd")),
            (5, AttrKey("eee")),
            (6, IndexKey(1)),
    ))
    def test_getitem(path, index, value):
        assert path[index] == value

    @staticmethod
    @mark.parametrize("key, is_contained", (
            (IndexKey(0), True),
            (IndexKey(1), True),
            (IndexKey(3), False),
            (AttrKey("aaa"), True),
            (AttrKey("bbb"), True),
            (AttrKey("ccc"), True),
            (AttrKey("ddd"), True),
            (AttrKey("eee"), True),
            (AttrKey("fff"), False),
    ))
    def test_contains(path, key, is_contained):
        assert (key in path) == is_contained

    @staticmethod
    @mark.parametrize("path, length", (
            (r"\.aaa", 1),
            (r"\[1\]\.ccc\[2\]", 3),
            (r"\.aaa\.bbb\.ccc\[0\]", 4),
            (r"\.aaa\.bbb\.ccc\[0\]\.ddd", 5),
            (r"\.aaa\.bbb\.ccc\[0\]\.ddd\.eee\[1\]\.fff", 8),
    ))
    def test_len(path, length):
        assert len(Path.from_str(path)) == length

    @staticmethod
    @mark.parametrize("path, keys", (
            (r"\.aaa", [AttrKey("aaa")]),
            (r"\[1\]\.ccc\[2\]", [IndexKey(1), AttrKey("ccc"), IndexKey(2)]),
            (r"\.aaa\.bbb\.ccc\[0\]", [AttrKey("aaa"), AttrKey("bbb"), AttrKey("ccc"), IndexKey(0)]),
            (r"\.aaa\.bbb\.ccc\[0\]\.ddd",
             [AttrKey("aaa"), AttrKey("bbb"), AttrKey("ccc"), IndexKey(0), AttrKey("ddd")]),
    ))
    def test_iter(path, keys):
        assert list(Path.from_str(path)) == keys

    @staticmethod
    @mark.parametrize("path", (
            r"\.aaa",
            r"\[1\]\.ccc\[2\]",
            r"\.aaa\.bbb\.ccc\[0\]",
            r"\.aaa\.bbb\.ccc\[0\]\.ddd",
    ))
    def test_eq(path):
        p = Path.from_str(path)
        assert p == deepcopy(p)
        assert p != NotImplemented


class TestPathSyntaxParser:
    @staticmethod
    @fixture
    def parser():
        return PathSyntaxParser()

    TokenizeTests = (
        "string, result, ignore_warns", (
            (
                r"\.a.a\\.a\.b\[c\]\[2\]\.e",
                [r"\.a.a\\.a", r"\.b", r"\[c", r"\]", r"\[2", r"\]", r"\.e"],
                ()
            ),
            (r"\[c\]\[d\]", [r"\[c", r"\]", r"\[d", r"\]"], ()),
            (r"\[c\]abc\[4\]", [r"\[c", r"\]", "abc", r"\[4", r"\]"], ()),
            (r"\[d\]abc", [r"\[d", r"\]", "abc"], ()),
            (r"abc\[e\]", ["abc", r"\[e", r"\]"], ()),
            ("abc", ["abc"], ()),
            (r"\.\a", [r"\.\a"], (SyntaxWarning,)),
            (r"\a\a", [r"\a\a"], (SyntaxWarning,)),
        )
    )

    @staticmethod
    @mark.parametrize(*TokenizeTests)
    def test_tokenize(parser, string, result, ignore_warns):
        with safe_warns(ignore_warns):
            tokenized = list(parser.tokenize(string))
        assert tokenized == result

    ParseTests = (
        "string, path_obj, ignore_excs, ignore_warns", (
            (
                r"\.a.a\\.a\.b\[18\]\[07\]\.e",
                [AttrKey(r"a.a\.a"), AttrKey('b'), IndexKey(18), IndexKey(7), AttrKey('e')],
                (), ()
            ),
            (r"\[2\]\[3\]", [IndexKey(2), IndexKey(3)], (), ()),
            (r"\[2\[3\]", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[2\]\.3\]", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[2\.3", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[2", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[a\]", None, (ValueError,), ()),
            (r"\.a\[2\]\.b\[3\]", [AttrKey('a'), IndexKey(2), AttrKey('b'), IndexKey(3)], (), ()),
            (r"\[4\]abc\[9\]", None, (UnknownTokenType,), ()),
            (r"\[5\]abc", None, (UnknownTokenType,), ()),
            (r"abc\[2\]", None, (UnknownTokenType,), ()),
            (r"abc", None, (UnknownTokenType,), ()),
            (r"\.\a", [AttrKey(r"\a")], (), (SyntaxWarning,)),
            (r"\a\a", None, (UnknownTokenType,), (SyntaxWarning,)),
        )
    )

    @staticmethod
    @mark.parametrize(*ParseTests)
    def test_parse(parser, string, path_obj, ignore_excs, ignore_warns):
        with safe_raises(ignore_excs) as e_info, safe_warns(ignore_warns):
            path = parser.parse(string)
        if not e_info:
            assert path == path_obj


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


class TestConfigPool:
    @staticmethod
    @fixture
    def pool():
        return ConfigPool()

    @staticmethod
    def test_root_path_attr(pool):
        assert pool.root_path
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            pool.root_path = ""


class TestRequiredPath:
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
    def pydantic_model():
        class Foo(BaseModel):
            bar: int = Field(123)
            bar1: int = Field(456)

        class Data(BaseModel):
            foo: Foo = Field(default_factory=Foo)
            foo1: int
            foo2: list[str]

        return Data

    @staticmethod
    @mark.parametrize("kwargs", (
            {},
            {"allow_create": True},
            {"ignore_missing": True},
            {"allow_create": True, "ignore_missing": True},
    ))
    def test_ignore(data, kwargs):
        assert RequiredPath(lambda _: _, "ignore").filter(deepcopy(data), **kwargs) == data

    PydanticTests = ("path, value, kwargs, ignore_excs, ignore_warns", (
        ("foo", {"bar": 123, "bar1": 456}, {}, (), ()),
        ("foo\\.bar", 123, {}, (), ()),
        ("foo.bar", 123, {}, (RequiredPathNotFoundError,), ()),
        ("foo1", 114, {}, (), ()),
        ("foo2", ["bar"], {}, (), ()),
        ("foo2", ["bar"], {"allow_create": True}, (), ()),
        ("foo.bar", None, {"ignore_missing": True}, (RequiredPathNotFoundError,), (UserWarning,)),
    ))

    @staticmethod
    @mark.parametrize(*PydanticTests)
    def test_pydantic(data, pydantic_model, path, value, kwargs, ignore_excs, ignore_warns):
        with safe_raises(ignore_excs), safe_warns(ignore_warns):
            data = RequiredPath(pydantic_model, "pydantic").filter(data, **kwargs)
            assert data.retrieve(path, get_raw=True) == value

    @staticmethod
    def test_pydantic_with_error(data):
        with raises(TypeError):
            RequiredPath(int, "pydantic").filter(data)

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
        ([], [],
         {}, ()),
        (
            ["foo", "foo1", "foo2"],
            [{"bar": 123, "bar1": 456}, 114, ["bar"]],
            {}, ()
        ),
        (
            ["foo", "foo\\.bar"],
            [{"bar": 123, "bar1": 456}, 123],
            {}, ()
        ),
        (
            ["foo\\.bar", "foo"],  # 无论顺序先后都应该在父路径单独存在时包含父路径下的所有子路径
            [123, {"bar": 123, "bar1": 456}],
            {}, ()
        ),
        (
            ["foo2\\.bar"],
            [987],
            {}, (ConfigDataTypeError,)
        ),
        (
            ["foo\\.bar2"],
            [987],
            {}, (RequiredPathNotFoundError,)
        ),
        (
            ["foo\\.bar2"],
            [987],
            {"allow_create": True}, (RequiredPathNotFoundError,)  # 因为没有默认值所以即便allow_create=True也会报错
        ),
        (
            ["foo\\.bar2", "foo1"],
            [float("-inf"), 114],  # -inf是占位符,表示该值可以不存在
            {"ignore_missing": True}, ()
        ),
        (
            ["foo2\\.bar", "foo1"],  # foo2为list 所以foo2.bar会报错
            [float("-inf"), 114],
            {"ignore_missing": True, "allow_create": True}, (ConfigDataTypeError,)
        ),
        (
            None, [], {}, (TypeError,)
        )
    ))

    @staticmethod
    @mark.parametrize(*IterableTests)
    def test_default_iterable(data, paths, values, kwargs, ignore_excs):
        with safe_raises(ignore_excs) as info:
            data = RequiredPath(paths).filter(data, **kwargs)
        if info:
            return

        for path, value in zip(paths, values):
            if isinstance(value, float) and value == float("-inf"):
                assert path not in data
                continue
            assert data.retrieve(path, get_raw=True) == value

    MappingTests = ("mapping, result, kwargs, ignore_excs", (
        (
            OrderedDict((
                ("foo", dict),
                ("foo\\.bar", int),
            )),
            {'foo': {'bar': 123, 'bar1': 456}},
            {}, ()
        ),
        (
            OrderedDict((
                ("foo\\.bar", int),
                ("foo", dict),
            )),
            {'foo': {'bar': 123, 'bar1': 456}},
            {}, ()
        ),
        (
            {
                "foo": dict,
                "foo\\.bar": int,
            },
            {'foo': {'bar': 123, 'bar1': 456}},
            {"model_config_key": "$$__model_config_key$$"}, ()
        ),
        ({
             "foo": dict,
             "foo\\.bar": int,
             "foo1": int,
             "foo2": list[str],
         },
         {
             "foo": {"bar": 123, "bar1": 456},
             "foo1": 114,
             "foo2": ["bar"],
         }, {}, ()),
        ({
             "foo": dict,
             "foo\\.bar": 111,
             "foo1": 222,
             "foo2": [333],
             "foo3\\.bar": 789,
             "foo3\\.test\\.value": 101112,
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
        (OrderedDict((
            ("foo", str),
            ("foo\\.bar", int),
        )), None, {}, (ConfigDataTypeError,)),
        (OrderedDict((
            ("foo\\.bar", int),
            ("foo", str),
        )), None, {}, (ConfigDataTypeError,)),
        ({
             "foo\\.bar": int,
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
        ({"foo\\.bar\\.baz": int},
         None,
         {"ignore_missing": True}, (ConfigDataTypeError,)),
        (None, None, {}, (TypeError,))
    ))

    @staticmethod
    @mark.parametrize(*MappingTests)
    def test_default_mapping(data, mapping, result, kwargs, ignore_excs):
        with safe_raises(ignore_excs):
            data = RequiredPath(mapping).filter(data, **kwargs)
            assert data.data == result

    @staticmethod
    @mark.parametrize("validator, static_config, times", (
            ({
                 "foo\\.bar": int,
                 "foo": dict,
                 "foo1": int,
                 "foo2": list[str]
             }, ValidatorFactoryConfig(), 100),
            ({
                 "foo\\.bar": int,
                 "foo": dict,
                 "foo1": int,
                 "foo2": list[str],
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
             }, ValidatorFactoryConfig(allow_create=True), 100),
    ))
    def test_static_config_usetime(data, validator, static_config, times):
        static_filter = RequiredPath(validator, static_config=static_config).filter
        dynamic_filter = RequiredPath(validator).filter

        def _timeit(cfg_filter) -> Decimal:
            time_used = Decimal(0)
            for _ in range(times):
                start = time.perf_counter_ns()
                cfg_filter(data)
                end = time.perf_counter_ns()
                time_used += Decimal(end - start)
            return time_used

        total_static_time = _timeit(static_filter) / Decimal(1_000_000)
        total_dynamic_time = _timeit(dynamic_filter) / Decimal(1_000_000)
        assert total_static_time < total_dynamic_time
        times = Decimal(times)
        average_static_time = total_static_time / times
        average_dynamic_time = total_dynamic_time / times
        print()
        print(static_config)
        print(f"total_static_time: {total_static_time}ms")
        print(f"total_dynamic_time: {total_dynamic_time}ms")
        print(f"times: {times}")
        print(f"average_static_time: {average_static_time}ms")
        print(f"average_dynamic_time: {average_dynamic_time}ms")
        print(f"speedup: {average_dynamic_time / average_static_time}")


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
        return ConfigFile(data, namespace="ns", file_name='f', config_format="json")

    @staticmethod
    def test_attr_readonly(file, data):
        assert file.namespace == "ns"
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.namespace = None

        assert file.data == data
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.data = None

        assert file.file_name == 'f'
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.file_name = None

        assert file.config_format == "json"
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            file.config_format = None

    ExtraKwargs = (
        {"namespace": "ns"},
        {"file_name": 'f'},
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
