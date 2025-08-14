import os
import re
from collections import OrderedDict
from collections.abc import Callable
from collections.abc import Generator
from datetime import datetime
from functools import wraps
from pathlib import Path
from textwrap import dedent
from typing import Any
from typing import cast
from typing import override

from mypy_extensions import KwArg
from mypy_extensions import VarArg
from pytest import fixture
from pytest import mark
from pytest import raises
from utils import EE
from utils import safe_raises

from c41811.config import BasicCompressedConfigSL
from c41811.config import BasicConfigSL
from c41811.config import BasicLocalFileConfigSL
from c41811.config import ComponentConfigData
from c41811.config import ComponentMeta
from c41811.config import ComponentMetaParser
from c41811.config import ComponentSL
from c41811.config import ConfigDataFactory
from c41811.config import ConfigFile
from c41811.config import ConfigPool
from c41811.config import EnvironmentConfigData
from c41811.config import HJsonSL
from c41811.config import JsonSL
from c41811.config import MappingConfigData
from c41811.config import OSEnvSL
from c41811.config import PickleSL
from c41811.config import PlainTextSL
from c41811.config import PythonLiteralSL
from c41811.config import PythonSL
from c41811.config import PyYamlSL
from c41811.config import RuamelYamlSL
from c41811.config import SequenceConfigData
from c41811.config import StringConfigData
from c41811.config import TarCompressionTypes
from c41811.config import TarFileSL
from c41811.config import TomlSL
from c41811.config import ZipCompressionTypes
from c41811.config import ZipFileSL
from c41811.config.abc import ABCConfigSL
from c41811.config.errors import ComponentMetadataException
from c41811.config.errors import FailedProcessConfigFileError

JsonTests: tuple[tuple[Any, tuple[EE, ...], tuple[dict[str, Any], ...]], ...] = (
    ({"a": 1, "b": {"c": 2}}, (), ()),
    ({"a": 1, "b": {"c": 2}}, (), ({"indent": 4}, {})),
    (OrderedDict((("a", 1), ("b", 2))), (), ({"indent": 4, "sort_keys": True}, {})),
    (OrderedDict((("b", 2), ("a", 1))), (), ({"indent": 4, "sort_keys": False}, {})),
    ([1, 2, [3, [4, 5, [6], {"7": 8}]]], (), ({"indent": 2}, {})),
    ("string", (), ()),
    (True, (), ()),
    (None, (), ()),
    (11.45, (), ()),
    (NotImplemented, ((FailedProcessConfigFileError,), ()), ()),
    (OrderedDict((("b", 2), ("a", 1))), ((), (FailedProcessConfigFileError,)), ({}, {"param not exist": None})),
)
HJsonTests = JsonTests

PickleTests: tuple[tuple[Any, tuple[EE, ...], tuple[Any, ...]], ...] = (
    ({"a": 1, "b": 2}, (), ()),
    ({"a": 1, "b": 2}, (), ({"protocol": 2}, {})),
    ({"a": 1, "b": 2}, (), ((2,), ())),
    (OrderedDict((("b", 2), ("a", 1))), (), ()),
    ([1, 2, [3, [4, 5, [6], {"7": 8}]]], (), ()),
    ("string", (), ()),
    (True, (), ()),
    (None, (), ()),
    (11.45, (), ()),
    (NotImplemented, (), ()),
    (lambda: None, ((FailedProcessConfigFileError,), ()), ()),
    (None, ((), (FailedProcessConfigFileError,)), ({}, {"param not exist": None})),
)

PyYamlTests: tuple[tuple[Any, tuple[EE, ...], tuple[dict[str, Any], ...]], ...] = (
    ({"a": 1, "b": {"c": 2}}, (), ()),
    ({"a": 1, "b": {"c": 2}}, (), ({"indent": 4}, {})),
    ([1, 2, [3, [4, 5, [6], {"7": 8}]]], (), ({"indent": 2}, {})),
    ("string", (), ()),
    (True, (), ()),
    (None, (), ()),
    (11.45, (), ()),
    (NotImplemented, ((FailedProcessConfigFileError,), ()), ()),
    (OrderedDict((("b", 2), ("a", 1))), ((FailedProcessConfigFileError,), (FailedProcessConfigFileError,)), ()),
)

RuamelYamlTests: tuple[tuple[Any, tuple[EE, ...], tuple[dict[str, Any], ...]], ...] = (
    ({"a": 1, "b": {"c": 2}}, (), ()),
    ([1, 2, [3, [4, 5, [6], {"7": 8}]]], (), ()),
    ("string", (), ()),
    (True, (), ()),
    (None, (), ()),
    (11.45, (), ()),
    (OrderedDict((("b", 2), ("a", 1))), (), ()),
    (NotImplemented, ((FailedProcessConfigFileError,), ()), ()),
)

TOMLTests: tuple[tuple[Any, tuple[EE, ...], tuple[dict[str, Any], ...]], ...] = (
    ({"a": 1, "b": {"c": 2}}, (), ()),
    ({"1": [1, 2, 3]}, (), ()),
    ({}, (), ()),
    (OrderedDict((("b", 2), ("a", 1))), (), ()),
    ({"1": [[1, 2], [3, 4], [5, 6]]}, (), ()),
    ([1, 2, 3], (FailedProcessConfigFileError,), ()),
    ("string", (FailedProcessConfigFileError,), ()),
    (True, (FailedProcessConfigFileError,), ()),
    (11.45, (FailedProcessConfigFileError,), ()),
    (None, (FailedProcessConfigFileError,), ()),
    (NotImplemented, ((FailedProcessConfigFileError,), ()), ()),
)


class ErrDuringRepr:
    @override
    def __repr__(self) -> str:
        raise Exception("repr error")  # noqa: TRY002, TRY003, EM101


PythonLiteralTests = (
    ({"a": 1, "b": 0.5}, (), ()),
    ({"a": True, "b": False, "c": None}, (), ()),
    ({"a": {"c": 2}, "b": {"c", 2}}, (), ()),
    ({"a": ["c", 2], "b": ("c", 2)}, (), ()),
    ([1, 2, [3, [4, 5, [6], {"7": 8}]]], (), ()),
    ("string", (), ()),
    (True, (), ()),
    (None, (), ()),
    (11.45, (), ()),
    ({"a": float("-inf"), "b": frozenset()}, ((), (FailedProcessConfigFileError,)), ()),
    ({"a": ErrDuringRepr()}, ((FailedProcessConfigFileError,), (FailedProcessConfigFileError,)), ()),
)

PlainTextTests = (
    ("A\nB\nC\nD\nE", (), ()),
    (["A", "B", "C", "D", "E"], (), ({"linesep": "\n"}, {"split_line": True, "remove_linesep": "\n"})),
)


def _insert_sl_cls(
    sl_cls: type[ABCConfigSL], tests: tuple[Any, ...]
) -> Generator[tuple[type[ABCConfigSL], Any], Any, None]:
    yield from ((sl_cls, *test) for test in tests)


LocalFileTests = (
    "sl_cls, raw_data, ignore_excs, init_arguments",
    (
        *_insert_sl_cls(JsonSL, JsonTests),
        *_insert_sl_cls(HJsonSL, HJsonTests),
        *_insert_sl_cls(PickleSL, PickleTests),
        *_insert_sl_cls(PyYamlSL, PyYamlTests),
        *_insert_sl_cls(RuamelYamlSL, RuamelYamlTests),
        *_insert_sl_cls(TomlSL, TOMLTests),
        *_insert_sl_cls(PythonLiteralSL, PythonLiteralTests),
        *_insert_sl_cls(PlainTextSL, PlainTextTests),
    ),
)


@fixture
def pool(tmpdir: Path) -> ConfigPool:
    return ConfigPool(root_path=str(tmpdir))


@mark.parametrize(*LocalFileTests)
def test_local_file_sl_processors(
    pool: ConfigPool,
    sl_cls: type[BasicLocalFileConfigSL],
    raw_data: Any,
    ignore_excs: tuple[EE, EE],
    init_arguments: tuple[Any, Any],
) -> None:
    sl_obj = sl_cls(*init_arguments)
    sl_obj.register_to(pool)

    file: ConfigFile[Any] = ConfigFile(ConfigDataFactory(raw_data), config_format=sl_obj.reg_name)
    file_name = f"TestConfigFile{sl_obj.supported_file_patterns[0]}"

    if not ignore_excs:
        ignore_excs = ((), ())

    with safe_raises(ignore_excs[0]) as info:
        pool.save("", file_name, config=file)
    if info:
        return
    pool.remove("", file_name)
    with safe_raises(ignore_excs[1]) as info:
        loaded_file = pool.load("", file_name)
    if info:
        return
    assert loaded_file == file


TarFileTests = (
    ({"Now": {"supports": {"compression": "!"}}}, (), {"compression": TarCompressionTypes.GZIP}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": TarCompressionTypes.BZIP2}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": TarCompressionTypes.LZMA}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": TarCompressionTypes.ONLY_STORAGE}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": None}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": "lzma"}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": "xz"}),
)

ZipFileTests: tuple[tuple[Any, tuple[EE, ...], dict[str, Any]], ...] = (
    ({"a": True, "b": {"c": [0.5, None]}}, (), {}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": ZipCompressionTypes.ZIP}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": ZipCompressionTypes.BZIP2}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": ZipCompressionTypes.LZMA}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": ZipCompressionTypes.ONLY_STORAGE}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": None}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": "lzma"}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": "xz", "compress_level": 9}),
    ({"a": True, "b": {"c": [0.5, None]}}, (), {"compression": ZipCompressionTypes.ZIP, "compress_level": 9}),
)

CompressedFileTests = (
    "sl_cls, raw_data, ignore_excs, init_arguments",
    (
        *_insert_sl_cls(TarFileSL, TarFileTests),
        *_insert_sl_cls(ZipFileSL, ZipFileTests),
    ),
)


@mark.parametrize(*CompressedFileTests)
def test_compressed_file_sl_processors(
    pool: ConfigPool,
    sl_cls: type[BasicCompressedConfigSL],
    raw_data: Any,
    ignore_excs: tuple[EE, EE],
    init_arguments: dict[str, Any],
) -> None:
    # noinspection PyArgumentList
    compressed_sl = sl_cls(**init_arguments)
    compressed_sl.register_to(pool)
    local_sl = JsonSL(s_arg={"indent": 2})
    local_sl.register_to(pool)

    file: ConfigFile[Any] = ConfigFile(ConfigDataFactory(raw_data), config_format=local_sl.reg_name)
    file_name = f"TestConfigFile{local_sl.supported_file_patterns[0]}{compressed_sl.supported_file_patterns[0]}"

    if not ignore_excs:
        ignore_excs = ((), ())

    with safe_raises(ignore_excs[0]) as info:
        pool.save("", file_name, config=file)
    if info:
        return
    pool.remove("", file_name)
    with safe_raises(ignore_excs[1]) as info:
        loaded_file = pool.load("", file_name)
    if info:
        return
    assert loaded_file == file


ComponentTests: tuple[
    str,
    tuple[
        tuple[
            tuple[ABCConfigSL, ...],
            dict[str, Any],
            dict[str, MappingConfigData[Any]],
            tuple[EE, ...],
            dict[str, Any],
        ],
        ...,
    ],
] = (
    "sl_clss, meta, members, ignore_excs, init_arguments",
    (
        (
            (JsonSL(s_arg={"indent": 2}),),
            {"members": ["test.json"]},
            {"test.json": MappingConfigData({"test": "test"})},
            (),
            {},
        ),
        (
            (JsonSL(s_arg={"indent": 2}),),
            {"members": [{"filename": "test", "config_format": "json"}]},
            {"test": MappingConfigData({"test": "test"})},
            (),
            {},
        ),
        (
            (JsonSL(s_arg={"indent": 2}),),
            {"members": ["test.json"], "orders": {"create": ["test.json"]}, "order": ["test.json"]},
            {"test.json": MappingConfigData({"test": "test"})},
            (),
            {},
        ),
        (
            (JsonSL(s_arg={"indent": 2}),),
            {"members": [{"filename": "test.json", "alies": "t"}], "orders": {"create": ["t"]}, "order": ["t"]},
            {"test.json": MappingConfigData({"test": "test"})},
            (),
            {},
        ),
        (
            (JsonSL(s_arg={"indent": 2}),),
            {"members": ["test.json"], "orders": {"create": ["test.json", "test.json"]}},
            {"test.json": MappingConfigData({"test": "test"})},
            ((ComponentMetadataException,), (), ()),
            {},
        ),
        (
            (
                JsonSL(s_arg={"indent": 2}),
                PythonLiteralSL(),
                ZipFileSL(compress_level=9),
                TarFileSL(compression=TarCompressionTypes.GZIP),
            ),
            {"members": ["test.json.zip", "test.py.tar.gz"], "order": ["test.py.tar.gz", "test.json.zip"]},
            {
                "test.json.zip": MappingConfigData({"test": "test"}),
                "test.py.tar.gz": MappingConfigData({"test": "test"}),
            },
            (),
            {},
        ),
        (
            (JsonSL(s_arg={"indent": 2}),),
            {"members": ["test.json"]},
            {"test.json": MappingConfigData({"test": "test"})},
            (),
            {"meta_file": "meta"},
        ),
        (
            (JsonSL(s_arg={"indent": 2}),),
            {"members": [{"filename": "test", "config_format": "json"}]},
            {"test": MappingConfigData({"test": "test"})},
            (),
            {"meta_file": "sth.sth"},
        ),
        (
            (JsonSL(s_arg={"indent": 2}),),
            {"members": ["test.json"], "orders": {"create": ["test.json"]}, "order": ["test.json"]},
            {"test.json": MappingConfigData({"test": "test"})},
            (),
            {"meta_file": "a meta file!"},
        ),
        (
            (
                JsonSL(s_arg={"indent": 2}),
                PythonLiteralSL(),
                ZipFileSL(compress_level=9),
                TarFileSL(compression=TarCompressionTypes.GZIP),
            ),
            {"members": ["test.json.zip", "test.py.tar.gz"], "order": ["test.py.tar.gz", "test.json.zip"]},
            {
                "test.json.zip": MappingConfigData({"test": "test"}),
                "test.py.tar.gz": MappingConfigData({"test": "test"}),
            },
            (),
            {"meta_file": "$meta"},
        ),
    ),
)


@mark.parametrize(*ComponentTests)
def test_component_file_sl_processor(
    pool: ConfigPool,
    sl_clss: list[ABCConfigSL],
    meta: dict[str | None, MappingConfigData[Any]] | ComponentMeta[Any] | None,
    members: dict[str, Any] | None,
    ignore_excs: tuple[EE, EE, EE],
    init_arguments: dict[str, Any],
) -> None:
    component_sl = ComponentSL(**init_arguments)
    component_sl.register_to(pool)
    for sl_cls in sl_clss:
        sl_cls.register_to(pool)

    if not ignore_excs:
        ignore_excs = ((), (), ())

    with safe_raises(ignore_excs[0]) as info:
        config_data = ComponentConfigData(
            meta
            if isinstance(meta, ComponentMeta)
            else ComponentMetaParser().convert_config2meta(MappingConfigData(meta)),  # type: ignore[arg-type]
            members=members,
        )
    if info:
        return

    file: ConfigFile[Any] = ConfigFile(config_data, config_format=component_sl.reg_name)
    file_name = f"TestConfigFile{sl_clss[0].supported_file_patterns[0]}{component_sl.supported_file_patterns[0]}"

    with safe_raises(ignore_excs[1]) as info:
        pool.save("", file_name, config=file)
    if info:
        return
    pool.remove("", file_name)
    with safe_raises(ignore_excs[2]) as info:
        loaded_data: ComponentConfigData[Any, Any] = pool.load("", file_name).config
    if info:
        return
    assert loaded_data.meta.members == config_data.meta.members
    assert loaded_data.meta.orders == config_data.meta.orders
    assert loaded_data.members == config_data.members


def test_save_none_component(pool: ConfigPool) -> None:
    comp_sl = ComponentSL()
    json_sl = JsonSL()
    comp_sl.register_to(pool)
    json_sl.register_to(pool)

    file_name = f"TestConfigFile{json_sl.supported_file_patterns[0]}{comp_sl.supported_file_patterns[0]}"
    pool.save("", file_name, config=ConfigFile(ConfigDataFactory(), config_format=comp_sl.reg_name))


def test_component_initialize(pool: ConfigPool) -> None:
    comp_sl = ComponentSL()
    json_sl = JsonSL()
    comp_sl.register_to(pool)
    json_sl.register_to(pool)

    file_name = f"TestConfigFile{json_sl.supported_file_patterns[0]}{comp_sl.supported_file_patterns[0]}"
    pool.load("", file_name, allow_initialize=True)


def test_component_wrong_config_data(pool: ConfigPool) -> None:
    comp_sl = ComponentSL()
    json_sl = JsonSL()
    comp_sl.register_to(pool)
    json_sl.register_to(pool)

    file_name = f"TestConfigFile{json_sl.supported_file_patterns[0]}{comp_sl.supported_file_patterns[0]}"
    with raises(FailedProcessConfigFileError, match="is not a"):
        pool.save(
            "",
            file_name,
            config=ConfigFile(SequenceConfigData()),
        )
    pool.discard("", file_name)
    pool.save(
        comp_sl.namespace_formatter("", file_name),
        comp_sl.meta_file + json_sl.supported_file_patterns[0],
        config=ConfigFile(SequenceConfigData()),
    )
    with raises(FailedProcessConfigFileError, match="is not a"):
        pool.load("", file_name)


def test_compressed_component(pool: ConfigPool) -> None:
    component_sl = ComponentSL()
    json_sl = JsonSL()
    tar_sl = TarFileSL(compression=TarCompressionTypes.GZIP, compress_level=0)
    zip_sl = ZipFileSL(compression=ZipCompressionTypes.LZMA, compress_level=9)

    component_sl.register_to(pool)
    json_sl.register_to(pool)
    tar_sl.register_to(pool)
    zip_sl.register_to(pool)

    file_name = f"TestConfigFile{''.join(sl.supported_file_patterns[0] for sl in (json_sl, component_sl, tar_sl))}"
    fn_a = f"a{json_sl.supported_file_patterns[0]}"
    fn_b = f"b{json_sl.supported_file_patterns[0]}{zip_sl.supported_file_patterns[0]}"
    fn_c = f"c{json_sl.supported_file_patterns[0]}{tar_sl.supported_file_patterns[0]}"

    cfg: MappingConfigData[Any] = pool.require(
        "",
        file_name,
        {
            None: {"members": [fn_a, fn_b, fn_c]},
            fn_a: {"key": None},
            fn_b: {"key": True},
            fn_c: {"key": False},
        },
        "component",
    ).check()
    assert cfg.retrieve(rf"\{{{fn_a}\}}\.key") is None
    assert cfg.retrieve(rf"\{{{fn_b}\}}\.key") is True
    assert cfg.retrieve(rf"\{{{fn_c}\}}\.key") is False
    pool.save_all()
    pool.remove("", file_name)
    cfg = pool.load("", file_name).config
    assert cfg.retrieve(rf"\{{{fn_a}\}}\.key") is None
    assert cfg.retrieve(rf"\{{{fn_b}\}}\.key") is True
    assert cfg.retrieve(rf"\{{{fn_c}\}}\.key") is False


def test_python(pool: ConfigPool) -> None:
    PythonSL().register_to(pool)
    PlainTextSL().register_to(pool)

    pool.save(
        "",
        "test-python.py",
        config=ConfigFile(
            dedent(
                """
            if __name__ == "__main__": raise NotImplementedError  # 避免被意外执行
            if locals():  # 如果正在尝试保存数据
                __data__ = locals()
                with open(__data__["file_path"], "w", encoding="utf-8") as f:
                    f.write(str(__data__["data"]))

            key = "value"
            length = len(key)
            repeated = key * length
            from datetime import datetime
            time = datetime.now()
            del datetime  # 避免污染命名空间
            """[1:]
            )
        ),
        config_formats={"plaintext"},
    )

    pool.remove("", "test-python.py")
    cfg: MappingConfigData[Any] = pool.load("", "test-python.py").config

    assert cfg["key"] == "value"
    assert cfg["length"] == 5
    assert cfg["repeated"] == ("value" * 5)
    assert isinstance(cfg["time"], datetime)

    cfg["file_path"] = pool.helper.calc_path(pool.root_path, "", "test.txt")
    data = {"key": "value"}
    cfg["data"] = data
    pool.save("", "test-python.py", config=ConfigFile(cfg))

    str_cfg: StringConfigData[str] = pool.load("", "test.txt").config
    assert str_cfg.data == str(data)


def _restore_environ[F: Callable[[VarArg(Any), KwArg(Any)], Any]](func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        environ = os.environ.copy()
        try:
            return func(*args, **kwargs)
        finally:
            os.environ.clear()
            os.environ.update(environ)

    return cast(F, wrapper)


@_restore_environ
def test_os_env_basic(pool: ConfigPool) -> None:
    OSEnvSL().register_to(pool)

    environ: EnvironmentConfigData = pool.load("", "snapshot.os.env").config
    assert dict(environ) == dict(os.environ)
    environ.unset("TEST_ENV_VAR")  # 预准备 确保该环境变量不存在
    pool.save("", "snapshot.os.env")
    assert "TEST_ENV_VAR" not in os.environ

    # save操作会重置environ内部维护的diff 所以不用担心这里再加回去会被认为还原刚刚的修改
    environ["TEST_ENV_VAR"] = "test"  # 检测同步新增键
    assert "TEST_ENV_VAR" not in os.environ  # 确保不会直接同步修改到环境变量 变更仅内存
    pool.save("", "snapshot.os.env")  # 同步修改到环境变量
    assert "TEST_ENV_VAR" in os.environ
    assert os.environ["TEST_ENV_VAR"] == "test"

    environ["TEST_ENV_VAR"] = "value"
    pool.save("", "snapshot.os.env")
    assert os.environ["TEST_ENV_VAR"] == "value"

    environ.unset("TEST_ENV_VAR")
    pool.save("", "snapshot.os.env")
    assert "TEST_ENV_VAR" not in os.environ


@mark.parametrize(
    "environment_setup, target_environment, strip_prefix, prefix",
    (
        (
            {"TEST_PREFIX_KEY1": "value1", "TEST_PREFIX_KEY2": "value2", "TEST_ENV_VAR": "test"},
            {"TEST_PREFIX_KEY1": "value1", "TEST_PREFIX_KEY2": "value2"},
            False,
            "TEST_PREFIX_",
        ),
        (
            {"TEST_KEY1": "value1", "TEST_KEY2": "value2", "TEST_ENV_VAR": "test"},
            {"TEST_KEY1": "value1", "TEST_KEY2": "value2"},
            True,
            "",
        ),
        (
            {"TEST_PREFIX_KEY1": "value1", "TEST_PREFIX_KEY2": "value2", "TEST_ENV_VAR": "test"},
            {"KEY1": "value1", "KEY2": "value2"},
            True,
            "TEST_PREFIX_",
        ),
    ),
)
@_restore_environ
def test_os_env_prefix(
    pool: ConfigPool,
    environment_setup: dict[str, str],
    target_environment: dict[str, str],
    strip_prefix: bool,  # noqa: FBT001
    prefix: str,
) -> None:
    OSEnvSL(strip_prefix=strip_prefix, prefix=prefix).register_to(pool)

    setup_data = EnvironmentConfigData()
    setup_data |= target_environment
    pool.save("", "setup.os.env", config=ConfigFile(setup_data))
    for key, value in setup_data.items():
        key = prefix + key if strip_prefix else key  # noqa: PLW2901
        assert key in os.environ, f"key {key} should be in os.environ"
        assert os.environ[key] == value, f"key {key} should be equal to {value}"

    for key, value in environment_setup.items():
        os.environ[key] = value

    environment_snapshot: EnvironmentConfigData = pool.load("", "snapshot.os.env").config
    for key, value in target_environment.copy().items():
        assert key in environment_snapshot, f"key {key} should be in environment_snapshot"
        assert environment_snapshot[key] == value, f"key {key} should be equal to {value}"
        del environment_snapshot[key]
    assert not (prefix and environment_snapshot), f"{environment_snapshot:r} should be empty"


def test_wrong_sl_arguments() -> None:
    with raises(TypeError):
        JsonSL(NotImplemented)


SLProcessors = (
    ComponentSL,
    HJsonSL,
    JsonSL,
    OSEnvSL,
    PickleSL,
    PlainTextSL,
    PythonLiteralSL,
    PythonSL,
    PyYamlSL,
    RuamelYamlSL,
    TarFileSL,
    TomlSL,
    ZipFileSL,
)


@mark.parametrize("sl_cls", SLProcessors)
def test_multi_register(pool: ConfigPool, sl_cls: type[ABCConfigSL]) -> None:
    sl_cls().register_to(pool)
    sl_obj = sl_cls()
    sl_obj.register_to(pool)
    assert len(pool.SLProcessors) == 1
    sl_cls(reg_alias=f"{sl_obj.reg_name}$test").register_to(pool)
    assert len(pool.SLProcessors) == 2


@mark.parametrize("sl_cls", SLProcessors)
def test_base(sl_cls: type[BasicConfigSL]) -> None:
    attr_tests: tuple[str, ...] = (
        "processor_reg_name",
        "reg_alias",
        "reg_name",
        "supported_file_patterns",
    )
    if issubclass(sl_cls, BasicLocalFileConfigSL):
        attr_tests = ("saver_args", "loader_args", *attr_tests)
    for attr in attr_tests:
        with raises(AttributeError, match=re.compile(rf"property '{attr}' of '.+' object has no setter")):
            setattr(sl_cls(), attr, None)
        hash(getattr(sl_cls(), attr))

    assert sl_cls() != NotImplemented
    assert sl_cls() == sl_cls()
    assert hash(sl_cls()) == hash(sl_cls())
    assert sl_cls() != sl_cls(reg_alias="never equal")
    assert hash(sl_cls()) != hash(sl_cls(reg_alias="never equal"))

    assert sl_cls().reg_name == sl_cls().processor_reg_name
    assert sl_cls(reg_alias="alias").reg_name == "alias"

    sl_cls().register_to()


LocalSLProcessors = tuple(cls for cls in SLProcessors if issubclass(cls, BasicLocalFileConfigSL))


@mark.parametrize("sl_cls", LocalSLProcessors)
def test_local_file_sl(sl_cls: type[BasicLocalFileConfigSL]) -> None:
    sl_obj = sl_cls()

    with raises(FailedProcessConfigFileError):
        # noinspection PyTypeChecker
        sl_obj.load_file(ConfigFile, None)

    with raises(FailedProcessConfigFileError):
        # noinspection PyTypeChecker
        sl_obj.save_file(ConfigFile, None)  # type: ignore[arg-type]
