# cython: language_level = 3

"""
杂项实用程序

.. versionadded:: 0.2.0
"""

from contextlib import suppress
from typing import Any
from typing import cast
from typing import override


def singleton[C: Any](target_cls: type[C], /) -> type[C]:
    """
    单例模式类装饰器
    """

    def __new__(cls: type[C], /, *args: Any, **kwargs: Any) -> C:  # noqa: N807
        if not hasattr(cls, "__singleton_instance__"):
            cls.__singleton_instance__ = cls.__singleton_new__(cls, *args, **kwargs)

        # noinspection PyProtectedMember
        return cast(C, cls.__singleton_instance__)

    __new__.__name__ = target_cls.__new__.__name__
    __new__.__qualname__ = target_cls.__new__.__qualname__
    __new__.__doc__ = target_cls.__new__.__doc__
    __new__.__module__ = target_cls.__new__.__module__
    with suppress(AttributeError):
        __new__.__annotations__ = target_cls.__new__.__annotations__

    target_cls.__singleton_new__ = target_cls.__new__
    target_cls.__new__ = staticmethod(__new__)  # type: ignore[assignment]

    return target_cls


@singleton
class UnsetType:
    """
    用于填充默认值的特殊值
    """

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

    def __init__(self, value: T):
        """
        :param value: 引用对象
        :type value: T
        """
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
