# -*- coding: utf-8 -*-
# cython: language_level = 3


import math
import operator
from abc import ABC
from collections import OrderedDict
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import ItemsView
from collections.abc import Iterable
from collections.abc import KeysView
from collections.abc import Mapping
from collections.abc import MutableMapping
from collections.abc import MutableSequence
from collections.abc import Sequence
from collections.abc import ValuesView
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from numbers import Number
from re import Pattern
from textwrap import dedent
from typing import Any
from typing import ClassVar
from typing import Optional
from typing import Self
from typing import override

import wrapt

from ._protocols import Indexed
from ._protocols import MutableIndexed
from .abc import ABCConfigData
from .abc import ABCConfigFile
from .abc import ABCConfigPool
from .abc import ABCIndexedConfigData
from .abc import ABCKey
from .abc import ABCMetaParser
from .abc import ABCPath
from .abc import ABCProcessorHelper
from .abc import ABCSLProcessorPool
from .errors import ConfigDataReadOnlyError
from .errors import ConfigDataTypeError
from .errors import ConfigOperate
from .errors import FailedProcessConfigFileError
from .errors import KeyInfo
from .errors import RequiredPathNotFoundError
from .errors import UnsupportedConfigFormatError
from .path import Path
from .utils import Unset as _Unset


def _fmt_path(path: str | ABCPath) -> ABCPath:
    if isinstance(path, ABCPath):
        return path
    return Path.from_str(path)


class BasicConfigData(ABCConfigData, ABC):
    # noinspection GrazieInspection
    """
    配置数据基类

    .. versionadded:: 0.1.5

    .. versionchanged:: 0.2.0
       重命名 ``BaseConfigData`` 为 ``BasicConfigData``
    """

    _read_only: bool | None = False

    @override
    @property
    def data_read_only(self) -> bool | None:
        return True  # 全被子类复写了，测不到 # pragma: no cover

    @override
    @property
    def read_only(self) -> bool | None:
        return super().read_only or self._read_only

    @override
    @read_only.setter
    def read_only(self, value: Any):
        if self.data_read_only:
            raise ConfigDataReadOnlyError
        self._read_only = bool(value)


class BasicSingleConfigData[D: Any](BasicConfigData, ABC):
    """
    单文件配置数据基类

    .. versionadded:: 0.2.0
    """

    def __init__(self, data: D):
        """
        :param data: 配置的原始数据
        :type data: Any
        """

        self._data: D = deepcopy(data)

    @property
    def data(self) -> D:
        """
        配置的原始数据*快照*

        :return: 配置的原始数据*快照*
        :rtype: Any
        """
        return deepcopy(self._data)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._data == other._data

    def __str__(self) -> str:
        return str(self._data)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._data!r})"

    def __deepcopy__(self, memo) -> Self:
        return self.from_data(self._data)


def _check_read_only(func):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        if instance.read_only:
            raise ConfigDataReadOnlyError
        return wrapped(*args, **kwargs)

    return wrapper(func)


class BasicIndexedConfigData[D: Indexed | MutableIndexed](
    BasicSingleConfigData,
    ABCIndexedConfigData,
    ABC
):
    # noinspection GrazieInspection
    """
    支持 ``索引`` 操作的配置数据基类

    .. versionadded:: 0.1.5

    .. versionchanged:: 0.2.0
       重命名 ``BaseSupportsIndexConfigData`` 为 ``BasicIndexedConfigData``
    """

    def _process_path(
            self,
            path: ABCPath,
            path_checker: Callable[[Any, ABCKey, list[ABCKey], int], Any],
            process_return: Callable[[Any], Any]
    ) -> Any:
        # noinspection GrazieInspection
        """
        处理键路径的通用函数

        :param path: 键路径
        :type path: str
        :param path_checker: 检查并处理每个路径段，返回值非None时结束操作并返回值
        :type path_checker: Callable[(current_data: Any, current_key: str, last_path: str, path_index: int), Any]
        :param process_return: 处理最终结果，该函数返回值会被直接返回
        :type process_return: Callable[(current_data: Any), Any]

        :return: 处理结果
        :rtype: Any

        .. versionchanged:: 0.2.0
           重命名参数 ``process_check`` 为 ``path_checker``
        """
        current_data = self._data

        for key_index, current_key in enumerate(path):
            current_key: ABCKey
            last_key: list[ABCKey] = path[key_index + 1:]

            check_result = path_checker(current_data, current_key, last_key, key_index)
            if check_result is not None:
                return check_result

            current_data = current_key.__get_inner_element__(current_data)

        return process_return(current_data)

    @override
    def retrieve(self, path: str | ABCPath, *, return_raw_value: bool = False) -> Any:
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, _last_key: list[ABCKey], key_index: int):
            missing_protocol = now_key.__supports__(now_data)
            if missing_protocol:
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), missing_protocol, type(now_data))
            if not now_key.__contains_inner_element__(now_data):
                raise RequiredPathNotFoundError(KeyInfo(path, now_key, key_index), ConfigOperate.Read)

        def process_return(now_data):
            if return_raw_value:
                return deepcopy(now_data)

            is_sequence = isinstance(now_data, Sequence) and not isinstance(now_data, (str, bytes))
            if isinstance(now_data, Mapping) or is_sequence:
                return ConfigData(now_data)

            return deepcopy(now_data)

        return self._process_path(path, checker, process_return)

    @override
    @_check_read_only
    def modify(self, path: str | ABCPath, value: Any, *, allow_create: bool = True) -> Self:
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, last_key: list[ABCKey], key_index: int):
            missing_protocol = now_key.__supports_modify__(now_data)
            if missing_protocol:
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), missing_protocol, type(now_data))
            if not now_key.__contains_inner_element__(now_data):
                if not allow_create:
                    raise RequiredPathNotFoundError(KeyInfo(path, now_key, key_index), ConfigOperate.Write)
                now_key.__set_inner_element__(now_data, type(self._data)())

            if not last_key:
                now_key.__set_inner_element__(now_data, value)

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    @_check_read_only
    def delete(self, path: str | ABCPath) -> Self:
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, last_key: list[ABCKey], key_index: int):
            missing_protocol = now_key.__supports_modify__(now_data)
            if missing_protocol:
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), missing_protocol, type(now_data))
            if not now_key.__contains_inner_element__(now_data):
                raise RequiredPathNotFoundError(KeyInfo(path, now_key, key_index), ConfigOperate.Delete)

            if not last_key:
                now_key.__delete_inner_element__(now_data)
                return True

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    def unset(self, path: str | ABCPath) -> Self:
        with suppress(RequiredPathNotFoundError):
            self.delete(path)
        return self

    @override
    def exists(self, path: str | ABCPath, *, ignore_wrong_type: bool = False) -> bool:
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, _last_key: list[ABCKey], key_index: int):
            missing_protocol = now_key.__supports__(now_data)
            if missing_protocol:
                if ignore_wrong_type:
                    return False
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), missing_protocol, type(now_data))
            if not now_key.__contains_inner_element__(now_data):
                return False

        return self._process_path(path, checker, lambda *_: True)

    @override
    def get(self, path: str | ABCPath, default=None, *, return_raw_value: bool = False) -> Any:
        try:
            return self.retrieve(path, return_raw_value=return_raw_value)
        except RequiredPathNotFoundError:
            return default

    @override
    def setdefault(self, path: str | ABCPath, default=None, *, return_raw_value: bool = False) -> Any:
        try:
            return self.retrieve(path)
        except RequiredPathNotFoundError:
            self.modify(path, default)
            return default

    @override
    def __contains__(self, key) -> bool:
        return key in self._data

    @override
    def __iter__(self):
        return iter(self._data)

    @override
    def __len__(self):
        return len(self._data)

    @override
    def __getitem__(self, key):
        data = self._data[key]
        is_sequence = isinstance(data, Sequence) and not isinstance(data, (str, bytes))
        if isinstance(data, Mapping) or is_sequence:
            return ConfigData(data)
        return deepcopy(data)

    @override
    def __setitem__(self, key, value) -> None:
        self._data[key] = value

    @override
    def __delitem__(self, key) -> None:
        del self._data[key]


class ConfigData(ABC):
    """
    配置数据类

    .. versionchanged:: 0.1.5
       会自动根据传入的配置数据类型选择对应的子类
    """
    TYPES: ClassVar[OrderedDict[tuple[type, ...], type]]
    """
    存储配置数据类型对应的子类

    .. versionchanged:: 0.2.0
       现在使用 ``OrderedDict`` 来保证顺序
    """

    def __new__(cls, *args, **kwargs) -> Any:
        if not args:
            args = (None,)
        for types, config_data_cls in cls.TYPES.items():
            if not isinstance(args[0], types):
                continue
            return config_data_cls(*args, **kwargs)
        raise TypeError(f"Unsupported type: {args[0]}")


def _generate_operators[T: type](cls: T) -> T:
    for name, func in dict(vars(cls)).items():
        if not hasattr(func, "__generate_operators__"):
            continue
        operator_funcs = getattr(func, "__generate_operators__")
        delattr(func, "__generate_operators__")

        i_name = f"__i{name[2:-2]}__"
        r_name = f"__r{name[2:-2]}__"

        code = dedent(f"""
        def {name}(self, other):
            return ConfigData(operate_func(self._data, other))
        def {r_name}(self, other):
            return ConfigData(operate_func(other, self._data))
        def {i_name}(self, other):
            self._data = inplace_func(self._data, other)
            return self
        """)

        funcs = {}
        exec(code, {**operator_funcs, "ConfigData": ConfigData}, funcs)

        funcs[name].__qualname__ = func.__qualname__
        funcs[r_name].__qualname__ = f"{cls.__qualname__}.{r_name}"
        funcs[i_name].__qualname__ = f"{cls.__qualname__}.{i_name}"

        @wrapt.decorator
        def wrapper(wrapped, _instance, args, kwargs):
            if isinstance(args[0], ABCConfigData):
                args = args[0].data, *args[1:]
            return wrapped(*args, **kwargs)

        setattr(cls, name, wrapper(funcs[name]))
        setattr(cls, r_name, funcs[r_name])
        setattr(cls, i_name, wrapper(_check_read_only(funcs[i_name])))

    return cls


def _operate(operate_func, inplace_func):
    def decorator[F: Callable](func) -> F:
        func.__generate_operators__ = {"operate_func": operate_func, "inplace_func": inplace_func}
        return func

    return decorator


class NoneConfigData(BasicSingleConfigData):
    """
    空的配置数据

    .. versionadded:: 0.2.0
    """

    def __init__(self, data: Optional[None] = None):
        """
        :param data: 配置的原始数据
        :type data: None
        """

        if data is not None:
            raise ValueError(f"{type(self).__name__} can only accept None as data")

        super().__init__(data)

    def __bool__(self):
        return False


@_generate_operators
class MappingConfigData[D: Mapping | MutableMapping](BasicIndexedConfigData, MutableMapping):
    """
    映射配置数据

    .. versionadded:: 0.1.5
    """
    _data: D
    data: D

    def __init__(self, data: Optional[D] = None):
        if data is None:
            data = dict()
        super().__init__(data)

    @override
    @property
    def data_read_only(self) -> bool:
        return not isinstance(self._data, MutableMapping)

    def keys(self, *, recursive: bool = False, end_point_only: bool = False) -> KeysView[str]:
        r"""
        获取所有键

        :param recursive: 是否递归获取
        :type recursive: bool
        :param end_point_only: 是否只获取叶子节点
        :type end_point_only: bool

        :return: 所有键
        :rtype: KeysView[str]

        例子
        ----

           >>> from C41811.Config import ConfigData
           >>> data = ConfigData({
           ...     "foo": {
           ...         "bar": {
           ...             "baz": "value"
           ...         },
           ...         "bar1": "value1"
           ...     },
           ...     "foo1": "value2"
           ... })

           不带参数行为与普通字典一样

           >>> data.keys()
           dict_keys(['foo', 'foo1'])

           参数 ``end_point_only`` 会滤掉非 ``叶子节点`` 的键

           >>> data.keys(end_point_only=True)  # 内部计算为保留顺序采用了OrderedDict所以返回值是odict_keys
           odict_keys(['foo1'])

           参数 ``recursive`` 用于获取所有的 ``路径``

           >>> data.keys(recursive=True)
           odict_keys(['foo\\.bar\\.baz', 'foo\\.bar', 'foo\\.bar1', 'foo', 'foo1'])

           同时提供 ``recursice`` 和 ``end_point_only`` 会产出所有 ``叶子节点`` 的路径

           >>> data.keys(recursive=True, end_point_only=True)
           odict_keys(['foo\\.bar\\.baz', 'foo\\.bar1', 'foo1'])
        """

        def _recursive(data: Mapping) -> Generator[str, None, None]:
            for k, v in data.items():
                k: str = k.replace('\\', "\\\\")
                if isinstance(v, Mapping):
                    yield from (f"{k}\\.{x}" for x in _recursive(v))
                    if end_point_only:
                        continue
                yield k

        if recursive:
            return OrderedDict.fromkeys(x for x in _recursive(self._data)).keys()

        if end_point_only:
            return OrderedDict.fromkeys(
                k.replace('\\', "\\\\") for k, v in self._data.items() if not isinstance(v, Mapping)
            ).keys()

        return self._data.keys()

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
    @_check_read_only
    def clear(self):
        self._data.clear()

    @override
    @_check_read_only
    def pop(self, path: str | Path, /, default: Any = _Unset):
        path = _fmt_path(path)
        try:
            result = self.retrieve(path)
            self.delete(path)
            return result
        except RequiredPathNotFoundError:
            if default is not _Unset:
                return default
            raise

    @override
    @_check_read_only
    def popitem(self):
        return self._data.popitem()

    @override
    @_check_read_only
    def update(self, m, /, **kwargs):
        self._data.update(m, **kwargs)

    def __getattr__(self, item) -> Self | Any:
        try:
            return self[item]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    @_operate(operator.or_, operator.ior)  # @formatter:off
    def __or__(self, other) -> Any: ...

    def __ror__(self, other) -> Any: ...
    # @formatter:on


@_generate_operators
class SequenceConfigData[D: Sequence | MutableSequence](BasicIndexedConfigData, MutableSequence):
    """
    序列配置数据

    .. versionadded:: 0.1.5
    """
    _data: D
    data: D

    def __init__(self, data: Optional[D] = None):
        if data is None:
            data = list()
        super().__init__(data)

    @override
    @property
    def data_read_only(self) -> bool:
        return not isinstance(self._data, MutableSequence)

    @override
    @_check_read_only
    def append(self, value):
        return self._data.append(value)

    @override
    @_check_read_only
    def insert(self, index, value):
        return self._data.insert(index, value)

    @override
    @_check_read_only
    def extend(self, values):
        return self._data.extend(values)

    @override
    def index(self, *args):
        return self._data.index(*args)

    @override
    def count(self, value):
        return self._data.count(value)

    @override
    @_check_read_only
    def pop(self, index=-1):
        return self._data.pop(index)

    @override
    @_check_read_only
    def remove(self, value):
        return self._data.remove(value)

    @override
    @_check_read_only
    def clear(self):
        return self._data.clear()

    @override
    @_check_read_only
    def reverse(self):
        return self._data.reverse()

    def __reversed__(self):
        return reversed(self._data)

    @_operate(operator.mul, operator.imul)
    def __mul__(self, other) -> Any: ...

    @_operate(operator.add, operator.iadd)
    def __add__(self, other) -> Any: ...

    def __rmul__(self, other) -> Any: ...

    def __radd__(self, other) -> Any: ...


@_generate_operators
class NumberConfigData[D: Number](BasicSingleConfigData):
    """
    数值配置数据

    .. versionadded:: 0.1.5
    """
    _data: D
    data: D

    def __init__(self, data: Optional[D] = None):
        if data is None:
            data = int()
        super().__init__(data)

    @override
    @property
    def data_read_only(self) -> False:
        return False

    def __int__(self) -> int:
        return int(self._data)

    def __float__(self) -> float:
        return float(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)

    @_operate(operator.add, operator.iadd)
    def __add__(self, other) -> Any: ...

    @_operate(operator.sub, operator.isub)
    def __sub__(self, other) -> Any: ...

    @_operate(operator.mul, operator.imul)
    def __mul__(self, other) -> Any: ...

    @_operate(operator.truediv, operator.itruediv)
    def __truediv__(self, other) -> Any: ...

    @_operate(operator.floordiv, operator.ifloordiv)
    def __floordiv__(self, other) -> Any: ...

    @_operate(operator.mod, operator.imod)
    def __mod__(self, other) -> Any: ...

    @_operate(operator.pow, operator.ipow)
    def __pow__(self, other) -> Any: ...

    @_operate(operator.and_, operator.iand)
    def __and__(self, other) -> Any: ...

    @_operate(operator.or_, operator.ior)
    def __or__(self, other) -> Any: ...

    @_operate(operator.xor, operator.ixor)
    def __xor__(self, other) -> Any: ...

    @_operate(operator.matmul, operator.imatmul)
    def __matmul__(self, other) -> Any: ...

    @_operate(operator.lshift, operator.ilshift)
    def __lshift__(self, other) -> Any: ...

    @_operate(operator.rshift, operator.irshift)
    def __rshift__(self, other) -> Any: ...

    def __radd__(self, other) -> Any: ...

    def __rsub__(self, other) -> Any: ...

    def __rmul__(self, other) -> Any: ...

    def __rtruediv__(self, other) -> Any: ...

    def __rfloordiv__(self, other) -> Any: ...

    def __rmod__(self, other) -> Any: ...

    def __rpow__(self, other) -> Any: ...

    def __rand__(self, other) -> Any: ...

    def __ror__(self, other) -> Any: ...

    def __rxor__(self, other) -> Any: ...

    def __rmatmul__(self, other) -> Any: ...

    def __rlshift__(self, other) -> Any: ...

    def __rrshift__(self, other) -> Any: ...

    def __invert__(self):
        return ~self._data

    def __neg__(self):
        return -self._data

    def __pos__(self):
        return +self._data

    def __abs__(self):
        return abs(self._data)

    # noinspection SpellCheckingInspection
    def __round__(self, ndigits: int | None = None):
        return round(self._data, ndigits)

    def __trunc__(self):
        return math.trunc(self._data)

    def __floor__(self):
        return math.floor(self._data)

    def __ceil__(self):
        return math.ceil(self._data)

    def __index__(self) -> int:
        return int(self._data)


class BoolConfigData[D: bool](NumberConfigData):
    # noinspection GrazieInspection
    """
    布尔值配置数据

    .. versionadded:: 0.1.5
    """
    _data: D
    data: D

    def __init__(self, data: Optional[D] = None):
        if data is None:
            data = bool()
        super().__init__(data)


@_generate_operators
class StringConfigData[D: str | bytes](BasicSingleConfigData):
    """
    字符/字节串配置数据
    """
    _data: D
    data: D

    def __init__(self, data: Optional[D] = None):
        if data is None:
            data = str()
        super().__init__(data)

    @override
    @property
    def data_read_only(self) -> False:
        return False

    def __format__(self, format_spec: D) -> D:
        return self._data.__format__(format_spec)

    @_operate(operator.add, operator.iadd)
    def __add__(self, other) -> Any: ...

    @_operate(operator.mul, operator.imul)
    def __mul__(self, other) -> Any: ...

    def __contains__(self, key) -> bool:
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, item):
        return self._data[item]

    @_check_read_only
    def __setitem__(self, key, value):
        self._data[key] = value

    @_check_read_only
    def __delitem__(self, key):
        del self._data[key]

    def __reversed__(self):
        return reversed(self._data)


class ObjectConfigData[D: object](BasicSingleConfigData):
    """
    对象配置数据
    """
    _data: D
    data: D

    def __init__(self, data: D):
        """
        :param data: 配置的原始数据
        :type data: Any

        .. caution::
           未默认做深拷贝，可能导致非预期行为
        """
        super().__init__(None)

        self._data: D = data

    @override
    @property
    def data_read_only(self) -> False:
        return False

    @override
    @property
    def data(self) -> D:
        """
        配置的原始数据

        :return: 配置的原始数据
        :rtype: Any

        .. caution::
           直接返回了原始对象，未默认进行深拷贝
        """
        return self._data


type AnyConfigData = (
        ABCConfigData
        | ABCIndexedConfigData
        | NoneConfigData
        | MappingConfigData
        | StringConfigData
        | SequenceConfigData
        | BoolConfigData
        | NumberConfigData
        | ObjectConfigData
)

ConfigData.TYPES = OrderedDict((
    ((ABCConfigData,), lambda _: _),
    ((type(None),), NoneConfigData),
    ((Mapping,), MappingConfigData),
    ((str, bytes), StringConfigData),
    ((Sequence,), SequenceConfigData),
    ((bool,), BoolConfigData),
    ((Number,), NumberConfigData),
    ((object,), ObjectConfigData),
))

ConfigData.register(NoneConfigData)
ConfigData.register(MappingConfigData)
ConfigData.register(SequenceConfigData)
ConfigData.register(NumberConfigData)
ConfigData.register(BoolConfigData)
ConfigData.register(StringConfigData)
ConfigData.register(ObjectConfigData)


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
class ComponentMeta:
    """
    组件元数据

    .. versionadded:: 0.2.0
    """

    config: MappingConfigData = field(default_factory=MappingConfigData)
    orders: ComponentOrders = field(default_factory=ComponentOrders)
    members: list[ComponentMember] = field(default_factory=list)
    parser: Optional[ABCMetaParser] = field(default=None)


class ComponentConfigData[D: MappingConfigData](BasicConfigData, ABCIndexedConfigData):
    """
    组件配置数据

    .. versionadded:: 0.2.0
    """

    def __init__(self, meta: ComponentMeta = None, members: MutableMapping[str, D] = None):
        """
        :param meta: 组件元数据
        :type meta: ComponentMeta
        :param members: 组件成员
        :type members: MutableMapping[str, MappingConfigData]
        """
        if meta is None:
            meta = ComponentMeta()
        if members is None:
            members = {}

        self._meta = deepcopy(meta)

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
    def meta(self) -> ComponentMeta:
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
        :rtype: MappingConfigData
        """
        try:
            return self._members[member]
        except KeyError:
            with suppress(KeyError):
                return self._members[self._alias2filename[member]]
            raise

    def _resolve_members[P: ABCPath, R: Any](
            self, path: P, order: list[str], processor: Callable[[P, D], R], exception: Exception
    ) -> R:
        """
        逐个尝试解析成员配置数据

        :param path: 路径
        :type path: ABCPath
        :param order: 成员处理顺序
        :type order: list[str]
        :param processor: 成员处理函数
        :type processor: Callable[[ABCPath, MappingConfigData], Any]
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
                member = self._member(path[0].meta)
            except KeyError:
                raise exception from None
            return processor(path, member)

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
        raise error from None

    def retrieve(self, path: str | ABCPath, *args, **kwargs) -> Any:
        path = _fmt_path(path)

        def processor(pth: ABCPath, member: D) -> Any:
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

    @_check_read_only
    def modify(self, path: str | ABCPath, *args, **kwargs) -> Self:
        path = _fmt_path(path)

        def processor(pth: ABCPath, member: D) -> Self:
            member.modify(pth, *args, **kwargs)
            return self

        return self._resolve_members(
            path,
            order=self._meta.orders.update,
            processor=processor,
            exception=RequiredPathNotFoundError(
                key_info=KeyInfo(path, path[0], 0),
                operate=ConfigOperate.Write,
            ),
        )

    @_check_read_only
    def delete(self, path: str | ABCPath, *args, **kwargs) -> Self:
        path = _fmt_path(path)

        def processor(pth: ABCPath, member: D) -> Self:
            member.delete(pth, *args, **kwargs)
            return self

        return self._resolve_members(
            path,
            order=self._meta.orders.delete,
            processor=processor,
            exception=RequiredPathNotFoundError(
                key_info=KeyInfo(path, path[0], 0),
                operate=ConfigOperate.Delete,
            ),
        )

    @_check_read_only
    def unset(self, path: str | ABCPath, *args, **kwargs) -> Self:
        path = _fmt_path(path)

        def processor(pth: ABCPath, member: D) -> Self:
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

    def exists(self, path: str | ABCPath, *args, **kwargs) -> bool:
        if not self._meta.orders.read:
            return False
        path = _fmt_path(path)

        def processor(pth: ABCPath, member: D) -> bool:
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

    def get(self, path: str | ABCPath, default=None, *args, **kwargs) -> Any:
        path = _fmt_path(path)

        def processor(pth: ABCPath, member: D) -> Any:
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

    @_check_read_only
    def setdefault(self, path: str | ABCPath, default=None, *args, **kwargs) -> Any:
        path = _fmt_path(path)

        def _retrieve_processor(pth: ABCPath, member: D) -> Any:
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

        def _modify_processor(pth: ABCPath, member: D) -> Any:
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

    def __eq__(self, other):
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

    def __deepcopy__(self, memo) -> Self:
        return self.from_data(self._meta, self._members)

    @override
    def __contains__(self, key) -> bool:
        return key in self._members

    @override
    def __iter__(self):
        return iter(self._members)

    @override
    def __len__(self):
        return len(self._members)

    @override
    def __getitem__(self, key) -> D:
        return self._members[key]

    @override
    @_check_read_only
    def __setitem__(self, key, value: D) -> None:
        self._members[key] = value

    @override
    @_check_read_only
    def __delitem__(self, key) -> None:
        del self._members[key]


ConfigData.register(ComponentConfigData)


class ConfigFile[D: Any](ABCConfigFile):
    """
    配置文件类
    """

    def __init__(
            self,
            initial_config: D,
            *,
            config_format: Optional[str] = None
    ) -> None:
        """
        :param initial_config: 配置数据
        :type initial_config: Any
        :param config_format: 配置文件的格式
        :type config_format: Optional[str]

        .. caution::
           本身并未对 ``initial_config`` 参数进行深拷贝，但是 :py:class:`ConfigData` 可能会将其深拷贝

        .. versionchanged:: 0.2.0
           现在会自动尝试转换 ``initial_config`` 参数为 :py:class:`ConfigData`

           重命名参数 ``config_data`` 为 ``initial_config``
        """

        super().__init__(ConfigData(initial_config), config_format=config_format)

    @override
    def save(
            self,
            processor_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: str | None = None,
            *processor_args,
            **processor_kwargs
    ) -> None:

        if config_format is None:
            config_format = self._config_format

        if config_format is None:
            raise UnsupportedConfigFormatError("Unknown")
        if config_format not in processor_pool.SLProcessors:
            raise UnsupportedConfigFormatError(config_format)

        return processor_pool.SLProcessors[config_format].save(processor_pool, self, processor_pool.root_path,
                                                               namespace, file_name, *processor_args,
                                                               **processor_kwargs)

    @classmethod
    @override
    def load(
            cls,
            processor_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: str,
            *processor_args,
            **processor_kwargs
    ) -> Self:

        if config_format not in processor_pool.SLProcessors:
            raise UnsupportedConfigFormatError(config_format)

        return processor_pool.SLProcessors[config_format].load(processor_pool, processor_pool.root_path, namespace,
                                                               file_name, *processor_args, **processor_kwargs)

    @classmethod
    @override
    def initialize(
            cls,
            processor_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: str,
            *processor_args,
            **processor_kwargs
    ) -> Self:

        if config_format not in processor_pool.SLProcessors:
            raise UnsupportedConfigFormatError(config_format)

        return processor_pool.SLProcessors[config_format].initialize(processor_pool, processor_pool.root_path,
                                                                     namespace, file_name, *processor_args,
                                                                     **processor_kwargs)


class PHelper(ABCProcessorHelper): ...  # noqa: E701


class BasicConfigPool(ABCConfigPool, ABC):
    """
    基础配置池类

    实现了一些通用方法

    .. versionchanged:: 0.2.0
       重命名 ``BaseConfigPool`` 为 ``BasicConfigPool``
    """

    def __init__(self, root_path="./.config"):
        super().__init__(root_path)
        self._configs: dict[str, dict[str, ABCConfigFile]] = {}
        self._helper = PHelper()

    @property
    def helper(self) -> ABCProcessorHelper:
        return self._helper

    @override
    def get(self, namespace: str, file_name: Optional[str] = None) -> dict[str, ABCConfigFile] | ABCConfigFile | None:
        if namespace not in self._configs:
            return None
        result = self._configs[namespace]

        if file_name is None:
            return result

        if file_name in result:
            return result[file_name]

        return None

    @override
    def set(self, namespace: str, file_name: str, config: ABCConfigFile) -> Self:
        if namespace not in self._configs:
            self._configs[namespace] = {}

        self._configs[namespace][file_name] = config
        return self

    def _calc_formats(
            self,
            file_name: str,
            config_formats: Optional[str | Iterable[str]],
            configfile_format: Optional[str] = None,
    ) -> Iterable[str]:
        """
        从给定参数计算所有可能的配置格式

        :param file_name: 文件名
        :type file_name: str
        :param config_formats: 配置格式
        :type config_formats: Optional[str | Iterable[str]]
        :param configfile_format:
           该配置文件对象本身配置格式属性的值
           可选项，一般在保存时填入
           用于在没手动指定配置格式且没文件后缀时使用该值进行尝试

           .. seealso::
              :py:attr:`ABCConfigFile.config_format`

        :return: 配置格式
        :rtype: set[str]

        :raise UnsupportedConfigFormatError: 不支持的配置格式
        :raise FailedProcessConfigFileError: 处理配置文件失败

        格式计算优先级
        --------------

        1.config_formats的bool求值为真

        2.文件名注册了对应的SL处理器

        3.file_config_format非None

        .. versionadded:: 0.2.0
        """
        result_formats = []
        # 先尝试从传入的参数中获取配置文件格式
        if config_formats is None:
            config_formats = []
        elif isinstance(config_formats, str):
            config_formats = [config_formats]
        else:
            config_formats = list(config_formats)

        if config_formats:
            result_formats.extend(config_formats)

        def _check_file_name(match: str | Pattern) -> bool:
            if isinstance(match, str):
                return file_name.endswith(match)
            return bool(match.fullmatch(file_name))  # 目前没SL处理器用得上 # pragma: no cover

        # 再尝试从文件名匹配配置文件格式
        for m in self.FileNameProcessors:
            if _check_file_name(m):
                result_formats.extend(self.FileNameProcessors[m])

        # 最后尝试从配置文件对象本身获取配置文件格式
        if configfile_format is not None:
            result_formats.append(configfile_format)

        if not result_formats:
            raise UnsupportedConfigFormatError("Unknown")

        return OrderedDict.fromkeys(result_formats)

    def _test_all_sl[R: Any](
            self,
            namespace: str,
            file_name: str,
            config_formats: Optional[str | Iterable[str]],
            processor: Callable[[Self, str, str, str], R],
            file_config_format: Optional[str] = None,
    ) -> R:
        """
        自动尝试推断ABCConfigFile所支持的config_format

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config_formats: 配置格式
        :type config_formats: Optional[str | Iterable[str]]
        :param processor:
           处理器，参数为[配置池对象, 命名空间, 文件名, 配置格式]返回值会被直接返回，
           出现意料内的SL处理器无法处理需抛出FailedProcessConfigFileError以允许继续尝试别的SL处理器
        :type processor: Callable[[Self, str, str, str], Any]
        :param file_config_format:
           该配置文件对象本身配置格式属性的值
           可选项，一般在保存时填入
           用于在没手动指定配置格式且没文件后缀时使用该值进行尝试

           .. seealso::
              :py:attr:`ABCConfigFile.config_format`

        :raise UnsupportedConfigFormatError: 不支持的配置格式
        :raise FailedProcessConfigFileError: 处理配置文件失败

        .. seealso::
           格式计算优先级

           :py:meth:`_calc_formats`

        .. versionadded:: 0.1.2

        .. versionchanged:: 0.2.0
           将格式计算部分提取到单独的函数 :py:meth:`_calc_formats`
        """

        def callback_wrapper(cfg_fmt: str):
            return processor(self, namespace, file_name, cfg_fmt)

        # 尝试从多个SL加载器中找到能正确加载的那一个
        errors = {}
        for config_format in self._calc_formats(file_name, config_formats, file_config_format):
            if config_format not in self.SLProcessors:
                errors[config_format] = UnsupportedConfigFormatError(config_format)
                continue
            try:
                # 能正常运行直接返回结果，不再进行尝试
                return callback_wrapper(config_format)
            except FailedProcessConfigFileError as err:
                errors[config_format] = err

        for err in errors.values():
            if isinstance(err, UnsupportedConfigFormatError):
                raise err from None

        # 如果没有一个SL加载器能正确加载，则抛出异常
        raise FailedProcessConfigFileError(errors)

    @override
    def save(
            self,
            namespace: str,
            file_name: str,
            config_formats: Optional[str | Iterable[str]] = None,
            config: Optional[ABCConfigFile] = None,
            *args, **kwargs
    ) -> Self:
        if config is not None:
            self.set(namespace, file_name, config)

        file = self._configs[namespace][file_name]

        def processor(pool: Self, ns: str, fn: str, cf: str):
            file.save(pool, ns, fn, cf, *args, **kwargs)

        self._test_all_sl(namespace, file_name, config_formats, processor, file_config_format=file.config_format)
        return self

    @override
    def save_all(self, ignore_err: bool = False) -> None | dict[str, dict[str, tuple[ABCConfigFile, Exception]]]:
        errors = {}
        for namespace, configs in deepcopy(self._configs).items():
            errors[namespace] = {}
            for file_name, config in configs.items():
                try:
                    self.save(namespace, file_name)
                except Exception as e:
                    if not ignore_err:
                        raise
                    errors[namespace][file_name] = (config, e)

        if not ignore_err:
            return None

        return {k: v for k, v in errors.items() if v}

    @override
    def initialize(
            self,
            namespace: str,
            file_name: str,
            *args,
            config_formats: Optional[str | Iterable[str]] = None,
            **kwargs,
    ) -> ABCConfigFile:
        def processor(pool: Self, ns: str, fn: str, cf: str):
            config_file_cls: type[ABCConfigFile] = self.SLProcessors[cf].supported_file_classes[0]
            result = config_file_cls.initialize(pool, ns, fn, cf, *args, **kwargs)

            pool.set(namespace, file_name, result)
            return result

        return self._test_all_sl(namespace, file_name, config_formats, processor)

    @override
    def load(
            self,
            namespace: str,
            file_name: str,
            *args,
            config_formats: Optional[str | Iterable[str]] = None,
            allow_initialize: bool = False,
            **kwargs,
    ) -> ABCConfigFile:
        """
        加载配置到指定命名空间并返回

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config_formats: 配置格式
        :type config_formats: Optional[str | Iterable[str]]
        :param allow_initialize: 是否允许初始化配置文件
        :type allow_initialize: bool

        :return: 配置对象
        :rtype: ABCConfigFile

        .. versionchanged:: 0.2.0
           现在会像 :py:meth:`save` 一样接收并传递额外参数

           移除 ``config_file_cls`` 参数

           重命名参数 ``allow_create`` 为 ``allow_initialize``

           现在由 :py:meth:`ABCConfigFile.initialize` 创建新的空 :py:class:`ABCConfigFile` 对象
        """
        if (namespace, file_name) in self:
            return self.get(namespace, file_name)

        def processor(pool: Self, ns: str, fn: str, cf: str):
            config_file_cls = self.SLProcessors[cf].supported_file_classes[0]
            try:
                result = config_file_cls.load(pool, ns, fn, cf, *args, **kwargs)
            except FileNotFoundError:
                if not allow_initialize:
                    raise
                result = pool.initialize(ns, fn, *args, config_formats=cf, **kwargs)

            pool.set(namespace, file_name, result)
            return result

        return self._test_all_sl(namespace, file_name, config_formats, processor)

    def delete(self, namespace: str, file_name: str) -> Self:
        del self._configs[namespace][file_name]
        if not self._configs[namespace]:
            del self._configs[namespace]
        return self

    def unset(self, namespace: str, file_name: Optional[str] = None) -> Self:
        with suppress(KeyError):
            self.delete(namespace, file_name)
        return self

    def __getitem__(self, item):
        if isinstance(item, tuple):
            if len(item) != 2:
                raise ValueError(f"item must be a tuple of length 2, got {item}")
            return self[item[0]][item[1]]
        return deepcopy(self.configs[item])

    def __contains__(self, item):
        """
        .. versionadded:: 0.1.2
        """
        if isinstance(item, str):
            return item in self._configs
        if isinstance(item, Iterable):
            item = tuple(item)
        if len(item) == 1:
            return item[0] in self._configs
        if len(item) != 2:
            raise ValueError(f"item must be a tuple of length 2, got {item}")
        return (item[0] in self._configs) and (item[1] in self._configs[item[0]])

    def __len__(self):
        """
        配置文件总数
        """
        return sum(len(v) for v in self._configs.values())

    @property
    def configs(self):
        return deepcopy(self._configs)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.configs!r})"


__all__ = (
    "BasicConfigData",
    "BasicSingleConfigData",
    "BasicIndexedConfigData",
    "NoneConfigData",
    "MappingConfigData",
    "SequenceConfigData",
    "BoolConfigData",
    "NumberConfigData",
    "StringConfigData",
    "ObjectConfigData",
    "AnyConfigData",
    "ConfigData",
    "ComponentOrders",
    "ComponentMember",
    "ComponentMeta",
    "ComponentConfigData",
    "ConfigFile",
    "PHelper",
    "BasicConfigPool",
)
