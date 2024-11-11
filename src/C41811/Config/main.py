# -*- coding: utf-8 -*-
# cython: language_level = 3

import functools
import inspect
import os.path
from collections.abc import Mapping
from collections.abc import MutableMapping
from copy import deepcopy
from types import UnionType
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Optional
from typing import Self
from typing import override

from .abc import *
from .errors import *


def _is_method(func):
    arguments = inspect.getargs(func.__code__).args
    if len(arguments) < 1:
        return False
    return arguments[0] in {"self", "cls"}


class ConfigData(ABCConfigData):

    def _process_path(self, path: str, process_check: Callable, process_return: Callable) -> Any:
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
        last_path = path
        now_data = self._data

        path_index = -1

        while last_path:
            path_index += 1
            try:
                now_path, last_path = last_path.split(self._sep_char, maxsplit=1)
            except ValueError:
                now_path, last_path = last_path, None

            check_result = process_check(now_data, now_path, last_path, path_index)
            if check_result is not None:
                return check_result

            now_data = now_data[now_path]

        return process_return(now_data)

    @override
    def getPathValue(self, path: str, *, get_raw: bool = False) -> Any:
        def checker(now_data, now_path, _last_path, path_index):
            if not isinstance(now_data, Mapping):
                raise ConfigDataTypeError(path, self._sep_char, now_path, path_index, Mapping, type(now_data))
            if now_path not in now_data:
                raise RequiredKeyNotFoundError(path, self._sep_char, now_path, path_index, ConfigOperate.Read)

        def process_return(now_data):
            if get_raw:
                return deepcopy(now_data)
            if isinstance(now_data, Mapping):
                return ConfigData(deepcopy(now_data))

            return deepcopy(now_data)

        return self._process_path(path, checker, process_return)

    @override
    def setPathValue(self, path: str, value: Any, *, allow_create: bool = True) -> Self:
        if self.read_only:
            raise TypeError("Config data is read-only")

        def checker(now_data, now_path, last_path, path_index):
            if not isinstance(now_data, MutableMapping):
                raise ConfigDataTypeError(path, self._sep_char, now_path, path_index, MutableMapping, type(now_data))
            if now_path not in now_data:
                if not allow_create:
                    raise RequiredKeyNotFoundError(path, self._sep_char, now_path, path_index, ConfigOperate.Write)
                now_data[now_path] = {}

            if last_path is None:
                now_data[now_path] = value

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    def deletePath(self, path: str) -> Self:
        if self.read_only:
            raise TypeError("Config data is read-only")

        def checker(now_data, now_path, last_path, path_index):
            if not isinstance(now_data, MutableMapping):
                raise ConfigDataTypeError(path, self._sep_char, now_path, path_index, MutableMapping, type(now_data))
            if now_path not in now_data:
                raise RequiredKeyNotFoundError(path, self._sep_char, now_path, path_index, ConfigOperate.Delete)

            if last_path is None:
                del now_data[now_path]
                return True

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    def hasPath(self, path: str) -> bool:
        def checker(now_data, now_path, _last_path, path_index):
            if not isinstance(now_data, Mapping):
                raise ConfigDataTypeError(path, self._sep_char, now_path, path_index, Mapping, type(now_data))
            if now_path not in now_data:
                return False

        return self._process_path(path, checker, lambda *_: True)

    @override
    def get(self, path: str, default=None, *, get_raw: bool = False) -> Any:
        try:
            return self.getPathValue(path, get_raw=get_raw)
        except RequiredKeyNotFoundError:
            return default


class RequiredKey:
    """
    对需求的键进行存在检查、类型检查、填充默认值
    """
    TypingType = {UnionType}

    def __init__(self, paths: Iterable[str] | Mapping[str, Any]):
        """
        当paths为Mapping时{key: value}

        value会被作为key不存在时的*默认值*填充，在key存在时会进行isinstance(data, type(value))检查

        如果type(value) is type也就是*默认值*是类型时，会将其直接用作类型检查issubclass(data, value)且不会尝试填充默认值

        :param paths: 需求的路径
        :type paths: Iterable[str] | Mapping[str, Any]
        """

        self._check_type: bool = isinstance(paths, Mapping)
        self._paths: Iterable[str] | Mapping[str, type] = paths

    def filter(self, data: ABCConfigData, *, allow_create: bool = False, ignore_missing: bool = False) -> Any:
        """
        检查过滤需求的键

        .. note::
           返回的配置数据是*快照*

        :param data: 要过滤的原始数据
        :type data: ABCConfigData
        :param allow_create: 是否允许值不存在时修改data参数对象填充默认值(即使为False仍然会在结果中填充默认值,但不会修改data参数对象)
        :type allow_create: bool
        :param ignore_missing: 忽略丢失的键
        :type ignore_missing: bool

        :return: 处理后的配置数据*快照*
        :rtype: Any
        """
        result = type(data)()

        if not self._check_type:
            for path in self._paths:
                value = data.getPathValue(path)
                result[path] = value
            return result

        for path, default in self._paths.items():

            _type = default
            if (type(default) not in self.TypingType) and (type(default) is not type):
                _type = type(default)
                value = deepcopy(default)
                try:
                    value = data.getPathValue(path)
                except RequiredKeyNotFoundError:
                    if allow_create:
                        data.setPathValue(path, value, allow_create=True)
            else:
                try:
                    value = data.getPathValue(path)
                except RequiredKeyNotFoundError:
                    if not ignore_missing:
                        raise
                    continue

            if (type(default) not in self.TypingType) and issubclass(_type, Mapping) and isinstance(value, type(data)):
                value = value.data

            if not isinstance(value, _type):  # todo 替换成专门的类型检查器
                path_chunks = path.split(data.sep_char)
                raise ConfigDataTypeError(
                    path, data.sep_char, path_chunks[-1], len(path_chunks) - 1, _type, type(value)
                )

            result[path] = value

        return result


class Config(ABCConfig):
    """
    配置类
    """

    @override
    def save(
            self,
            config_pool: ABCSLProcessorPool,
            namespace: str | None = None,
            file_name: str | None = None,
            config_format: str | None = None,
            *processor_args,
            **processor_kwargs
    ) -> None:

        if config_format is None:
            config_format = self._config_format

        if config_format is None:
            raise UnsupportedConfigFormatError("Unknown")
        if config_format not in config_pool.SLProcessor:
            raise UnsupportedConfigFormatError(config_format)

        return config_pool.SLProcessor[config_format].save(
            self,
            config_pool.root_path,
            namespace,
            file_name,
            *processor_args,
            **processor_kwargs
        )

    @classmethod
    @override
    def load(
            cls,
            config_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: str,
            *processor_args,
            **processor_kwargs
    ) -> Self:

        if config_format not in config_pool.SLProcessor:
            raise UnsupportedConfigFormatError(config_format)

        return config_pool.SLProcessor[
            config_format
        ].load(
            cls,
            config_pool.root_path,
            namespace,
            file_name,
            *processor_args,
            **processor_kwargs
        )


class ConfigPool(ABCConfigPool):

    def __init__(self, root_path="./.config"):
        super().__init__(root_path)
        self._configs: dict[str, dict[str, ABCConfig]] = {}

    @override
    def get(self, namespace: str, file_name: Optional[str] = None) -> dict[str, ABCConfig] | ABCConfig | None:
        if namespace not in self._configs:
            return None
        result = self._configs[namespace]

        if file_name is None:
            return result

        if file_name in result:
            return result[file_name]

        return None

    @override
    def set(self, namespace: str, file_name: str, config: ABCConfig) -> None:
        if namespace not in self._configs:
            self._configs[namespace] = {}

        self._configs[namespace][file_name] = config

    @override
    def saveAll(self, ignore_err: bool = False) -> None | dict[str, dict[str, tuple[ABCConfig, Exception]]]:
        """
        保存所有配置

        :param ignore_err: 是否忽略保存导致的错误
        :type ignore_err: bool

        :return: ignore_err为True时返回{Namespace: {FileName: (ConfigObj, Exception)}}，否则返回None
        :rtype: None | dict[str, dict[str, tuple[ABCConfig, Exception]]]
        """
        errors = {}
        for namespace, configs in self._configs.items():
            errors[namespace] = {}
            for file_name, config in configs.items():
                try:
                    config.save(self)
                except Exception as e:
                    if not ignore_err:
                        raise
                    errors[namespace][file_name] = (config, e)

        if not ignore_err:
            return None

        return {k: v for k, v in errors.items() if v}

    @override
    def requireConfig(
            self,
            namespace: str,
            file_name: str,
            required: list[str] | dict[str, Any],
            *args,
            **kwargs,
    ):
        return RequireConfig(self, namespace, file_name, RequiredKey(required), *args, **kwargs)

    def __getitem__(self, item):
        return deepcopy(self.configs[item])

    @property
    def configs(self):
        return deepcopy(self._configs)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.configs!r})"


class RequireConfig:
    """
    配置获取器，可作装饰器使用
    """

    def __init__(
            self,
            config_pool: ConfigPool,
            namespace: str,
            raw_file_name: str,
            required: RequiredKey,
            *,
            config_cls: type[ABCConfig] = Config,
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
        :type required: RequiredKey
        :param config_format: 配置文件格式
        :type config_format: Optional[str]
        :param cache_config: 缓存配置的装饰器，默认为None，即不缓存
        :type cache_config: Optional[Callable[[Callable], Callable]]
        :param allow_create: 是否允许在文件不存在时新建文件
        :type allow_create: bool
        :param filter_kwargs: RequiredKey.filter要绑定的默认参数，默认为allow_create=True
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

        def _load_config(format_: str) -> ABCConfig:
            if format_ not in config_pool.SLProcessor:
                raise UnsupportedConfigFormatError(format_)

            result: ABCConfig | None = config_pool.get(namespace, raw_file_name)
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
            config: ABCConfig = ret
            break
        else:
            raise FailedProcessConfigFileError(errors)

        if filter_kwargs is None:
            filter_kwargs = {}

        self._config: ABCConfig = config
        self._required = required
        self._filter_kwargs = {"allow_create": True} | filter_kwargs
        self._cache_config: Callable = cache_config if cache_config is not None else lambda x: x

    def checkConfig(self, *, ignore_cache: bool = False, **filter_kwargs) -> Any:
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
        if _is_method(func):
            processor = self._method_processor
        else:
            processor = self._function_processor

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*processor(*args), **kwargs)

        return wrapper

    def _wrapped_filter(self, **kwargs):
        return self._cache_config(self._required.filter(self._config.data, **kwargs))

    def _function_processor(self, *args):
        return self._wrapped_filter(**self._filter_kwargs), *args

    def _method_processor(self, obj, *args):
        return obj, self._wrapped_filter(**self._filter_kwargs), *args


DefaultConfigPool = ConfigPool()
requireConfig = DefaultConfigPool.requireConfig

__all__ = (
    "ConfigData",
    "RequiredKey",
    "Config",
    "ConfigPool",
    "RequireConfig",

    "DefaultConfigPool",
    "requireConfig",
)
