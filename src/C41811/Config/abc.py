# -*- coding: utf-8 -*-
# cython: language_level = 3


from abc import ABC
from abc import abstractmethod
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import Sequence
from copy import deepcopy
from re import Pattern
from typing import Any
from typing import Optional
from typing import Self

from ._protocols import SupportsIndex
from ._protocols import SupportsWriteIndex


class ABCKey(ABC):
    """
    用于获取配置的键
    """

    def __init__(self, key: Any):
        self._key = deepcopy(key)

    @property
    def key(self):
        return deepcopy(self._key)

    @abstractmethod
    def unparse(self) -> str:
        """
        还原为可被解析的字符串

        .. versionadded:: 0.1.1
        """

    @abstractmethod
    def __get_inner_element__[T: Any](self, data: T) -> T:
        """
        获取内层元素

        :param data: 配置数据
        :type data: Any
        :return: 内层配置数据
        :rtype: Any

        .. versionadded:: 0.1.4
        """

    @abstractmethod
    def __set_inner_element__(self, data: Any, value: Any) -> None:
        """
        设置内层元素

        :param data: 配置数据
        :type data: Any
        :param value: 值
        :type value: Any

        .. versionadded:: 0.1.4
        """

    @abstractmethod
    def __delete_inner_element__(self, data: Any) -> None:
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
    def __supports__(self, data: Any) -> tuple:
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
    def __supports_modify__(self, data: Any) -> tuple:
        """
        检查此键是否支持修改该配置数据

        返回缺失的协议

        :param data: 配置数据
        :type data: Any
        :return: 此键缺失支持的数据类型
        :rtype: tuple

        .. versionadded:: 0.1.4
        """

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        return self._key == other._key

    def __hash__(self):
        return hash(self._key)

    def __deepcopy__(self, memo):
        return type(self)(self.key)

    def __str__(self):
        return str(self._key)

    def __repr__(self):
        return f"<{type(self).__name__}({self._key})>"


class ABCPath(ABC):
    """
    用于获取数据的路径
    """

    def __init__(self, keys: Iterable[ABCKey]):
        self._keys = deepcopy(tuple(keys))

    @abstractmethod
    def unparse(self) -> str:
        """
        还原为可被解析的字符串

        .. versionadded:: 0.1.1
        """

    def __getitem__(self, item):
        return self._keys[item]

    def __contains__(self, item):
        return item in self._keys

    def __len__(self):
        return len(self._keys)

    def __iter__(self):
        return iter(self._keys)

    def __hash__(self):
        return hash(self._keys)

    def __deepcopy__(self, memo):
        return type(self)(self._keys)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._keys == other._keys

    def __repr__(self):
        return f"<{type(self).__name__}{self._keys}>"


class ABCConfigData[D: Any](ABC):
    """
    配置数据抽象基类

    .. versionchanged:: 0.1.5
       现在配置数据不再局限于Mapping
    """

    def __init__(self, data: D):
        """
        :param data: 配置的原始数据
        :type data: Any
        """

        self._data: D = deepcopy(data)
        self._read_only: bool | None = False

    @classmethod
    def from_data[S: Self](cls: type[S], data: D) -> S:
        """
        提供创建同类型配置数据的快捷方式

        :param data: 配置的原始数据
        :type data: Any
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
        """
        return cls(data)

    @property
    def data(self) -> D:
        """
        配置的原始数据*快照*

        :return: 配置的原始数据*快照*
        :rtype: Any
        """
        return deepcopy(self._data)

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
        return self.data_read_only or self._read_only

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

        :param freeze: 是否冻结配置数据, 为 ``None`` 时进行切换
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

    def __contains__(self, key) -> bool:
        return key in self._data

    def __len__(self):
        return len(self._data)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._data == other._data

    def __iter__(self):
        return iter(self._data)

    def __str__(self) -> str:
        return str(self._data)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._data!r})"

    def __format__(self, format_spec):
        if format_spec == 'r':
            return repr(self)
        return super().__format__(format_spec)

    def __deepcopy__(self, memo) -> Self:
        return self.from_data(self._data)


class ABCSupportsIndexConfigData[D: SupportsIndex | SupportsWriteIndex](
    ABCConfigData,
    SupportsIndex,
    SupportsWriteIndex,
    ABC
):
    """
    支持 ``索引`` 操作的配置数据

    .. versionadded:: 0.1.5
    """

    @abstractmethod
    def retrieve(self, path: str | ABCPath, *, get_raw: bool = False) -> Any:
        """
        获取路径的值的*快照*

        :param path: 路径
        :type path: str | ABCPath
        :param get_raw: 是否获取原始值，为False时，会将Mapping转换为当前类
        :type get_raw: bool

        :return: 路径的值
        :rtype: Any

        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredPathNotFoundError: 需求的键不存在
        """

    @abstractmethod
    def modify(self, path: str | ABCPath, value: Any, *, allow_create: bool = True) -> Self:
        """
        修改路径的值

        .. caution::
           value参数未默认做深拷贝，可能导致非预期的行为

        .. attention::
           allow_create时，使用与self.data一样的类型新建路径

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
        """

    @abstractmethod
    def delete(self, path: str | ABCPath) -> Self:
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
    def unset(self, path: str | ABCPath) -> Self:
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
    def exists(self, path: str | ABCPath, *, ignore_wrong_type: bool = False) -> bool:
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
    def get(self, path: str | ABCPath, default=None, *, get_raw: bool = False) -> Any:
        """
        获取路径的值的*快照*，路径不存在时填充默认值

        :param path: 路径
        :type path: str | ABCPath

        :param default: 默认值
        :type default: Any
        :param get_raw: 是否获取原始值
        :type get_raw: bool

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

           >>> data.get("with default", default="default value")
           'default value'
        """

    @abstractmethod
    def set_default(self, path: str | ABCPath, default=None, *, get_raw: bool = False) -> Any:
        """
        如果路径不在配置数据中则填充默认值到配置数据并返回

        :param path: 路径
        :type path: str | ABCPath
        :param default: 默认值
        :type default: Any
        :param get_raw: 是否获取原始值
        :type get_raw: bool

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

           >>> data.set_default("key")
           'value'

           路径不存在时返回默认值None并填充到原始数据

           >>> print(data.set_default("not exists"))
           None
           >>> data
           MappingConfigData({'key': 'value', 'not exists': None})

           自定义默认值

           >>> data.set_default("with default", default="default value")
           'default value'
           >>> data
           MappingConfigData({'key': 'value', 'not exists': None, 'with default': 'default value'})
        """

    @abstractmethod
    def __getitem__(self, key): ...

    def __setitem__(self, key, value) -> None:
        self._data[key] = value

    def __delitem__(self, key) -> None:
        del self._data[key]


class ABCSLProcessorPool(ABC):
    """
    SL处理器池
    """

    def __init__(self, root_path: str = "./.config"):
        self.SLProcessors: dict[str, ABCConfigSL] = {}
        """
        处理器注册表

        数据结构: ``{处理器注册名: 处理器实例}}``

        .. versionchanged:: 0.1.6
           从 ``SLProcessor`` 重命名为 ``SLProcessors``
        """
        self.FileNameProcessors: dict[str | Pattern, set[str]] = {}  # {FileNameMatch: {RegName}}
        # noinspection SpellCheckingInspection
        """
        文件名处理器注册表

        数据结构: ``{文件名匹配: {处理器注册名}}``

        文件名匹配:
            - 为字符串时会使用 ``endswith`` 进行匹配
            - 为 ``re.Pattern`` 时会使用 ``Pattern.fullmatch`` 进行匹配

        .. versionchanged:: 0.1.6
           从 ``FileExtProcessor`` 重命名为 ``FileNameProcessors``
        """
        self._root_path = root_path

    @property
    def root_path(self) -> str:
        """
        :return: 配置文件根目录
        """
        return self._root_path


class ABCConfigFile(ABC):
    """
    配置文件类
    """

    def __init__(
            self,
            config_data: ABCConfigData,
            *,
            config_format: Optional[str] = None
    ) -> None:
        """
        .. caution::
           config_data参数未默认做深拷贝，可能导致非预期的行为

        :param config_data: 配置数据
        :type config_data: ABCConfigData
        :param config_format: 配置文件的格式
        :type config_format: Optional[str]
        """

        self._data: ABCConfigData = config_data

        self._config_format: str | None = config_format

    @property
    def data(self) -> ABCConfigData:
        """
        :return: 配置数据
        """
        return self._data

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
            *processor_args,
            **processor_kwargs
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

        .. versionchanged:: 0.1.6
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
            *processor_args,
            **processor_kwargs
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

        .. versionchanged:: 0.1.6
           重命名 ``config_pool`` 为 ``processor_pool``
        """

    def __bool__(self):
        return bool(self._data)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        for field in ["_config_format", "_data"]:
            if getattr(self, field) != getattr(other, field):
                return False
        return True

    def __repr__(self):
        fmt_ls: list[str] = []
        for field in ["_config_format", "_data"]:
            field_value = getattr(self, field)
            if field_value is None:
                continue

            fmt_ls.append(f"{field[1:]}={field_value!r}")

        fmt_str = ", ".join(fmt_ls)
        return f"{self.__class__.__name__}({fmt_str})"


class ABCConfigPool(ABCSLProcessorPool):
    """
    配置池抽象类
    """

    @abstractmethod
    def get(self, namespace: str, file_name: Optional[str] = None) -> dict[str, ABCConfigFile] | ABCConfigFile | None:
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
    def set(self, namespace: str, file_name: str, config: ABCConfigFile) -> None:
        """
        设置配置

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config: 配置
        :type config: ABCConfigFile
        """

    @abstractmethod
    def save(
            self,
            namespace: str,
            file_name: str,
            config_formats: Optional[str | Iterable[str]] = None,
            config: Optional[ABCConfigFile] = None,
            *args, **kwargs
    ) -> None:
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

        .. versionchanged:: 0.1.2
           添加 ``config_formats`` 和 ``config`` 参数
        """

    @abstractmethod
    def save_all(self, ignore_err: bool = False) -> None | dict[str, dict[str, tuple[ABCConfigFile, Exception]]]:
        """
        保存所有配置

        :param ignore_err: 是否忽略保存导致的错误
        :type ignore_err: bool

        :return: ignore_err为True时返回{Namespace: {FileName: (ConfigObj, Exception)}}，否则返回None
        :rtype: None | dict[str, dict[str, tuple[ABCConfigFile, Exception]]]
        """

    @abstractmethod
    def load(
            self,
            namespace: str,
            file_name: str,
            *args,
            config_formats: Optional[str | Iterable[str]] = None,
            allow_create: bool = False,
            **kwargs
    ) -> ABCConfigFile:
        """
        加载配置

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config_formats: 配置格式
        :type config_formats: Optional[str | Iterable[str]]
        :param allow_create: 是否允许创建配置文件
        :type allow_create: bool

        :return: 配置对象
        :rtype: ABCConfigFile

        .. versionchanged:: 0.1.6
           现在会像 :py:meth:`save` 一样接收并传递额外参数
           移除 ``config_file_cls`` 参数

        """

    @abstractmethod
    def delete(self, namespace: str, file_name: str) -> None:
        """
        删除配置文件

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        """

    @abstractmethod
    def require(
            self,
            namespace: str,
            file_name: str,
            validator: Any,
            validator_factory: Any,
            static_config: Optional[Any] = None,
            **kwargs,
    ):
        """
        获取配置

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param validator: 详见 :py:class:`RequiredPath`
        :param validator_factory: 详见 :py:class:`RequiredPath`
        :param static_config: 详见 :py:class:`RequiredPath`

        :param kwargs: 详见 :py:class:`RequireConfigDecorator`

        :return: 详见 :py:class:`RequireConfigDecorator`
        :rtype: :py:class:`RequireConfigDecorator`
        """


type SLArgument = Optional[Sequence | Mapping | tuple[Sequence, Mapping[str, Any]]]


class ABCConfigSL(ABC):
    """
    配置SaveLoad处理器抽象类

    .. versionchanged:: 0.1.6
       移动 ``保存加载器参数`` 相关至 :py:class:`BaseLocalFileConfigSL`
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
    def supported_file_classes(self) -> list[type[ABCConfigFile]]:
        """
        :return: 支持的配置文件类

        .. versionadded:: 0.1.6
        """

    @property
    def reg_alias(self) -> Optional[str]:
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
    def file_match(self) -> tuple[str | Pattern, ...]:
        """
        :return: 支持的文件名匹配

        .. versionchanged:: 0.1.6
           从 ``file_ext`` 重命名为 ``file_match``
        """

    def register_to(self, config_pool: ABCSLProcessorPool) -> None:
        """
        注册到配置池中

        :param config_pool: 配置池
        :type config_pool: ABCSLProcessorPool
        """

        config_pool.SLProcessors[self.reg_name] = self
        for match in self.file_match:
            if match not in config_pool.FileNameProcessors:
                config_pool.FileNameProcessors[match] = {self.reg_name}
                continue
            config_pool.FileNameProcessors[match].add(self.reg_name)

    @abstractmethod
    def save(
            self,
            processor_pool: ABCSLProcessorPool,
            config_file: ABCConfigFile,
            root_path: str,
            namespace: str,
            file_name: str,
            *args,
            **kwargs,
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

        .. versionchanged:: 0.1.6
           添加参数 ``processor_pool``
        """

    @abstractmethod
    def load(
            self,
            processor_pool: ABCSLProcessorPool,
            root_path: str,
            namespace: str,
            file_name: str,
            *args,
            **kwargs
    ) -> ABCConfigFile:
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

        .. versionchanged:: 0.1.6
           移除 ``config_file_cls`` 参数

           添加参数 ``processor_pool``
        """

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented  # pragma: no cover

        processor_reg_name = self.processor_reg_name == other.processor_reg_name
        reg_alias = self.reg_alias == other.reg_alias
        file_match_eq = self.file_match == other.file_match

        return all((
            processor_reg_name,
            reg_alias,
            file_match_eq,
        ))

    def __hash__(self):
        return hash((
            self.processor_reg_name,
            self.reg_alias,
            self.file_match,
        ))


__all__ = (
    "ABCKey",
    "ABCPath",
    "ABCConfigData",
    "ABCSupportsIndexConfigData",
    "ABCSLProcessorPool",
    "ABCConfigPool",
    "ABCConfigFile",
    "SLArgument",
    "ABCConfigSL",
)
