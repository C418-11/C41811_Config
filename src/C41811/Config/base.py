# -*- coding: utf-8 -*-
# cython: language_level = 3


import os.path
from abc import ABC
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import MutableMapping
from copy import deepcopy
from typing import Any
from typing import Optional
from typing import Self
from typing import override

from .abc import ABCConfigData
from .abc import ABCConfigFile
from .abc import ABCConfigPool
from .abc import ABCKey
from .abc import ABCPath
from .abc import ABCSLProcessorPool
from .errors import ConfigDataReadOnlyError
from .errors import ConfigDataTypeError
from .errors import ConfigOperate
from .errors import FailedProcessConfigFileError
from .errors import KeyInfo
from .errors import RequiredPathNotFoundError
from .errors import UnsupportedConfigFormatError
from .path import Path


def _fmt_path(path: str | ABCPath) -> ABCPath:
    if isinstance(path, ABCPath):
        return path
    return Path.from_str(path)


class ConfigData(ABCConfigData):
    """
    配置数据类
    """

    @override
    @property
    def read_only(self) -> bool:
        return super().read_only

    @override
    @read_only.setter
    def read_only(self, value: Any):
        if self._data_read_only:
            raise ConfigDataReadOnlyError
        self._read_only = bool(value)

    def _process_path(
            self,
            path: ABCPath,
            process_check: Callable[[Mapping | MutableMapping, ABCKey, list[ABCKey], int], Any],
            process_return: Callable[[Mapping | MutableMapping], Any]
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

            now_data = now_data[now_key]

        return process_return(now_data)

    @override
    def retrieve(self, path: str | ABCPath, *, get_raw: bool = False) -> Any:
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, _last_key: list[ABCKey], key_index: int):
            if not isinstance(now_data, Mapping):
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), Mapping, type(now_data))
            if now_key not in now_data:
                raise RequiredPathNotFoundError(KeyInfo(path, now_key, key_index), ConfigOperate.Read)

        def process_return(now_data):
            if get_raw:
                return deepcopy(now_data)
            if isinstance(now_data, Mapping):
                return ConfigData(now_data)

            return deepcopy(now_data)

        return self._process_path(path, checker, process_return)

    @override
    def modify(self, path: str | ABCPath, value: Any, *, allow_create: bool = True) -> Self:
        if self.read_only:
            raise ConfigDataReadOnlyError
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, last_key: list[ABCKey], key_index: int):
            if not isinstance(now_data, MutableMapping):
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), MutableMapping, type(now_data))
            if now_key not in now_data:
                if not allow_create:
                    raise RequiredPathNotFoundError(KeyInfo(path, now_key, key_index), ConfigOperate.Write)
                now_data[now_key.key] = type(self._data)()

            if not last_key:
                now_data[now_key.key] = value

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    def delete(self, path: str | ABCPath) -> Self:
        if self.read_only:
            raise ConfigDataReadOnlyError
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, last_key: list[ABCKey], key_index: int):
            if not isinstance(now_data, MutableMapping):
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), MutableMapping, type(now_data))
            if now_key not in now_data:
                raise RequiredPathNotFoundError(KeyInfo(path, now_key, key_index), ConfigOperate.Delete)

            if not last_key:
                del now_data[now_key]
                return True

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    def unset(self, path: str | ABCPath) -> Self:
        try:
            self.delete(path)
        except RequiredPathNotFoundError:
            pass
        return self

    @override
    def exists(self, path: str | ABCPath, *, ignore_wrong_type: bool = False) -> bool:
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, _last_key: list[ABCKey], key_index: int):
            if not isinstance(now_data, Mapping):
                if ignore_wrong_type:
                    return False
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), Mapping, type(now_data))
            if now_key not in now_data:
                return False

        return self._process_path(path, checker, lambda *_: True)

    @override
    def get(self, path: str | ABCPath, default=None, *, get_raw: bool = False) -> Any:
        try:
            return self.retrieve(path, get_raw=get_raw)
        except RequiredPathNotFoundError:
            return default

    @override
    def set_default(self, path: str | ABCPath, default=None, *, get_raw: bool = False) -> Any:
        try:
            return self.retrieve(path, get_raw=get_raw)
        except RequiredPathNotFoundError:
            self.modify(path, default)
            return default


class ConfigFile(ABCConfigFile):
    """
    配置文件类
    """

    @override
    def save(
            self,
            config_pool: ABCSLProcessorPool,
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
        if config_format not in config_pool.SLProcessor:
            raise UnsupportedConfigFormatError(config_format)

        return config_pool.SLProcessor[config_format].save(self, config_pool.root_path, namespace, file_name,
                                                           *processor_args, **processor_kwargs)

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
        ].load(cls, config_pool.root_path, namespace, file_name, *processor_args, **processor_kwargs)


class BaseConfigPool(ABCConfigPool, ABC):
    """
    基础配置池类

    实现了一些通用方法
    """

    def __init__(self, root_path="./.config"):
        super().__init__(root_path)
        self._configs: dict[str, dict[str, ABCConfigFile]] = {}

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
    def set(self, namespace: str, file_name: str, config: ABCConfigFile) -> None:
        if namespace not in self._configs:
            self._configs[namespace] = {}

        self._configs[namespace][file_name] = config

    def _test_all_sl[R: Any](
            self,
            namespace: str,
            file_name: str,
            config_formats: Optional[str | Iterable[str]],
            processor: Callable[[Self, str, str, str], R],
            file_config_format: Optional[str] = None
    ) -> R:
        """
        尝试自动推断ABCConfigFile所支持的config_format

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
           可选项，一般在保存时填入
           :py:attr:`ABCConfigData.config_format`
           用于在没手动指定配置格式且没文件后缀时使用该值进行尝试

        :raise UnsupportedConfigFormatError: 不支持的配置格式
        :raise FailedProcessConfigFileError: 处理配置文件失败

        .. versionadded:: 0.1.2

        格式推断优先级
        --------------

        1.如果传入了config_formats且非None非空集则直接使用

        2.如果有文件后缀则查找文件后缀是否注册了对应的SL处理器，如果有就直接使用

        3.如果传入了file_config_format且非None则直接使用
        """
        if config_formats is None:
            config_formats = set()
        elif isinstance(config_formats, str):
            config_formats = {config_formats}
        else:
            config_formats = set(config_formats)

        format_set: set[str]
        # 配置文件格式未提供时尝试从文件后缀推断
        _, file_ext = os.path.splitext(file_name)
        if not config_formats and file_ext:
            if file_ext not in self.FileExtProcessor:
                raise UnsupportedConfigFormatError(file_ext)
            format_set = self.FileExtProcessor[file_ext]
        else:
            format_set = config_formats

        if (not format_set) and (file_config_format is not None):
            format_set.add(file_config_format)

        if not format_set:
            raise UnsupportedConfigFormatError("Unknown")

        def callback_wrapper(cfg_fmt: str):
            return processor(self, namespace, file_name, cfg_fmt)

        # 尝试从多个SL加载器中找到能正确加载的那一个
        errors = {}
        for fmt in format_set:
            if fmt not in self.SLProcessor:
                errors[fmt] = UnsupportedConfigFormatError(fmt)
                continue
            try:
                # 能正常运行直接返回结果，不再进行尝试
                return callback_wrapper(fmt)
            except FailedProcessConfigFileError as err:
                errors[fmt] = err

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
    ) -> None:
        if config is not None:
            self.set(namespace, file_name, config)

        file = self._configs[namespace][file_name]

        def processor(pool: Self, ns: str, fn: str, cf: str):
            file.save(pool, ns, fn, cf, *args, **kwargs)

        self._test_all_sl(namespace, file_name, config_formats, processor, file_config_format=file.config_format)

    @override
    def save_all(self, ignore_err: bool = False) -> None | dict[str, dict[str, tuple[ABCConfigFile, Exception]]]:
        errors = {}
        for namespace, configs in self._configs.items():
            errors[namespace] = {}
            for file_name, config in configs.items():
                try:
                    config.save(self, namespace=namespace, file_name=file_name)
                except Exception as e:
                    if not ignore_err:
                        raise
                    errors[namespace][file_name] = (config, e)

        if not ignore_err:
            return None

        return {k: v for k, v in errors.items() if v}

    def delete(self, namespace: str, file_name: str) -> None:
        del self._configs[namespace][file_name]

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
    "ConfigData",
    "ConfigFile",
    "BaseConfigPool"
)
