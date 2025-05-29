

import math
from collections.abc import Callable
from numbers import Number
from typing import Any

from pytest import fixture
from pytest import mark

from C41811.Config import BoolConfigData
from C41811.Config import NumberConfigData


class TestNumberConfigData:
    @staticmethod
    @fixture
    def number() -> int:
        return 0

    @staticmethod
    @fixture
    def data[N: Number](number: N) -> NumberConfigData[N]:
        return NumberConfigData(number)

    @staticmethod
    @fixture
    def readonly_data[N: Number](number: N) -> NumberConfigData[N]:
        cfg = NumberConfigData(number)
        cfg.freeze()
        return cfg

    @staticmethod
    def test_freeze(
            data: NumberConfigData[int],  # type: ignore[type-var]
            readonly_data: NumberConfigData[int]  # type: ignore[type-var]
    ) -> None:
        data.freeze()
        readonly_data.freeze()
        assert data.read_only is True
        assert readonly_data.read_only is False
        data.freeze(True)
        readonly_data.freeze(True)
        assert data.read_only is True
        assert readonly_data.read_only is True
        data.freeze(False)
        readonly_data.freeze(False)
        assert data.read_only is False
        assert readonly_data.read_only is False

    @staticmethod
    def test_init(data: NumberConfigData[int], readonly_data: NumberConfigData[int]) -> None:  # type: ignore[type-var]
        assert data.data == 0
        assert data.read_only is False

        assert NumberConfigData().data == 0

        assert readonly_data.data == 0
        assert readonly_data.read_only is True

    @staticmethod
    @mark.parametrize("number", (
            0,
            0.,
    ))
    def test_int(number: Number) -> None:
        assert int(NumberConfigData(number)) == 0

    @staticmethod
    @mark.parametrize("number", (
            0,
            0.,
    ))
    def test_float(number: Number) -> None:
        assert float(NumberConfigData(number)) == 0.

    @staticmethod
    @mark.parametrize("number, value", (
            (0, False),
            (0., False),
            (1, True),
            (.1, True),
            (0j, False),
            (1j, True),
            (0.j, False),
            (.1j, True),
    ))
    def test_bool(number: Number, value: bool) -> None:
        assert bool(NumberConfigData(number)) == value

    @staticmethod
    @mark.parametrize("func, number, args", (
            (round, 0.55, ()),
            (round, 0.55, (2,)),
            (round, 0.55, (1,)),
            (math.trunc, -0.55, ()),
            (math.trunc, 0.55, ()),
            (math.trunc, 1.55, ()),
            (math.ceil, 0, ()),
            (math.ceil, 0.5, ()),
            (math.ceil, 0.4, ()),
            (math.ceil, 1.5, ()),
            (math.ceil, 1.4, ()),
            (math.floor, 0, ()),
            (math.floor, 0.5, ()),
            (math.floor, 0.4, ()),
            (math.floor, 1.5, ()),
            (math.floor, 1.4, ()),
    ))
    def test_protocol(func: Callable[..., Any], number: Number, args: Any) -> None:
        assert func(NumberConfigData(number), *args) == func(number, *args)


class TestBoolConfigData:
    @staticmethod
    def test_init() -> None:
        assert BoolConfigData().data is False
