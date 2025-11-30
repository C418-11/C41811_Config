# cython: language_level = 3  # noqa: ERA001


"""
组件配置数据实现

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
from typing import Any
from typing import Self
from typing import cast
from typing import override

from .core import BasicConfigData
from .factory import ConfigDataFactory
from .utils import check_read_only
from .utils import fmt_path
from ..abc import ABCConfigData
from ..abc import ABCIndexedConfigData
from ..abc import ABCMetaParser
from ..abc import ABCPath
from ..abc import PathLike
from ..errors import ComponentMemberMismatchError
from ..errors import ComponentMetadataException
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
class ComponentMeta[D: ABCConfigData]:
    """
    组件元数据

    .. versionadded:: 0.2.0
    """

    config: D = field(default_factory=ConfigDataFactory)  # type: ignore[assignment]
    orders: ComponentOrders = field(default_factory=ComponentOrders)
    members: list[ComponentMember] = field(default_factory=list)
    parser: ABCMetaParser[Any, Any] | None = field(default=None)


class ComponentConfigData[D: ABCIndexedConfigData[Any], M: ComponentMeta[Any]](
    BasicConfigData[D], ABCIndexedConfigData[D]
):
    """
    组件配置数据

    .. versionadded:: 0.2.0
    """

    def __init__(self, meta: M | None = None, members: Mapping[str, D] | None = None):
        """
        :param meta: 组件元数据
        :type meta: M | None
        :param members: 组件成员
        :type members: Mapping[str, D] | None
        """  # noqa: D205
        if meta is None:
            meta = ComponentMeta()  # type: ignore[assignment]
        if members is None:
            members = {}

        # 准备元数据
        self._meta: M = cast(M, deepcopy(meta))
        self._filename2meta: dict[str, ComponentMember] = {}
        self._alias2filename: dict[str, str] = {}
        for member_meta in self._meta.members:
            if member_meta.filename in self._filename2meta:  # 文件名不能重复
                msg = f"filename {member_meta.filename} is repeated"
                raise ComponentMetadataException(msg)
            self._filename2meta[member_meta.filename] = member_meta
            if member_meta.filename in self._alias2filename:  # 别名不能和文件名重复
                msg = f"alias {member_meta.filename} is same as filename {member_meta.filename}"
                raise ComponentMetadataException(msg)
            if member_meta.alias is None:
                continue
            if member_meta.alias in self._alias2filename:  # 别名不能重复
                msg = f"alias {member_meta.alias} is repeated"
                raise ComponentMetadataException(msg)
            if member_meta.alias in self._filename2meta:  # 别名不能和文件名相同
                msg = f"alias {member_meta.alias} is same as filename {member_meta.filename}"
                raise ComponentMetadataException(msg)
            self._alias2filename[member_meta.alias] = member_meta.filename

        self._members: Mapping[str, D] = deepcopy(members)
        missing = self._filename2meta.keys() - self._members.keys()
        redundant = self._members.keys() - self._filename2meta.keys()
        if missing | redundant:
            raise ComponentMemberMismatchError(missing=missing, redundant=redundant)

    @property
    def meta(self) -> M:
        """
        组件元信息

        .. caution::
            未默认做深拷贝，可能导致非预期行为

            除非你知道你在做什么，不要轻易修改！

                由于 :py:class:`ComponentMeta` 仅提供一个通用的接口，
                直接修改其中元数据而不修改 ``config`` 字段 `*可能*` 会导致SL与元数据的不同步，
                这取决于 :py:class:`ComponentSL` 所取用的元数据解析器的行为
        """  # noqa: RUF002
        return self._meta

    @property
    def members(self) -> Mapping[str, D]:
        """
        组件成员

        .. caution::
            未默认做深拷贝，可能导致非预期行为
        """  # noqa: RUF002
        return self._members

    @property
    @override
    def data_read_only(self) -> bool | None:
        """组件数据是否为只读"""
        return not isinstance(self._members, MutableMapping)

    @property
    def filename2meta(self) -> Mapping[str, ComponentMember]:
        """文件名到成员元信息的映射"""
        return deepcopy(self._filename2meta)

    @property
    def alias2filename(self) -> Mapping[str, str]:
        """别名到文件名的映射"""
        return deepcopy(self._alias2filename)

    def _member(self, member: str) -> D:
        """
        通过成员文件名以及其别名获取成员配置数据

        :param member: 成员名
        :type member: str

        :return: 成员数据
        :rtype: D
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
        :type path: P
        :param order: 成员处理顺序
        :type order: list[str]
        :param processor: 成员处理函数
        :type processor: Callable[[P, D], R]
        :param exception: 顺序为空抛出的错误
        :type exception: Exception

        :return: 处理结果
        :rtype: R

        .. important::
           针对 :py:exc:`RequiredPathNotFoundError` ， :py:exc:`ConfigDataTypeError` 做了特殊处理，
           多个成员都抛出其一时最终仅抛出其中 :py:attr:`KeyInfo.index` 最大的
        """  # noqa: RUF002
        if path and (path[0].meta is not None):
            try:
                selected_member = self._member(path[0].meta)
            except KeyError:
                raise exception from None
            return processor(path, selected_member)

        if not order:
            raise exception

        error: RequiredPathNotFoundError | ConfigDataTypeError | None = None
        for member in order:
            try:
                return processor(path, self._member(member))
            except (RequiredPathNotFoundError, ConfigDataTypeError) as err:
                if error is None:
                    error = err
                if err.key_info.index > error.key_info.index:
                    error = err
        raise cast(RequiredPathNotFoundError | ConfigDataTypeError, error) from None

    @override
    def retrieve(self, path: PathLike, *args: Any, **kwargs: Any) -> Any:
        path = fmt_path(path)

        def processor(pth: ABCPath[Any], member: D) -> Any:
            return member.retrieve(pth, *args, **kwargs)

        return self._resolve_members(
            path,
            order=self._meta.orders.read,
            processor=processor,
            exception=RequiredPathNotFoundError(
                key_info=KeyInfo(path, path[0], 0),
                operate=ConfigOperate.Read,
            ),
        )

    @override
    @check_read_only
    def modify(self, path: PathLike, *args: Any, **kwargs: Any) -> Self:
        # noinspection PyIncorrectDocstring
        """
        修改路径的值

        :param path: 路径
        :type path: PathLike
        :param value: 值
        :type value: Any
        :param allow_create: 是否允许创建不存在的路径，默认为True
        :type allow_create: bool

        :return: 返回当前实例便于链式调用
        :rtype: Self

        :raise ConfigDataReadOnlyError: 配置数据为只读
        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredPathNotFoundError: 需求的键不存在

        .. caution::
           ``value`` 参数未默认做深拷贝，可能导致非预期行为

        .. attention::
           ``allow_create`` 时，使用与 `self.data` 一样的类型新建路径

        .. versionchanged:: 0.3.0
           现在正确的先尝试使用 :py:attr:`~ComponentOrders.update` 对现有数据进行更新再尝试通过
           :py:attr:`~ComponentOrders.create` 创建新数据
        """  # noqa: RUF002
        path = fmt_path(path)

        def _update_processor(pth: ABCPath[Any], member: D) -> None:
            try:
                member.retrieve(pth, return_raw_value=True)  # 避免转换返回值带来的额外开销
            except (RequiredPathNotFoundError, ConfigDataTypeError) as err:
                raise RequiredPathNotFoundError(
                    key_info=err.key_info,
                    operate=ConfigOperate.Write,  # 将操作从Read变为Write
                ) from None
            member.modify(pth, *args, **kwargs)

        with suppress(RequiredPathNotFoundError):
            self._resolve_members(
                path,
                order=self._meta.orders.update,
                processor=_update_processor,
                exception=RequiredPathNotFoundError(
                    key_info=KeyInfo(path, path[0], 0),
                    operate=ConfigOperate.Write,
                ),
            )
            return self

        def _create_processor(pth: ABCPath[Any], member: D) -> None:
            member.modify(pth, *args, **kwargs)

        self._resolve_members(
            path,
            order=self._meta.orders.create,
            processor=_create_processor,
            exception=RequiredPathNotFoundError(
                key_info=KeyInfo(path, path[0], 0),
                operate=ConfigOperate.Write,
            ),
        )
        return self

    @override
    @check_read_only
    def delete(self, path: PathLike, *args: Any, **kwargs: Any) -> Self:
        path = fmt_path(path)

        def processor(pth: ABCPath[Any], member: D) -> None:
            # noinspection PyArgumentList
            member.delete(pth, *args, **kwargs)

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

    @override
    @check_read_only
    def unset(self, path: PathLike, *args: Any, **kwargs: Any) -> Self:
        path = fmt_path(path)

        def processor(pth: ABCPath[Any], member: D) -> None:
            # noinspection PyArgumentList
            member.delete(pth, *args, **kwargs)

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

    @override
    def exists(self, path: PathLike, *args: Any, **kwargs: Any) -> bool:
        if not self._meta.orders.read:
            return False
        path = fmt_path(path)

        def processor(pth: ABCPath[Any], member: D) -> bool:
            return member.exists(pth, *args, **kwargs)

        with suppress(RequiredPathNotFoundError):  # 个别极端条件触发 例如\{不存在的成员\}\.key
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

    @override
    def get[V](
        self, path: PathLike, default: V | None = None, *args: Any, return_raw_value: bool = False, **kwargs: Any
    ) -> V | Any:
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

    @override
    @check_read_only
    def setdefault[V](
        self, path: PathLike, default: V | None = None, *args: Any, return_raw_value: bool = False, **kwargs: Any
    ) -> V | Any:
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

    @override
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return all((self._meta == other._meta, self._members == other._members))

    __hash__ = None  # type: ignore[assignment]

    @override
    def __str__(self) -> str:
        return str(self._members)

    @override
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
        """
        .. danger::
           使用此操作可能会导致与元数据不同步且不经过校验！
        """  # noqa: RUF002, D205
        self._members[index] = value  # type: ignore[index]

    @override
    @check_read_only
    def __delitem__(self, index: Any) -> None:
        """
        .. danger::
           使用此操作可能会导致与元数据不同步且不经过校验！
        """  # noqa: RUF002, D205
        del self._members[index]  # type: ignore[attr-defined]


__all__ = (
    "ComponentConfigData",
    "ComponentMember",
    "ComponentMeta",
    "ComponentOrders",
)
