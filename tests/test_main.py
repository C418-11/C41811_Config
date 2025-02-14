# -*- coding: utf-8 -*-


import time
from collections import OrderedDict
from copy import deepcopy
from decimal import Decimal

from pydantic import BaseModel
from pydantic import Field
# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from pytest import fixture
from pytest import mark
from pytest import raises

from C41811.Config import ConfigData
from C41811.Config import ConfigFile
from C41811.Config import ConfigPool
from C41811.Config import FieldDefinition
from C41811.Config import JsonSL
from C41811.Config import Path
from C41811.Config import RequiredPath
from C41811.Config import ValidatorFactoryConfig
from C41811.Config.errors import ConfigDataTypeError
from C41811.Config.errors import RequiredPathNotFoundError
from C41811.Config.errors import UnsupportedConfigFormatError
from utils import safe_raises
from utils import safe_warns


class TestConfigPool:
    @staticmethod
    @fixture
    def pool(tmpdir):
        pool = ConfigPool(root_path=tmpdir)
        JsonSL().register_to(pool)
        return pool

    @staticmethod
    def test_root_path_attr(pool):
        assert pool.root_path
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            pool.root_path = ""

    @staticmethod
    @fixture
    def data():
        return ConfigData({"foo": 123})

    @staticmethod
    @fixture
    def file(data):
        return ConfigFile(data)

    @staticmethod
    def test_set_get_delete(pool, file):
        pool.set('', "test", deepcopy(file))
        assert pool.get("not", "exists") is None
        assert pool.get('', "not exists") is None
        assert pool.get('', "test") == file
        assert pool.get('') == {"test": file}
        pool.delete('', "test")
        assert pool.get('', "test") is None, "File should be deleted"

    @staticmethod
    def test_save_load(pool, file):
        pool.set('', "test", deepcopy(file))

        pool.save('', "test", config_formats="json")
        assert pool.load('', "test", config_formats="json") == file

        pool.save('', "test", config_formats={"pickle", "json"})
        assert pool.load('', "test", config_formats={"pickle", "json"}) == file
        assert pool.load('', "test", config_formats={"pickle", "json"}) == file

        json_file = ConfigFile(file.data, config_format="json")
        pool.save('', "test", config=deepcopy(json_file))
        assert pool.load('', "test", config_formats="json") == json_file

        pool.save('', "test1", config_formats="json", config=deepcopy(file))
        assert pool.load('', "test1", config_formats="json") == file

    @staticmethod
    def test_file_not_found_load(pool):
        with raises(FileNotFoundError, match="No such file or directory"):
            pool.load('', "test", config_formats="json")

        assert pool.load(
            '', "test",
            config_formats="json",
            allow_create=True
        ) == ConfigFile(ConfigData({}), config_format="json")

    @staticmethod
    def test_wrong_save(pool, data):
        pool.set('', "test", ConfigFile(data))
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: Unknown"):
            pool.save('', "test")

        pool.set('', "test.wrong", ConfigFile(data))
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: Unknown"):
            pool.save('', "test.wrong")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: wrong"):
            pool.save('', "test", config_formats="wrong")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: "):
            pool.save('', "test", config_formats={''})

    @staticmethod
    def test_wrong_load(pool, data):
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: Unknown"):
            pool.load('', "test")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: Unknown"):
            pool.load('', "test.wrong")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: wrong"):
            pool.load('', "test.wrong", config_formats="wrong")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: "):
            pool.load('', "test", config_formats={''})

    @staticmethod
    def test_save_all(pool, data):
        pool.set('', "test", ConfigFile(data, config_format="json"))
        pool.set('', "test1", ConfigFile(data, config_format="json"))
        pool.save_all()
        assert pool.load('', "test", config_formats="json").data == data
        assert pool.load('', "test1", config_formats="json").data == data

    @staticmethod
    def test_save_all_with_error(pool, data):
        file = ConfigFile(data, config_format="pickle")
        pool.set('', "test", file)
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: pickle"):
            pool.save_all()
        assert pool.save_all(ignore_err=True) == {'': {"test": (file, UnsupportedConfigFormatError("pickle"))}}

    @staticmethod
    def test_require(pool):
        cfg_data: ConfigData = pool.require(
            '', "test.json", {
                "foo\\.bar": "test",
                "foo\\.baz": "test"
            }
        ).check()
        assert cfg_data == ConfigData({"foo": {"bar": "test", "baz": "test"}})
        cfg_data: ConfigData = pool.require(
            '', "test.json", {
                "foo\\.bar": "test",
                "foo\\.baz": "test"
            }
        ).check(ignore_cache=True)
        assert cfg_data == ConfigData({"foo": {"bar": "test", "baz": "test"}})

        @pool.require(
            '', "test.json", {
                "foo\\.bar": "test",
                "foo\\.baz": "test"
            }
        )
        def func(cfg: ConfigData):
            assert cfg == ConfigData({"foo": {"bar": "test", "baz": "test"}})

        func()

    @staticmethod
    def test_getitem(pool, file):
        pool.set('', "test", deepcopy(file))
        assert pool['']["test"] == file
        assert pool['', "test"] == file
        assert pool[''] == {"test": file}
        with raises(ValueError, match="item must be a tuple of length 2, got"):
            # noinspection PyStatementEffect
            pool['', "test", "extra"]

    @staticmethod
    def test_contains(pool, file):
        pool.set('', "test", deepcopy(file))
        assert '' in pool
        assert [''] in pool
        assert ['', "test"] in pool
        with raises(ValueError, match="item must be a tuple of length 2, got"):
            # noinspection PyStatementEffect
            ['', "test", "extra"] in pool

    @staticmethod
    def test_len(pool, file):
        pool.set('a', "1", file)
        pool.set('a', "2", file)
        pool.set('a', "3", file)
        pool.set('b', "1", file)
        pool.set('b', "2", file)
        pool.set('v', "1", file)
        assert len(pool) == 6

    @staticmethod
    def test_configs_attr(pool, file):
        pool.set('', "test", deepcopy(file))
        assert pool.configs == {'': {'test': file}}

    @staticmethod
    def test_repr(pool):
        assert repr(pool.configs) in repr(pool)


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
            {"allow_modify": True},
            {"ignore_missing": True},
            {"allow_modify": True, "ignore_missing": True},
    ))
    def test_ignore(data, kwargs):
        assert RequiredPath(lambda _: _, "ignore").filter(deepcopy(data), **kwargs) == data

    PydanticTests = ("path, value, kwargs, ignore_excs, ignore_warns", (
        ("foo", {"bar": 123, "bar1": 456}, {}, (), ()),
        ("foo\\.bar", 123, {}, (), ()),
        ("foo.bar", 123, {}, (RequiredPathNotFoundError,), ()),
        ("foo1", 114, {}, (), ()),
        ("foo2", ["bar"], {}, (), ()),
        ("foo2", ["bar"], {"allow_modify": True}, (), ()),
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
            {"allow_modify": True}, (RequiredPathNotFoundError,)  # 因为没有默认值所以即便allow_modify=True也会报错
        ),
        (
            ["foo\\.bar2", "foo1"],
            [float("-inf"), 114],  # -inf是占位符,表示该值可以不存在
            {"ignore_missing": True}, ()
        ),
        (
            ["foo2\\.bar", "foo1"],  # foo2为list 所以foo2.bar会报错
            [float("-inf"), 114],
            {"ignore_missing": True, "allow_modify": True}, (ConfigDataTypeError,)
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

    MappingTests = ("mapping, result, kwargs, ignores", (
        (
            OrderedDict((
                ("foo", dict),
                ("foo\\.bar", int),
            )),
            {"foo": {"bar": 123, "bar1": 456}},
            {}, ()
        ),
        (
            OrderedDict((
                ("foo\\.bar", int),
                ("foo", dict),
            )),
            {"foo": {"bar": 123, "bar1": 456}},
            {}, ()
        ),
        (
            {
                "foo": dict,
                "foo\\.bar": int,
            },
            {"foo": {"bar": 123, "bar1": 456}},
            {"model_config_key": "$$__model_config_key$$"}, ()
        ),
        (
            {"foo": {"bar": 2, 3: 4}},  # 遇到键不完全为字符串时禁止递归检查
            {"foo": {"bar": 123, "bar1": 456}},
            {}, ()
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
         }, {"allow_modify": True}, ()),
        (OrderedDict((
            ("foo", str),
            ("foo\\.bar", int),
        )), None, {}, (ConfigDataTypeError,)),
        (OrderedDict((
            ("foo\\.bar", int),
            ("foo", str),
        )), None, {}, (ConfigDataTypeError, UserWarning)),
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
         }, {"ignore_missing": True}, ()),
        ({
             "foo\\.bar": FieldInfo(annotation=int),
             "foo\\.qux": FieldInfo(annotation=int, default=7),
         },
         {
             "foo": {"bar": 123, "qux": 7},
         }, {}, ()),
        ({
             "foo\\.bar": FieldDefinition(int, FieldInfo()),
             "foo\\.qux": FieldDefinition(int, FieldInfo(default=7)),
         },
         {
             "foo": {"bar": 123, "qux": 7},
         }, {}, ()),
        ({
             "foo\\.bar": FieldDefinition(int, 999),
             "foo\\.qux": FieldDefinition(int, 888),
         },
         {
             "foo": {"bar": 123, "qux": 888},
         }, {}, ()),
        ({"foo\\.bar\\.baz": int},
         None,
         {"ignore_missing": True}, (ConfigDataTypeError,)),
        (None, None, {}, (TypeError,))
    ))

    @staticmethod
    @mark.parametrize(*MappingTests)
    def test_default_mapping(data, mapping, result, kwargs, ignores):
        ignore_warns = tuple(e for e in ignores if issubclass(e, Warning))
        ignore_excs = tuple(set(ignores) - set(ignore_warns))

        with safe_raises(ignore_excs), safe_warns(ignore_warns):
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
             }, ValidatorFactoryConfig(allow_modify=True), 100),
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

    @staticmethod
    @fixture
    def recursive_data():
        return ConfigData({
            "first": {
                "second": {
                    "third": 111,
                    "foo": 222
                },
                "bar": 333
            },
            "baz": 444
        })

    IncludeSubKeyTests = ("validator, result, ignores", (
        ((
             "first\\.second\\.third",
             "first"
         ), {
             "first": {
                 "second": {
                     "third": 111
                 },
                 "bar": 333
             }
         }, ()),
        ((
             "first",
             "first\\.second\\.third",
         ), {
             "first": {
                 "second": {
                     "third": 111
                 },
                 "bar": 333
             }
         }, ()),
        ((
             "first\\.second\\.third",
             "first\\.second"
         ), {
             "first": {
                 "second": {
                     "third": 111,
                     "foo": 222
                 },
             }
         }, ()),
        ({
             "first": {  # 混搭
                 Path.from_str("\\.second\\.third"): int,
                 "second": dict,
                 "bar": int
             },
             "baz": int
         }, {
             "first": {
                 "second": {
                     "third": 111,
                     "foo": 222
                 },
                 "bar": 333
             },
             "baz": 444
         }, ()),
        (OrderedDict((
            ("first\\.second\\.third", int),
            ("first", int)
        )), None, ((UserWarning,), (ConfigDataTypeError,))),
        (
            {"first": {"second\\.third": str, 3: 4}},  # 遇到键不完全为字符串时禁止递归检查
            {"first": {"bar": 333, "second": {"foo": 222, "third": 111}}},
            ()
        ),
    ))

    @staticmethod  # 专门针对保留子键的测试
    @mark.parametrize(*IncludeSubKeyTests)
    def test_include_sub_key(recursive_data, validator, result, ignores):
        if not ignores:
            ignores = ((), ())
        ignore_warns, ignore_excs = ignores

        with safe_warns(ignore_warns), safe_raises(ignore_excs) as info:
            data = RequiredPath(validator).filter(recursive_data)

        if info:
            return

        # noinspection PyTestUnpassedFixture
        assert data.data == result
