# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

from collections.abc import Callable
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import MutableMapping
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from types import NotImplementedType
from typing import Any
from typing import Optional
from typing import Self
from typing import cast
from typing import override

from .core import BasicConfigData
from .core import ConfigData
from .utils import check_read_only
from .utils import fmt_path
from ..abc import ABCConfigData
from ..abc import ABCIndexedConfigData
from ..abc import ABCMetaParser
from ..abc import ABCPath
from ..abc import PathLike
from ..errors import ConfigDataTypeError
from ..errors import ConfigOperate
from ..errors import KeyInfo
from ..errors import RequiredPathNotFoundError


@dataclass
class ComponentOrders:
    """
    组件顺序

    .. versionadded:: 0.2.0
    """

    create: list[str] = field(default_factory=list)
    read: list[str] = field(default_factory=list)
    update: list[str] = field(default_factory=list)
    delete: list[str] = field(default_factory=list)


@dataclass
class ComponentMember:
    """
    组件成员

    .. versionadded:: 0.2.0
    """

    filename: str
    alias: str | None = field(default=None)
    config_format: str | None = field(default=None)


@dataclass
class ComponentMeta[D: ABCConfigData[Any]]:
    """
    组件元数据

    .. versionadded:: 0.2.0
    """

    config: D = cast(D, field(default_factory=ConfigData))
    orders: ComponentOrders = field(default_factory=ComponentOrders)
    members: list[ComponentMember] = field(default_factory=list)
    parser: Optional[ABCMetaParser[Any, Any]] = field(default=None)


class ComponentConfigData[D: ABCIndexedConfigData[Any], M: ComponentMeta[Any]](BasicConfigData[D],
                                                                               ABCIndexedConfigData[D]):
    """
    组件配置数据

    .. versionadded:: 0.2.0
    """

    def __init__(self, meta: Optional[M] = None, members: Optional[MutableMapping[str, D]] = None):
        """
        :param meta: 组件元数据
        :type meta: Optional[ComponentMeta]
        :param members: 组件成员
        :type members: Optional[MutableMapping[str, ABCIndexedConfigData]]
        """
        if meta is None:
            meta = ComponentMeta()  # type: ignore[assignment]
        if members is None:
            members = {}

        self._meta: M = cast(M, deepcopy(meta))

        self._filename2meta: dict[str, ComponentMember] = {
            member_meta.filename: member_meta for member_meta in self._meta.members
        }
        self._alias2filename = {
            member_meta.alias: member_meta.filename
            for member_meta in self._meta.members
            if member_meta.alias is not None
        }
        self._members: MutableMapping[str, D] = deepcopy(members)

        if len(self._filename2meta) != len(self._meta.members):
            raise ValueError("repeated filename in meta")

        same_names = self._alias2filename.keys() & self._alias2filename.values()
        if same_names:
            raise ValueError(f"alias and filename cannot be the same {tuple(same_names)}")

        unexpected_names = self._members.keys() ^ self._filename2meta.keys()
        if unexpected_names:
            raise ValueError(f"cannot match members from meta {tuple(unexpected_names)}")

    @property
    def meta(self) -> M:
        """
        .. caution::
            未默认做深拷贝，可能导致非预期行为

            除非你知道你在做什么，不要轻易修改！

                由于 :py:class:`ComponentMeta` 仅提供一个通用的接口，
                直接修改其中元数据而不修改 ``config`` 字段 `*可能*` 会导致SL与元数据的不同步，
                这取决于 :py:class:`ComponentSL` 所取用的元数据解析器的行为
        """
        return self._meta

    @property
    def members(self) -> Mapping[str, D]:
        """
        .. caution::
            未默认做深拷贝，可能导致非预期行为
        """
        return self._members

    @property
    def data_read_only(self) -> bool | None:
        return not isinstance(self._members, MutableMapping)

    @property
    def filename2meta(self) -> Mapping[str, ComponentMember]:
        return deepcopy(self._filename2meta)

    @property
    def alias2filename(self) -> Mapping[str, str]:
        return deepcopy(self._alias2filename)

    def _member(self, member: str) -> D:
        """
        通过成员文件名以及其别名获取成员配置数据

        :param member: 成员名
        :type member: str

        :return: 成员数据
        :rtype: base.mapping.MappingConfigData
        """
        try:
            return self._members[member]
        except KeyError:
            with suppress(KeyError):
                return self._members[self._alias2filename[member]]
            raise

    def _resolve_members[P: ABCPath[Any], R](
            self, path: P, order: list[str], processor: Callable[[P, D], R], exception: Exception
    ) -> R:
        """
        逐个尝试解析成员配置数据

        :param path: 路径
        :type path: ABCPath
        :param order: 成员处理顺序
        :type order: list[str]
        :param processor: 成员处理函数
        :type processor: Callable[[ABCPath, base.mapping.MappingConfigData], Any]
        :param exception: 顺序为空抛出的错误
        :type exception: Exception

        :return: 处理结果
        :rtype: Any

        .. important::
           针对 :py:exc:`RequiredPathNotFoundError` ， :py:exc:`ConfigDataTypeError` 做了特殊处理，
           多个成员都抛出其一时最终仅抛出其中 :py:attr:`KeyInfo.index` 最大的
        """
        if path and (path[0].meta is not None):
            try:
                selected_member = self._member(path[0].meta)
            except KeyError:
                raise exception from None
            return processor(path, selected_member)

        if not order:
            raise exception

        error: None | RequiredPathNotFoundError | ConfigDataTypeError = None
        for member in order:
            try:
                return processor(path, self._member(member))
            except (RequiredPathNotFoundError, ConfigDataTypeError) as err:
                if error is None:
                    error = err
                if err.key_info.index > error.key_info.index:
                    error = err
        raise cast(RequiredPathNotFoundError | ConfigDataTypeError, error) from None

    def retrieve(self, path: PathLike, *args: Any, **kwargs: Any) -> Any:
        path = fmt_path(path)

        def processor(pth: ABCPath[Any], member: D) -> Any:
            return member.retrieve(pth, *args, **kwargs)

        return cast(
            Self,
            self._resolve_members(
                path,
                order=self._meta.orders.read,
                processor=processor,
                exception=RequiredPathNotFoundError(
                    key_info=KeyInfo(path, path[0], 0),
                    operate=ConfigOperate.Read,
                ),
            )
        )

    @check_read_only
    def modify(self, path: PathLike, *args: Any, **kwargs: Any) -> Self:
        path = fmt_path(path)

        def processor(pth: ABCPath[Any], member: D) -> ComponentConfigData[D, M]:
            member.modify(pth, *args, **kwargs)
            return self

        return cast(
            Self,
            self._resolve_members(
                path,
                order=self._meta.orders.update,
                processor=processor,
                exception=RequiredPathNotFoundError(
                    key_info=KeyInfo(path, path[0], 0),
                    operate=ConfigOperate.Write,
                ),
            )
        )

    @check_read_only
    def delete(self, path: PathLike, *args: Any, **kwargs: Any) -> Self:
        path = fmt_path(path)

        def processor(pth: ABCPath[Any], member: D) -> ComponentConfigData[D, M]:
            # noinspection PyArgumentList
            member.delete(pth, *args, **kwargs)
            return self

        return cast(
            Self,
            self._resolve_members(
                path,
                order=self._meta.orders.delete,
                processor=processor,
                exception=RequiredPathNotFoundError(
                    key_info=KeyInfo(path, path[0], 0),
                    operate=ConfigOperate.Delete,
                ),
            )
        )

    @check_read_only
    def unset(self, path: PathLike, *args: Any, **kwargs: Any) -> Self:
        path = fmt_path(path)

        def processor(pth: ABCPath[Any], member: D) -> ComponentConfigData[D, M]:
            # noinspection PyArgumentList
            member.delete(pth, *args, **kwargs)
            return self

        with suppress(RequiredPathNotFoundError):
            self._resolve_members(
                path,
                order=self._meta.orders.delete,
                processor=processor,
                exception=RequiredPathNotFoundError(
                    key_info=KeyInfo(path, path[0], 0),
                    operate=ConfigOperate.Delete,
                ),
            )
        return self

    def exists(self, path: PathLike, *args: Any, **kwargs: Any) -> bool:
        if not self._meta.orders.read:
            return False
        path = fmt_path(path)

        def processor(pth: ABCPath[Any], member: D) -> bool:
            return member.exists(pth, *args, **kwargs)

        with suppress(RequiredPathNotFoundError):  # 个别极端条件触发，例如\{不存在的成员\}\.key
            return self._resolve_members(
                path,
                order=self._meta.orders.read,
                processor=processor,
                exception=RequiredPathNotFoundError(
                    key_info=KeyInfo(path, path[0], 0),
                    operate=ConfigOperate.Delete,
                ),
            )
        return False

    def get(self, path: PathLike, default: Any = None, *args: Any, **kwargs: Any) -> Any:
        path = fmt_path(path)

        def processor(pth: ABCPath[Any], member: D) -> Any:
            return member.retrieve(pth, *args, **kwargs)

        with suppress(RequiredPathNotFoundError):
            return self._resolve_members(
                path,
                order=self._meta.orders.read,
                processor=processor,
                exception=RequiredPathNotFoundError(
                    key_info=KeyInfo(path, path[0], 0),
                    operate=ConfigOperate.Read,
                ),
            )
        return default

    @check_read_only
    def setdefault(self, path: PathLike, default: Any = None, *args: Any, **kwargs: Any) -> Any:
        path = fmt_path(path)

        def _retrieve_processor(pth: ABCPath[Any], member: D) -> Any:
            return member.retrieve(pth, *args, **kwargs)

        with suppress(RequiredPathNotFoundError):
            return self._resolve_members(
                path,
                order=self._meta.orders.read,
                processor=_retrieve_processor,
                exception=RequiredPathNotFoundError(
                    key_info=KeyInfo(path, path[0], 0),
                    operate=ConfigOperate.Read,
                ),
            )

        def _modify_processor(pth: ABCPath[Any], member: D) -> Any:
            member.modify(pth, default)
            return default

        return self._resolve_members(
            path,
            order=self._meta.orders.create,
            processor=_modify_processor,
            exception=RequiredPathNotFoundError(
                key_info=KeyInfo(path, path[0], 0),
                operate=ConfigOperate.Write,
            ),
        )

    def __eq__(self, other: Any) -> bool | NotImplementedType:
        if not isinstance(other, type(self)):
            return NotImplemented
        return all((
            self._meta == other._meta,
            self._members == other._members
        ))

    def __str__(self) -> str:
        return str(self._members)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(meta={self._meta!r}, members={self._members!r})"

    def __deepcopy__(self, memo: dict[str, Any]) -> Self:
        return self.from_data(self._meta, self._members)

    @override
    def __contains__(self, key: Any) -> bool:
        return key in self._members

    @override
    def __iter__(self) -> Iterator[str]:
        return iter(self._members)

    @override
    def __len__(self) -> int:
        return len(self._members)

    @override
    def __getitem__(self, index: Any) -> D:
        return self._members[index]

    @override
    @check_read_only
    def __setitem__(self, index: Any, value: D) -> None:
        self._members[index] = value

    @override
    @check_read_only
    def __delitem__(self, index: Any) -> None:
        del self._members[index]


__all__ = (
    "ComponentOrders",
    "ComponentMember",
    "ComponentMeta",
    "ComponentConfigData",
)
