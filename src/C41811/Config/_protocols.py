# cython: language_level = 3  # noqa: ERA001


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

    @overload
    def readline(self, __length: int) -> _T_co: ...

    def readline(self, __length: int = ...) -> _T_co: ...


class Indexed(Protocol[_T_contra, _T_co]):
    # noinspection GrazieInspection
    """
    可索引

    .. versionchanged:: 0.2.0
       重命名 ``SupportsIndex`` 为 ``Indexed``
    """

    def __getitem__(self, __index: _T_contra) -> _T_co: ...


class MutableIndexed(Indexed[_T_contra, _T_co]):
    # noinspection GrazieInspection
    """
    可变可索引

    .. versionchanged:: 0.2.0
       重命名 ``SupportsWriteIndex`` 为 ``MutableIndexed``
    """

    def __setitem__(self, __index: _T_contra, __value: _T_contra) -> None: ...

    def __delitem__(self, __index: _T_contra) -> None: ...


__all__ = (
    "Indexed",
    "MutableIndexed",
    "SupportsReadAndReadline",
    "SupportsWrite",
)
