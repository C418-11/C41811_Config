# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

from collections.abc import Callable
from collections.abc import MutableMapping
from typing import Any
from typing import Optional
from typing import Self
from typing import cast
from typing import override

import wrapt  # type: ignore[import-untyped]

from .mapping import MappingConfigData
from ..abc import PathLike
from ..utils import Unset


def diff_keys[F: Callable[..., Any]](func: F) -> F:
    @wrapt.decorator  # type: ignore[misc]
    def wrapper(
            wrapped: F,
            instance: Any,
            args: tuple[Any, ...],
            kwargs: dict[str, Any]
    ) -> Any:
        if not isinstance(instance, EnvironmentConfigData):
            raise TypeError(  # pragma: no cover
                f"instance must be {EnvironmentConfigData.__name__} but got {type(instance).__name__}"
            )

        before = set(instance.keys())
        before_never_changed = before - instance.updated_keys - instance.removed_keys
        may_change = {k: instance[k] for k in before_never_changed}

        result = wrapped(*args, **kwargs)
        after = set(instance.keys())

        added = after - before
        deleted = before - after

        instance.updated_keys -= deleted
        instance.removed_keys -= added
        instance.updated_keys |= added
        instance.removed_keys |= deleted

        current_never_changed = before_never_changed - added - deleted
        for may_changed in current_never_changed:
            if may_change[may_changed] != instance[may_changed]:
                instance.updated_keys.add(may_changed)

        return result

    return cast(F, wrapper(func))


class EnvironmentConfigData(MappingConfigData[MutableMapping[str, str]]):
    def __init__(self, data: Optional[MutableMapping[str, str]] = None):
        super().__init__(data)
        self.updated_keys: set[str] = set()
        self.removed_keys: set[str] = set()

    @diff_keys
    @override
    def modify(self, path: PathLike, value: str, *, allow_create: bool = True) -> Self:
        return super().modify(path, value, allow_create=allow_create)

    @diff_keys
    @override
    def delete(self, path: PathLike) -> Self:
        return super().delete(path)

    @diff_keys
    @override
    def unset(self, path: PathLike) -> Self:
        return super().unset(path)

    @diff_keys
    @override
    def setdefault(self, path: PathLike, default: Optional[Any] = None, *, return_raw_value: bool = False) -> Any:
        return super().setdefault(path, default, return_raw_value=return_raw_value)

    @diff_keys
    @override
    def clear(self) -> None:
        super().clear()

    @diff_keys
    @override
    def pop(self, path: PathLike, /, default: Any = Unset) -> Any:
        return super().pop(path, default)

    @diff_keys
    @override
    def popitem(self) -> Any:
        return super().popitem()

    @diff_keys
    @override
    def update(self, m: Optional[Any] = None, /, **kwargs: str) -> None:
        super().update(m, **kwargs)

    @diff_keys
    @override
    def __setitem__(self, index: str, value: str) -> None:
        super().__setitem__(index, value)

    @diff_keys
    @override
    def __delitem__(self, index: str) -> None:
        super().__delitem__(index)

    @diff_keys
    def __ior__(self, other: MutableMapping[str, str]) -> Self:
        return super().__ior__(other)  # type: ignore[misc, no-any-return]


__all__ = (
    "EnvironmentConfigData",
)
