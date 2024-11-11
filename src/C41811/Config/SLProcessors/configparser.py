# -*- coding: utf-8 -*-
# cython: language_level = 3

import configparser
from typing import Optional
from typing import TypeVar
from typing import override

from ..abc import ABCConfig
from ..abc import ABCConfigSL
from ..errors import FailedProcessConfigFileError
from ..main import ConfigData

C = TypeVar("C", bound=ABCConfig)


class ConfigParserSL(ABCConfigSL):
    """
    未完成 TODO
    """  # todo
    _parser = configparser.ConfigParser

    @property
    @override
    def regName(self) -> str:
        return "configparser"

    @property
    @override
    def fileExt(self) -> list[str]:
        return [".ini", ".properties", ".cfg"]

    @override
    def save(
            self,
            config: ABCConfig,
            root_path: str,
            namespace: Optional[str],
            file_name: Optional[str],
            *args,
            **kwargs
    ) -> None:
        file_path = self._getFilePath(config, root_path, namespace, file_name)
        config_data = self._parser()
        try:
            config_data.read_dict(config.data.data)
            with open(file_path, "w", encoding="utf-8") as f:
                config_data.write(f)
        except Exception as e:
            raise FailedProcessConfigFileError(e) from e

    @override
    def load(
            self,
            config_cls: type[C],
            root_path: str,
            namespace: Optional[str],
            file_name: Optional[str],
            *args,
            **kwargs
    ) -> C:
        file_path = self._getFilePath(config_cls, root_path, namespace, file_name)
        data = self._parser()
        try:
            data.read(file_path, encoding="utf-8")
            obj = config_cls(ConfigData(data), namespace=namespace, file_name=file_name, config_format=self.regName)
        except Exception as e:
            raise FailedProcessConfigFileError(e) from e

        return obj


__all__ = (
    "ConfigParserSL",
)
