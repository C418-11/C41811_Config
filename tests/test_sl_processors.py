# -*- coding: utf-8 -*-


import re
from collections import OrderedDict
from datetime import datetime
from textwrap import dedent
from typing import Optional

from pytest import fixture
from pytest import mark
from pytest import raises

from C41811.Config import BasicConfigSL
from C41811.Config import BasicLocalFileConfigSL
from C41811.Config import ComponentConfigData
from C41811.Config import ComponentMeta
from C41811.Config import ComponentSL
from C41811.Config import ConfigData
from C41811.Config import ConfigFile
from C41811.Config import ConfigPool
from C41811.Config import JsonSL
from C41811.Config import MappingConfigData
from C41811.Config import PickleSL
from C41811.Config import PlainTextSL
from C41811.Config import PythonLiteralSL
from C41811.Config import PythonSL
from C41811.Config import TarFileSL
from C41811.Config import ZipFileSL
from C41811.Config.abc import ABCConfigSL
from C41811.Config.errors import FailedProcessConfigFileError
from C41811.Config.main import BasicCompressedConfigSL
from C41811.Config.processors.Component import ComponentMetaParser
from C41811.Config.processors.PyYaml import PyYamlSL
from C41811.Config.processors.RuamelYaml import RuamelYamlSL
from C41811.Config.processors.TarFile import TarCompressionTypes
from C41811.Config.processors.Toml import TomlSL
from C41811.Config.processors.ZipFile import ZipCompressionTypes
from utils import safe_raises

JsonSLTests = (
    (
        {"a": 1, "b": {"c": 2}},
        (), ()
    ),
    (
        {"a": 1, "b": {"c": 2}},
        (), ({"indent": 4}, {})
    ),
    (
        OrderedDict((('b', 2), ('a', 1))),
        (), ({"indent": 4, "sort_keys": True}, {})
    ),
    (
        OrderedDict((('b', 2), ('a', 1))),
        (), ({"indent": 4, "sort_keys": False}, {})
    ),
    (
        [1, 2, [3, [4, 5, [6], {'7': 8}]]],
        (), ({"indent": 2}, {})
    ),
    (
        "string",
        (), ()
    ),
    (
        True,
        (), ()
    ),
    (
        None,
        (), ()
    ),
    (
        11.45,
        (), ()
    ),
    (
        NotImplemented,
        ((FailedProcessConfigFileError,), ()), ()
    ),
    (
        OrderedDict((('b', 2), ('a', 1))),
        ((), (FailedProcessConfigFileError,)), ({}, {"param not exist": None})
    ),
)

PickleSLTests = (
    (
        {"a": 1, "b": 2},
        (), ()
    ),
    (
        {"a": 1, "b": 2},
        (), ({"protocol": 2}, {})
    ),
    (
        {"a": 1, "b": 2},
        (), ((2,), ())
    ),
    (
        OrderedDict((('b', 2), ('a', 1))),
        (), ()
    ),
    (
        [1, 2, [3, [4, 5, [6], {'7': 8}]]],
        (), ()
    ),
    (
        "string",
        (), ()
    ),
    (
        True,
        (), ()
    ),
    (
        None,
        (), ()
    ),
    (
        11.45,
        (), ()
    ),
    (
        NotImplemented,
        (), ()
    ),
    (
        lambda: None,
        ((FailedProcessConfigFileError,), ()), ()
    ),
    (
        None,
        ((), (FailedProcessConfigFileError,)), ({}, {"param not exist": None})
    ),
)

PyYamlTests = (
    (
        {"a": 1, "b": {"c": 2}},
        (), ()
    ),
    (
        {"a": 1, "b": {"c": 2}},
        (), ({"indent": 4}, {})
    ),
    (
        [1, 2, [3, [4, 5, [6], {'7': 8}]]],
        (), ({"indent": 2}, {})
    ),
    (
        "string",
        (), ()
    ),
    (
        True,
        (), ()
    ),
    (
        None,
        (), ()
    ),
    (
        11.45,
        (), ()
    ),
    (
        NotImplemented,
        ((FailedProcessConfigFileError,), ()), ()
    ),
    (
        OrderedDict((('b', 2), ('a', 1))),
        ((FailedProcessConfigFileError,), (FailedProcessConfigFileError,)), ()
    ),
)

RuamelYamlTests = (
    (
        {"a": 1, "b": {"c": 2}},
        (), ()
    ),
    (
        [1, 2, [3, [4, 5, [6], {'7': 8}]]],
        (), ()
    ),
    (
        "string",
        (), ()
    ),
    (
        True,
        (), ()
    ),
    (
        None,
        (), ()
    ),
    (
        11.45,
        (), ()
    ),
    (
        OrderedDict((('b', 2), ('a', 1))),
        (), ()
    ),
    (
        NotImplemented,
        ((FailedProcessConfigFileError,), ()), ()
    ),
)

TOMLTests = (
    (
        {"a": 1, "b": {"c": 2}},
        (), ()
    ),
    (
        {'1': [1, 2, 3]},
        (), ()
    ),
    (
        {},
        (), ()
    ),
    (
        OrderedDict((('b', 2), ('a', 1))),
        (), ()
    ),
    (
        {'1': [[1, 2], [3, 4], [5, 6]]},
        (), ()
    ),
    (
        [1, 2, 3],
        (FailedProcessConfigFileError,), ()
    ),
    (
        "string",
        (FailedProcessConfigFileError,), ()
    ),
    (
        True,
        (FailedProcessConfigFileError,), ()
    ),
    (
        11.45,
        (FailedProcessConfigFileError,), ()
    ),
    (
        None,
        (FailedProcessConfigFileError,), ()
    ),
    (
        NotImplemented,
        ((FailedProcessConfigFileError,), ()), ()
    ),
)


class ErrDuringRepr:
    def __repr__(self):
        raise Exception("repr error")


PythonLiteralTests = (
    (
        {"a": 1, "b": .5},
        (), ()
    ),
    (
        {"a": True, "b": False, "c": None},
        (), ()
    ),
    (
        {"a": {"c": 2}, "b": {"c", 2}},
        (), ()
    ),
    (
        {"a": ["c", 2], "b": ("c", 2)},
        (), ()
    ),
    (
        [1, 2, [3, [4, 5, [6], {'7': 8}]]],
        (), ()
    ),
    (
        "string",
        (), ()
    ),
    (
        True,
        (), ()
    ),
    (
        None,
        (), ()
    ),
    (
        11.45,
        (), ()
    ),
    (
        {"a": float("-inf"), "b": frozenset()},
        ((), (FailedProcessConfigFileError,)), ()
    ),
    (
        {"a": ErrDuringRepr()},
        ((FailedProcessConfigFileError,), (FailedProcessConfigFileError,)), ()
    ),
)

PlainTextTests = (
    (
        "A\nB\nC\nD\nE",
        (), (),
    ),
    (
        ["A", "B", "C", "D", "E"],
        (), ({"linesep": "\n"}, {"split_line": True, "remove_linesep": "\n"}),
    ),
)


def _insert_sl_cls(sl_cls, tests: tuple):
    yield from ((sl_cls, *test) for test in tests)


LocalFileTests = (
    "sl_cls, raw_data, ignore_excs, sl_args",
    (
        *_insert_sl_cls(JsonSL, JsonSLTests),
        *_insert_sl_cls(PickleSL, PickleSLTests),
        *_insert_sl_cls(PyYamlSL, PyYamlTests),
        *_insert_sl_cls(RuamelYamlSL, RuamelYamlTests),
        *_insert_sl_cls(TomlSL, TOMLTests),
        *_insert_sl_cls(PythonLiteralSL, PythonLiteralTests),
        *_insert_sl_cls(PlainTextSL, PlainTextTests),
    )
)


@fixture
def pool(tmpdir):
    return ConfigPool(root_path=tmpdir)


@mark.parametrize(*LocalFileTests)
def test_local_file_sl_processors(pool, sl_cls: type[BasicLocalFileConfigSL], raw_data, ignore_excs, sl_args):
    sl_obj = sl_cls(*sl_args)
    sl_obj.register_to(pool)

    file = ConfigFile(ConfigData(raw_data), config_format=sl_obj.reg_name)
    file_name = f"TestConfigFile{sl_obj.supported_file_patterns[0]}"

    if not ignore_excs:
        ignore_excs = ((), ())

    with safe_raises(ignore_excs[0]) as info:
        pool.save('', file_name, config=file)
    if info:
        return
    pool.delete('', file_name)
    with safe_raises(ignore_excs[1]) as info:
        loaded_file = pool.load('', file_name)
    if info:
        return
    assert loaded_file == file


TarFileTests = (
    (
        {"Now": {"supports": {"compression": "!"}}},
        (), dict(compression=TarCompressionTypes.GZIP)
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression=TarCompressionTypes.BZIP2)
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression=TarCompressionTypes.LZMA)
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression=TarCompressionTypes.ONLY_STORAGE)
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression=None)
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression="lzma")
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression="xz")
    ),
)

ZipFileTests = (
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), {}
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression=ZipCompressionTypes.ZIP)
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression=ZipCompressionTypes.BZIP2)
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression=ZipCompressionTypes.LZMA)
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression=ZipCompressionTypes.ONLY_STORAGE)
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression=None)
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression="lzma")
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression="xz", compress_level=9)
    ),
    (
        {"a": True, "b": {"c": [.5, None]}},
        (), dict(compression=ZipCompressionTypes.ZIP, compress_level=9)
    ),
)

CompressedFileTests = (
    "sl_cls, raw_data, ignore_excs, init_arguments",
    (
        *_insert_sl_cls(TarFileSL, TarFileTests),
        *_insert_sl_cls(ZipFileSL, ZipFileTests),
    )
)


@mark.parametrize(*CompressedFileTests)
def test_compressed_file_sl_processors(
        pool,
        sl_cls: type[BasicCompressedConfigSL],
        raw_data,
        ignore_excs,
        init_arguments: dict
):
    # noinspection PyArgumentList
    compressed_sl = sl_cls(**init_arguments)
    compressed_sl.register_to(pool)
    local_sl = JsonSL(s_arg=dict(indent=2))
    local_sl.register_to(pool)

    file = ConfigFile(ConfigData(raw_data), config_format=local_sl.reg_name)
    file_name = f"TestConfigFile{local_sl.supported_file_patterns[0]}{compressed_sl.supported_file_patterns[0]}"

    if not ignore_excs:
        ignore_excs = ((), ())

    with safe_raises(ignore_excs[0]) as info:
        pool.save('', file_name, config=file)
    if info:
        return
    pool.delete('', file_name)
    with safe_raises(ignore_excs[1]) as info:
        loaded_file = pool.load('', file_name)
    if info:
        return
    assert loaded_file == file


ComponentTests = (
    "sl_clss, meta, members, ignore_excs, init_arguments",
    (
        ((JsonSL(s_arg=dict(indent=2)),),
         {"members": ["test.json"]},
         {"test.json": ConfigData({"test": "test"})},
         (), {}),
        ((JsonSL(s_arg=dict(indent=2)),),
         {"members": [dict(filename="test", config_format="json")]},
         {"test": ConfigData({"test": "test"})},
         (), {}),
        ((JsonSL(s_arg=dict(indent=2)),),
         {"members": ["test.json"], "orders": {"create": ["test.json"]}, "order": ["test.json"]},
         {"test.json": ConfigData({"test": "test"})},
         (), {}),
        ((JsonSL(s_arg=dict(indent=2)),),
         {"members": [dict(filename="test.json", alies="t")], "orders": {"create": ["t"]}, "order": ["t"]},
         {"test.json": ConfigData({"test": "test"})},
         (), {}),
        ((JsonSL(s_arg=dict(indent=2)),),
         {"members": ["test.json"], "orders": {"create": ["test.json", "test.json"]}},
         {"test.json": ConfigData({"test": "test"})},
         ((ValueError,), (), ()), {}),
        ((
             JsonSL(s_arg=dict(indent=2)),  # 爷真是个天才，这都能一遍过正常跑👍
             PythonLiteralSL(),
             ZipFileSL(compress_level=9),
             TarFileSL(compression=TarCompressionTypes.GZIP)
         ),
         {"members": ["test.json.zip", "test.py.tar.gz"], "order": ["test.py.tar.gz", "test.json.zip"]},
         {"test.json.zip": ConfigData({"test": "test"}), "test.py.tar.gz": ConfigData({"test": "test"})},
         (), {}),
    )
)


@mark.parametrize(*ComponentTests)
def test_component_file_sl_processor(
        pool,
        sl_clss: list[ABCConfigSL],
        meta: Optional[dict] | ComponentMeta,
        members: Optional[dict],
        ignore_excs,
        init_arguments: dict
):
    component_sl = ComponentSL(**init_arguments)
    component_sl.register_to(pool)
    for sl_cls in sl_clss:
        sl_cls.register_to(pool)

    if not ignore_excs:
        ignore_excs = ((), (), ())

    with safe_raises(ignore_excs[0]) as info:
        config_data = ComponentConfigData(
            meta if isinstance(meta, ComponentMeta) else ComponentMetaParser().convert_config2meta(ConfigData(meta)),
            members=members,
        )
    if info:
        return

    file = ConfigFile(config_data, config_format=component_sl.reg_name)
    file_name = f"TestConfigFile{sl_clss[0].supported_file_patterns[0]}{component_sl.supported_file_patterns[0]}"

    with safe_raises(ignore_excs[1]) as info:
        pool.save('', file_name, config=file)
    if info:
        return
    pool.delete('', file_name)
    with safe_raises(ignore_excs[2]) as info:
        loaded_data: ComponentConfigData = pool.load('', file_name).config
    if info:
        return
    assert loaded_data.meta.members == config_data.meta.members
    assert loaded_data.meta.orders == config_data.meta.orders
    assert loaded_data.members == config_data.members


def test_save_none_component(pool):
    comp_sl = ComponentSL()
    json_sl = JsonSL()
    comp_sl.register_to(pool)
    json_sl.register_to(pool)

    file_name = f"TestConfigFile{json_sl.supported_file_patterns[0]}{comp_sl.supported_file_patterns[0]}"
    pool.save('', file_name, config=ConfigFile(ConfigData(), config_format=comp_sl.reg_name))


def test_component_initialize(pool):
    comp_sl = ComponentSL()
    json_sl = JsonSL()
    comp_sl.register_to(pool)
    json_sl.register_to(pool)

    file_name = f"TestConfigFile{json_sl.supported_file_patterns[0]}{comp_sl.supported_file_patterns[0]}"
    pool.load('', file_name, allow_create=True)


def test_component_wrong_config_data(pool):
    comp_sl = ComponentSL()
    json_sl = JsonSL()
    comp_sl.register_to(pool)
    json_sl.register_to(pool)

    file_name = f"TestConfigFile{json_sl.supported_file_patterns[0]}{comp_sl.supported_file_patterns[0]}"
    with raises(FailedProcessConfigFileError, match="is not a"):
        pool.save(
            '', file_name,
            config=ConfigFile(ConfigData([])),
        )
    pool.unset('', file_name)
    pool.save(
        comp_sl.namespace_formatter('', file_name), comp_sl.initial_file + json_sl.supported_file_patterns[0],
        config=ConfigFile(ConfigData([])),
    )
    with raises(FailedProcessConfigFileError, match="is not a"):
        pool.load('', file_name, )


def test_python(pool):
    PythonSL().register_to(pool)
    PlainTextSL().register_to(pool)

    pool.save(
        '', "test-python.py",
        config=ConfigFile(dedent(
            """
            key = "value"

            length = len(key)

            repeated = key * length

            from datetime import datetime as _dt

            datetime = _dt.now()
            """
        )), config_formats={"plaintext"})

    pool.unset('', "test-python.py")
    cfg: MappingConfigData = pool.load('', "test-python.py").config

    assert cfg["key"] == "value"
    assert cfg["length"] == 5
    assert cfg["repeated"] == ("value" * 5)
    assert isinstance(cfg["datetime"], datetime)


def test_wrong_sl_arguments():
    with raises(TypeError):
        JsonSL(NotImplemented)


SLProcessors = (
    JsonSL,
    PickleSL,
    PythonLiteralSL,
    PyYamlSL,
    RuamelYamlSL,
    TomlSL,
    TarFileSL,
    ZipFileSL,
    ComponentSL,
    PythonSL,
    PlainTextSL,
)


@mark.parametrize("sl_cls", SLProcessors)
def test_multi_register(pool, sl_cls):
    sl_cls().register_to(pool)
    sl_obj = sl_cls()
    sl_obj.register_to(pool)
    assert len(pool.SLProcessors) == 1
    sl_cls(reg_alias=f"{sl_obj.reg_name}$test").register_to(pool)
    assert len(pool.SLProcessors) == 2


@mark.parametrize("sl_cls", SLProcessors)
def test_base(sl_cls: type[BasicConfigSL]):
    attr_tests = (
        "processor_reg_name",
        "reg_alias",
        "reg_name",
        "supported_file_patterns",
    )
    if issubclass(sl_cls, BasicLocalFileConfigSL):
        attr_tests = (
            "saver_args",
            "loader_args",
            *attr_tests
        )
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
def test_local_file_sl(sl_cls):
    sl_obj = sl_cls()

    with raises(FailedProcessConfigFileError):
        # noinspection PyTypeChecker
        sl_obj.load_file(ConfigFile, None)

    with raises(FailedProcessConfigFileError):
        # noinspection PyTypeChecker
        sl_obj.save_file(ConfigFile, None)
