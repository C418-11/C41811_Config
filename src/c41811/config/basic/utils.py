# cython: language_level = 3  # noqa: ERA001


"""
杂项实用程序

.. versionadded:: 0.2.0
"""

from collections.abc import Callable
from functools import update_wrapper
from typing import Any
from typing import cast
from typing import overload

import wrapt

from ..abc import ABCConfigData
from ..abc import ABCPath
from ..abc import PathLike
from ..errors import ConfigDataReadOnlyError
from ..path import Path


@overload
def fmt_path(path: str) -> Path: ...


@overload
def fmt_path[P: ABCPath[Any]](path: P) -> P: ...


def fmt_path(path: PathLike) -> ABCPath[Any] | Path:
    """
    格式化配置数据路径

    :param path: 任意可转换为配置数据路径的对象
    :type path: PathLike

    :return: 配置数据
    :rtype: ABCPath | Path
    """
    if isinstance(path, ABCPath):
        return path
    return Path.from_str(path)


# noinspection PyNewStyleGenericSyntax
def check_read_only[F: Callable[..., Any]](func: F) -> F:
    """
    装饰 :py:class:`ABCConfigData` 的方法提供 :py:attr:`ABCConfigData.read_only` 的便捷检查，当其不为 :py:const:`True`
    时抛出 :py:exc:`TypeError`

    :param func: 目标方法
    :type func: F

    :return: 装饰后方法
    :rtype: F
    """  # noqa: RUF002, D205

    @wrapt.decorator  # type: ignore[arg-type]
    def wrapper(wrapped: F, instance: ABCConfigData | None, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        if instance is None:  # pragma: no cover
            msg = "must be called from an instance"
            raise TypeError(msg)
        if instance.read_only:
            raise ConfigDataReadOnlyError
        return wrapped(*args, **kwargs)

    return cast(F, update_wrapper(wrapper(func), func))


__all__ = (
    "check_read_only",
    "fmt_path",
)
