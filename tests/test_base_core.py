import functools
import itertools
import operator
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path as FPath
from typing import Any
from typing import ClassVar
from typing import cast

from pytest import fixture
from pytest import mark
from pytest import raises

from C41811.Config import ConfigData
from C41811.Config import ConfigFile
from C41811.Config import ConfigPool
from C41811.Config import MappingConfigData
from C41811.Config.errors import UnsupportedConfigFormatError

type D_MCD = MappingConfigData[dict[Any, Any]]


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
        return cast(D_MCD, MappingConfigData({"foo": {"bar": 123}, "foo1": 114, "foo2": ["bar"]}))

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
            file.save(pool, "", ".json")

        with raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.save(pool, "", ".json", config_format="json")

    @staticmethod
    def test_wrong_load(file: ConfigFile[D_MCD], pool: P) -> None:
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.load(pool, "", ".json", config_format="json")

    @staticmethod
    def test_wrong_initialize(file: ConfigFile[D_MCD], pool: P) -> None:
        with raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.initialize(pool, "", ".json", config_format="json")

    ExtraKwargs = ({"config_format": "json"},)

    CombExtraKwargs: list[dict[str, str]] = []
    for i in range(1, len(ExtraKwargs) + 1):
        CombExtraKwargs.extend(
            functools.reduce(operator.or_, kwargs_tuple) for kwargs_tuple in itertools.combinations(ExtraKwargs, i)
        )

    CombEQKwargs: tuple[
        dict[str, dict[str, dict[str, int]] | str],
        ...,
    ] = tuple(
        d[0] | k
        for d, k in itertools.product(
            itertools.product(
                (
                    {"initial_config": {"foo": {"bar": 123}}},
                    {"initial_config": {"foo": {"bar": 456}}},
                )
            ),
            CombExtraKwargs,
        )
    )

    EQTests: tuple[str, tuple[tuple[ConfigFile[D_MCD], ConfigFile[D_MCD], bool], ...]] = (
        "a, b, is_eq",
        tuple(
            (
                (ConfigFile(**cast(dict[str, Any], a)), ConfigFile(**cast(dict[str, Any], b)), a == b)
                for a, b in itertools.product(CombEQKwargs, CombEQKwargs)
            )
        ),
    )

    @staticmethod
    @mark.parametrize(*EQTests)
    def test_eq(a: ConfigFile[D_MCD], b: ConfigFile[D_MCD], is_eq: bool) -> None:
        assert (a == b) is is_eq

    @staticmethod
    def test_eq_diff_type(file: ConfigFile[D_MCD]) -> None:
        assert file != NotImplemented

    @staticmethod
    @mark.parametrize(
        "raw_data, is_empty",
        (
            ({}, True),
            ({"foo": 123}, False),
        ),
    )
    def test_bool(raw_data: D_MCD, is_empty: bool) -> None:
        assert bool(ConfigFile(ConfigData(raw_data))) is not is_empty

    @staticmethod
    def test_repr(file: ConfigFile[D_MCD], data: D_MCD) -> None:
        assert repr(file.config) in repr(file)
        assert repr(data) in repr(ConfigFile(data))
