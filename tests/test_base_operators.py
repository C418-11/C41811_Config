import operator
from collections.abc import Callable
from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from pytest import mark

from C41811.Config import ConfigData


class TestMappingConfigData:
    MergeTests = (
        ({"a": 1, "b": 2}, {"a": -1, "b": 3}),
        ({"a": 1, "b": 2}, {"b": 3, "c": 4}),
        ({"a": 1, "b": 2}, {"b": 3}),
    )


class TestNumberConfigData:
    InvertTests = (
        (0,),
        (2,),
        (4562,),
    )
    IndexTests = InvertTests
    RoundTests = (
        (0,),
        (2,),
        (4562,),
        (9.2,),
    )
    NegTests = ((0,), (2,), (4562,), (9.2,), (1.2j,))
    PosTests = NegTests
    AbsTests = NegTests


class TestSequenceConfigData:
    RepeatTests = (
        ([1, 2, 3], 3),
        ([7], 4),
        ([9, 4, 2, 6], 8),
    )

    ExtendTests = (
        ([1, 2, 3], [4, 5, 6]),
        ([7], [8, 9, 10]),
        ([9, 4, 2, 6], [8, 7, 6, 5]),
    )


def _insert_operator(
    tests: tuple[Any, ...],
    op: Callable[[Any], Any] | Callable[[Any, Any], Any],
    iop: Callable[[Any], Any] | Callable[[Any, Any], Any] | None = None,
    *ext: Any,
) -> Iterable[tuple[Any, Any, Any]]:
    yield from ((*test, *((op,) if iop is None else (op, iop)), *ext) for test in tests)


UnaryOperatorTests = (
    "a, op",
    (
        *_insert_operator(TestNumberConfigData.InvertTests, operator.invert),
        *_insert_operator(TestNumberConfigData.NegTests, operator.neg),
        *_insert_operator(TestNumberConfigData.PosTests, operator.pos),
        *_insert_operator(TestNumberConfigData.AbsTests, operator.abs),
        *_insert_operator(TestNumberConfigData.RoundTests, round),
        *_insert_operator(TestNumberConfigData.IndexTests, operator.index),
    ),
)


@mark.parametrize(*UnaryOperatorTests)
def test_unary_operator(a: Any, op: Callable[[Any], Any]) -> None:
    assert op(ConfigData(a)) == op(a), f"op({ConfigData(a):r}) != {op(a)}"


DyadicOperatorTests = (
    "a, b, op, iop, convert_raw",
    (
        *_insert_operator(TestMappingConfigData.MergeTests, operator.or_, operator.ior, True),
        *_insert_operator(TestSequenceConfigData.RepeatTests, operator.mul, operator.imul, False),
        *_insert_operator(TestSequenceConfigData.ExtendTests, operator.add, operator.iadd, False),
    ),
)


@mark.parametrize(*DyadicOperatorTests)
def test_dyadic_operator(
    a: ConfigData,
    b: ConfigData,
    op: Callable[[Any, Any], Any],
    iop: Callable[[Any, Any], Any],
    convert_raw: bool,
) -> None:
    converter: Callable[[Any], Any] = (lambda _: _) if convert_raw else ConfigData
    assert op(ConfigData(a), ConfigData(b)) == ConfigData(op(a, b)), (
        f"op({ConfigData(a):r}, {ConfigData(b):r}) != {ConfigData(op(a, b)):r}"
    )
    assert op(a, ConfigData(b)) == ConfigData(op(a, b)), f"op({a}, {ConfigData(b):r}) != {ConfigData(op(a, b)):r}"
    assert op(ConfigData(a), b) == ConfigData(op(a, b)), f"op({ConfigData(a):r}, {b}) != {ConfigData(op(a, b)):r}"

    assert op(ConfigData(b), ConfigData(a)) == ConfigData(op(b, a)), (
        f"op({ConfigData(b):r}, {ConfigData(a):r}) != {ConfigData(op(b, a)):r}"
    )
    assert op(b, ConfigData(a)) == ConfigData(op(b, a)), f"op({b}, {ConfigData(a):r}) != {ConfigData(op(b, a)):r}"
    assert op(ConfigData(b), a) == ConfigData(op(b, a)), f"op({ConfigData(b):r}, {a}) != {ConfigData(op(b, a)):r}"

    assert iop(ConfigData(deepcopy(a)), ConfigData(b)) == ConfigData(iop(deepcopy(a), b)), (
        f"iop({ConfigData(deepcopy(a)):r}, {ConfigData(b):r}) != {ConfigData(iop(deepcopy(a), b)):r}"
    )
    assert iop(deepcopy(a), ConfigData(b)) == converter(iop(deepcopy(a), b)), (
        f"iop({deepcopy(a)}, {ConfigData(b):r}) != {converter(iop(deepcopy(a), b)):r}"
    )
    assert iop(ConfigData(deepcopy(a)), b) == ConfigData(iop(deepcopy(a), b)), (
        f"iop({ConfigData(deepcopy(a)):r}, {b}) != {ConfigData(iop(deepcopy(a), b)):r}"
    )
