# cython: language_level = 3  # noqa: ERA001

"""
杂项实用程序

.. versionadded:: 0.2.0
"""

from collections import OrderedDict
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence
from copy import deepcopy
from functools import wraps
from types import NotImplementedType
from typing import Any
from typing import Self
from typing import cast
from typing import override


def singleton[C: type[Any]](target_cls: C, /) -> C:
    """
    单例模式类装饰器

    :param target_cls: 目标类
    :type target_cls: C

    :return: 装饰后的类
    :rtype: C
    """

    @wraps(target_cls.__new__)
    def new_singleton(cls: C, /, *args: Any, **kwargs: Any) -> C:
        if not hasattr(cls, "__singleton_instance__"):
            # noinspection PyUnresolvedReferences
            cls.__singleton_instance__ = cls.__singleton_new__(cls, *args, **kwargs)

        # noinspection PyProtectedMember
        return cast(C, cls.__singleton_instance__)

    target_cls.__singleton_new__ = target_cls.__new__
    target_cls.__new__ = staticmethod(new_singleton)  # type: ignore[assignment]

    return target_cls


@singleton
class UnsetType:
    """用于填充默认值的特殊值"""

    __slots__ = ()

    @override
    def __str__(self) -> str:
        return "<Unset Argument>"

    def __bool__(self) -> bool:
        return False


Unset = UnsetType()
"""
用于填充默认值的特殊值
"""


class Ref[T]:
    """
    间接持有对象引用的容器

    .. versionchanged:: 0.3.0
       重命名 ``CellType`` 为 ``Ref``

       重命名字段 ``cell_contents`` 为 ``value``
    """

    __slots__ = ("value",)

    def __init__(self, value: T):
        """
        :param value: 引用对象
        :type value: T
        """  # noqa: D205
        self.value = value

    @override
    def __repr__(self) -> str:
        return f"<{type(self).__name__} ({self.value!r})>"


class FrozenArguments:
    """
    存储冻结的参数的容器

    .. versionadded:: 0.3.0
    """

    def __init__(self, args: Sequence[Any] | None = None, kwargs: Mapping[str, Any] | None = None):
        """
        :param args: 位置参数
        :type args: Sequence[Any]
        :param kwargs: 关键字参数
        :type kwargs: Mapping[str, Any]
        """  # noqa: D205
        self._args = () if args is None else tuple(args)
        self._kwargs: tuple[tuple[str, Any], ...] = () if kwargs is None else tuple((k, v) for k, v in kwargs.items())

    @property
    def args(self) -> tuple[Any, ...]:
        """
        位置参数

        :return: 位置参数
        :rtype: tuple[Any]
        """
        return deepcopy(self._args)

    @property
    def kwargs(self) -> OrderedDict[str, Any]:
        """
        关键字参数

        :return: 关键字参数
        :rtype: OrderedDict[str, Any]
        """
        return OrderedDict(deepcopy(self._kwargs))

    # noinspection PyTypeHints
    def __or__(self, other: tuple[Sequence[Any], Mapping[str, Any]] | Self) -> Self | NotImplementedType:
        if isinstance(other, tuple):
            other = type(self)(*other)
        if not isinstance(other, FrozenArguments):
            return NotImplemented
        merged_args = list(self._args)
        merged_args[: len(other._args)] = other.args

        merged_kwargs = self.kwargs | other.kwargs
        return type(self)(merged_args, merged_kwargs)

    def __iter__(self) -> Iterator[tuple[Any, ...] | OrderedDict[str, Any]]:
        yield self.args
        yield self.kwargs

    @override
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FrozenArguments):
            return NotImplemented
        return self._args == other._args and self._kwargs == other._kwargs

    @override
    def __hash__(self) -> int:
        return hash(self._args) ^ hash(self._kwargs)


__all__ = (
    "FrozenArguments",
    "Ref",
    "Unset",
    "UnsetType",
    "singleton",
)
