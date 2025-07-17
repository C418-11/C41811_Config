import time
from collections import OrderedDict
from collections.abc import Callable
from collections.abc import Mapping
from copy import deepcopy
from decimal import Decimal
from pathlib import Path as FPath
from typing import Any
from typing import cast

from pydantic import BaseModel
from pydantic import Field

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from pytest import fixture
from pytest import mark
from pytest import raises
from utils import EE
from utils import EW
from utils import safe_raises
from utils import safe_warns

from c41811.config import ComponentConfigData
from c41811.config import ComponentMember
from c41811.config import ComponentMeta
from c41811.config import ComponentOrders
from c41811.config import ConfigData
from c41811.config import ConfigFile
from c41811.config import ConfigPool
from c41811.config import FieldDefinition
from c41811.config import JsonSL  # type: ignore[attr-defined]
from c41811.config import MappingConfigData
from c41811.config import NoneConfigData
from c41811.config import Path as DPath
from c41811.config import RequiredPath
from c41811.config import ValidatorFactoryConfig
from c41811.config.abc import ABCConfigFile
from c41811.config.errors import ConfigDataTypeError
from c41811.config.errors import RequiredPathNotFoundError
from c41811.config.errors import UnsupportedConfigFormatError
from c41811.config.processor.Component import ComponentMetaParser

type MCD = MappingConfigData[Mapping[Any, Any]]


class TestConfigPool:
    @staticmethod
    @fixture
    def pool(tmpdir: FPath) -> ConfigPool:
        pool = ConfigPool(root_path=str(tmpdir))
        JsonSL().register_to(pool)
        return pool

    @staticmethod
    def test_root_path_attr(pool: ConfigPool) -> None:
        assert pool.root_path
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            pool.root_path = ""  # type: ignore[misc]

    @staticmethod
    @fixture
    def data() -> MCD:
        return MappingConfigData({"foo": 123})

    @staticmethod
    @fixture
    def file(data: MCD) -> ConfigFile[MCD]:
        return ConfigFile(data)

    @staticmethod
    def test_set_get_remove(pool: ConfigPool, file: ConfigFile[MCD]) -> None:
        pool.set("", "test", deepcopy(file))
        assert pool.get("not", "exists") is None
        assert pool.get("", "not exists") is None
        assert pool.get("", "test") == file
        assert pool.get("") == {"test": file}
        pool.remove("", "test")
        assert pool.get("", "test") is None, "File should be removed"
        pool.set("", "test", deepcopy(file))
        pool.remove(
            "",
        )
        assert pool.get("", "test") is None, "All files should be removed"

    @staticmethod
    def test_save_load(pool: ConfigPool, file: ConfigFile[MCD]) -> None:
        pool.set("", "test", deepcopy(file))

        pool.save("", "test", config_formats="json")
        assert pool.load("", "test", config_formats="json") == file

        pool.save("", "test", config_formats={"pickle", "json"})
        assert pool.load("", "test", config_formats={"pickle", "json"}) == file
        assert pool.load("", "test", config_formats={"pickle", "json"}) == file

        json_file: ConfigFile[MCD] = ConfigFile(file.config, config_format="json")
        pool.save("", "test", config=deepcopy(json_file))
        assert pool.load("", "test", config_formats="json") == json_file

        pool.save("", "test1", config_formats="json", config=deepcopy(file))
        assert pool.load("", "test1", config_formats="json") == file

    @staticmethod
    def test_file_not_found_load(pool: ConfigPool) -> None:
        with raises(FileNotFoundError, match="No such file or directory"):
            pool.load("", "test", config_formats="json")

        assert pool.load("", "test", config_formats="json", allow_initialize=True) == ConfigFile(
            ConfigData(), config_format="json"
        )

    @staticmethod
    def test_wrong_save(pool: ConfigPool, data: MCD) -> None:
        pool.set("", "test", ConfigFile(data))
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: Unknown"):
            pool.save("", "test")

        pool.set("", "test.wrong", ConfigFile(data))
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: Unknown"):
            pool.save("", "test.wrong")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: wrong"):
            pool.save("", "test", config_formats="wrong")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: "):
            pool.save("", "test", config_formats={""})

    @staticmethod
    def test_wrong_load(pool: ConfigPool) -> None:
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: Unknown"):
            pool.load("", "test")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: Unknown"):
            pool.load("", "test.wrong")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: wrong"):
            pool.load("", "test.wrong", config_formats="wrong")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: "):
            pool.load("", "test", config_formats={""})

    @staticmethod
    def test_save_all(pool: ConfigPool, data: MCD) -> None:
        pool.set("", "test", ConfigFile(data, config_format="json"))
        pool.set("", "test1", ConfigFile(data, config_format="json"))
        pool.save_all()
        assert pool.load("", "test", config_formats="json").config == data
        assert pool.load("", "test1", config_formats="json").config == data

    @staticmethod
    def test_save_all_with_error(pool: ConfigPool, data: MCD) -> None:
        file: ConfigFile[MCD] = ConfigFile(data, config_format="pickle")
        pool.set("", "test", file)
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: pickle"):
            pool.save_all()
        assert pool.save_all(ignore_err=True) == {"": {"test": (file, UnsupportedConfigFormatError("pickle"))}}

    @staticmethod
    def test_require(pool: ConfigPool) -> None:
        cfg_data: ConfigData = pool.require("", "test.json", {"foo\\.bar": "test", "foo\\.baz": "test"}).check()
        assert cfg_data == ConfigData({"foo": {"bar": "test", "baz": "test"}})
        cfg_data = pool.require("", "test.json", {"foo\\.bar": "test", "foo\\.baz": "test"}).check(ignore_cache=True)
        assert cfg_data == ConfigData({"foo": {"bar": "test", "baz": "test"}})

        @pool.require(  # type: ignore[arg-type]
            "", "test.json", {"foo\\.bar": "test", "foo\\.baz": "test"}
        )
        def func(cfg: MCD) -> None:
            assert cfg == ConfigData({"foo": {"bar": "test", "baz": "test"}})

        func()

    @staticmethod
    def test_getitem(pool: ConfigPool, file: ConfigFile[MCD]) -> None:
        pool.set("", "test", deepcopy(file))
        assert cast(dict[str, ABCConfigFile[Any]], pool[""])["test"] == file
        assert pool["", "test"] == file
        assert pool[""] == {"test": file}
        with raises(ValueError, match="item must be a tuple of length 2, got"):
            # noinspection PyStatementEffect,PyTypeChecker
            pool["", "test", "extra"]  # type: ignore[index]

    @staticmethod
    def test_contains(pool: ConfigPool, file: ConfigFile[MCD]) -> None:
        pool.set("", "test", deepcopy(file))
        assert "" in pool
        assert [""] in pool
        assert ["", "test"] in pool
        with raises(ValueError, match="item must be a tuple of length 2, got"):
            # noinspection PyStatementEffect
            ["", "test", "extra"] in pool  # noqa: B015

    @staticmethod
    def test_len(pool: ConfigPool, file: ConfigFile[MCD]) -> None:
        pool.set("a", "1", file)
        pool.set("a", "2", file)
        pool.set("a", "3", file)
        pool.set("b", "1", file)
        pool.set("b", "2", file)
        pool.set("v", "1", file)
        assert len(pool) == 6

    @staticmethod
    def test_configs_attr(pool: ConfigPool, file: ConfigFile[MCD]) -> None:
        pool.set("", "test", deepcopy(file))
        assert pool.configs == {"": {"test": file}}

    @staticmethod
    def test_repr(pool: ConfigPool) -> None:
        assert repr(pool.configs) in repr(pool)


class TestRequiredPath:
    @staticmethod
    @fixture
    def data() -> MCD:
        return MappingConfigData(
            {
                "foo": {"bar": 123, "bar1": 456},
                "foo1": 114,
                "foo2": ["bar"],
            }
        )

    @staticmethod
    @fixture
    def pydantic_model() -> type[BaseModel]:
        class Foo(BaseModel):
            bar: int = Field(123)
            bar1: int = Field(456)

        class Data(BaseModel):
            foo: Foo = Field(default_factory=cast(Callable[..., Any], Foo))
            foo1: int
            foo2: list[str]

        return Data

    @staticmethod
    @mark.parametrize(
        "kwargs",
        (
            {},
            {"allow_modify": True},
            {"skip_missing": True},
            {"allow_modify": True, "skip_missing": True},
        ),
    )
    def test_no_validation(data: MCD, kwargs: dict[str, Any]) -> None:
        assert RequiredPath(lambda _: _.value, "no-validation").filter(deepcopy(data), **kwargs) == data  # type: ignore[arg-type]

    PydanticTests: tuple[
        str,
        tuple[
            tuple[
                str,
                Any,
                dict[str, Any],
                EE,
                EW,
            ],
            ...,
        ],
    ] = (
        "path, value, kwargs, ignore_excs, ignore_warns",
        (
            ("foo", {"bar": 123, "bar1": 456}, {}, (), ()),
            ("foo\\.bar", 123, {}, (), ()),
            ("foo\\.bar", 123, {"allow_modify": False}, (), ()),
            ("foo.bar", 123, {}, (RequiredPathNotFoundError,), ()),
            ("foo1", 114, {}, (), ()),
            ("foo2", ["bar"], {}, (), ()),
            ("foo2", ["bar"], {"allow_modify": True}, (), ()),
            ("foo2", ["bar"], {"allow_modify": False}, (), ()),
            ("foo.bar", None, {"skip_missing": True}, (RequiredPathNotFoundError,), (UserWarning,)),
        ),
    )

    @staticmethod
    @mark.parametrize(*PydanticTests)
    def test_pydantic(
        data: MCD,
        pydantic_model: type[BaseModel],
        path: str,
        value: Any,
        kwargs: dict[str, Any],
        ignore_excs: EE,
        ignore_warns: EW,
    ) -> None:
        with safe_raises(ignore_excs), safe_warns(ignore_warns):
            data = cast(
                MappingConfigData[Any],
                RequiredPath(pydantic_model, "pydantic").filter(data, **kwargs),  # type: ignore[arg-type]
            )
            assert data.retrieve(path, return_raw_value=True) == value

    @staticmethod
    def test_pydantic_with_none_data() -> None:
        class Data(BaseModel):
            foo: int = Field(10)
            bar: dict[Any, Any] = Field(default_factory=dict)

        RequiredPath(Data, "pydantic").filter(NoneConfigData())  # type: ignore[arg-type]

        class NotExist(BaseModel):
            key: int

        with raises(RequiredPathNotFoundError):
            RequiredPath(NotExist, "pydantic").filter(NoneConfigData())  # type: ignore[arg-type]

    @staticmethod
    def test_pydantic_with_error(data: MCD) -> None:
        with raises(TypeError):
            RequiredPath(int, "pydantic").filter(data)  # type: ignore[arg-type]

        class NotExist(BaseModel):
            foo3: int

        with raises(RequiredPathNotFoundError):
            RequiredPath(NotExist, "pydantic").filter(data)  # type: ignore[arg-type]

        class NotExist2(BaseModel):
            foo: NotExist

        with raises(RequiredPathNotFoundError):
            RequiredPath(NotExist2, "pydantic").filter(data)  # type: ignore[arg-type]

        class WrongType(BaseModel):
            foo: str

        with raises(ConfigDataTypeError):
            RequiredPath(WrongType, "pydantic").filter(data)  # type: ignore[arg-type]

        class WrongType2(BaseModel):
            foo2: list[int]

        with raises(ConfigDataTypeError):
            RequiredPath(WrongType2, "pydantic").filter(data)  # type: ignore[arg-type]

    IterableTests: tuple[str, tuple[tuple[list[str] | None, list[Any], dict[str, Any], EE], ...]] = (
        "paths, values, kwargs, ignore_excs",
        (
            ([], [], {}, ()),
            (["foo", "foo1", "foo2"], [{"bar": 123, "bar1": 456}, 114, ["bar"]], {}, ()),
            (["foo", "foo\\.bar"], [{"bar": 123, "bar1": 456}, 123], {}, ()),
            (
                ["foo\\.bar", "foo"],  # 无论顺序先后都应该在父路径单独存在时包含父路径下的所有子路径
                [123, {"bar": 123, "bar1": 456}],
                {},
                (),
            ),
            (
                ["foo\\.bar", "foo"],
                [123, {"bar": 123, "bar1": 456}],
                {"allow_modify": False},
                (),
            ),
            (["foo2\\.bar"], [987], {}, (ConfigDataTypeError,)),
            (["foo\\.bar2"], [987], {}, (RequiredPathNotFoundError,)),
            (
                ["foo\\.bar2"],
                [987],
                {"allow_modify": True},
                (RequiredPathNotFoundError,),  # 因为没有默认值所以即便allow_modify=True也会报错
            ),
            (
                ["foo\\.bar2"],
                [987],
                {"allow_modify": False},
                (RequiredPathNotFoundError,),
            ),
            (
                ["foo\\.bar2", "foo1"],
                [float("-inf"), 114],  # -inf是占位符,表示该值可以不存在
                {"skip_missing": True},
                (),
            ),
            (
                ["foo2\\.bar", "foo1"],  # foo2为list 所以foo2.bar会报错
                [float("-inf"), 114],
                {"skip_missing": True, "allow_modify": True},
                (ConfigDataTypeError,),
            ),
            (None, [], {}, (TypeError,)),
        ),
    )

    @staticmethod
    @mark.parametrize(*IterableTests)
    def test_default_iterable(
        data: MCD,
        paths: list[str],
        values: list[Any],
        kwargs: dict[str, Any],
        ignore_excs: EE,
    ) -> None:
        with safe_raises(ignore_excs) as info:
            data = cast(
                MappingConfigData[Any],
                RequiredPath(paths).filter(data, **kwargs),  # type: ignore[arg-type]
            )
        if info:
            return

        for path, value in zip(paths, values, strict=False):
            if isinstance(value, float) and value == float("-inf"):
                assert path not in data
                continue
            assert data.retrieve(path, return_raw_value=True) == value

    MappingTests: tuple[
        str,
        tuple[
            tuple[
                Mapping[str, Any] | None,
                dict[str, Any] | None,
                dict[str, Any],
                tuple[type[Warning | BaseException], ...],
            ],
            ...,
        ],
    ] = (
        "mapping, result, kwargs, ignores",
        (
            (
                OrderedDict(
                    (
                        ("foo", dict),
                        ("foo\\.bar", int),
                    )
                ),
                {"foo": {"bar": 123, "bar1": 456}},
                {},
                (),
            ),
            (
                OrderedDict(
                    (
                        ("foo", dict),
                        ("foo\\.bar", int),
                    )
                ),
                {"foo": {"bar": 123, "bar1": 456}},
                {"allow_modify": False},
                (),
            ),
            (
                OrderedDict(
                    (
                        ("foo\\.bar", int),
                        ("foo", dict),
                    )
                ),
                {"foo": {"bar": 123, "bar1": 456}},
                {},
                (),
            ),
            (
                {
                    "foo": dict,
                    "foo\\.bar": int,
                },
                {"foo": {"bar": 123, "bar1": 456}},
                {"model_config_key": "$$__model_config_key$$"},
                (),
            ),
            (
                {"foo": {"bar": 2, 3: 4}},  # 遇到键不完全为字符串时禁止递归检查
                {"foo": {"bar": 123, "bar1": 456}},
                {},
                (),
            ),
            (
                {"foo": {"bar": 2, 3: 4}},  # 遇到键不完全为字符串时禁止递归检查
                {"foo": {"bar": 123, "bar1": 456}},
                {"allow_modify": False},
                (),
            ),
            (
                {
                    "foo": dict,
                    "foo\\.bar": int,
                    "foo1": int,
                    "foo2": list[str],
                },
                {
                    "foo": {"bar": 123, "bar1": 456},
                    "foo1": 114,
                    "foo2": ["bar"],
                },
                {},
                (),
            ),
            (
                {
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
                        },
                    },
                },
                {
                    "foo": {"bar": 123, "bar1": 456},
                    "foo1": 114,
                    "foo2": ["bar"],
                    "foo3": {
                        "bar": 789,
                        "test": {
                            "value": 101112,
                        },
                    },
                    "foo4": {
                        "bar": 789,
                        "test": {
                            "value": 101112,
                        },
                    },
                },
                {"allow_modify": True},
                (),
            ),
            (
                {
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
                        },
                    },
                },
                {
                    "foo": {"bar": 123, "bar1": 456},
                    "foo1": 114,
                    "foo2": ["bar"],
                    "foo3": {
                        "bar": 789,
                        "test": {
                            "value": 101112,
                        },
                    },
                    "foo4": {
                        "bar": 789,
                        "test": {
                            "value": 101112,
                        },
                    },
                },
                {"allow_modify": False},
                (),
            ),
            (
                OrderedDict(
                    (
                        ("foo", str),
                        ("foo\\.bar", int),
                    )
                ),
                None,
                {},
                (ConfigDataTypeError,),
            ),
            (
                OrderedDict(
                    (
                        ("foo\\.bar", int),
                        ("foo", str),
                    )
                ),
                None,
                {},
                (ConfigDataTypeError, UserWarning),
            ),
            (
                OrderedDict(
                    (
                        ("foo\\.bar", int),
                        ("foo", str),
                    )
                ),
                None,
                {"allow_modify": False},
                (ConfigDataTypeError, UserWarning),
            ),
            (
                {
                    "foo\\.bar": int,
                    "foo": dict,
                    "foo1": int,
                    "foo2": list[str],
                    "foo3": {
                        "bar": int,
                        "test": {
                            "value": 101112,
                        },
                    },
                },
                {
                    "foo": {"bar": 123, "bar1": 456},
                    "foo1": 114,
                    "foo2": ["bar"],
                    "foo3": {
                        "test": {
                            "value": 101112,
                        }
                    },
                },
                {"skip_missing": True},
                (),
            ),
            (
                {
                    "foo\\.bar": int,
                    "foo": dict,
                    "foo1": int,
                    "foo2": list[str],
                    "foo3": {
                        "bar": int,
                        "test": {
                            "value": 101112,
                        },
                    },
                },
                {
                    "foo": {"bar": 123, "bar1": 456},
                    "foo1": 114,
                    "foo2": ["bar"],
                    "foo3": {
                        "test": {
                            "value": 101112,
                        }
                    },
                },
                {"skip_missing": True, "allow_modify": False},
                (),
            ),
            (
                {
                    "foo\\.bar": FieldInfo(annotation=int),
                    "foo\\.qux": FieldInfo(annotation=int, default=7),
                },
                {
                    "foo": {"bar": 123, "qux": 7},
                },
                {},
                (),
            ),
            (
                {
                    "foo\\.bar": FieldDefinition(int, FieldInfo()),
                    "foo\\.qux": FieldDefinition(int, FieldInfo(default=7)),
                },
                {
                    "foo": {"bar": 123, "qux": 7},
                },
                {},
                (),
            ),
            (
                {
                    "foo\\.bar": FieldDefinition(int, 999),
                    "foo\\.qux": FieldDefinition(int, 888),
                },
                {
                    "foo": {"bar": 123, "qux": 888},
                },
                {},
                (),
            ),
            ({"foo\\.bar\\.baz": int}, None, {"skip_missing": True}, (ConfigDataTypeError,)),
            (None, None, {}, (TypeError,)),
        ),
    )

    @staticmethod
    @mark.parametrize(*MappingTests)
    def test_default_mapping(
        data: MCD,
        mapping: dict[str, Any],
        result: dict[str, Any],
        kwargs: dict[str, Any],
        ignores: tuple[type[Warning | BaseException], ...],
    ) -> None:
        ignore_warns = tuple(e for e in ignores if issubclass(e, Warning))
        ignore_excs = tuple(set(ignores) - set(ignore_warns))

        with safe_raises(ignore_excs), safe_warns(ignore_warns):
            data = cast(
                MappingConfigData[Any],
                RequiredPath(mapping).filter(data, **kwargs),  # type: ignore[arg-type]
            )
            assert data.data == result

    ComponentTests: tuple[
        str,
        tuple[
            tuple[
                ComponentConfigData[MappingConfigData[Any], ComponentMeta[MCD]] | NoneConfigData,
                dict[str | None, dict[str, Any]],
                ComponentConfigData[MappingConfigData[Any], ComponentMeta[MCD]] | None,
                dict[str, Any],
                tuple[type[Warning | BaseException], ...],
            ],
            ...,
        ],
    ] = (
        "data, validator, result, kwargs, ignores",
        (
            (
                ComponentConfigData(ComponentMeta(parser=ComponentMetaParser()), {}),
                #                                   ↑ 一般情况是由ComponentSL的initialize|load在构造时自动传入parser参数
                {
                    None: {"members": ["foo.json", "bar.json"]},
                    "foo.json": {
                        "first\\.second\\.third": 4,
                    },
                    "bar.json": {
                        "key": {"value"},
                    },
                },
                ComponentConfigData(
                    ComponentMeta(
                        members=[ComponentMember("foo.json"), ComponentMember("bar.json")],
                        orders=ComponentOrders(*([["foo.json", "bar.json"]] * 4)),
                    ),
                    {
                        "foo.json": MappingConfigData({"first": {"second": {"third": 4}}}),
                        "bar.json": MappingConfigData({"key": {"value"}}),
                    },
                ),
                {},
                (),
            ),
            (
                ComponentConfigData(ComponentMeta(parser=ComponentMetaParser()), {}),
                #                                   ↑ 一般情况是由ComponentSL的initialize|load在构造时自动传入parser参数
                {
                    None: {"members": ["foo.json", "bar.json"]},
                    "foo.json": {
                        "first\\.second\\.third": 4,
                    },
                    "bar.json": {
                        "key": {"value"},
                    },
                },
                ComponentConfigData(
                    ComponentMeta(
                        members=[ComponentMember("foo.json"), ComponentMember("bar.json")],
                        orders=ComponentOrders(*([["foo.json", "bar.json"]] * 4)),
                    ),
                    {
                        "foo.json": MappingConfigData({"first": {"second": {"third": 4}}}),
                        "bar.json": MappingConfigData({"key": {"value"}}),
                    },
                ),
                {"allow_modify": False},
                (),
            ),
            (
                NoneConfigData(),
                {
                    None: {"members": ["foo.json"]},
                    "foo.json": {
                        "first\\.second\\.third": 4,
                    },
                },
                ComponentConfigData(
                    ComponentMeta(members=[ComponentMember("foo.json")], orders=ComponentOrders(*([["foo.json"]] * 4))),
                    {
                        "foo.json": MappingConfigData({"first": {"second": {"third": 4}}}),
                    },
                ),
                {"meta_validator": ComponentMetaParser().validator},
                (),
            ),
            (
                NoneConfigData(),
                {
                    None: {"members": ["foo.json"]},
                    "foo.json": {
                        "first\\.second\\.third": 4,
                    },
                },
                ComponentConfigData(
                    ComponentMeta(members=[ComponentMember("foo.json")], orders=ComponentOrders(*([["foo.json"]] * 4))),
                    {
                        "foo.json": MappingConfigData({"first": {"second": {"third": 4}}}),
                    },
                ),
                {"meta_validator": ComponentMetaParser().validator, "allow_modify": False},
                (),
            ),
            (
                NoneConfigData(),
                {
                    None: {"members": ["foo.json"]},
                    "foo.json": {
                        "first\\.second\\.third": 4,
                    },
                },
                None,
                {},
                (ValueError,),
            ),
        ),
    )

    @staticmethod
    @mark.parametrize(*ComponentTests)
    def test_component[CCD: ComponentConfigData[MappingConfigData[Any], ComponentMeta[MCD]]](
        data: CCD,
        validator: dict[str | None, dict[str, Any]],
        result: CCD,
        kwargs: dict[str, Any],
        ignores: tuple[type[Warning | BaseException], ...],
    ) -> None:
        ignore_warns = tuple(e for e in ignores if issubclass(e, Warning))
        ignore_excs = tuple(set(ignores) - set(ignore_warns))

        with safe_raises(ignore_excs), safe_warns(ignore_warns):
            data = cast(
                CCD,
                RequiredPath(validator, "component").filter(data, **kwargs),  # type: ignore[arg-type]
            )
            # noinspection PyUnresolvedReferences
            assert data.meta.orders == result.meta.orders
            # noinspection PyUnresolvedReferences
            assert data.meta.members == result.meta.members
            assert data.members == result.members

    @staticmethod
    @mark.parametrize(
        "validator, static_config, times",
        (
            ({"foo\\.bar": int, "foo": dict, "foo1": int, "foo2": list[str]}, ValidatorFactoryConfig(), 100),
            (
                {
                    "foo\\.bar": int,
                    "foo": dict,
                    "foo1": int,
                    "foo2": list[str],
                    "foo3": {
                        "bar": 789,
                        "test": {
                            "value": 101112,
                        },
                    },
                    "foo4": {
                        "bar": 789,
                        "test": {
                            "value": 101112,
                        },
                    },
                },
                ValidatorFactoryConfig(allow_modify=True),
                100,
            ),
        ),
    )
    def test_static_config_usetime(
        data: MCD,
        validator: dict[str, Any],
        static_config: ValidatorFactoryConfig,
        times: int,
    ) -> None:
        static_filter = cast(Callable[[MCD], MCD], RequiredPath(validator, static_config=static_config).filter)
        dynamic_filter = cast(Callable[[MCD], MCD], RequiredPath(validator).filter)

        def _timeit(cfg_filter: Callable[[MCD], MCD]) -> Decimal:
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
        average_static_time = total_static_time / times
        average_dynamic_time = total_dynamic_time / times
        print()  # noqa: T201
        print(static_config)  # noqa: T201
        print(f"total_static_time: {total_static_time}ms")  # noqa: T201
        print(f"total_dynamic_time: {total_dynamic_time}ms")  # noqa: T201
        print(f"times: {times}")  # noqa: T201
        print(f"average_static_time: {average_static_time}ms")  # noqa: T201
        print(f"average_dynamic_time: {average_dynamic_time}ms")  # noqa: T201
        print(f"speedup: {average_dynamic_time / average_static_time}")  # noqa: T201

    @staticmethod
    @fixture
    def recursive_data() -> MCD:
        return MappingConfigData({"first": {"second": {"third": 111, "foo": 222}, "bar": 333}, "baz": 444})

    IncludeSubKeyTests = (
        "validator, result, ignores",
        (
            (("first\\.second\\.third", "first"), {"first": {"second": {"third": 111}, "bar": 333}}, ()),
            (
                (
                    "first",
                    "first\\.second\\.third",
                ),
                {"first": {"second": {"third": 111}, "bar": 333}},
                (),
            ),
            (
                ("first\\.second\\.third", "first\\.second"),
                {
                    "first": {
                        "second": {"third": 111, "foo": 222},
                    }
                },
                (),
            ),
            (
                {
                    "first": {  # 混搭
                        DPath.from_str("\\.second\\.third"): int,
                        "second": dict,
                        "bar": int,
                    },
                    "baz": int,
                },
                {"first": {"second": {"third": 111, "foo": 222}, "bar": 333}, "baz": 444},
                (),
            ),
            (
                OrderedDict((("first\\.second\\.third", int), ("first", int))),
                None,
                ((UserWarning,), (ConfigDataTypeError,)),
            ),
            (
                {"first": {"second\\.third": str, 3: 4}},  # 遇到键不完全为字符串时禁止递归检查
                {"first": {"bar": 333, "second": {"foo": 222, "third": 111}}},
                (),
            ),
        ),
    )

    @staticmethod  # 专门针对保留子键的测试
    @mark.parametrize(*IncludeSubKeyTests)
    def test_include_sub_key(
        recursive_data: MCD,
        validator: dict[str, Any],
        result: Any,
        ignores: tuple[EW, EE],
    ) -> None:
        if not ignores:
            ignores = ((), ())
        ignore_warns, ignore_excs = ignores

        with safe_warns(ignore_warns), safe_raises(ignore_excs) as info:
            data: MCD = RequiredPath(validator).filter(recursive_data)  # type: ignore[arg-type]

        if info:
            return

        # noinspection PyTestUnpassedFixture
        assert data.data == result
