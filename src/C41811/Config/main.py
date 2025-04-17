# -*- coding: utf-8 -*-
# cython: language_level = 3


import os.path
import re
from abc import ABC
from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import Sequence
from contextlib import contextmanager
from copy import deepcopy
from typing import Any
from typing import Literal
from typing import Optional
from typing import cast
from typing import override

import wrapt  # type: ignore[import-untyped]
from mypy_extensions import KwArg
from mypy_extensions import VarArg
from pyrsistent import PMap
from pyrsistent import pmap

from .abc import ABCConfigData
from .abc import ABCConfigFile
from .abc import ABCConfigPool
from .abc import ABCConfigSL
from .abc import ABCSLProcessorPool
from .abc import SLArgument
from .base import BasicConfigPool
from .base import ConfigData
from .base import ConfigFile
from .errors import FailedProcessConfigFileError
from .safe_writer import safe_open
from .utils import CellType
from .validators import ComponentValidatorFactory
from .validators import DefaultValidatorFactory
from .validators import ValidatorFactoryConfig
from .validators import ValidatorTypes
from .validators import pydantic_validator

type VALIDATOR_FACTORY[V, D: ABCConfigData[Any]] = Callable[
    [V, ValidatorFactoryConfig],
    Callable[[CellType[D]], D]
]


class RequiredPath[V, D: ABCConfigData[Any]]:
    """
    对需求的键进行存在检查、类型检查、填充默认值
    """

    def __init__(
            self,
            validator: V,
            validator_factory: Optional[
                VALIDATOR_FACTORY[V, D]
                | ValidatorTypes
                | Literal["no-validation", "pydantic", "component"]
                ] = ValidatorTypes.DEFAULT,
            static_config: Optional[ValidatorFactoryConfig] = None
    ):
        """
        :param validator: 数据验证器
        :type validator: Any
        :param validator_factory: 数据验证器工厂
        :type validator_factory:
            Optional[
            Callable[
            [Any, validators.ValidatorFactoryConfig],
            Callable[[CellType[ABCConfigData]], ABCConfigData]
            ] | validators.ValidatorTypes | Literal["ignore", "pydantic", "component"]
            ]
        :param static_config: 静态配置
        :type static_config: Optional[validators.ValidatorFactoryConfig]

        .. tip::
           提供 ``static_config`` 参数，可以避免在 :py:meth:`~RequiredPath.filter` 中反复调用 ``validator_factory`` 以提高性能
           ( :py:meth:`~RequiredPath.filter` 配置一切都为默认值的前提下)
        """
        if not callable(validator_factory):
            validator_factory = ValidatorTypes(validator_factory)
        if isinstance(validator_factory, ValidatorTypes):
            validator_factory = self.ValidatorFactories[validator_factory]

        self._validator = deepcopy(validator)
        self._validator_factory: VALIDATOR_FACTORY[V, D] = validator_factory
        if static_config is not None:
            self._static_validator: Optional[Callable[[CellType[D]], D]] = self._validator_factory(self._validator,
                                                                                                   static_config)
        else:
            self._static_validator = None

    ValidatorFactories: dict[
        ValidatorTypes,
        VALIDATOR_FACTORY[V, D]
    ] = {
        ValidatorTypes.DEFAULT: cast(VALIDATOR_FACTORY[V, D], DefaultValidatorFactory),
        ValidatorTypes.NO_VALIDATION: lambda v, *_: v,
        ValidatorTypes.PYDANTIC: cast(VALIDATOR_FACTORY[V, D], pydantic_validator),
        ValidatorTypes.COMPONENT: cast(VALIDATOR_FACTORY[V, D], ComponentValidatorFactory),
    }
    """
    验证器工厂注册表

    .. versionchanged:: 0.2.0
       现在待验证的配置数据必须由 :py:class:`~Config.utils.CellType` 包装后传入
    """

    def filter(
            self,
            data: D | CellType[D],
            *,
            allow_modify: Optional[bool] = None,
            skip_missing: Optional[bool] = None,
            **extra: Any
    ) -> D:
        """
        检查过滤需求的键

        :param data: 要过滤的原始数据
        :type data: CellType[ABCConfigData] | ABCConfigData
        :param allow_modify: 是否允许值不存在时修改data参数对象填充默认值(即使为False仍然会在结果中填充默认值,但不会修改data参数对象)
        :type allow_modify: Optional[bool]
        :param skip_missing: 忽略丢失的键
        :type skip_missing: Optional[bool]
        :param extra: 额外参数
        :type extra: Any

        :return: 处理后的配置数据*快照*
        :rtype: ABCConfigData

        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredPathNotFoundError: 必要的键未找到
        :raise UnknownErrorDuringValidateError: 验证过程中发生未知错误

        .. attention::
           返回的配置数据是 `*快照*`

        .. caution::
           提供了任意配置参数(``allow_modify``, ``skip_missing``, ...)时,这次调用将完全舍弃 `static_config` 使用当前提供的配置参数

           这会导致调用 `validator_factory` 产生额外开销(如果你提供 `static_config` 参数是为了避免反复调用 `validator_factory` 的话)

        .. versionchanged:: 0.2.0
           重命名参数 ``ignore_missing`` 为 ``skip_missing``

           ``data`` 参数支持 :py:class:`CellType`
        """
        config_kwargs: dict[str, Any] = {}
        if allow_modify is not None:
            config_kwargs["allow_modify"] = allow_modify
        if skip_missing is not None:
            config_kwargs["skip_missing"] = skip_missing
        if extra:
            config_kwargs["extra"] = extra

        if not isinstance(data, CellType):
            data = CellType(data)

        if (self._static_validator is None) or config_kwargs:
            config = ValidatorFactoryConfig(**config_kwargs)
            validator: Callable[
                [CellType[D]], D
            ] = self._validator_factory(self._validator, config)
        else:
            validator = self._static_validator

        return validator(data)


class ConfigRequirementDecorator:
    """
    配置获取器，可作装饰器使用

    .. versionchanged:: 0.2.0
       重命名 ``RequireConfigDecorator`` 为 ``ConfigRequirementDecorator``
    """

    def __init__[D: ABCConfigData[Any]](
            self,
            config_pool: ABCConfigPool,
            namespace: str,
            file_name: str,
            required: RequiredPath[Any, D],
            *,
            config_formats: Optional[str | Iterable[str]] = None,
            allow_initialize: bool = True,
            config_cacher: Optional[Callable[[Callable[..., D], VarArg(), KwArg()], D]] = None,
            filter_kwargs: Optional[dict[str, Any]] = None
    ):
        # noinspection GrazieInspection
        """
        :param config_pool: 所在的配置池
        :type config_pool: ConfigPool
        :param namespace: 详见 :py:meth:`ConfigPool.load`
        :param file_name: 详见 :py:meth:`ConfigPool.load`
        :param required: 需求的键
        :type required: RequiredPath
        :param config_formats: 详见 :py:meth:`ConfigPool.load`
        :param allow_initialize: 详见 :py:meth:`ConfigPool.load`
        :param config_cacher: 缓存配置的装饰器，默认为None，即不缓存
        :type config_cacher: Optional[Callable[[Callable[..., ABCConfigData]], ABCConfigData]]
        :param filter_kwargs: :py:meth:`RequiredPath.filter` 要绑定的默认参数，这会导致 ``static_config`` 失效
        :type filter_kwargs: dict[str, Any]

        :raise UnsupportedConfigFormatError: 不支持的配置格式

        .. versionchanged:: 0.2.0
           重命名参数 ``cache_config`` 为 ``config_cacher``

           重命名参数 ``allow_create`` 为 ``allow_initialize``
        """
        config = config_pool.load(namespace, file_name,
                                  config_formats=config_formats, allow_initialize=allow_initialize)

        if filter_kwargs is None:
            filter_kwargs = {}

        self._config_file: ABCConfigFile[Any] = config
        self._required = required
        self._filter_kwargs = filter_kwargs
        self._config_cacher: Callable[[Callable[..., D], VarArg(), KwArg()], D] = (cast(
            Callable[[Callable[..., D], VarArg(), KwArg()], D],
            lambda func, *args, **kwargs: func(*args, **kwargs)
        ) if config_cacher is None else config_cacher)

    def check(self, *, ignore_cache: bool = False, **filter_kwargs: Any) -> Any:
        """
        手动检查配置

        :param ignore_cache: 是否忽略缓存
        :type ignore_cache: bool
        :param filter_kwargs: RequiredConfig.filter的参数
        :return: 得到的配置数据
        :rtype: Any
        """
        kwargs = self._filter_kwargs | filter_kwargs
        cell = CellType(self._config_file.config)
        if ignore_cache:
            result = self._required.filter(cell, **kwargs)
            self._config_file._config = cell.cell_contents
            return result
        return self._wrapped_filter(**kwargs)

    def __call__(self, func: Callable[[ABCConfigData[Any], Any], Any]) -> Callable[..., Any]:
        @wrapt.decorator  # type: ignore[misc]
        def wrapper(
                wrapped: Callable[..., Any],
                _instance: object | None,
                args: tuple[Any, ...],
                kwargs: dict[str, Any],
        ) -> Any:
            config_data = self._wrapped_filter(**self._filter_kwargs)

            return wrapped(
                config_data,
                *args,
                **kwargs
            )

        return cast(Callable[..., Any], wrapper(func))

    def _wrapped_filter(self, **kwargs: Any) -> ABCConfigData[Any]:
        cell = CellType(self._config_file.config)

        result = self._config_cacher(self._required.filter, cell, **kwargs)
        self._config_file._config = cell.cell_contents
        return result


class ConfigPool(BasicConfigPool):
    """
    配置池
    """

    def require(
            self,
            namespace: str,
            file_name: str,
            validator: Any,
            validator_factory: Any = ValidatorTypes.DEFAULT,
            static_config: Optional[Any] = None,
            **kwargs: Any,
    ) -> ConfigRequirementDecorator:
        # noinspection GrazieInspection
        """
        获取配置

        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        :param validator: 详见 :py:class:`RequiredPath`
        :param validator_factory: 详见 :py:class:`RequiredPath`
        :param static_config: 详见 :py:class:`RequiredPath`

        :param kwargs: 详见 :py:class:`ConfigRequirementDecorator`

        :return: 详见 :py:class:`ConfigRequirementDecorator`
        :rtype: :py:class:`ConfigRequirementDecorator`

        .. versionchanged:: 0.2.0
           删除声明于 ``ABCConfigPool``
        """
        return ConfigRequirementDecorator(self, namespace, file_name,
                                          RequiredPath(validator, validator_factory, static_config), **kwargs)


DefaultConfigPool = ConfigPool()
"""
默认配置池
"""
requireConfig = DefaultConfigPool.require
"""
:py:data:`DefaultConfigPool` . :py:meth:`~ConfigPool.require`
"""
saveAll = DefaultConfigPool.save_all
"""
:py:data:`DefaultConfigPool` . :py:meth:`~ConfigPool.save_all`
"""
get = DefaultConfigPool.get
"""
:py:data:`DefaultConfigPool` . :py:meth:`~ConfigPool.get`
"""
set_ = DefaultConfigPool.set
"""
:py:data:`DefaultConfigPool` . :py:meth:`~ConfigPool.set`
"""
save = DefaultConfigPool.save
"""
:py:data:`DefaultConfigPool` . :py:meth:`~ConfigPool.save`
"""
load = DefaultConfigPool.load
"""
:py:data:`DefaultConfigPool` . :py:meth:`~ConfigPool.load`
"""


class BasicConfigSL(ABCConfigSL, ABC):
    """
    基础配置SL管理器 提供了一些实用功能

    .. versionchanged:: 0.2.0
       重命名 ``BaseConfigSL`` 为 ``BasicConfigSL``
    """

    @override
    def register_to(self, config_pool: Optional[ABCSLProcessorPool] = None) -> None:
        """
        注册到配置池中

        :param config_pool: 配置池
        :type config_pool: Optional[ABCSLProcessorPool]
        """
        if config_pool is None:
            config_pool = DefaultConfigPool

        super().register_to(config_pool)

    @override
    def initialize(
            self,
            processor_pool: ABCSLProcessorPool,
            root_path: str,
            namespace: str,
            file_name: str,
            *args: Any,
            **kwargs: Any,
    ) -> ABCConfigFile[Any]:
        return ConfigFile(ConfigData(), config_format=self.reg_name)


def _merge_args(
        base_arguments: tuple[tuple[Any, ...], PMap[str, Any]],
        args: tuple[Any, ...],
        kwargs: dict[str, Any]
) -> tuple[tuple[Any, ...], PMap[str, Any]]:
    """
    合并参数

    :param base_arguments: 基础参数
    :type base_arguments: tuple[tuple, PMap[str, Any]]
    :param args: 新参数
    :type args: tuple
    :param kwargs: 新参数
    :type kwargs: dict

    :return: 合并后的参数
    :rtype: tuple[tuple, PMap[str, Any]]

    .. versionchanged:: 0.2.0
       提取为函数
    """
    merged_args = list(deepcopy(base_arguments[0]))
    merged_args[:len(args)] = args

    merged_kwargs = dict(deepcopy(base_arguments[1])) | kwargs

    return tuple(merged_args), pmap(merged_kwargs)


@contextmanager
def raises(excs: type[Exception] | tuple[type[Exception], ...] = Exception) -> Generator[None, Any, None]:
    """
    包装意料内的异常

    提供给子类的便捷方法

    :param excs: 意料内的异常
    :type excs: type[Exception] | tuple[type[Exception], ...]

    :raise FailedProcessConfigFileError: 当触发了对应的异常时

    .. versionadded:: 0.1.4

    .. versionchanged:: 0.2.0
       提取为函数
    """
    try:
        yield
    except excs as err:
        raise FailedProcessConfigFileError(err) from err


class BasicLocalFileConfigSL(BasicConfigSL, ABC):
    """
    基础本地配置文件SL处理器

    .. versionchanged:: 0.2.0
       重命名从 ``BaseLocalFileConfigSL`` 为 ``BasicLocalFileConfigSL``
    """

    _s_open_kwargs: dict[str, Any] = dict(mode='w', encoding="utf-8")
    _l_open_kwargs: dict[str, Any] = dict(mode='r', encoding="utf-8")

    def __init__(
            self,
            s_arg: SLArgument = None,
            l_arg: SLArgument = None,
            *,
            reg_alias: Optional[str] = None,
            create_dir: bool = True
    ):
        # noinspection GrazieInspection
        """
        :param s_arg: 保存器默认参数
        :type s_arg: Optional[Sequence | Mapping | tuple[Sequence, Mapping[str, Any]]]
        :param l_arg: 加载器默认参数
        :type l_arg: Optional[Sequence | Mapping | tuple[Sequence, Mapping[str, Any]]]
        :param reg_alias: 详见 :py:class:`BasicConfigSL`
        :param create_dir: 是否允许创建目录
        :type create_dir: bool

        .. seealso::
           :py:class:`BasicConfigSL`

        .. versionchanged:: 0.2.0
           将 ``保存加载器参数`` 相关从 :py:class:`BasicConfigSL` 移动到此类
        """

        def _build_arg(value: SLArgument) -> tuple[tuple[Any, ...], PMap[str, Any]]:
            if value is None:
                return (), pmap()
            if isinstance(value, Sequence):
                return tuple(value), pmap()
            if isinstance(value, Mapping):
                return (), pmap(value)
            raise TypeError(f"Invalid argument type, must be '{SLArgument}'")

        self._saver_args: tuple[tuple[Any, ...], PMap[str, Any]] = _build_arg(s_arg)
        self._loader_args: tuple[tuple[Any, ...], PMap[str, Any]] = _build_arg(l_arg)

        super().__init__(reg_alias=reg_alias)

        self.create_dir = create_dir

    @property
    def saver_args(self) -> tuple[tuple[Any, ...], PMap[str, Any]]:
        """
        :return: 保存器默认参数
        """
        return self._saver_args

    @property
    def loader_args(self) -> tuple[tuple[Any, ...], PMap[str, Any]]:
        """
        :return: 加载器默认参数
        """
        return self._loader_args

    raises = staticmethod(raises)

    @override
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
        保存处理器 (原子操作 多线/进程安全)

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
           现在操作是原子的(操作过程发生异常会回滚操作)

           现在操作是理论上是多线/进程安全的

           添加参数 ``processor_pool``
        """
        merged_args, merged_kwargs = _merge_args(self._saver_args, args, kwargs)

        file_path = processor_pool.helper.calc_path(root_path, namespace, file_name)
        if self.create_dir:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with safe_open(file_path, **self._s_open_kwargs) as f:
            self.save_file(config_file, f, *merged_args, **merged_kwargs)

    @override
    def load(
            self,
            processor_pool: ABCSLProcessorPool,
            root_path: str,
            namespace: str,
            file_name: str,
            *args: Any,
            **kwargs: Any,
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
           现在操作是原子的(操作过程发生异常会回滚操作)

           现在操作是理论上是多线/进程安全的

           删除参数 ``config_file_cls``

           添加参数 ``processor_pool``
        """
        merged_args, merged_kwargs = _merge_args(self._loader_args, args, kwargs)

        file_path = processor_pool.helper.calc_path(root_path, namespace, file_name)
        if self.create_dir:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with safe_open(file_path, **self._l_open_kwargs) as f:
            return self.load_file(f, *merged_args, **merged_kwargs)

    @abstractmethod
    def save_file(
            self,
            config_file: ABCConfigFile[Any],
            target_file: Any,
            *merged_args: Any,
            **merged_kwargs: Any,
    ) -> None:
        """
        将配置保存到文件

        :param config_file: 配置文件
        :type config_file: ABCConfigFile
        :param target_file: 目标文件对象
        :type target_file: Any
        :param merged_args: 合并后的位置参数
        :param merged_kwargs: 合并后的关键字参数

        :raise FailedProcessConfigFileError: 处理配置文件失败

        .. versionchanged:: 0.2.0
           更改 ``target_file`` 参数类型为 ``Any``
        """

    @abstractmethod
    def load_file(
            self,
            source_file: Any,
            *merged_args: Any,
            **merged_kwargs: Any,
    ) -> ABCConfigFile[Any]:
        """
        从文件加载配置

        :param source_file: 源文件对象
        :type source_file: Any
        :param merged_args: 合并后的位置参数
        :param merged_kwargs: 合并后的关键字参数

        :return: 本地配置文件对象
        :rtype: ABCConfigFile

        :raise FailedProcessConfigFileError: 处理配置文件失败

        .. versionchanged:: 0.2.0
           删除参数 ``config_file_cls``

           更改 ``source_file`` 参数类型为 ``Any``
        """

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        saver_args_eq = self._saver_args == other._saver_args
        loader_args_eq = self._loader_args == other._loader_args

        return all((
            super().__eq__(other),
            saver_args_eq,
            loader_args_eq
        ))

    def __hash__(self) -> int:
        return hash((
            super().__hash__(),
            self._saver_args,
            self._loader_args
        ))


class BasicChainConfigSL(BasicConfigSL, ABC):
    """
    基础连锁配置文件SL处理器

    .. caution::
       会临时在配置文件池中添加文件以传递SL操作

    .. versionadded:: 0.2.0
    """

    def __init__(self, *, reg_alias: Optional[str] = None, create_dir: bool = True):
        """
        :param reg_alias: sl处理器注册别名
        :type reg_alias: Optional[str]
        :param create_dir: 是否创建目录
        :type create_dir: bool
        """
        super().__init__(reg_alias=reg_alias)

        self.create_dir = create_dir
        self._cleanup_registry: bool = True
        """
        自动清理为了传递SL处理所加入配置池的配置文件
        """

    raises = staticmethod(raises)

    def namespace_formatter(self, namespace: str, file_name: str) -> str:
        """
        格式化命名空间以传递给其他SL处理器

        :param namespace: 配置的命名空间
        :type namespace: Optional[str]
        :param file_name: 配置文件名
        :type file_name: Optional[str]

        :return: 格式化后的命名空间
        :rtype: str
        """
        return namespace  # 全被子类复写了，测不到 # pragma: no cover

    def filename_formatter(self, file_name: str) -> str:
        # noinspection SpellCheckingInspection
        """
        格式化文件名以传递给其他SL处理器

        :param file_name: 配置文件名
        :type file_name: str

        :return: 格式化后的文件名
        :rtype: str

        默认实现:
            - 遍历 :py:attr:`BasicCompressedConfigSL`
            - 如果为 ``str`` 且 ``file_name.endswith`` 成立则返回移除后缀后的结果
            - 如果为 ``re.Pattern`` 且 ``Pattern.fullmatch(file_name)`` 成立则返回 ``Pattern.sub(file_name, '')``
            - 直接返回
        """
        for match in self.supported_file_patterns:
            if isinstance(match, str) and file_name.endswith(match):
                return file_name[:-len(match)]
            if isinstance(match, re.Pattern) and match.fullmatch(file_name):  # 目前没SL处理器用得上 # pragma: no cover
                return match.sub(file_name, '')
        return file_name  # 不好测试 # pragma: no cover

    def save(
            self,
            processor_pool: ABCSLProcessorPool,
            config_file: ABCConfigFile[Any],
            root_path: str,
            namespace: str,
            file_name: str,
            *args: Any, **kwargs: Any,
    ) -> None:
        config_pool = cast(ABCConfigPool, processor_pool)
        file_path = config_pool.helper.calc_path(root_path, namespace, file_name)
        if self.create_dir:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

        formatted_filename = self.filename_formatter(file_name)
        formatted_namespace = self.namespace_formatter(namespace, file_name)

        self.save_file(config_pool, config_file, formatted_namespace, formatted_filename, *args, **kwargs)
        self.after_save(config_pool, config_file, file_path, root_path, formatted_namespace, formatted_filename)

    def load(
            self,
            processor_pool: ABCSLProcessorPool,
            root_path: str,
            namespace: str,
            file_name: str,
            *args: Any, **kwargs: Any,
    ) -> ABCConfigFile[Any]:
        config_pool = cast(ABCConfigPool, processor_pool)
        file_path = config_pool.helper.calc_path(root_path, namespace, file_name)
        if self.create_dir:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

        formatted_filename = self.filename_formatter(file_name)
        formatted_namespace = self.namespace_formatter(namespace, file_name)

        self.before_load(config_pool, file_path, root_path, formatted_namespace, formatted_filename)
        return self.load_file(config_pool, formatted_namespace, formatted_filename, *args, **kwargs)

    def initialize(
            self,
            processor_pool: ABCSLProcessorPool,
            root_path: str,
            namespace: str,
            file_name: str,
            *args: Any, **kwargs: Any
    ) -> ABCConfigFile[Any]:
        config_pool = cast(ABCConfigPool, processor_pool)

        formatted_namespace = self.namespace_formatter(namespace, file_name)
        formatted_filename = self.filename_formatter(file_name)

        return config_pool.initialize(
            formatted_namespace,
            formatted_filename,
            *args, **kwargs
        )

    def save_file(
            self,
            config_pool: ABCConfigPool,
            config_file: ABCConfigFile[Any],
            namespace: str,
            file_name: str,
            *args: Any,
            **kwargs: Any
    ) -> None:
        """
        保存指定命名空间的配置

        :param config_pool: 配置池
        :type config_pool: ABCConfigPool
        :param config_file: 配置文件
        :type config_file: ABCConfigFile
        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str
        """

        config_pool.save(namespace, file_name, config=config_file, *args, **kwargs)  # type: ignore[misc]
        if self._cleanup_registry:
            config_pool.discard(namespace, file_name)

    def load_file(
            self,
            config_pool: ABCConfigPool,
            namespace: str,
            file_name: str,
            *args: Any,
            **kwargs: Any,
    ) -> ABCConfigFile[Any]:
        """
        加载指定命名空间的配置

        :param config_pool: 配置池
        :type config_pool: ABCConfigPool
        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str

        .. caution::
           传递SL处理前没有清理已经缓存在配置池里的配置文件，返回的可能不是最新数据
        """

        cfg_file = config_pool.load(namespace, file_name, *args, **kwargs)
        if self._cleanup_registry:
            config_pool.discard(namespace, file_name)
        return cfg_file

    def before_load(
            self,
            config_pool: ABCConfigPool,
            file_path: str,
            root_path: str,
            namespace: str,
            file_name: str,  # @formatter:off
    ) -> None: ...

    def after_save(
            self,
            config_pool: ABCConfigPool,
            config_file: ABCConfigFile[Any],
            file_path: str,
            root_path: str,
            namespace: str,
            file_name: str,
    ) -> None: ...
    # @formatter:on


class BasicCachedConfigSL(BasicChainConfigSL, ABC):
    """
    基础缓存配置处理器
    """

    @property
    def namespace_suffix(self) -> str:
        """
        命名空间后缀
        """
        return "$temporary~"

    def namespace_formatter(self, namespace: str, file_name: str) -> str:
        return os.path.normpath(os.path.join(namespace, self.namespace_suffix, file_name))


class BasicCompressedConfigSL(BasicCachedConfigSL, ABC):
    """
    基础压缩配置文件SL处理器

    .. versionadded:: 0.2.0
    """

    @property
    def namespace_suffix(self) -> str:
        return super().namespace_suffix

    @override
    def after_save(
            self,
            config_pool: ABCConfigPool,
            config_file: ABCConfigFile[Any],
            file_path: str,
            root_path: str,
            namespace: str,
            file_name: str,
    ) -> None:
        extract_dir = config_pool.helper.calc_path(root_path, namespace)
        self.compress_file(file_path, extract_dir)

    @override
    def before_load(
            self,
            config_pool: ABCConfigPool,
            file_path: str,
            root_path: str,
            namespace: str,
            file_name: str,
    ) -> None:
        extract_dir = config_pool.helper.calc_path(root_path, namespace)
        self.extract_file(file_path, extract_dir)

    @abstractmethod  # @formatter:off
    def compress_file(self, file_path: str, extract_dir: str) -> None: ...

    @abstractmethod
    def extract_file(self, file_path: str, extract_dir: str) -> None: ...
    # @formatter:on


__all__ = (
    "RequiredPath",
    "ConfigPool",
    "ConfigRequirementDecorator",
    "raises",
    "BasicConfigSL",
    "BasicLocalFileConfigSL",
    "BasicChainConfigSL",
    "BasicCompressedConfigSL",
    "DefaultConfigPool",
    "requireConfig",
    "saveAll",
    "get",
    "set_",
    "save",
    "load",
)
