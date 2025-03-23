# -*- coding: utf-8 -*-


import re
from collections import OrderedDict

from pytest import fixture
from pytest import mark
from pytest import raises

from C41811.Config import BasicConfigSL
from C41811.Config import BasicLocalFileConfigSL
from C41811.Config import ConfigData
from C41811.Config import ConfigFile
from C41811.Config import ConfigPool
from C41811.Config import JsonSL
from C41811.Config import PickleSL
from C41811.Config import PythonLiteralSL
from C41811.Config.errors import FailedProcessConfigFileError
from C41811.Config.main import BasicCompressedConfigSL
from C41811.Config.processors import TarFileSL
from C41811.Config.processors import ZipFileSL
from C41811.Config.processors.Component import ComponentSL
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
