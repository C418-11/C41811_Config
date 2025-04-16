# -*- coding: utf-8 -*-
# cython: language_level = 3


import os
from abc import ABC
from abc import abstractmethod
from collections import OrderedDict
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence
from copy import deepcopy
from re import Pattern
from types import NotImplementedType
from typing import Any
from typing import Optional
from typing import Self
from typing import cast
from typing import overload

from ._protocols import Indexed
from ._protocols import MutableIndexed

type AnyKey = ABCKey[Any, Any]
"""
.. versionadded:: 0.2.0
"""


class ABCKey[K, D](ABC):
    """
    用于获取配置的键
    """

    def __init__(self, key: K, meta: Optional[str] = None):
        """
        :param key: 键名
        :type key: str
        :param meta: 元信息
        :type meta: Optional[str]
        """
        self._key = deepcopy(key)
        self._meta: None | str = meta

    @property
    def key(self) -> K:
        return deepcopy(self._key)

    @property
    def meta(self) -> str | None:
        """
        .. versionadded:: 0.2.0
        """
        return self._meta

    @abstractmethod
    def unparse(self) -> str:
        """
        还原为可被解析的字符串

        .. versionadded:: 0.1.1
        """

    @abstractmethod
    def __get_inner_element__(self, data: D) -> D:
        """
        获取内层元素

        :param data: 配置数据
        :type data: Any
        :return: 内层配置数据
        :rtype: Any

        .. versionadded:: 0.1.4
        """

    @abstractmethod
    def __set_inner_element__(self, data: D, value: Any) -> None:
        """
        设置内层元素

        :param data: 配置数据
        :type data: Any
        :param value: 值
        :type value: Any

        .. versionadded:: 0.1.4
        """

    @abstractmethod
    def __delete_inner_element__(self, data: D) -> None:
        """
        删除内层元素

        :param data: 配置数据
        :type data: Any

        .. versionadded:: 0.1.4
        """

    @abstractmethod
    def __contains_inner_element__(self, data: Any) -> bool:
        """
        是否包含内层元素

        :param data: 配置数据
        :type data: Any
        :return: 是否包含内层配置数据
        :rtype: bool

        .. versionadded:: 0.1.4
        """

    @abstractmethod
    def __supports__(self, data: Any) -> tuple[Any, ...]:
        """
        检查此键是否支持该配置数据

        返回缺失的协议

        :param data: 配置数据
        :type data: Any
        :return: 此键缺失支持的数据类型
        :rtype: tuple

        .. versionadded:: 0.1.4
        """

    @abstractmethod
    def __supports_modify__(self, data: Any) -> tuple[Any, ...]:
        """
        检查此键是否支持修改该配置数据

        返回缺失的协议

        :param data: 配置数据
        :type data: Any
        :return: 此键缺失支持的数据类型
        :rtype: tuple

        .. versionadded:: 0.1.4
        """

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented

        return all((
            self._key == other._key,
            self._meta == other._meta,
        ))

    def __hash__(self) -> int:
        return hash((self._key, self._meta))

    def __deepcopy__(self, memo: dict[Any, Any]) -> Self:
        if self._meta is None:
            return type(self)(self._key)
        return type(self)(self._key, self._meta)

    def __str__(self) -> str:
        return str(self._key)

    def __repr__(self) -> str:
        meta = '' if self._meta is None else f", meta={self._meta}"
        return f"<{type(self).__name__}(key={self._key}{meta})>"


class ABCPath[K: AnyKey](ABC, Iterable[K]):
    """
    用于获取数据的路径
    """

    def __init__(self, keys: Iterable[K]):
        self._keys = deepcopy(tuple(keys))

    @property
    def keys(self) -> tuple[K, ...]:
        """
        .. versionadded:: 0.2.0
        """
        return deepcopy(self._keys)

    @abstractmethod
    def unparse(self) -> str:
        """
        还原为可被解析的字符串

        .. versionadded:: 0.1.1
        """

    @overload  # @formatter:off
    def __getitem__(self, item: slice) -> Self: ...

    @overload
    def __getitem__(self, item: int) -> K: ...
    #  @formatter:on

    def __getitem__(self, item: Any) -> K | Self:
        items = self._keys[item]
        if isinstance(items, ABCKey):
            return cast(K, items)
        return type(self)(items)

    def __contains__(self, item: Any) -> bool:
        return item in self._keys

    def __bool__(self) -> bool:
        return bool(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def __iter__(self) -> Iterator[K]:
        return iter(self._keys)

    def __hash__(self) -> int:
        return hash(self._keys)

    def __deepcopy__(self, memo: dict[Any, Any]) -> Self:
        return type(self)(self._keys)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._keys == other._keys

    def __repr__(self) -> str:
        return f"<{type(self).__name__}{self._keys}>"


class ABCConfigData[D](ABC):
    """
    配置数据抽象基类

    .. versionchanged:: 0.1.5
       现在配置数据不再局限于Mapping
    """

    @classmethod
    def from_data(cls, *args: Any, **kwargs: Any) -> Self:
        """
        提供创建同类型配置数据的快捷方式

        :return: 新的配置数据
        :rtype: Self

        .. note::
           套壳__init__，主要是为了方便内部快速创建与传入的ABCConfigData同类型的对象

           例如：

           .. code-block:: python

              type(instance)(data)

           可以简写为

           .. code-block:: python

              instance.from_data(data)

        .. versionchanged:: 0.2.0
           现在会自适应初始化参数
        """
        # noinspection PyArgumentList
        return cls(*args, **kwargs)

    @property
    @abstractmethod
    def data_read_only(self) -> bool | None:
        """
        配置数据是否为只读

        :return: 配置数据是否为只读
        :rtype: bool | None

        .. versionadded:: 0.1.3
        .. versionchanged:: 0.1.5
           改为抽象属性
        """

    @property
    @abstractmethod
    def read_only(self) -> bool | None:
        """
        配置数据是否为 ``只读模式``

        :return: 配置数据是否为 ``只读模式``
        :rtype: bool | None
        """
        return self.data_read_only

    @read_only.setter
    @abstractmethod
    def read_only(self, value: Any) -> None:
        """
        设置配置数据是否为 ``只读模式``

        :raise ConfigDataReadOnlyError: 配置数据为只读
        """

    def freeze(self, freeze: Optional[bool] = None) -> Self:
        """
        冻结配置数据 (切换只读模式)

        :param freeze: 是否冻结配置数据, 为 :py:const:`None` 时进行切换
        :type freeze: Optional[bool]
        :return: 返回当前实例便于链式调用
        :rtype: Self

        .. versionadded:: 0.1.5
        """
        if freeze is None:
            self.read_only = not self.read_only
            return self
        self.read_only = freeze
        return self

    def __format__(self, format_spec: str) -> str:
        if format_spec == 'r':
            return repr(self)
        return super().__format__(format_spec)


type PathLike = str | ABCPath[AnyKey]
"""
.. versionadded:: 0.2.0
"""


class ABCIndexedConfigData[D: Indexed[Any, Any]](
    ABCConfigData[D],
    MutableIndexed[Any, Any],
    ABC
):
    # noinspection GrazieInspection
    """
    支持 ``索引`` 操作的配置数据

    .. versionadded:: 0.1.5

    .. versionchanged:: 0.2.0
       重命名 ``ABCSupportsIndexConfigData`` 为 ``ABCIndexedConfigData``
    """

    @abstractmethod
    def retrieve(self, path: PathLike, *, return_raw_value: bool = False) -> Any:
        """
        获取路径的值的*快照*

        :param path: 路径
        :type path: str | ABCPath
        :param return_raw_value: 是否获取原始值，为False时，会将Mapping | Sequence转换为对应类
        :type return_raw_value: bool

        :return: 路径的值
        :rtype: Any

        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredPathNotFoundError: 需求的键不存在

        .. versionchanged:: 0.2.0
           重命名参数 ``get_raw`` 为 ``return_raw_value``
        """

    @abstractmethod
    def modify(self, path: PathLike, value: Any, *, allow_create: bool = True) -> Self:
        """
        修改路径的值

        :param path: 路径
        :type path: str | ABCPath
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
           ``value`` 参数未默认做深拷贝，可能导致非预期的行为

        .. attention::
           ``allow_create`` 时，使用与 `self.data` 一样的类型新建路径
        """

    @abstractmethod
    def delete(self, path: PathLike) -> Self:
        """
        删除路径

        :param path: 路径
        :type path: str | ABCPath

        :return: 返回当前实例便于链式调用
        :rtype: Self

        :raise ConfigDataReadOnlyError: 配置数据为只读
        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredPathNotFoundError: 需求的键不存在
        """

    @abstractmethod
    def unset(self, path: PathLike) -> Self:
        """
        确保路径不存在 (删除路径，但是找不到路径时不会报错)

        :param path: 路径
        :type path: str | ABCPath

        :return: 返回当前实例便于链式调用
        :rtype: Self

        :raise ConfigDataReadOnlyError: 配置数据为只读
        :raise ConfigDataTypeError: 配置数据类型错误

        .. versionadded:: 0.1.2
        """

    @abstractmethod
    def exists(self, path: PathLike, *, ignore_wrong_type: bool = False) -> bool:
        """
        判断路径是否存在

        :param path: 路径
        :type path: str | ABCPath
        :param ignore_wrong_type: 忽略配置数据类型错误
        :type ignore_wrong_type: bool

        :return: 路径是否存在
        :rtype: bool

        :raise ConfigDataTypeError: 配置数据类型错误
        """

    @abstractmethod
    def get(self, path: PathLike, default: Any = None, *, return_raw_value: bool = False) -> Any:
        """
        获取路径的值的*快照*，路径不存在时填充默认值

        :param path: 路径
        :type path: str | ABCPath

        :param default: 默认值
        :type default: Any
        :param return_raw_value: 是否获取原始值
        :type return_raw_value: bool

        :return: 路径的值
        :rtype: Any

        :raise ConfigDataTypeError: 配置数据类型错误

        例子
        ----

           >>> from C41811.Config import ConfigData
           >>> data = ConfigData({
           ...     "key": "value"
           ... })

           路径存在时返回值

           >>> data.get("key")
           'value'

           路径不存在时返回默认值None

           >>> print(data.get("not exists"))
           None

           自定义默认值

           >>> data.get("with default",default="default value")
           'default value'

        .. versionchanged:: 0.2.0
           重命名参数 ``get_raw`` 为 ``return_raw_value``
        """

    @abstractmethod
    def setdefault(self, path: PathLike, default: Any = None, *, return_raw_value: bool = False) -> Any:
        """
        如果路径不在配置数据中则填充默认值到配置数据并返回

        :param path: 路径
        :type path: str | ABCPath
        :param default: 默认值
        :type default: Any
        :param return_raw_value: 是否获取原始值
        :type return_raw_value: bool

        :return: 路径的值
        :rtype: Any

        :raise ConfigDataReadOnlyError: 配置数据为只读
        :raise ConfigDataTypeError: 配置数据类型错误

        例子
        ----

           >>> from C41811.Config import ConfigData
           >>> data = ConfigData({
           ...     "key": "value"
           ... })

           路径存在时返回值

           >>> data.setdefault("key")
           'value'

           路径不存在时返回默认值None并填充到原始数据

           >>> print(data.setdefault("not exists"))
           None
           >>> data
           MappingConfigData({'key': 'value', 'not exists': None})

           自定义默认值

           >>> data.setdefault("with default",default="default value")
           'default value'
           >>> data
           MappingConfigData({'key': 'value', 'not exists': None, 'with default': 'default value'})

        .. versionchanged:: 0.2.0
           重命名参数 ``get_raw`` 为 ``return_raw_value``

           重命名 ``set_default`` 为 ``setdefault``
        """

    @abstractmethod
    def __contains__(self, key: Any) -> bool: ...

    @abstractmethod
    def __iter__(self) -> Iterator[Any]: ...

    @abstractmethod
    def __len__(self) -> int: ...

    @abstractmethod
    def __getitem__(self, index: Any) -> Any: ...

    @abstractmethod
    def __setitem__(self, index: Any, value: Any) -> None: ...

    @abstractmethod
    def __delitem__(self, index: Any) -> None: ...


class ABCProcessorHelper(ABC):
    """
    辅助SL处理器

    .. versionadded:: 0.2.0
    """

    @staticmethod
    def calc_path(
            root_path: str,
            namespace: str,
            file_name: Optional[str] = None,
    ) -> str:
        """
        处理配置文件对应的文件路径

        file_name为None时，返回文件所在的目录

        :param root_path: 保存的根目录
        :type root_path: str
        :param namespace: 配置的命名空间
        :type namespace: Optional[str]
        :param file_name: 配置文件名
        :type file_name: Optional[str]

        :return: 配置文件路径
        :rtype: str
        """

        if file_name is None:
            file_name = ''

        return os.path.normpath(os.path.join(root_path, namespace, file_name))


class ABCSLProcessorPool(ABC):
    """
    SL处理器池
    """

    def __init__(self, root_path: str = "./.config"):
        self.SLProcessors: dict[str, ABCConfigSL] = {}
        """
        处理器注册表

        数据结构: ``{处理器注册名: 处理器实例}}``

        .. versionchanged:: 0.2.0
           重命名 ``SLProcessor`` 为 ``SLProcessors``
        """
        self.FileNameProcessors: OrderedDict[
            str | Pattern[str], list[str]
        ] = OrderedDict()  # {FileNameMatch: [RegName]}
        # noinspection SpellCheckingInspection
        """
        文件名处理器注册表

        .. caution::
           此字典是顺序敏感的，越靠前越优先被检查

        数据结构: ``{文件名匹配: [处理器注册名]}``

        文件名匹配:
            - 为字符串时会使用 ``endswith`` 进行匹配
            - 为 ``re.Pattern`` 时会使用 ``Pattern.fullmatch`` 进行匹配

        .. versionchanged:: 0.2.0
           重命名 ``FileExtProcessor`` 为 ``FileNameProcessors``

           现在是顺序敏感的
        """
        self._root_path = root_path

    @property
    @abstractmethod
    def helper(self) -> ABCProcessorHelper: ...

    @property
    def root_path(self) -> str:
        """
        :return: 配置文件根目录
        """
        return self._root_path


class ABCConfigFile[D: ABCConfigData[Any]](ABC):
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
        :type initial_config: ABCConfigData
        :param config_format: 配置文件的格式
        :type config_format: Optional[str]

        .. caution::
           ``initial_config`` 参数未默认做深拷贝，可能导致非预期的行为

        .. versionchanged:: 0.2.0
           重命名参数 ``config_data`` 为 ``initial_config``
        """

        self._config: D = initial_config

        self._config_format: str | None = config_format

    @property
    def config(self) -> D:
        """
        :return: 配置数据

        .. versionchanged:: 0.2.0
           重命名属性 ``data`` 为 ``config``
        """
        return self._config

    @property
    def config_format(self) -> str | None:
        """
        :return: 配置文件的格式
        """
        return self._config_format

    @abstractmethod
    def save(
            self,
            processor_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: Optional[str] = None,
            *processor_args: Any,
            **processor_kwargs: Any,
    ) -> None:
        """
        使用SL处理保存配置

        :param processor_pool: 配置池
        :type processor_pool: ABCSLProcessorPool
        :param namespace: 文件命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config_format: 配置文件的格式
        :type config_format: Optional[str]

        :raise UnsupportedConfigFormatError: 不支持的配置格式

        .. versionchanged:: 0.2.0
           重命名 ``config_pool`` 为 ``processor_pool``
        """

    @classmethod
    @abstractmethod
    def load(
            cls,
            processor_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: str,
            *processor_args: Any,
            **processor_kwargs: Any,
    ) -> Self:
        """
        从SL处理器加载配置

        :param processor_pool: 配置池
        :type processor_pool: ABCSLProcessorPool
        :param namespace: 文件命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config_format: 配置文件的格式
        :type config_format: str

        :return: 配置对象
        :rtype: Self

        :raise UnsupportedConfigFormatError: 不支持的配置格式

        .. versionchanged:: 0.2.0
           重命名 ``config_pool`` 为 ``processor_pool``
        """

    @classmethod
    @abstractmethod
    def initialize(
            cls,
            processor_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: str,
            *processor_args: Any,
            **processor_kwargs: Any,
    ) -> Self:
        """
        初始化一个受SL处理器支持的配置文件

        :param processor_pool: 配置池
        :type processor_pool: ABCSLProcessorPool
        :param namespace: 文件命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config_format: 配置文件的格式
        :type config_format: str

        :return: 配置对象
        :rtype: Self

        :raise UnsupportedConfigFormatError: 不支持的配置格式

        .. versionadded:: 0.2.0
        """

    def __bool__(self) -> bool:
        return bool(self._config)

    def __eq__(self, other: Any) -> bool | NotImplementedType:
        if not isinstance(other, type(self)):
            return NotImplemented

        for field in ["_config_format", "_config"]:
            if getattr(self, field) != getattr(other, field):
                return False
        return True

    def __repr__(self) -> str:
        repr_parts: list[str] = []
        for field in ["_config_format", "_config"]:
            field_value = getattr(self, field)
            if field_value is None:
                continue

            repr_parts.append(f"{field[1:]}={field_value!r}")

        fmt_str = ", ".join(repr_parts)
        return f"{self.__class__.__name__}({fmt_str})"


class ABCConfigPool(ABCSLProcessorPool):
    """
    配置池抽象类
    """

    @overload
    def get(self, namespace: str) -> dict[str, ABCConfigFile[Any]] | None: ...

    @overload
    def get(self, namespace: str, file_name: str) -> ABCConfigFile[Any] | None: ...

    @overload
    def get(
            self,
            namespace: str,
            file_name: Optional[str] = None,
    ) -> dict[str, ABCConfigFile[Any]] | ABCConfigFile[Any] | None: ...

    @abstractmethod
    def get(
            self,
            namespace: str,
            file_name: Optional[str] = None,
    ) -> dict[str, ABCConfigFile[Any]] | ABCConfigFile[Any] | None:
        """
        获取配置

        如果配置不存在则返回None

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: Optional[str]

        :return: 配置
        :rtype: dict[str, ABCConfigFile] | ABCConfigFile | None
        """

    @abstractmethod
    def set(self, namespace: str, file_name: str, config: ABCConfigFile[Any]) -> Self:
        """
        设置配置

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config: 配置
        :type config: ABCConfigFile

        :return: 返回当前实例便于链式调用
        :rtype: Self

        .. versionchanged:: 0.2.0
           返回当前实例便于链式调用
        """

    @abstractmethod
    def save(
            self,
            namespace: str,
            file_name: str,
            config_formats: Optional[str | Iterable[str]] = None,
            config: Optional[ABCConfigFile[Any]] = None,
            *args: Any, **kwargs: Any,
    ) -> Self:
        """
        保存配置

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config_formats: 配置格式
        :type config_formats: Optional[str | Iterable[str]]
        :param config: 配置文件，可选，提供此参数相当于自动调用了一遍pool.set
        :type config: Optional[ABCConfigFile]

        :return: 返回当前实例便于链式调用
        :rtype: Self

        .. versionchanged:: 0.1.2
           添加 ``config_formats`` 和 ``config`` 参数

        .. versionchanged:: 0.2.0
           返回当前实例便于链式调用
        """

    @abstractmethod
    def save_all(self, ignore_err: bool = False) -> None | dict[str, dict[str, tuple[ABCConfigFile[Any], Exception]]]:
        """
        保存所有配置

        :param ignore_err: 是否忽略保存导致的错误
        :type ignore_err: bool

        :return: ignore_err为True时返回{Namespace: {FileName: (ConfigObj, Exception)}}，否则返回None
        :rtype: None | dict[str, dict[str, tuple[ABCConfigFile, Exception]]]
        """

    @abstractmethod
    def initialize(
            self,
            namespace: str,
            file_name: str,
            *args: Any,
            config_formats: Optional[str | Iterable[str]] = None,
            **kwargs: Any,
    ) -> ABCConfigFile[Any]:
        """
        初始化配置文件到指定命名空间并返回

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config_formats: 配置格式
        :type config_formats: Optional[str | Iterable[str]]

        :return: 配置对象
        :rtype: ABCConfigFile

        .. versionadded:: 0.2.0
        """

    @abstractmethod
    def load(
            self,
            namespace: str,
            file_name: str,
            *args: Any,
            config_formats: Optional[str | Iterable[str]] = None,
            allow_initialize: bool = False,
            **kwargs: Any,
    ) -> ABCConfigFile[Any]:
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

           删除参数 ``config_file_cls``

           重命名参数 ``allow_create`` 为 ``allow_initialize``
        """

    @abstractmethod
    def remove(self, namespace: str, file_name: Optional[str] = None) -> Self:
        """
        从配置池移除配置文件

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str

        :return: 返回当前实例便于链式调用
        :rtype: Self

        .. versionchanged:: 0.2.0
           返回当前实例便于链式调用

           重命名 ``delete`` 为 ``remove``
        """

    @abstractmethod
    def discard(self, namespace: str, file_name: Optional[str] = None) -> Self:
        """
        确保配置文件不存在于配置池

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: Optional[str]

        :return: 返回当前实例便于链式调用
        :rtype: Self

        .. versionadded:: 0.2.0
        """


type SLArgument = Optional[Sequence[Any] | Mapping[str, Any] | tuple[Sequence[Any], Mapping[str, Any]]]


class ABCConfigSL(ABC):
    """
    配置SaveLoad处理器抽象类

    .. versionchanged:: 0.2.0
       移动 ``保存加载器参数`` 相关至 :py:class:`BasicLocalFileConfigSL`
    """

    def __init__(
            self,
            *,
            reg_alias: Optional[str] = None,
    ):
        """
        :param reg_alias: sl处理器注册别名
        :type reg_alias: Optional[str]
        """
        self._reg_alias: Optional[str] = reg_alias

    @property
    @abstractmethod
    def processor_reg_name(self) -> str:
        """
        :return: SL处理器的默认注册名
        """

    @property
    @abstractmethod
    def supported_file_classes(self) -> list[type[ABCConfigFile[Any]]]:
        """
        :return: 支持的配置文件类

        .. versionadded:: 0.2.0
        """

    @property
    def reg_alias(self) -> str | None:
        """
        :return: 处理器的别名
        """
        return self._reg_alias

    @property
    def reg_name(self) -> str:
        """
        :return: 处理器的注册名
        """
        return self.processor_reg_name if self._reg_alias is None else self._reg_alias

    @property
    @abstractmethod
    def supported_file_patterns(self) -> tuple[str | Pattern[Any], ...]:
        """
        :return: 支持的文件名匹配

        .. versionchanged:: 0.2.0
           重命名 ``file_ext`` 为 ``supported_file_patterns``
        """

    def register_to(self, config_pool: ABCSLProcessorPool) -> None:
        """
        注册到配置池中

        :param config_pool: 配置池
        :type config_pool: ABCSLProcessorPool
        """

        config_pool.SLProcessors[self.reg_name] = self
        for match in self.supported_file_patterns:
            config_pool.FileNameProcessors.setdefault(match, []).append(self.reg_name)

    @abstractmethod
    def save(
            self,
            processor_pool: ABCSLProcessorPool,
            config_file: ABCConfigFile[Any],
            root_path: str,
            namespace: str,
            file_name: str,
            *args: Any,
            **kwargs: Any,
    ) -> None:
        """
        保存处理器

        :param processor_pool: 配置池
        :type processor_pool: ABCSLProcessorPool
        :param config_file: 待保存配置
        :type config_file: ABCConfigFile
        :param root_path: 保存的根目录
        :type root_path: str
        :param namespace: 配置的命名空间
        :type namespace: str
        :param file_name: 配置文件名
        :type file_name: str

        :raise FailedProcessConfigFileError: 处理配置文件失败

        .. versionchanged:: 0.2.0
           添加参数 ``processor_pool``
        """

    @abstractmethod
    def load(
            self,
            processor_pool: ABCSLProcessorPool,
            root_path: str,
            namespace: str,
            file_name: str,
            *args: Any,
            **kwargs: Any
    ) -> ABCConfigFile[Any]:
        """
        加载处理器

        :param processor_pool: 配置池
        :type processor_pool: ABCSLProcessorPool
        :param root_path: 保存的根目录
        :type root_path: str
        :param namespace: 配置的命名空间
        :type namespace: str
        :param file_name: 配置文件名
        :type file_name: str

        :return: 配置对象
        :rtype: ABCConfigFile

        :raise FailedProcessConfigFileError: 处理配置文件失败

        .. versionchanged:: 0.2.0
           删除参数 ``config_file_cls``

           添加参数 ``processor_pool``
        """

    @abstractmethod
    def initialize(
            self,
            processor_pool: ABCSLProcessorPool,
            root_path: str,
            namespace: str,
            file_name: str,
            *args: Any,
            **kwargs: Any
    ) -> ABCConfigFile[Any]:
        """
        初始化一个受SL处理器支持的配置文件

        :param processor_pool: 配置池
        :type processor_pool: ABCSLProcessorPool
        :param root_path: 保存的根目录
        :type root_path: str
        :param namespace: 配置的命名空间
        :type namespace: str
        :param file_name: 配置文件名
        :type file_name: str

        :return: 配置对象
        :rtype: ABCConfigFile

        .. versionadded:: 0.2.0
        """

    def __eq__(self, other: Any) -> bool | NotImplementedType:
        if not isinstance(other, type(self)):
            return NotImplemented

        processor_reg_name = self.processor_reg_name == other.processor_reg_name
        reg_alias = self.reg_alias == other.reg_alias
        file_match_eq = self.supported_file_patterns == other.supported_file_patterns

        return all((
            processor_reg_name,
            reg_alias,
            file_match_eq,
        ))

    def __hash__(self) -> int:
        return hash((
            self.processor_reg_name,
            self.reg_alias,
            self.supported_file_patterns,
        ))


class ABCMetaParser[D: ABCConfigData[Any], M](ABC):
    """
    元信息解析器抽象类

    .. versionadded:: 0.2.0
    """

    @abstractmethod
    def convert_config2meta(self, meta_config: D) -> M:
        """
        解析元配置

        :param meta_config: 元配置
        :type meta_config: ABCConfigData

        :return: 元数据
        :rtype: Any
        """

    @abstractmethod
    def convert_meta2config(self, meta: M) -> D:
        """
        解析元数据

        :param meta: 元数据
        :type meta: Any

        :return: 元配置
        :rtype: ABCConfigData
        """

    @abstractmethod
    def validator(self, meta: M, *args: Any) -> M:
        """
        元数据验证器
        """


__all__ = (
    "AnyKey",
    "ABCKey",
    "ABCPath",
    "ABCConfigData",
    "PathLike",
    "ABCIndexedConfigData",
    "ABCProcessorHelper",
    "ABCSLProcessorPool",
    "ABCConfigPool",
    "ABCConfigFile",
    "SLArgument",
    "ABCConfigSL",
    "ABCMetaParser",
)
