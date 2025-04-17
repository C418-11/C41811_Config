# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

from abc import ABC
from collections import OrderedDict
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence
from contextlib import suppress
from copy import deepcopy
from re import Pattern
from types import NotImplementedType
from typing import Any
from typing import ClassVar
from typing import Literal
from typing import Optional
from typing import Self
from typing import cast
from typing import overload
from typing import override

from .utils import check_read_only
from .utils import fmt_path
from .._protocols import Indexed
from ..abc import ABCConfigData
from ..abc import ABCConfigFile
from ..abc import ABCConfigPool
from ..abc import ABCIndexedConfigData
from ..abc import ABCPath
from ..abc import ABCProcessorHelper
from ..abc import ABCSLProcessorPool
from ..abc import AnyKey
from ..abc import PathLike
from ..errors import ConfigDataReadOnlyError
from ..errors import ConfigDataTypeError
from ..errors import ConfigOperate
from ..errors import FailedProcessConfigFileError
from ..errors import KeyInfo
from ..errors import RequiredPathNotFoundError
from ..errors import UnsupportedConfigFormatError


class BasicConfigData[D](ABCConfigData[D], ABC):
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

    @property
    @override
    def read_only(self) -> bool | None:
        return super().read_only or self._read_only

    @read_only.setter
    @override
    def read_only(self, value: Any) -> None:
        if self.data_read_only:
            raise ConfigDataReadOnlyError
        self._read_only = bool(value)


class BasicSingleConfigData[D](BasicConfigData[D], ABC):
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

    def __eq__(self, other: Any) -> bool | NotImplementedType:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._data == other._data

    def __str__(self) -> str:
        return str(self._data)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._data!r})"

    def __deepcopy__(self, memo: dict[str, Any]) -> Self:
        return self.from_data(self._data)


class BasicIndexedConfigData[D: Indexed[Any, Any]](
    BasicSingleConfigData[D],
    ABCIndexedConfigData[D],
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
            path: ABCPath[Any],
            path_checker: Callable[[Any, AnyKey, ABCPath[Any], int], Any],
            process_return: Callable[[Any], Any]
    ) -> Any:
        # noinspection GrazieInspection
        """
        处理键路径的通用函数

        :param path: 键路径
        :type path: ABCPath
        :param path_checker: 检查并处理每个路径段，返回值非None时结束操作并返回值
        :type path_checker: Callable[(current_data: Any, current_key: ABCKey, last_path: list[ABCKey], path_index: int),
                            Any]
        :param process_return: 处理最终结果，该函数返回值会被直接返回
        :type process_return: Callable[(current_data: Any), Any]

        :return: 处理结果
        :rtype: Any

        .. versionchanged:: 0.2.0
           重命名参数 ``process_check`` 为 ``path_checker``
        """
        current_data = self._data

        for key_index, current_key in enumerate(path):
            last_path: ABCPath[Any] = path[key_index + 1:]

            check_result = path_checker(current_data, current_key, last_path, key_index)
            if check_result is not None:
                return check_result

            current_data = current_key.__get_inner_element__(current_data)

        return process_return(current_data)

    @override
    def retrieve(self, path: PathLike, *, return_raw_value: bool = False) -> Any:
        path = fmt_path(path)

        def checker(current_data: Any, current_key: AnyKey, _last_path: ABCPath[Any], key_index: int) -> None:
            missing_protocol = current_key.__supports__(current_data)
            if missing_protocol:
                raise ConfigDataTypeError(
                    KeyInfo(cast(ABCPath[Any], path), current_key, key_index), missing_protocol, type(current_data)
                )
            if not current_key.__contains_inner_element__(current_data):
                raise RequiredPathNotFoundError(
                    KeyInfo(cast(ABCPath[Any], path), current_key, key_index), ConfigOperate.Read
                )

        def process_return[V: Any](current_data: V) -> V | ConfigData:
            if return_raw_value:
                return deepcopy(current_data)

            is_sequence = isinstance(current_data, Sequence) and not isinstance(current_data, (str, bytes))
            if isinstance(current_data, Mapping) or is_sequence:
                return ConfigData(current_data)

            return deepcopy(current_data)

        return self._process_path(path, checker, process_return)

    @override
    @check_read_only
    def modify(self, path: PathLike, value: Any, *, allow_create: bool = True) -> Self:
        path = fmt_path(path)

        def checker(current_data: Any, current_key: AnyKey, last_path: ABCPath[Any], key_index: int) -> None:
            missing_protocol = current_key.__supports_modify__(current_data)
            if missing_protocol:
                raise ConfigDataTypeError(
                    KeyInfo(cast(ABCPath[Any], path), current_key, key_index), missing_protocol, type(current_data)
                )
            if not current_key.__contains_inner_element__(current_data):
                if not allow_create:
                    raise RequiredPathNotFoundError(
                        KeyInfo(cast(ABCPath[Any], path), current_key, key_index), ConfigOperate.Write
                    )
                current_key.__set_inner_element__(current_data, type(self._data)())

            if not last_path:
                current_key.__set_inner_element__(current_data, value)

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    @check_read_only
    def delete(self, path: PathLike) -> Self:
        path = fmt_path(path)

        def checker(
                current_data: Any,
                current_key: AnyKey,
                last_path: ABCPath[Any],
                key_index: int,
        ) -> Literal[True] | None:
            missing_protocol = current_key.__supports_modify__(current_data)
            if missing_protocol:
                raise ConfigDataTypeError(
                    KeyInfo(cast(ABCPath[Any], path), current_key, key_index), missing_protocol, type(current_data)
                )
            if not current_key.__contains_inner_element__(current_data):
                raise RequiredPathNotFoundError(
                    KeyInfo(cast(ABCPath[Any], path), current_key, key_index), ConfigOperate.Delete
                )

            if not last_path:
                current_key.__delete_inner_element__(current_data)
                return True
            return None  # 被mypy强制要求

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    def unset(self, path: PathLike) -> Self:
        with suppress(RequiredPathNotFoundError):
            self.delete(path)
        return self

    @override
    def exists(self, path: PathLike, *, ignore_wrong_type: bool = False) -> bool:
        path = fmt_path(path)

        def checker(current_data: Any, current_key: AnyKey, _last_path: ABCPath[Any],
                    key_index: int) -> bool | None:
            missing_protocol = current_key.__supports__(current_data)
            if missing_protocol:
                if ignore_wrong_type:
                    return False
                raise ConfigDataTypeError(
                    KeyInfo(cast(ABCPath[Any], path), current_key, key_index), missing_protocol, type(current_data)
                )
            if not current_key.__contains_inner_element__(current_data):
                return False
            return None

        return cast(bool, self._process_path(path, checker, lambda *_: True))

    @override
    def get(self, path: PathLike, default: Optional[Any] = None, *, return_raw_value: bool = False) -> Any:
        try:
            return self.retrieve(path, return_raw_value=return_raw_value)
        except RequiredPathNotFoundError:
            return default

    @override
    def setdefault(self, path: PathLike, default: Optional[Any] = None, *, return_raw_value: bool = False) -> Any:
        try:
            return self.retrieve(path)
        except RequiredPathNotFoundError:
            self.modify(path, default)
            return default

    @override
    def __contains__(self, key: Any) -> bool:
        return key in self._data  # type: ignore[operator]

    @override
    def __iter__(self) -> Iterator[D]:
        return iter(self._data)

    @override
    def __len__(self) -> int:
        return len(self._data)  # type: ignore[arg-type]

    @override
    def __getitem__(self, index: Any) -> Any:
        data = self._data[index]
        is_sequence = isinstance(data, Sequence) and not isinstance(data, (str, bytes))
        if isinstance(data, Mapping) or is_sequence:
            return cast(Self, ConfigData(data))
        return cast(D, deepcopy(data))

    @override
    def __setitem__(self, index: Any, value: Any) -> None:
        self._data[index] = value  # type: ignore[index]

    @override
    def __delitem__(self, index: Any) -> None:
        del self._data[index]  # type: ignore[attr-defined]


class ConfigData(ABC):
    """
    配置数据类

    .. versionchanged:: 0.1.5
       会自动根据传入的配置数据类型选择对应的子类
    """
    TYPES: ClassVar[OrderedDict[tuple[type, ...], Callable[[Any], Any] | type]]
    """
    存储配置数据类型对应的子类

    .. versionchanged:: 0.2.0
       现在使用 ``OrderedDict`` 来保证顺序
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        if not args:
            args = (None,)
        for types, config_data_cls in cls.TYPES.items():
            if not isinstance(args[0], types):
                continue
            return config_data_cls(*args, **kwargs)
        raise TypeError(f"Unsupported type: {args[0]}")


class ConfigFile[D: ABCConfigData[Any]](ABCConfigFile[D]):
    """
    配置文件类
    """

    def __init__(
            self,
            initial_config: D | Any,
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

        super().__init__(cast(D, ConfigData(initial_config)), config_format=config_format)

    @override
    def save(
            self,
            processor_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: str | None = None,
            *processor_args: Any,
            **processor_kwargs: Any
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
            *processor_args: Any,
            **processor_kwargs: Any,
    ) -> Self:

        if config_format not in processor_pool.SLProcessors:
            raise UnsupportedConfigFormatError(config_format)

        return cast(
            Self,
            processor_pool.SLProcessors[config_format].load(
                processor_pool,
                processor_pool.root_path,
                namespace,
                file_name,
                *processor_args,
                **processor_kwargs),
        )

    @classmethod
    @override
    def initialize(
            cls,
            processor_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: str,
            *processor_args: Any,
            **processor_kwargs: Any,
    ) -> Self:

        if config_format not in processor_pool.SLProcessors:
            raise UnsupportedConfigFormatError(config_format)

        return cast(
            Self,
            processor_pool.SLProcessors[config_format].initialize(
                processor_pool,
                processor_pool.root_path,
                namespace,
                file_name,
                *processor_args,
                **processor_kwargs),
        )


class PHelper(ABCProcessorHelper): ...  # noqa: E701


class BasicConfigPool(ABCConfigPool, ABC):
    """
    基础配置池类

    实现了一些通用方法

    .. versionchanged:: 0.2.0
       重命名 ``BaseConfigPool`` 为 ``BasicConfigPool``
    """

    def __init__(self, root_path: str = "./.config"):
        super().__init__(root_path)
        self._configs: dict[str, dict[str, ABCConfigFile[Any]]] = {}
        self._helper = PHelper()

    @property
    def helper(self) -> ABCProcessorHelper:
        return self._helper

    # noinspection PyMethodOverriding
    @overload  # 咱也不知道为什么mypy只有这样检查会通过而pycharm会报错  # @formatter:off
    def get(self, namespace: str) -> dict[str, ABCConfigFile[Any]] | None: ...

    # noinspection PyMethodOverriding
    @overload
    def get(self, namespace: str, file_name: str) -> ABCConfigFile[Any] | None: ...

    @overload
    def get(
            self,
            namespace: str,
            file_name: Optional[str] = None,
    ) -> dict[str, ABCConfigFile[Any]] | ABCConfigFile[Any] | None: ...
    # @formatter:on

    @override
    def get(
            self,
            namespace: str,
            file_name: Optional[str] = None,
    ) -> dict[str, ABCConfigFile[Any]] | ABCConfigFile[Any] | None:
        if namespace not in self._configs:
            return None
        result = self._configs[namespace]

        if file_name is None:
            return result

        if file_name in result:
            return result[file_name]

        return None

    @override
    def set(self, namespace: str, file_name: str, config: ABCConfigFile[Any]) -> Self:
        if namespace not in self._configs:
            self._configs[namespace] = {}

        self._configs[namespace][file_name] = config
        return self

    def _get_formats(
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

        def _check_file_name(match: str | Pattern[str]) -> bool:
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

    def _try_sl_processors[R](
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

           :py:meth:`_get_formats`

        .. versionadded:: 0.1.2

        .. versionchanged:: 0.2.0
           将格式计算部分提取到单独的函数 :py:meth:`_get_formats`
        """

        def callback_wrapper(cfg_fmt: str) -> R:
            return processor(self, namespace, file_name, cfg_fmt)

        # 尝试从多个SL加载器中找到能正确加载的那一个
        errors: dict[str, FailedProcessConfigFileError[Any] | UnsupportedConfigFormatError] = {}
        for config_format in self._get_formats(file_name, config_formats, file_config_format):
            if config_format not in self.SLProcessors:
                errors[config_format] = UnsupportedConfigFormatError(config_format)
                continue
            try:
                # 能正常运行直接返回结果，不再进行尝试
                return callback_wrapper(config_format)
            except FailedProcessConfigFileError as err:
                errors[config_format] = err

        for error in errors.values():
            if isinstance(error, UnsupportedConfigFormatError):
                raise error from None

        # 如果没有一个SL加载器能正确加载，则抛出异常
        raise FailedProcessConfigFileError(errors)

    @override
    def save(
            self,
            namespace: str,
            file_name: str,
            config_formats: Optional[str | Iterable[str]] = None,
            config: Optional[ABCConfigFile[Any]] = None,
            *args: Any, **kwargs: Any,
    ) -> Self:
        if config is not None:
            self.set(namespace, file_name, config)

        file = self._configs[namespace][file_name]

        def processor(pool: Self, ns: str, fn: str, cf: str) -> None:
            file.save(pool, ns, fn, cf, *args, **kwargs)

        self._try_sl_processors(namespace, file_name, config_formats, processor, file_config_format=file.config_format)
        return self

    @override
    def save_all(self, ignore_err: bool = False) -> None | dict[str, dict[str, tuple[ABCConfigFile[Any], Exception]]]:
        errors: dict[str, dict[str, tuple[ABCConfigFile[Any], Exception]]] = {}
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
            *args: Any,
            config_formats: Optional[str | Iterable[str]] = None,
            **kwargs: Any,
    ) -> ABCConfigFile[Any]:
        def processor(pool: Self, ns: str, fn: str, cf: str) -> ABCConfigFile[Any]:
            config_file_cls: type[ABCConfigFile[Any]] = self.SLProcessors[cf].supported_file_classes[0]
            result = config_file_cls.initialize(pool, ns, fn, cf, *args, **kwargs)

            pool.set(namespace, file_name, result)
            return result

        return self._try_sl_processors(namespace, file_name, config_formats, processor)

    @override
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

           现在由 :py:meth:`ABCConfigFile.initialize` 创建新的空 :py:class:`ABCConfigFile` 对象
        """
        cache = self.get(namespace, file_name)
        if cache is not None:
            return cache

        def processor(pool: Self, ns: str, fn: str, cf: str) -> ABCConfigFile[Any]:
            config_file_cls = self.SLProcessors[cf].supported_file_classes[0]
            try:
                result = config_file_cls.load(pool, ns, fn, cf, *args, **kwargs)
            except FileNotFoundError:
                if not allow_initialize:
                    raise
                result = pool.initialize(ns, fn, *args, config_formats=cf, **kwargs)

            pool.set(namespace, file_name, result)
            return result

        return self._try_sl_processors(namespace, file_name, config_formats, processor)

    def remove(self, namespace: str, file_name: Optional[str] = None) -> Self:
        if file_name is None:
            del self._configs[namespace]
            return self

        del self._configs[namespace][file_name]
        if not self._configs[namespace]:
            del self._configs[namespace]
        return self

    def discard(self, namespace: str, file_name: Optional[str] = None) -> Self:
        with suppress(KeyError):
            self.remove(namespace, file_name)
        return self

    def __getitem__(self, item: str | tuple[str, str]) -> dict[str, ABCConfigFile[Any]] | ABCConfigFile[Any]:
        if isinstance(item, tuple):
            if len(item) != 2:
                raise ValueError(f"item must be a tuple of length 2, got {item}")
            return deepcopy(self.configs[item[0]][item[1]])
        return deepcopy(self.configs[item])

    def __contains__(self, item: Any) -> bool:
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

    def __len__(self) -> int:
        """
        配置文件总数
        """
        return sum(len(v) for v in self._configs.values())

    @property
    def configs(self) -> dict[str, dict[str, ABCConfigFile[Any]]]:
        return deepcopy(self._configs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.configs!r})"


__all__ = (
    "BasicConfigData",
    "BasicSingleConfigData",
    "BasicIndexedConfigData",
    "ConfigData",
    "ConfigFile",
    "PHelper",
    "BasicConfigPool",
)
