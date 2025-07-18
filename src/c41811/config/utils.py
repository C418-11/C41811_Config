# cython: language_level = 3  # noqa: ERA001

"""
杂项实用程序

.. versionadded:: 0.2.0
"""

import inspect
from collections.abc import Callable
from contextlib import suppress
from importlib import import_module
from typing import Any
from typing import cast
from typing import override


def singleton[C: Any](target_cls: type[C], /) -> type[C]:
    """单例模式类装饰器"""

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
    """用于填充默认值的特殊值"""

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
        """  # noqa: D205
        self.value = value

    @override
    def __repr__(self) -> str:
        return f"<{type(self).__name__} ({self.value!r})>"


def lazy_import(properties: dict[str, str], /) -> tuple[tuple[str, ...], Callable[[str], Any]]:
    """
    为 `__init__` 文件生成 `__all__` 和 `__getattr__`

    :param properties: 属性字典 ``dict[属性, 模块]``
    :type properties: dict[str, str]

    :return: 返回 ``tuple[__all__, __getattr__]``
    :rtype: tuple[tuple[str, ...], Callable[[str], Any]]

    .. versionadded:: 0.3.0
    """
    caller_package = inspect.getmodule(inspect.stack()[1][0]).__name__  # type: ignore[union-attr]

    def __getattr__(name: str) -> Any:  # noqa: N807
        try:
            sub_pkg = properties[name]
        except KeyError:
            msg = f"module '{__name__}' has no attribute '{name}'"
            raise AttributeError(msg) from None
        return getattr(import_module(sub_pkg, package=caller_package), name)

    return tuple(properties.keys()), __getattr__


__all__ = (
    "Ref",
    "Unset",
    "UnsetType",
    "lazy_import",
    "singleton",
)
