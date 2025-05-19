# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

from collections.abc import Callable
from typing import Any
from typing import cast

import wrapt  # type: ignore[import-untyped]

from ..abc import ABCConfigData
from ..abc import ABCPath
from ..abc import PathLike
from ..errors import ConfigDataReadOnlyError
from ..path import Path


def fmt_path(path: PathLike) -> ABCPath[Any]:
    if isinstance(path, ABCPath):
        return path
    return Path.from_str(path)


def check_read_only[F: Callable[..., Any]](func: F) -> F:
    @wrapt.decorator  # type: ignore[misc]
    def wrapper(wrapped: F, instance: ABCConfigData[Any] | None, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        if instance is None:
            raise TypeError("must be called from an instance")  # pragma: no cover
        elif instance.read_only:
            raise ConfigDataReadOnlyError
        return wrapped(*args, **kwargs)

    return cast(F, wrapper(func))


__all__ = (
    "fmt_path",
    "check_read_only",
)
