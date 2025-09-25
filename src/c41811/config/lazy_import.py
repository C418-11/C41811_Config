# cython: language_level = 3  # noqa: ERA001


"""
懒加载处理

.. versionadded:: 0.3.0
"""

import inspect
from importlib import import_module
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Callable
else:
    from collections.abc import Callable


def lazy_import(properties: dict[str, str], /) -> tuple[list[str], Callable[[str], Any]]:
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
    property_list = list(properties.keys())

    def attr_getter(name: str) -> Any:
        from .errors import DependencyNotFoundError  # noqa: PLC0415
        from .errors import UnavailableAttribute  # noqa: PLC0415

        try:
            sub_pkg = properties[name]
        except KeyError:
            # noinspection PyShadowingNames
            msg = f"module '{caller_package}' has no attribute '{name}'"
            raise AttributeError(msg) from None
        try:
            module = import_module(sub_pkg, package=caller_package)
        except DependencyNotFoundError as err:
            property_list.remove(name)
            del properties[name]
            return UnavailableAttribute(name, err)
        attr = getattr(module, name)
        if isinstance(attr, UnavailableAttribute):
            property_list.remove(name)
            del properties[name]
        return attr

    attr_getter.__name__ = "__getattr__"
    attr_getter.__qualname__ = f"{caller_package}.__getattr__"
    attr_getter.__module__ = caller_package

    return property_list, attr_getter


__all__ = ("lazy_import",)
