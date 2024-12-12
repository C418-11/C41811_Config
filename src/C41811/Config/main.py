# -*- coding: utf-8 -*-
# cython: language_level = 3


import os.path
from abc import ABC
from collections.abc import Mapping
from copy import deepcopy
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Literal
from typing import Optional
from typing import override

import wrapt

from .abc import ABCConfigData
from .abc import ABCConfigFile
from .abc import ABCConfigPool
from .abc import ABCConfigSL
from .abc import ABCSLProcessorPool
from .base import BaseConfigPool
from .base import ConfigData
from .base import ConfigFile
from .errors import FailedProcessConfigFileError
from .errors import UnsupportedConfigFormatError
from .validators import DefaultValidatorFactory
from .validators import ValidatorFactoryConfig
from .validators import ValidatorTypes
from .validators import pydantic_validator


class RequiredPath:
    """
    对需求的键进行存在检查、类型检查、填充默认值
    """

    def __init__[V: Any, D: ABCConfigData](
            self,
            validator: V,
            validator_factory: Optional[
                Callable[[V, ValidatorFactoryConfig], Callable[[D], D]] | ValidatorTypes | Literal["ignore", "pydantic"]
                ] = ValidatorTypes.DEFAULT,
            static_config: Optional[ValidatorFactoryConfig] = None
    ):
        """
        .. tip::
           提供static_config参数，可以避免在filter中反复调用validator_factory(filter配置一切都为默认值的前提下)

        :param validator: 数据验证器
        :type validator: Any
        :param validator_factory: 数据验证器工厂
        :type validator_factory:
            Optional[
            Callable[
            [Any, validators.ValidatorFactoryConfig],
            Callable[[ABCConfigData], ABCConfigData]
            ] | validators.ValidatorTypes | Literal["ignore", "pydantic"]
            ]
        :param static_config: 静态配置
        :type static_config: Optional[validators.ValidatorFactoryConfig]
        """
        if not callable(validator_factory):
            validator_factory = ValidatorTypes(validator_factory)
        if isinstance(validator_factory, ValidatorTypes):
            validator_factory = self.ValidatorFactories[validator_factory]

        self._validator: Iterable[str] | Mapping[str, type] = deepcopy(validator)
        self._validator_factory: Callable[[V, ValidatorFactoryConfig], Callable[[D], D]] = validator_factory
        if static_config is not None:
            self._static_validator: Optional[Callable[[D], D]] = self._validator_factory(self._validator, static_config)
        else:
            self._static_validator = None

    ValidatorFactories: dict[
        ValidatorTypes,
        Callable[[Any, ValidatorFactoryConfig], Callable[[ABCConfigData], ABCConfigData]]
    ] = {
        ValidatorTypes.DEFAULT: DefaultValidatorFactory,
        ValidatorTypes.IGNORE: lambda v, *_: v,
        ValidatorTypes.PYDANTIC: pydantic_validator,
    }

    def filter[D: ABCConfigData](
            self,
            data: D,
            *,
            allow_create: Optional[bool] = None,
            ignore_missing: Optional[bool] = None,
            **extra
    ) -> D:
        """
        检查过滤需求的键

        .. attention::
           返回的配置数据是*快照*

        .. caution::
           提供了任意配置参数(`allow_create`, `ignore_missing`, ...)时,这次调用将完全舍弃static_config使用当前提供的配置参数

           这会导致调用validator_factory产生额外开销(如果你提供static_config参数是为了避免反复调用validator_factory的话)

        :param data: 要过滤的原始数据
        :type data: ABCConfigData
        :param allow_create: 是否允许值不存在时修改data参数对象填充默认值(即使为False仍然会在结果中填充默认值,但不会修改data参数对象)
        :type allow_create: bool
        :param ignore_missing: 忽略丢失的键
        :type ignore_missing: bool
        :param extra: 额外参数
        :type extra: Any

        :return: 处理后的配置数据*快照*
        :rtype: ABCConfigData

        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredPathNotFoundError: 必要的键未找到
        :raise UnknownErrorDuringValidate: 验证过程中发生未知错误
        """
        config_kwargs = {}
        if allow_create is not None:
            config_kwargs["allow_create"] = allow_create
        if ignore_missing is not None:
            config_kwargs["ignore_missing"] = ignore_missing
        if extra:
            config_kwargs["extra"] = extra

        if (self._static_validator is None) or config_kwargs:
            config = ValidatorFactoryConfig(**config_kwargs)
            validator: Callable[[ABCConfigData], ABCConfigData] = self._validator_factory(self._validator, config)
        else:
            validator = self._static_validator

        return validator(data)


class ConfigPool(BaseConfigPool):
    @override
    def require(
            self,
            namespace: str,
            file_name: str,
            validator: Any,
            validator_factory: Any,
            *args, **kwargs
    ):
        return RequireConfigDecorator(
            self,
            namespace,
            file_name,
            RequiredPath(validator, validator_factory),
            *args,
            **kwargs
        )


class RequireConfigDecorator:
    """
    配置获取器，可作装饰器使用
    """

    def __init__(
            self,
            config_pool: ABCConfigPool,
            namespace: str,
            raw_file_name: str,
            required: RequiredPath,
            *,
            config_cls: type[ABCConfigFile] = ConfigFile,
            config_format: Optional[str] = None,
            cache_config: Optional[Callable[[Callable], Callable]] = None,
            allow_create: bool = True,
            filter_kwargs: Optional[dict[str, Any]] = None
    ):
        """
        :param config_pool: 所在的配置池
        :type config_pool: ConfigPool
        :param namespace: 命名空间
        :type namespace: str
        :param raw_file_name: 源文件名
        :type raw_file_name: str
        :param required: 需求的键
        :type required: RequiredPath
        :param config_format: 配置文件格式
        :type config_format: Optional[str]
        :param cache_config: 缓存配置的装饰器，默认为None，即不缓存
        :type cache_config: Optional[Callable[[Callable], Callable]]
        :param allow_create: 是否允许在文件不存在时新建文件
        :type allow_create: bool
        :param filter_kwargs: :py:func:`RequiredPath.filter` 要绑定的默认参数，默认为allow_create=True
        :type filter_kwargs: dict[str, Any]

        :raise UnsupportedConfigFormatError: 不支持的配置格式
        """
        format_set: set[str]
        if config_format is None:
            _, config_format = os.path.splitext(raw_file_name)
            if not config_format:
                raise UnsupportedConfigFormatError("Unknown")
            if config_format not in config_pool.FileExtProcessor:
                raise UnsupportedConfigFormatError(config_format)
            format_set = config_pool.FileExtProcessor[config_format]
        else:
            format_set = {config_format, }

        def _load_config(format_: str) -> ABCConfigFile:
            if format_ not in config_pool.SLProcessor:
                raise UnsupportedConfigFormatError(format_)

            result: ABCConfigFile | None = config_pool.get(namespace, raw_file_name)
            if result is None:
                try:
                    result = config_cls.load(config_pool, namespace, raw_file_name, format_)
                except FileNotFoundError:
                    if not allow_create:
                        raise
                    result = config_cls(
                        ConfigData(),
                        namespace=namespace,
                        file_name=raw_file_name,
                        config_format=format_
                    )

                config_pool.set(namespace, raw_file_name, result)
            return result

        errors = {}
        for f in format_set:
            try:
                ret = _load_config(f)
            except FailedProcessConfigFileError as err:
                errors[f] = err
                continue
            config: ABCConfigFile = ret
            break
        else:
            raise FailedProcessConfigFileError(errors)

        if filter_kwargs is None:
            filter_kwargs = {}

        self._config: ABCConfigFile = config
        self._required = required
        self._filter_kwargs = {"allow_create": True} | filter_kwargs
        self._cache_config: Callable = cache_config if cache_config is not None else lambda x: x

    def check(self, *, ignore_cache: bool = False, **filter_kwargs) -> Any:
        """
        手动检查配置

        :param ignore_cache: 是否忽略缓存
        :type ignore_cache: bool
        :param filter_kwargs: RequiredConfig.filter的参数
        :return: 得到的配置数据
        :rtype: Any
        """
        kwargs = self._filter_kwargs | filter_kwargs
        if ignore_cache:
            return self._required.filter(self._config.data, **kwargs)
        return self._wrapped_filter(**kwargs)

    def __call__(self, func):
        @wrapt.decorator
        def wrapper(wrapped, _instance, args, kwargs):
            config_data = self._wrapped_filter(**self._filter_kwargs)

            return wrapped(
                *(config_data, *args),
                **kwargs
            )

        return wrapper

    def _wrapped_filter(self, **kwargs):
        return self._cache_config(self._required.filter(self._config.data, **kwargs))

    def _function_processor(self, *args):
        return self._wrapped_filter(**self._filter_kwargs), *args

    def _method_processor(self, obj, *args):
        return obj, self._wrapped_filter(**self._filter_kwargs), *args


DefaultConfigPool = ConfigPool()
requireConfig = DefaultConfigPool.require
saveAll = DefaultConfigPool.save_all
getConfig = DefaultConfigPool.get
setConfig = DefaultConfigPool.set


class BaseConfigSL(ABCConfigSL, ABC):
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


__all__ = (
    "RequiredPath",
    "ConfigPool",
    "RequireConfigDecorator",
    "BaseConfigSL",

    "DefaultConfigPool",
    "requireConfig",
)
