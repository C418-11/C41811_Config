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


__all__ = ("SupportsWrite", "SupportsReadAndReadline")
