# -*- coding: utf-8 -*-
# cython: language_level = 3


import os
from abc import ABC
from abc import abstractmethod
from collections import OrderedDict
from collections.abc import Mapping
from copy import deepcopy
from typing import Any
from typing import ItemsView
from typing import KeysView
from typing import MutableMapping
from typing import Optional
from typing import Self
from typing import Sequence
from typing import TypeVar

from pydantic_core import core_schema

D = TypeVar('D', Mapping, MutableMapping)


class ABCConfigData(ABC, Mapping):
    """
    配置数据
    """

    def __init__(self, data: Optional[D] = None, sep_char: str = '.'):
        """
        data为None时，默认为空字典

        如果data不继承自MutableMapping，则该配置数据被设为只读

        :param data: 配置的原始数据
        :type data: Mapping | MutableMapping
        """

        if data is None:
            data = {}
        self._data: D = deepcopy(data)
        self._data_read_only: bool = not isinstance(data, MutableMapping)
        self._read_only: bool = self._data_read_only

        self._sep_char: str = sep_char

    def new_data(self, data: D) -> Self:
        """
        初始化同类型同格式配置数据的快捷方式

        :param data: 配置的原始数据
        :type data: Mapping | MutableMapping
        :return: 新的配置数据
        :rtype: Self
        """
        return type(self)(data, self._sep_char)

    @property
    def data(self) -> D:
        """
        配置的原始数据*快照*

        :return: 配置的原始数据*快照*
        :rtype: Mapping | MutableMapping
        """
        return deepcopy(self._data)

    @property
    def read_only(self) -> bool:
        """
        配置数据是否为只读

        :return: 配置数据是否为只读
        :rtype: bool
        """
        return self._data_read_only or self._read_only

    @property
    def sep_char(self) -> str:
        """
        配置数据键的分隔符

        :return: 分隔符
        :rtype: str
        """
        return self._sep_char

    @read_only.setter
    def read_only(self, value: Any):
        if self._data_read_only:
            raise TypeError("ConfigData is read-only")
        self._read_only = bool(value)

    @abstractmethod
    def getPathValue(self, path: str, *, get_raw: bool = False) -> Any:
        """
        获取路径的值的*快照*

        :param path: 路径
        :type path: str
        :param get_raw: 是否获取原始值，为False时，会将Mapping转换为当前类
        :type get_raw: bool

        :return: 路径的值
        :rtype: Any

        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredKeyNotFoundError: 需求的键不存在
        """

    @abstractmethod
    def setPathValue(self, path: str, value: Any, *, allow_create: bool = True) -> Self:
        """
        设置路径的值

        .. caution::
           value参数未默认做深拷贝，可能导致非预期的行为

        .. attention::
           allow_create时，使用与self.data一样的类型新建路径

        :param path: 路径
        :type path: str
        :param value: 值
        :type value: Any
        :param allow_create: 是否允许创建不存在的路径，默认为True
        :type allow_create: bool

        :return: 返回当前实例便于链式调用
        :rtype: Self

        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredKeyNotFoundError: 需求的键不存在
        """

    @abstractmethod
    def deletePath(self, path: str) -> Self:
        """
        删除路径

        :param path: 路径
        :type path: str

        :return: 返回当前实例便于链式调用
        :rtype: Self

        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredKeyNotFoundError: 需求的键不存在
        """

    @abstractmethod
    def hasPath(self, path: str) -> bool:
        """
        判断路径是否存在

        :param path: 路径
        :type path: str

        :return: 路径是否存在
        :rtype: bool

        :raise ConfigDataTypeError: 配置数据类型错误
        """

    @abstractmethod
    def get(self, path: str, default=None, *, get_raw: bool = False) -> Any:
        """
        获取路径的值

        :param path: 路径
        :type path: str

        :param default: 默认值
        :type default: Any
        :param get_raw: 是否获取原始值
        :type get_raw: bool

        :return: 路径的值
        :rtype: Any

        :raise ConfigDataTypeError: 配置数据类型错误
        """

    @abstractmethod
    def set_default(self, path: str, default=None, *, get_raw: bool = False) -> Any:
        """
        如果路径不在配置数据中则填充默认值到配置数据并返回

        :param path: 路径
        :type path: str
        :param default: 默认值
        :type default: Any
        :param get_raw: 是否获取原始值
        :type get_raw: bool

        :return: 路径的值
        :rtype: Any

        :raise ConfigDataTypeError: 配置数据类型错误
        """

    def keys(self, *, recursive: bool = False, end_point_only: bool = False) -> KeysView[str]:
        """
        获取所有键

        :param recursive: 是否递归获取
        :type recursive: bool
        :param end_point_only: 是否只获取叶子节点
        :type end_point_only: bool

        :return: 所有键
        :rtype: KeysView[str]
        """

        if not any((
                recursive,
                end_point_only,
        )):
            return self._data.keys()

        def _recursive(data: Mapping) -> OrderedDict:
            ordered_keys = OrderedDict()
            for k, v in data.items():
                if isinstance(v, Mapping):
                    ordered_keys.update((f"{k}{self.sep_char}{x}", None) for x in _recursive(v))
                    if end_point_only:
                        continue
                ordered_keys[k] = None
            return ordered_keys

        if recursive:
            keys = _recursive(self._data)
            return keys.keys()

        if end_point_only:
            keys = OrderedDict.fromkeys(
                k for k, v in self._data.items() if not isinstance(v, Mapping))
            return keys.keys()

    def values(self):
        copied_values = [deepcopy(x) for x in self._data.values()]
        return [(self.new_data(x) if isinstance(x, Mapping) else x) for x in copied_values]

    def items(self, *, get_raw: bool = False) -> ItemsView[str, Any]:
        """
        获取所有键值对

        :param get_raw: 是否获取原始数据
        :type get_raw: bool

        :return: 所有键值对
        :rtype: ItemsView[str, Any]
        """
        if get_raw:
            return self._data.items()
        copied_items = [(deepcopy(k), deepcopy(v)) for k, v in self._data.items()]
        return OrderedDict((k, (self.new_data(v) if isinstance(v, Mapping) else v)) for k, v in copied_items).items()

    def __getitem__(self, key):
        """
        getPathValue的快捷方式
        """
        return self.getPathValue(key)

    def __setitem__(self, key, value) -> None:
        """
        setPathValue的快捷方式
        """
        self.setPathValue(key, value)

    def __delitem__(self, key) -> None:
        """
        deletePath的快捷方式
        """
        self.deletePath(key)

    def __contains__(self, key) -> bool:
        """
        hasPath的快捷方式
        """
        return self.hasPath(key)

    def __len__(self):
        return len(self._data)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._data == other._data

    def __getattr__(self, item) -> Self | Any:
        item_obj = self._data[item]
        return self.new_data(item_obj) if isinstance(item_obj, Mapping) else item_obj

    def __iter__(self):
        return iter(self._data)

    def __str__(self) -> str:
        return str(self._data)

    def __repr__(self) -> str:
        data_repr = f"{self._data!r}"
        if type(self) is dict:
            data_repr = data_repr[1:-1]

        return f"{self.__class__.__name__}({data_repr})"

    def __deepcopy__(self, memo) -> Self:
        return self.new_data(self._data)

    @staticmethod
    def __get_pydantic_core_schema__() -> core_schema.DictSchema:
        return core_schema.dict_schema(
            keys_schema=core_schema.str_schema(),
            values_schema=core_schema.any_schema()
        )


class ABCSLProcessorPool(ABC):
    """
    SL处理器池
    """

    def __init__(self, root_path: str = "./.config"):
        self.SLProcessor: dict[str, ABCConfigSL] = {}  # SaveLoadProcessor {RegName: Processor}
        self.FileExtProcessor: dict[str, set[str]] = {}  # {FileExt: {RegName}}
        self._root_path = root_path

    @property
    def root_path(self) -> str:
        return self._root_path


class ABCConfig(ABC):
    """
    配置文件类
    """

    def __init__(
            self,
            config_data: ABCConfigData,
            *,
            namespace: Optional[str] = None,
            file_name: Optional[str] = None,
            config_format: Optional[str] = None
    ) -> None:
        """
        :param config_data: 配置数据
        :type config_data: ABCConfigData
        :param namespace: 文件命名空间
        :type namespace: Optional[str]
        :param file_name: 文件名
        :type file_name: Optional[str]
        :param config_format: 配置文件的格式
        :type config_format: Optional[str]
        """

        self._data: ABCConfigData = config_data

        self._namespace: str | None = namespace
        self._file_name: str | None = file_name
        self._config_format: str | None = config_format

    @property
    def data(self) -> ABCConfigData:
        return self._data

    @property
    def namespace(self) -> str | None:
        return self._namespace

    @property
    def file_name(self) -> str | None:
        return self._file_name

    @property
    def config_format(self) -> str | None:
        return self._config_format

    @abstractmethod
    def save(
            self,
            config_pool: ABCSLProcessorPool,
            namespace: str | None = None,
            file_name: str | None = None,
            config_format: str | None = None,
            *processor_args,
            **processor_kwargs
    ) -> None:
        """
        保存配置到文件系统

        :param config_pool: 配置池
        :type config_pool: ABCSLProcessorPool
        :param namespace: 文件命名空间
        :type namespace: Optional[str]
        :param file_name: 文件名
        :type file_name: Optional[str]
        :param config_format: 配置文件的格式
        :type config_format: Optional[str]

        :raise UnsupportedConfigFormatError: 不支持的配置格式
        """

    @classmethod
    @abstractmethod
    def load(
            cls,
            config_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: str,
            *processor_args,
            **processor_kwargs
    ) -> Self:
        """
        从文件系统加载配置

        :param config_pool: 配置池
        :type config_pool: ABCSLProcessorPool
        :param namespace: 文件命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config_format: 配置文件的格式
        :type config_format: str

        :return: 配置对象
        :rtype: Self

        :raise UnsupportedConfigFormatError: 不支持的配置格式
        """

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        for field in ["_config_format", "_data", "_namespace", "_file_name"]:
            if getattr(self, field) != getattr(other, field):
                return False
        return True

    def __repr__(self):
        fmt_ls: list[str] = []
        for field in ["_config_format", "_data", "_namespace", "_file_name"]:
            field_value = getattr(self, field)
            if field_value is None:
                continue

            fmt_ls.append(f"{field[1:]}={field_value!r}")

        fmt_str = ", ".join(fmt_ls)
        return f"{self.__class__.__name__}({fmt_str})"


class ABCConfigPool(ABCSLProcessorPool):
    """
    配置池
    """

    @abstractmethod
    def get(self, namespace: str, file_name: Optional[str] = None) -> dict[str, ABCConfig] | ABCConfig | None:
        """
        获取配置

        如果配置不存在则返回None

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: Optional[str]

        :return: 配置
        :rtype: dict[str, ABCConfig] | ABCConfig | None
        """

    @abstractmethod
    def set(self, namespace: str, file_name: str, config: ABCConfig) -> None:
        """
        设置配置

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config: 配置
        :type config: ABCConfig

        :return: None
        :rtype: None
        """

    @abstractmethod
    def saveAll(self, ignore_err: bool = False) -> None | dict[str, dict[str, tuple[ABCConfig, Exception]]]:
        """
        保存所有配置

        :param ignore_err: 是否忽略保存导致的错误
        :type ignore_err: bool

        :return: ignore_err为True时返回{Namespace: {FileName: (ConfigObj, Exception)}}，否则返回None
        :rtype: None | dict[str, dict[str, tuple[ABCConfig, Exception]]]
        """

    @abstractmethod
    def requireConfig(
            self,
            namespace: str,
            file_name: str,
            required: list[str] | dict[str, Any],
            *args,
            **kwargs,
    ):
        """
        获取配置

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param required: 必须的配置
        :type required: list[str] | dict[str, Any]
        :param args: 详见 :py:func:`RequireConfigDecorator`
        :param kwargs: 详见 :py:func:`RequireConfigDecorator`

        :return: 详见 :py:class:`RequireConfigDecorator`
        :rtype: :py:class:`RequireConfigDecorator`
        """


SLArgument = Sequence | Mapping | tuple[Sequence, Mapping[str, Any]]
C = TypeVar("C", bound=ABCConfig)


class ABCConfigSL(ABC):
    """
    配置文件SaveLoad管理器抽象类
    """

    def __init__(
            self,
            s_arg: SLArgument = None,
            l_arg: SLArgument = None,
            *,
            create_dir: bool = True,
    ):
        """
        :param s_arg: 保存器默认参数
        :type s_arg: Sequence | Mapping | tuple[Sequence, Mapping[str, Any]]
        :param l_arg: 加载器默认参数
        :type l_arg: Sequence | Mapping | tuple[Sequence, Mapping[str, Any]]
        :param create_dir: 是否允许创建目录
        :type create_dir: bool
        """

        def _build_arg(value: SLArgument) -> tuple[list, dict[str, Any]]:
            if value is None:
                return [], {}
            if isinstance(value, Sequence):
                return list(value), {}
            if isinstance(value, Mapping):
                return [], dict(value)
            raise TypeError(f"Invalid argument type, must be '{SLArgument}'")

        self.save_arg: tuple[list, dict[str, Any]] = _build_arg(s_arg)
        self.load_arg: tuple[list, dict[str, Any]] = _build_arg(l_arg)

        self.create_dir = create_dir

    @property
    @abstractmethod
    def regName(self) -> str:
        """
        :return: SL处理器的注册名
        """

    @property
    @abstractmethod
    def fileExt(self) -> list[str]:
        """
        :return: 支持的文件扩展名
        """

    def registerTo(self, config_pool: ABCSLProcessorPool) -> None:
        """
        注册到配置池中

        :param config_pool: 配置池
        :type config_pool: ABCSLProcessorPool
        """

        config_pool.SLProcessor[self.regName] = self
        for ext in self.fileExt:
            if ext not in config_pool.FileExtProcessor:
                config_pool.FileExtProcessor[ext] = {self.regName}
                continue
            config_pool.FileExtProcessor[ext].add(self.regName)

    @abstractmethod
    def save(
            self,
            config: ABCConfig,
            root_path: str,
            namespace: Optional[str],
            file_name: Optional[str],
            *args,
            **kwargs
    ) -> None:
        """
        保存处理器

        :param config: 待保存配置
        :type config: ABCConfig
        :param root_path: 保存的根目录
        :type root_path: str
        :param namespace: 配置的命名空间
        :type namespace: Optional[str]
        :param file_name: 配置文件名
        :type file_name: Optional[str]

        :return: None
        :rtype: None

        :raise FailedProcessConfigFileError: 处理配置文件失败
        """

    @abstractmethod
    def load(
            self,
            config_cls: type[C],
            root_path: str,
            namespace: Optional[str],
            file_name: Optional[str],
            *args,
            **kwargs
    ) -> C:
        """
        加载处理器

        :param config_cls: 配置类
        :type config_cls: type[C]
        :param root_path: 保存的根目录
        :type root_path: str
        :param namespace: 配置的命名空间
        :type namespace: Optional[str]
        :param file_name: 配置文件名
        :type file_name: Optional[str]

        :return: 配置对象
        :rtype: C

        :raise FailedProcessConfigFileError: 处理配置文件失败
        """

    @staticmethod
    def _norm_join(*paths: str) -> str:
        return os.path.normpath(os.path.join(*paths))

    def _getFilePath(
            self,
            config: ABCConfig,
            root_path: str,
            namespace: Optional[str] = None,
            file_name: Optional[str] = None,
    ) -> str:
        """
        获取配置文件对应的文件路径(提供给子类的便捷方法)

        :param config: 配置对象
        :type config: ABCConfig
        :param root_path: 保存的根目录
        :type root_path: str
        :param namespace: 配置的命名空间
        :type namespace: Optional[str]
        :param file_name: 配置文件名
        :type file_name: Optional[str]

        :return: 配置文件路径
        :rtype: str

        :raise ValueError: 当 namespace 和 file_name (即便尝试从config读值)都为 None 时
        """
        if namespace is None:
            namespace = config.namespace
        if file_name is None:
            file_name = config.file_name

        if namespace is None or file_name is None:
            raise ValueError("namespace and file_name can't be None")

        full_path = self._norm_join(root_path, namespace, file_name)
        if self.create_dir:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

        return full_path


__all__ = (
    "ABCConfigData",
    "ABCSLProcessorPool",
    "ABCConfigPool",
    "ABCConfig",
    "ABCConfigSL",
)
