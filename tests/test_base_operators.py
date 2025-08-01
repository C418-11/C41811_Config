import operator
from collections.abc import Callable
from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from pytest import mark

from c41811.config import ConfigDataFactory as CDFactory
from c41811.config.abc import ABCConfigData


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
    assert op(CDFactory(a)) == op(a), f"op({CDFactory(a):r}) != {op(a)}"


DyadicOperatorTests = (
    "a, b, op, iop, convert_raw",
    (
        *_insert_operator(TestMappingConfigData.MergeTests, operator.or_, operator.ior, True),  # noqa: FBT003
        *_insert_operator(TestSequenceConfigData.RepeatTests, operator.mul, operator.imul, False),  # noqa: FBT003
        *_insert_operator(TestSequenceConfigData.ExtendTests, operator.add, operator.iadd, False),  # noqa: FBT003
    ),
)


@mark.parametrize(*DyadicOperatorTests)
def test_dyadic_operator(
    a: ABCConfigData,
    b: ABCConfigData,
    op: Callable[[Any, Any], Any],
    iop: Callable[[Any, Any], Any],
    convert_raw: bool,  # noqa: FBT001
) -> None:
    converter: Callable[[Any], Any] = (lambda _: _) if convert_raw else CDFactory
    assert op(CDFactory(a), CDFactory(b)) == CDFactory(op(a, b)), (
        f"op({CDFactory(a):r}, {CDFactory(b):r}) != {CDFactory(op(a, b)):r}"
    )
    assert op(a, CDFactory(b)) == CDFactory(op(a, b)), f"op({a}, {CDFactory(b):r}) != {CDFactory(op(a, b)):r}"
    assert op(CDFactory(a), b) == CDFactory(op(a, b)), f"op({CDFactory(a):r}, {b}) != {CDFactory(op(a, b)):r}"

    assert op(CDFactory(b), CDFactory(a)) == CDFactory(op(b, a)), (
        f"op({CDFactory(b):r}, {CDFactory(a):r}) != {CDFactory(op(b, a)):r}"
    )
    assert op(b, CDFactory(a)) == CDFactory(op(b, a)), f"op({b}, {CDFactory(a):r}) != {CDFactory(op(b, a)):r}"
    assert op(CDFactory(b), a) == CDFactory(op(b, a)), f"op({CDFactory(b):r}, {a}) != {CDFactory(op(b, a)):r}"

    assert iop(CDFactory(deepcopy(a)), CDFactory(b)) == CDFactory(iop(deepcopy(a), b)), (
        f"iop({CDFactory(deepcopy(a)):r}, {CDFactory(b):r}) != {CDFactory(iop(deepcopy(a), b)):r}"
    )
    assert iop(deepcopy(a), CDFactory(b)) == converter(iop(deepcopy(a), b)), (
        f"iop({deepcopy(a)}, {CDFactory(b):r}) != {converter(iop(deepcopy(a), b)):r}"
    )
    assert iop(CDFactory(deepcopy(a)), b) == CDFactory(iop(deepcopy(a), b)), (
        f"iop({CDFactory(deepcopy(a)):r}, {b}) != {CDFactory(iop(deepcopy(a), b)):r}"
    )
