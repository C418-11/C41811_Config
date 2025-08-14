# cython: language_level = 3  # noqa: ERA001


"""
映射类型配置数据实现

.. versionadded:: 0.2.0
"""

import operator
from collections import OrderedDict
from collections.abc import Generator
from collections.abc import ItemsView
from collections.abc import KeysView
from collections.abc import Mapping
from collections.abc import MutableMapping
from collections.abc import ValuesView
from copy import deepcopy
from typing import Any
from typing import Self
from typing import cast
from typing import override

from ._generate_operators import generate
from ._generate_operators import operate
from .core import BasicIndexedConfigData
from .utils import check_read_only
from .utils import fmt_path
from ..abc import PathLike
from ..errors import CyclicReferenceError
from ..errors import KeyInfo
from ..errors import RequiredPathNotFoundError
from ..path import AttrKey
from ..path import Path
from ..utils import Unset


def _keys_recursive(
    data: Mapping[Any, Any],
    seen: set[int] | None = None,
    *,
    strict: bool,
    end_point_only: bool,
) -> Generator[str, None, None]:
    """
    递归获取配置的键

    :param data: 配置数据
    :type data: Mapping
    :param seen: 已访问的配置数据的id
    :type seen: set[int] | None
    :param strict: 是否严格模式，如果为 True，则当遇到循环引用时，会抛出异常
    :type strict: bool
    :param end_point_only: 是否只返回叶子节点的键
    :type end_point_only: bool

    :return: 获取的生成器
    :rtype: Generator[str, None, None]

    :raises CyclicReferenceError: 当遇到循环引用时，如果 strict 为 True，则抛出此异常
    :raises TypeError: 递归获取时键不为str时抛出

    .. versionadded:: 0.2.0
    """  # noqa: RUF002
    if seen is None:
        seen = set()

    if id(data) in seen:
        if strict:
            # noinspection PyTypeChecker
            raise CyclicReferenceError(key_info=KeyInfo(Path([]), None, -1))
        return
    seen.add(id(data))

    for k, v in data.items():
        if not isinstance(k, str):
            msg = f"key must be str, not {type(k).__name__}"
            raise TypeError(msg)
        k = k.replace("\\", "\\\\")  # noqa: PLW2901
        if isinstance(v, Mapping):
            try:
                yield from (
                    f"{k}\\.{x}" for x in _keys_recursive(v, seen, strict=strict, end_point_only=end_point_only)
                )
            except CyclicReferenceError as err:
                key_info = err.key_info
                key = AttrKey(k)

                key_info.path = Path((key, *key_info.path))
                key_info.current_key = key if key_info.current_key is None else key_info.current_key
                key_info.index += 1
                raise
            if end_point_only:
                continue
        yield k
    seen.remove(id(data))


@generate
class MappingConfigData[D: Mapping[Any, Any]](BasicIndexedConfigData[D], MutableMapping[Any, Any]):
    """
    映射配置数据

    .. versionadded:: 0.1.5
    """

    _data: D
    data: D

    def __init__(self, data: D | None = None):
        """
        :param data: 映射数据
        :type data: D | None
        """  # noqa: D205
        if data is None:
            data = {}  # type: ignore[assignment]
        super().__init__(cast(D, data))

    @property
    @override
    def data_read_only(self) -> bool:
        return not isinstance(self._data, MutableMapping)

    @override
    def keys(self, *, recursive: bool = False, strict: bool = True, end_point_only: bool = False) -> KeysView[Any]:
        # noinspection GrazieInspection
        r"""
        获取所有键

        不为 :py:class:`~collections.abc.Mapping` 默认行为时键必须为 :py:class:`str` 且返回值会被转换为
        :ref:`配置数据路径字符串 <term-config-data-path-syntax>`

        :param recursive: 是否递归获取
        :type recursive: bool
        :param strict: 是否严格检查循环引用数据，为真时提前抛出错误，否则静默忽略
        :type strict: bool
        :param end_point_only: 是否只获取叶子节点
        :type end_point_only: bool

        :return: 所有键
        :rtype: KeysView[str]

        :raise TypeError: 递归获取时键不为str时抛出
        :raise CyclicReferenceError: 严格检查循环引用数据时发现循环引用抛出

        例子
        ----

           >>> from c41811.config import MappingConfigData
           >>> data = MappingConfigData({"foo": {"bar": {"baz": "value"}, "bar1": "value1"}, "foo1": "value2"})

           不带参数行为与普通字典一样

           >>> data.keys()
           dict_keys(['foo', 'foo1'])

           参数 ``end_point_only`` 会滤掉非 ``叶子节点`` 的键

           >>> data.keys(end_point_only=True)  # 内部计算为保留顺序采用了OrderedDict所以返回值是odict_keys
           odict_keys(['foo1'])

           参数 ``recursive`` 用于获取所有的 ``路径``

           >>> data.keys(recursive=True)
           odict_keys(['foo\\.bar\\.baz', 'foo\\.bar', 'foo\\.bar1', 'foo', 'foo1'])

           同时提供 ``recursive`` 和 ``end_point_only`` 会产出所有 ``叶子节点`` 的路径

           >>> data.keys(recursive=True, end_point_only=True)
           odict_keys(['foo\\.bar\\.baz', 'foo\\.bar1', 'foo1'])

           为严格模式时会检查循环引用并提前引发错误

           >>> cyclic: dict[str, Any] = {"cyclic": None, "key": "value"}
           >>> cyclic["cyclic"] = cyclic
           >>> cyclic: MappingConfigData[dict[str, Any]] = MappingConfigData(cyclic)

           >>> cyclic.keys(recursive=True)  # 默认为严格模式
           Traceback (most recent call last):
               ...
           c41811.config.errors.CyclicReferenceError: Cyclic reference detected at \.cyclic -> \.cyclic (1/1)

           否则静默跳过循环引用

           >>> cyclic.keys(recursive=True, strict=False)
           odict_keys(['cyclic', 'key'])

           >>> cyclic.keys(recursive=True, strict=False, end_point_only=True)
           odict_keys(['key'])

        .. versionchanged:: 0.2.0
           添加参数 ``strict``
        """  # noqa: RUF002
        if recursive:
            return OrderedDict.fromkeys(
                x for x in _keys_recursive(self._data, strict=strict, end_point_only=end_point_only)
            ).keys()

        if end_point_only:
            return OrderedDict.fromkeys(
                k.replace("\\", "\\\\") for k, v in self._data.items() if not isinstance(v, Mapping)
            ).keys()

        return self._data.keys()

    @override
    def values(self, return_raw_value: bool = False) -> ValuesView[Any]:
        """
        获取所有值

        :param return_raw_value: 是否获取原始数据
        :type return_raw_value: bool

        :return: 所有键值对
        :rtype: ValuesView[Any]

        .. versionchanged:: 0.2.0
           重命名参数 ``get_raw`` 为 ``return_raw_value``
        """
        if return_raw_value:
            return self._data.values()

        return OrderedDict(
            (k, self.from_data(v) if isinstance(v, Mapping) else deepcopy(v)) for k, v in self._data.items()
        ).values()

    @override
    def items(self, *, return_raw_value: bool = False) -> ItemsView[str, Any]:
        """
        获取所有键值对

        :param return_raw_value: 是否获取原始数据
        :type return_raw_value: bool

        :return: 所有键值对
        :rtype: ItemsView[str, Any]

        .. versionchanged:: 0.2.0
           重命名参数 ``get_raw`` 为 ``return_raw_value``
        """
        if return_raw_value:
            return self._data.items()
        return OrderedDict(
            (deepcopy(k), self.from_data(v) if isinstance(v, Mapping) else deepcopy(v)) for k, v in self._data.items()
        ).items()

    @override
    @check_read_only
    def clear(self) -> None:
        self._data.clear()  # type: ignore[attr-defined]

    @override
    @check_read_only
    def pop(self, path: PathLike, /, default: Any = Unset) -> Any:
        path = fmt_path(path)
        try:
            result = self.retrieve(path)
            self.delete(path)
        except RequiredPathNotFoundError:
            if default is not Unset:
                return default
            raise
        return result

    @override
    @check_read_only
    def popitem(self) -> Any:
        return self._data.popitem()  # type: ignore[attr-defined]

    @override
    @check_read_only
    def update(self, m: Any = None, /, **kwargs: Any) -> None:
        if m is not None:
            self._data.update(m)  # type: ignore[attr-defined]
            return
        self._data.update(**kwargs)  # type: ignore[attr-defined]

    def __getattr__(self, item: Any) -> Self | Any:
        try:
            return self[item]
        except KeyError:
            msg = f"'{self.__class__.__name__}' object has no attribute '{item}'"
            raise AttributeError(msg) from None

    @operate(operator.or_, operator.ior)
    def __or__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...

    def __ror__(self, other: Any) -> Self:  # type: ignore[empty-body]
        ...


__all__ = ("MappingConfigData",)
