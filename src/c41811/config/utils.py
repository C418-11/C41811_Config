# cython: language_level = 3  # noqa: ERA001

"""
杂项实用程序

.. versionadded:: 0.2.0
"""

from functools import wraps
from typing import Any
from typing import cast
from typing import override


def singleton[C: Any](target_cls: type[C], /) -> type[C]:
    """
    单例模式类装饰器

    :param target_cls: 目标类
    :type target_cls: type[C]

    :return: 装饰后的类
    :rtype: type[C]
    """

    @wraps(target_cls.__new__)
    def new_singleton(cls: type[C], /, *args: Any, **kwargs: Any) -> C:
        if not hasattr(cls, "__singleton_instance__"):
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


__all__ = (
    "Ref",
    "Unset",
    "UnsetType",
    "singleton",
)
