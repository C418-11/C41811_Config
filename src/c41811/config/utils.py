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

    def new_singleton(cls: type[C], /, *args: Any, **kwargs: Any) -> C:
        if not hasattr(cls, "__singleton_instance__"):
            cls.__singleton_instance__ = cls.__singleton_new__(cls, *args, **kwargs)

        # noinspection PyProtectedMember
        return cast(C, cls.__singleton_instance__)

    new_singleton.__name__ = target_cls.__new__.__name__
    new_singleton.__qualname__ = target_cls.__new__.__qualname__
    new_singleton.__doc__ = target_cls.__new__.__doc__
    new_singleton.__module__ = target_cls.__new__.__module__
    with suppress(AttributeError):
        new_singleton.__annotations__ = target_cls.__new__.__annotations__

    target_cls.__singleton_new__ = target_cls.__new__
    target_cls.__new__ = staticmethod(new_singleton)  # type: ignore[assignment]

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
    if (caller_module := inspect.getmodule(inspect.stack()[1][0])) is None:  # pragma: no cover
        msg = "Cannot find caller module"
        raise RuntimeError(msg)
    caller_package = caller_module.__name__

    def attr_getter(name: str) -> Any:
        try:
            sub_pkg = properties[name]
        except KeyError:
            msg = f"module '{__name__}' has no attribute '{name}'"
            raise AttributeError(msg) from None
        return getattr(import_module(sub_pkg, package=caller_package), name)

    attr_getter.__name__ = "__getattr__"
    attr_getter.__qualname__ = "__getattr__"
    attr_getter.__module__ = caller_package

    return tuple(properties.keys()), attr_getter


__all__ = (
    "Ref",
    "Unset",
    "UnsetType",
    "lazy_import",
    "singleton",
)
