# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

import operator
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import MutableSequence
from collections.abc import Sequence
from typing import Any
from typing import Literal
from typing import Optional
from typing import Self
from typing import cast
from typing import override

from ._generate_operators import generate
from ._generate_operators import operate
from .core import BasicIndexedConfigData
from .core import BasicSingleConfigData
from .utils import check_read_only


@generate
class SequenceConfigData[D: Sequence[Any]](
    BasicIndexedConfigData[D],
    MutableSequence[Any]
):
    """
    序列配置数据

    .. versionadded:: 0.1.5
    """
    _data: D
    data: D

    def __init__(self, data: Optional[D] = None):
        if data is None:
            data = list()  # type: ignore[assignment]
        super().__init__(cast(D, data))

    @override
    @property
    def data_read_only(self) -> bool:
        return not isinstance(self._data, MutableSequence)

    @override
    @check_read_only
    def append(self, value: Any) -> None:
        self._data.append(value)  # type: ignore[attr-defined]

    @override
    @check_read_only
    def insert(self, index: int, value: Any) -> None:
        self._data.insert(index, value)  # type: ignore[attr-defined]

    @override
    @check_read_only
    def extend(self, values: Iterable[Any]) -> None:
        self._data.extend(values)  # type: ignore[attr-defined]

    @override
    def index(self, *args: Any) -> int:
        return self._data.index(*args)

    @override
    def count(self, value: Any) -> int:
        return self._data.count(value)

    @override
    @check_read_only
    def pop(self, index: int = -1) -> Any:
        return self._data.pop(index)  # type: ignore[attr-defined]

    @override
    @check_read_only
    def remove(self, value: Any) -> None:
        self._data.remove(value)  # type: ignore[attr-defined]

    @override
    @check_read_only
    def clear(self) -> None:
        self._data.clear()  # type: ignore[attr-defined]

    @override
    @check_read_only
    def reverse(self) -> None:
        self._data.reverse()  # type: ignore[attr-defined]

    def __reversed__(self) -> Iterator[D]:
        return reversed(self._data)

    @operate(operator.mul, operator.imul)
    def __mul__(self, other: Any) -> Self: ...  # type: ignore[empty-body]

    @operate(operator.add, operator.iadd)
    def __add__(self, other: Any) -> Self: ...  # type: ignore[empty-body]

    def __rmul__(self, other: Any) -> Self: ...  # type: ignore[empty-body]

    def __radd__(self, other: Any) -> Self: ...  # type: ignore[empty-body]


@generate
class StringConfigData[D: str | bytes](BasicSingleConfigData[D]):
    """
    字符/字节串配置数据
    """
    _data: D
    data: D

    def __init__(self, data: Optional[D] = None):
        if data is None:
            data = str()  # type: ignore[assignment]
        super().__init__(cast(D, data))

    @override
    @property
    def data_read_only(self) -> Literal[False]:
        return False

    def __format__(self, format_spec: str) -> str:
        return self._data.__format__(format_spec)

    @operate(operator.add, operator.iadd)
    def __add__(self, other: Any) -> Self: ...  # type: ignore[empty-body]

    @operate(operator.mul, operator.imul)
    def __mul__(self, other: Any) -> Self: ...  # type: ignore[empty-body]

    def __contains__(self, key: Any) -> bool:
        return key in self._data

    def __iter__(self) -> Iterator[D]:
        return iter(cast(Iterable[D], self._data))

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, item: Any) -> D:
        return cast(D, self._data[item])

    @check_read_only
    def __setitem__(self, key: Any, value: D) -> None:
        self._data[key] = value  # type: ignore[index]

    @check_read_only
    def __delitem__(self, key: Any) -> None:
        del self._data[key]  # type: ignore[union-attr]

    def __reversed__(self) -> Any:  # 不支持reversed[D]语法
        return reversed(self._data)


__all__ = (
    "SequenceConfigData",
    "StringConfigData",
)
