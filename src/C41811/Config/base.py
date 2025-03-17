# -*- coding: utf-8 -*-
# cython: language_level = 3


import builtins
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
from .utils import singleton


def _fmt_path(path: str | ABCPath) -> ABCPath:
    if isinstance(path, ABCPath):
        return path
    return Path.from_str(path)


class BasicConfigData(ABCConfigData, ABC):
    # noinspection GrazieInspection
    """
    配置数据基类

    .. versionadded:: 0.1.5

    .. versionchanged:: 0.1.6
       从 ``BaseConfigData`` 重命名为 ``BasicConfigData``
    """

    _read_only: bool | None = False

    @override
    @property
    def data_read_only(self) -> bool | None:
        return True

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

    .. versionadded:: 0.1.6
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

    .. versionchanged:: 0.1.6
       从 ``BaseSupportsIndexConfigData`` 重命名为 ``BasicIndexedConfigData``
    """

    def _process_path(
            self,
            path: ABCPath,
            process_check: Callable[[Any, ABCKey, list[ABCKey], int], Any],
            process_return: Callable[[Any], Any]
    ) -> Any:
        """
        处理键路径的通用函数阿

        :param path: 键路径
        :type path: str
        :param process_check: 检查并处理每个路径段，返回值非None时结束操作并返回值
        :type process_check: Callable[(now_data: Any, now_path: str, last_path: str, path_index: int), Any]
        :param process_return: 处理最终结果，该函数返回值会被直接返回
        :type process_return: Callable[(now_data: Any), Any]

        :return: 处理结果
        :rtype: Any
        """
        now_data = self._data

        for key_index, now_key in enumerate(path):
            now_key: ABCKey
            last_key: list[ABCKey] = path[key_index + 1:]

            check_result = process_check(now_data, now_key, last_key, key_index)
            if check_result is not None:
                return check_result

            now_data = now_key.__get_inner_element__(now_data)

        return process_return(now_data)

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
    def __getitem__(self, key):
        data = self._data[key]
        is_sequence = isinstance(data, Sequence) and not isinstance(data, (str, bytes))
        if isinstance(data, Mapping) or is_sequence:
            return ConfigData(data)
        return deepcopy(data)


class ConfigData(ABC):
    """
    配置数据类

    .. versionchanged:: 0.1.5
       会自动根据传入的配置数据类型选择对应的子类
    """
    TYPES: ClassVar[OrderedDict[tuple[type, ...], type]]
    """
    存储配置数据类型对应的子类

    .. versionchanged:: 0.1.6
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


@singleton
class _UnsetArgType:
    def __str__(self):
        return "<Unset Argument>"

    def __bool__(self):
        return False


_UnsetArg = _UnsetArgType()


@_generate_operators
class MappingConfigData[D: Mapping | MutableMapping](BasicIndexedConfigData, MutableMapping):
    """
    支持 Mapping 的 ConfigData

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

           >>> data.keys(end_point_only=True)
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

        .. versionchanged:: 0.1.6
           重命名 ``get_raw`` 参数为 ``return_raw_value``
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

        .. versionchanged:: 0.1.6
           重命名 ``get_raw`` 参数为 ``return_raw_value``
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
    def pop(self, key, /, default: Any = _UnsetArg):
        if default is _UnsetArg:
            return self._data.pop(key)
        return self._data.pop(key, default)

    @override
    @_check_read_only
    def popitem(self):
        self._data.popitem()

    @override
    @_check_read_only
    def update(self, m, /, **kwargs):
        self._data.update(m, **kwargs)

    def __getattr__(self, item) -> Self | Any:
        try:
            item_obj = self[item]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")
        return item_obj

    @_operate(operator.or_, operator.ior)  # @formatter:off
    def __or__(self, other) -> Any: ...

    def __ror__(self, other) -> Any: ...
    # @formatter:on


@_generate_operators
class SequenceConfigData[D: Sequence | MutableSequence](BasicIndexedConfigData, MutableSequence):
    """
    支持 Sequence 的 ConfigData

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
    支持 Number 的 ConfigData

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
    支持 bool 的 ConfigData

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
    支持 str 和 bytes 的 ConfigData
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
    _data: D
    data: D

    @override
    @property
    def data_read_only(self) -> False:
        return False

    @override
    @property
    def data(self) -> D:
        """
        配置的原始数据

        .. caution::
           直接返回了原始对象，未默认进行深拷贝

        :return: 配置的原始数据
        :rtype: Any
        """
        return self._data


type AnyConfigData = (
        ABCConfigData
        | ABCIndexedConfigData
        | MappingConfigData
        | StringConfigData
        | SequenceConfigData
        | BoolConfigData
        | NumberConfigData
        | ObjectConfigData
)

ConfigData.TYPES = OrderedDict((
    ((ABCConfigData,), lambda _: _),
    ((Mapping, MutableMapping, type(None)), MappingConfigData),
    ((str, bytes), StringConfigData),
    ((Sequence, MutableSequence), SequenceConfigData),
    ((bool,), BoolConfigData),
    ((Number,), NumberConfigData),
    ((object,), ObjectConfigData),
))

ConfigData.register(MappingConfigData)
ConfigData.register(SequenceConfigData)
ConfigData.register(NumberConfigData)
ConfigData.register(BoolConfigData)
ConfigData.register(StringConfigData)
ConfigData.register(ObjectConfigData)


class ConfigFile(ABCConfigFile):
    """
    配置文件类
    """

    def __init__(
            self,
            initial_config: Any,
            *,
            config_format: Optional[str] = None
    ) -> None:
        """
        .. caution::
           本身并未对 ``initial_config`` 参数进行深拷贝，但是 :py:class:`ConfigData` 可能会将其深拷贝

        :param initial_config: 配置数据
        :type initial_config: Any
        :param config_format: 配置文件的格式
        :type config_format: Optional[str]

        .. versionchanged:: 0.1.6
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

        return processor_pool.SLProcessors[
            config_format
        ].load(processor_pool, processor_pool.root_path, namespace, file_name, *processor_args, **processor_kwargs)


class PHelper(ABCProcessorHelper): ...  # noqa: E701


class BasicConfigPool(ABCConfigPool, ABC):
    """
    基础配置池类

    实现了一些通用方法

    .. versionchanged:: 0.1.6
       从 ``BaseConfigPool`` 重命名为 ``BasicConfigPool``
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
    ) -> builtins.set[str]:
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

        1.如果传入了config_formats且非None非空集则直接使用

        2.如果文件名注册了对应的SL处理器则直接使用

        3.如果传入了file_config_format且非None则直接使用

        .. versionadded:: 0.1.6
        """
        # 先尝试从传入的参数中获取配置文件格式
        if config_formats is None:
            config_formats = set()
        elif isinstance(config_formats, str):
            return {config_formats}
        else:
            config_formats = set(config_formats)

        if config_formats:
            return config_formats

        def _check_file_name(match: str | Pattern) -> bool:
            if isinstance(match, str):
                return file_name.endswith(match)
            return bool(match.fullmatch(file_name))  # 目前没SL处理器用得上 # pragma: no cover

        # 再尝试从文件名匹配配置文件格式
        for m in self.FileNameProcessors:
            if _check_file_name(m):
                return self.FileNameProcessors[m]

        # 最后尝试从配置文件对象本身获取配置文件格式
        if configfile_format is None:
            raise UnsupportedConfigFormatError("Unknown")
        return {configfile_format}

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

        .. versionchanged:: 0.1.6
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
    "MappingConfigData",
    "SequenceConfigData",
    "BoolConfigData",
    "NumberConfigData",
    "StringConfigData",
    "ObjectConfigData",
    "AnyConfigData",
    "ConfigData",
    "ConfigFile",
    "PHelper",
    "BasicConfigPool",
)
