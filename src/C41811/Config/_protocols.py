# -*- coding: utf-8 -*-
# cython: language_level = 3


from typing import Protocol
from typing import TypeVar
from typing import overload

_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)


class SupportsWrite(Protocol[_T_contra]):
    def write(self, __s: _T_contra) -> object: ...


class SupportsReadAndReadline(Protocol[_T_co]):
    def read(self, __length: int = ...) -> _T_co: ...

    @overload
    def readline(self) -> _T_co: ...

    def readline(self, __length: int = ...) -> _T_co: ...


class SupportsIndex(Protocol[_T_co]):
    def __getitem__(self, __key: _T_contra) -> _T_co: ...


class SupportsWriteIndex(Protocol[_T_contra]):
    def __getitem__(self, __key: _T_contra) -> _T_contra: ...

    def __setitem__(self, __key: _T_contra, __value: _T_contra) -> None: ...

    def __delitem__(self, __key: _T_contra) -> None: ...


__all__ = (
    "SupportsWrite",
    "SupportsReadAndReadline",
    "SupportsIndex",
    "SupportsWriteIndex",
)
