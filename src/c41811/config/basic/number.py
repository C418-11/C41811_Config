# cython: language_level = 3  # noqa: ERA001


"""
数值类型配置数据实现

.. versionadded:: 0.2.0
"""

import math
import operator
from numbers import Number
from typing import Any
from typing import Literal
from typing import Self
from typing import cast
from typing import override

from ._generate_operators import generate
from ._generate_operators import operate
from .core import BasicSingleConfigData


@generate
class NumberConfigData[D: int | float | Number](BasicSingleConfigData[D]):
    """
    数值配置数据

    .. versionadded:: 0.1.5
    """

    _data: D

    def __init__(self, data: D | None = None):
        """
        :param data: 数值数据
        :type data: D | None
        """  # noqa: D205
        if data is None:
            data = 0  # type: ignore[assignment]
        super().__init__(cast(D, data))

    @property
    @override
    def data_read_only(self) -> Literal[False]:
        """
        配置数据是否为只读

        :return: 配置数据是否为只读
        :rtype: Literal[False]

        .. note::
           该配置数据类始终认为配置数据非只读，使其能正确作为配置数据容器使用
        """  # noqa: RUF002
        return False

    @property  # type: ignore[explicit-override]  # mypy抽风
    @override
    def data(self) -> D:
        """
        配置的原始数据

        .. caution::
           未默认做深拷贝，可能导致非预期的行为

        .. versionchanged:: 0.3.0
           现在是可写属性
        """  # noqa: RUF002
        return self._data

    @data.setter
    def data(self, data: D) -> None:
        self._data = data

    def __int__(self) -> int:
        return int(self._data)  # type: ignore[arg-type]

    def __float__(self) -> float:
        return float(self._data)  # type: ignore[arg-type]

    @operate(operator.add, operator.iadd)
    def __add__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.sub, operator.isub)
    def __sub__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.mul, operator.imul)
    def __mul__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.truediv, operator.itruediv)
    def __truediv__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.floordiv, operator.ifloordiv)
    def __floordiv__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.mod, operator.imod)
    def __mod__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.pow, operator.ipow)
    def __pow__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.and_, operator.iand)
    def __and__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.or_, operator.ior)
    def __or__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.xor, operator.ixor)
    def __xor__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.matmul, operator.imatmul)
    def __matmul__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.lshift, operator.ilshift)
    def __lshift__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    @operate(operator.rshift, operator.irshift)
    def __rshift__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __radd__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __rsub__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __rmul__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __rtruediv__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __rfloordiv__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __rmod__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __rpow__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __rand__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __ror__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __rxor__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __rmatmul__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __rlshift__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __rrshift__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __invert__(self) -> Any:
        return ~self._data  # type: ignore[operator]

    def __neg__(self) -> Any:
        return -self._data  # type: ignore[operator]

    def __pos__(self) -> Any:
        return +self._data  # type: ignore[operator]

    def __abs__(self) -> D:
        return abs(self._data)  # type: ignore[return-value,arg-type]

    # noinspection SpellCheckingInspection
    def __round__(self, ndigits: int | None = None) -> Any:
        return round(self._data, ndigits)  # type: ignore[arg-type]

    def __trunc__(self) -> Any:
        return math.trunc(self._data)  # type: ignore[arg-type]

    def __floor__(self) -> Any:
        return math.floor(self._data)  # type: ignore[arg-type]

    def __ceil__(self) -> Any:
        return math.ceil(self._data)  # type: ignore[arg-type]

    def __index__(self) -> Any:
        return self._data.__index__()  # type: ignore[union-attr]


class BoolConfigData[D: bool](NumberConfigData[D]):
    # noinspection GrazieInspection
    """
    布尔值配置数据

    .. versionadded:: 0.1.5

    .. versionchanged:: 0.2.0
       直接对参数调用 :py:class:`bool`
    """

    _data: D
    data: D

    def __init__(self, data: D | None = None):
        """
        :param data: 布尔值数据
        :type data: D | None
        """  # noqa: D205
        super().__init__(cast(D, bool(data)))


__all__ = (
    "BoolConfigData",
    "NumberConfigData",
)
