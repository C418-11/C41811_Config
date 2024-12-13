# -*- coding: utf-8 -*-
# cython: language_level = 3


from abc import ABC
from abc import abstractmethod
from collections import OrderedDict
from collections.abc import Mapping
from copy import deepcopy
from typing import Any
from typing import Generator
from typing import ItemsView
from typing import Iterable
from typing import KeysView
from typing import MutableMapping
from typing import Optional
from typing import Self
from typing import Sequence
from typing import TypeAlias
from typing import ValuesView

from pydantic_core import core_schema
from pyrsistent import PMap
from pyrsistent import pmap


class ABCKey(ABC):
    """
    用于获取配置的键
    """

    def __init__(self, key: Any):
        self._key = deepcopy(key)

    @property
    def key(self):
        return deepcopy(self._key)

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


class ABCConfigData[D: Mapping | MutableMapping](ABC, Mapping):
    """
    配置数据
    """

    def __init__(self, data: Optional[D] = None):
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

    @classmethod
    def from_data(cls, data: D) -> Self:
        """
        提供创建同类型配置数据的快捷方式

        :param data: 配置的原始数据
        :type data: Mapping | MutableMapping
        :return: 新的配置数据
        :rtype: Self
        """
        return cls(data)

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

    @read_only.setter
    def read_only(self, value: Any):
        if self._data_read_only:
            raise TypeError("ConfigData is read-only")
        self._read_only = bool(value)

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

        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredPathNotFoundError: 需求的键不存在
        """

    @abstractmethod
    def exists(self, path: str | ABCPath) -> bool:
        """
        判断路径是否存在

        :param path: 路径
        :type path: str | ABCPath

        :return: 路径是否存在
        :rtype: bool

        :raise ConfigDataTypeError: 配置数据类型错误
        """

    @abstractmethod
    def get(self, path: str | ABCPath, default=None, *, get_raw: bool = False) -> Any:
        """
        获取路径的值

        :param path: 路径
        :type path: str | ABCPath

        :param default: 默认值
        :type default: Any
        :param get_raw: 是否获取原始值
        :type get_raw: bool

        :return: 路径的值
        :rtype: Any

        :raise ConfigDataTypeError: 配置数据类型错误
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

    def values(self, get_raw: bool = False) -> ValuesView[Any]:
        """
        获取所有值

        :param get_raw: 是否获取原始数据
        :type get_raw: bool

        :return: 所有键值对
        :rtype: ValuesView[Any]
        """
        if get_raw:
            return self._data.values()

        return OrderedDict(
            (k, self.from_data(v) if isinstance(v, Mapping) else deepcopy(v)) for k, v in self._data.items()
        ).values()

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
        return OrderedDict(
            (deepcopy(k), self.from_data(v) if isinstance(v, Mapping) else deepcopy(v)) for k, v in self._data.items()
        ).items()

    def __getitem__(self, key):
        return self.from_data(self._data[key]) if isinstance(self._data[key], Mapping) else deepcopy(self._data[key])

    def __setitem__(self, key, value) -> None:
        self._data[key] = value

    def __delitem__(self, key) -> None:
        del self._data[key]

    def __contains__(self, key) -> bool:
        return key in self._data

    def __len__(self):
        return len(self._data)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._data == other._data

    def __getattr__(self, item) -> Self | Any:
        try:
            item_obj = self._data[item]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")
        return self.from_data(item_obj) if isinstance(item_obj, Mapping) else item_obj

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
        return self.from_data(self._data)

    @staticmethod
    def __get_pydantic_core_schema__() -> core_schema.DictSchema:  # pragma: no cover
        return core_schema.dict_schema(
            keys_schema=core_schema.any_schema(),
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
            config_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: Optional[str] = None,
            *processor_args,
            **processor_kwargs
    ) -> None:
        """
        保存配置到文件系统

        :param config_pool: 配置池
        :type config_pool: ABCSLProcessorPool
        :param namespace: 文件命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
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
    配置池
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

        :return: None
        :rtype: NoneType
        """

    @abstractmethod
    def save(self, namespace: str, file_name: str, *args, **kwargs) -> None:
        """
        保存配置

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str

        :return: None
        :rtype: NoneType
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
    def load[F: ABCConfigFile](
            self,
            namespace: str,
            file_name: str,
            *,
            config_file_cls: type[F],
            config_formats: Optional[str | Iterable[str]] = None,
            allow_create: bool = False,
    ) -> F:
        """
        加载配置

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param config_file_cls: 配置文件类
        :type config_file_cls: type[ABCConfigFile]
        :param config_formats: 配置格式
        :type config_formats: Optional[str | Iterable[str]]
        :param allow_create: 是否允许创建配置文件
        :type allow_create: bool

        :return: 配置对象
        :rtype: ABCConfigFile
        """

    @abstractmethod
    def delete(self, namespace: str, file_name: str) -> None:
        """
        删除配置文件

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str

        :return: None
        :rtype: NoneType
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


SLArgument: TypeAlias = Optional[Sequence | Mapping | tuple[Sequence, Mapping[str, Any]]]


class ABCConfigSL(ABC):
    """
    配置SaveLoad处理器抽象类
    """

    def __init__(
            self,
            s_arg: SLArgument = None,
            l_arg: SLArgument = None,
            *,
            reg_alias: Optional[str] = None,
    ):
        """
        :param s_arg: 保存器默认参数
        :type s_arg: Optional[Sequence | Mapping | tuple[Sequence, Mapping[str, Any]]]
        :param l_arg: 加载器默认参数
        :type l_arg: Optional[Sequence | Mapping | tuple[Sequence, Mapping[str, Any]]]
        :param reg_alias: sl处理器注册别名
        :type reg_alias: Optional[str]
        """

        def _build_arg(value: SLArgument) -> tuple[tuple, PMap[str, Any]]:
            if value is None:
                return (), pmap()
            if isinstance(value, Sequence):
                return tuple(value), pmap()
            if isinstance(value, Mapping):
                return (), pmap(value)
            raise TypeError(f"Invalid argument type, must be '{SLArgument}'")

        self._saver_args: tuple[tuple, PMap[str, Any]] = _build_arg(s_arg)
        self._loader_args: tuple[tuple, PMap[str, Any]] = _build_arg(l_arg)
        self._reg_alias: Optional[str] = reg_alias

    @property
    def saver_args(self) -> tuple[tuple, PMap[str, Any]]:
        """
        :return: 保存器默认参数
        """
        return self._saver_args

    @property
    def loader_args(self) -> tuple[tuple, PMap[str, Any]]:
        """
        :return: 加载器默认参数
        """
        return self._loader_args

    @property
    @abstractmethod
    def processor_reg_name(self) -> str:
        """
        :return: SL处理器的默认注册名
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
    def file_ext(self) -> tuple[str, ...]:
        """
        :return: 支持的文件扩展名
        """

    def register_to(self, config_pool: ABCSLProcessorPool) -> None:
        """
        注册到配置池中

        :param config_pool: 配置池
        :type config_pool: ABCSLProcessorPool
        """

        config_pool.SLProcessor[self.reg_name] = self
        for ext in self.file_ext:
            if ext not in config_pool.FileExtProcessor:
                config_pool.FileExtProcessor[ext] = {self.reg_name}
                continue
            config_pool.FileExtProcessor[ext].add(self.reg_name)

    @abstractmethod
    def save(
            self,
            config_file: ABCConfigFile,
            root_path: str,
            namespace: str,
            file_name: str,
            *args,
            **kwargs
    ) -> None:
        """
        保存处理器

        :param config_file: 待保存配置
        :type config_file: ABCConfigFile
        :param root_path: 保存的根目录
        :type root_path: str
        :param namespace: 配置的命名空间
        :type namespace: str
        :param file_name: 配置文件名
        :type file_name: str

        :return: None
        :rtype: NoneType

        :raise FailedProcessConfigFileError: 处理配置文件失败
        """

    @abstractmethod
    def load[C: ABCConfigFile](
            self,
            config_file_cls: type[C],
            root_path: str,
            namespace: str,
            file_name: str,
            *args,
            **kwargs
    ) -> C:
        """
        加载处理器

        :param config_file_cls: 配置文件类
        :type config_file_cls: type[C]
        :param root_path: 保存的根目录
        :type root_path: str
        :param namespace: 配置的命名空间
        :type namespace: str
        :param file_name: 配置文件名
        :type file_name: str

        :return: 配置对象
        :rtype: ABCConfigFile

        :raise FailedProcessConfigFileError: 处理配置文件失败
        """

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        processor_reg_name = self.processor_reg_name == other.processor_reg_name
        reg_alias = self.reg_alias == other.reg_alias
        file_ext_eq = self.file_ext == other.file_ext
        saver_args_eq = self._saver_args == other._saver_args
        loader_args_eq = self._loader_args == other._loader_args

        return all((
            processor_reg_name,
            reg_alias,
            file_ext_eq,
            saver_args_eq,
            loader_args_eq
        ))

    def __hash__(self):
        return hash((
            self.processor_reg_name,
            self.reg_alias,
            self.file_ext,
            self._saver_args,
            self._loader_args
        ))


__all__ = (
    "ABCKey",
    "ABCPath",
    "ABCConfigData",
    "ABCSLProcessorPool",
    "ABCConfigPool",
    "ABCConfigFile",
    "SLArgument",
    "ABCConfigSL",
)
