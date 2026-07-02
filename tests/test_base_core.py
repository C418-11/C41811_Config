import functools
import itertools
import operator
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path as FPath
from typing import Any
from typing import ClassVar
from typing import cast

from jproperties import Properties as JProperties
from pytest import fixture
from pytest import mark
from utils import EE
from utils import safe_raises

from c41811.config import BoolConfigData
from c41811.config import ConfigDataFactory
from c41811.config import ConfigFile
from c41811.config import ConfigPool
from c41811.config import EnvironmentConfigData
from c41811.config import JPropertiesConfigData
from c41811.config import MappingConfigData
from c41811.config import NumberConfigData
from c41811.config import ObjectConfigData
from c41811.config import SequenceConfigData
from c41811.config import StringConfigData
from c41811.config.abc import ABCConfigData
from c41811.config.errors import UnsupportedConfigFormatError

type D_MCD = MappingConfigData[dict[Any, Any]]


def test_wrong_type_config_data() -> None:
    class EmptyTypesConfigDataFactory(ConfigDataFactory):
        TYPES: ClassVar[OrderedDict[tuple[type, ...], Callable[[Any], Any] | type]] = OrderedDict()

    with safe_raises(TypeError, match="Unsupported type"):
        EmptyTypesConfigDataFactory(type)


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
        return ConfigPool(root_path=str(tmpdir))

    @staticmethod
    def test_attr_readonly(file: ConfigFile[D_MCD], data: D_MCD) -> None:
        assert file.config == data
        with safe_raises(AttributeError):
            # noinspection PyPropertyAccess
            file.config = None  # type: ignore[misc, assignment]

        assert file.config_format == "json"
        with safe_raises(AttributeError):
            # noinspection PyPropertyAccess
            file.config_format = None  # type: ignore[misc]

    @staticmethod
    def test_wrong_save(data: D_MCD, pool: P) -> None:
        file: ConfigFile[D_MCD] = ConfigFile(data)
        with safe_raises(UnsupportedConfigFormatError, match="Unspecified config format"):
            file.save(pool, "", ".json")

        with safe_raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.save(pool, "", ".json", config_format="json")

    @staticmethod
    def test_wrong_load(file: ConfigFile[D_MCD], pool: P) -> None:
        with safe_raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.load(pool, "", ".json", config_format="json")

    @staticmethod
    def test_wrong_initialize(file: ConfigFile[D_MCD], pool: P) -> None:
        with safe_raises(UnsupportedConfigFormatError, match="Unsupported config format: json"):
            file.initialize(pool, "", ".json", config_format="json")

    ExtraKwargs = ({"config_format": "json"},)

    CombExtraKwargs: list[dict[str, str]] = []  # noqa: RUF012
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
    def test_eq(a: ConfigFile[D_MCD], b: ConfigFile[D_MCD], is_eq: bool) -> None:  # noqa: FBT001
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
    def test_bool(raw_data: D_MCD, is_empty: bool) -> None:  # noqa: FBT001
        assert bool(ConfigFile(ConfigDataFactory(raw_data))) is not is_empty

    @staticmethod
    def test_repr(file: ConfigFile[D_MCD], data: D_MCD) -> None:
        assert repr(file.config) in repr(file)
        assert repr(data) in repr(ConfigFile(data))


@mark.parametrize(
    "typ, args, target, excs",
    (
        (EnvironmentConfigData, (1,), None, (TypeError,)),
        (EnvironmentConfigData, ({},), EnvironmentConfigData(), ()),
        (EnvironmentConfigData, (None,), EnvironmentConfigData({}), ()),
        (JPropertiesConfigData, (1,), None, (TypeError,)),
        (JPropertiesConfigData, ({}), JPropertiesConfigData(), ()),
        (JPropertiesConfigData, (JProperties(),), JPropertiesConfigData(), ()),
        (JPropertiesConfigData, (None,), JPropertiesConfigData(JProperties()), ()),
        (MappingConfigData, (1,), None, (TypeError,)),
        (MappingConfigData, ({},), MappingConfigData(), ()),
        (MappingConfigData, (None,), MappingConfigData({}), ()),
        (NumberConfigData, ("a",), None, (TypeError,)),
        (NumberConfigData, ("123",), None, (TypeError,)),
        (NumberConfigData, (0,), NumberConfigData(), ()),
        (NumberConfigData, (0.0,), NumberConfigData(0), ()),
        (NumberConfigData, (None,), NumberConfigData(0), ()),
        (BoolConfigData, ("",), BoolConfigData(False), ()),  # noqa: FBT003
        (BoolConfigData, ("abc",), BoolConfigData(True), ()),  # noqa: FBT003
        (BoolConfigData, (), BoolConfigData(False), ()),  # noqa: FBT003
        (BoolConfigData, (1,), BoolConfigData(True), ()),  # noqa: FBT003
        (BoolConfigData, ([],), BoolConfigData(False), ()),  # noqa: FBT003
        (BoolConfigData, (None,), BoolConfigData(False), ()),  # noqa: FBT003
        (ObjectConfigData, (), None, (TypeError,)),
        (ObjectConfigData, (111,), ObjectConfigData(111), ()),
        (SequenceConfigData, (1,), None, (TypeError,)),
        (SequenceConfigData, ("123",), SequenceConfigData("123"), ()),
        (SequenceConfigData, ((2, 1),), SequenceConfigData((2, 1)), ()),
        (SequenceConfigData, (), SequenceConfigData([]), ()),
        (SequenceConfigData, (None,), SequenceConfigData([]), ()),
        (StringConfigData, (1,), None, (TypeError,)),
        (StringConfigData, (b"",), StringConfigData(b""), (TypeError,)),
        (StringConfigData, (), StringConfigData(""), (TypeError,)),
        (StringConfigData, (None,), StringConfigData(""), (TypeError,)),
    ),
)
def test_base_type_init(typ: type, args: tuple[Any, ...], target: ABCConfigData | None, excs: EE):
    with safe_raises(excs):
        assert typ(*args) == target
