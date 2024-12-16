# -*- coding: utf-8 -*-
# cython: language_level = 3


from abc import ABC
from copy import deepcopy
from typing import Any
from typing import Callable
from typing import Mapping
from typing import MutableMapping
from typing import Optional
from typing import Self
from typing import override

from .abc import ABCConfigData
from .abc import ABCConfigFile
from .abc import ABCConfigPool
from .abc import ABCKey
from .abc import ABCPath
from .abc import ABCSLProcessorPool
from .errors import ConfigDataTypeError
from .errors import ConfigOperate
from .errors import KeyInfo
from .errors import RequiredPathNotFoundError
from .errors import UnsupportedConfigFormatError
from .path import Path


def _fmt_path(path: str | ABCPath) -> ABCPath:
    if isinstance(path, ABCPath):
        return path
    if not path.startswith('\\'):
        path = rf"\.{path}"
    return Path.from_str(path)


class ConfigData(ABCConfigData):
    r"""
    配置数据类

    .. note::
       所有参数可以为 ``未解析路径转义字符串`` 的参数都做了预操作
       可以省略字符串开头的 ``\.``

       例如：

       ``r"\.first\.second\.third“``

       可以简写为

       ``r"first\.second\.third"``
    """

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
            raise TypeError("Config data is read-only")
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
            raise TypeError("Config data is read-only")
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

    @override
    def save(self, namespace: str, file_name: str, *args, **kwargs) -> None:
        self._configs[namespace][file_name].save(self, namespace, file_name, *args, **kwargs)

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
