# -*- coding: utf-8 -*-
# cython: language_level = 3

import configparser
from typing import Optional
from typing import TypeVar
from typing import override

from ..abc import ABCConfig
from ..errors import FailedProcessConfigFileError
from ..main import BaseConfigSL
from ..main import ConfigData

C = TypeVar("C", bound=ABCConfig)


class ConfigParserSL(BaseConfigSL):
    """
    未完成 TODO
    """  # todo
    _parser = configparser.ConfigParser

    @property
    @override
    def reg_name(self) -> str:
        return "configparser"

    @property
    @override
    def file_ext(self) -> list[str]:
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
        file_path = self._get_file_path(config, root_path, namespace, file_name)
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
        file_path = self._get_file_path(config_cls, root_path, namespace, file_name)
        data = self._parser()
        try:
            data.read(file_path, encoding="utf-8")
            obj = config_cls(ConfigData(data), namespace=namespace, file_name=file_name, config_format=self.reg_name)
        except Exception as e:
            raise FailedProcessConfigFileError(e) from e

        return obj


__all__ = (
    "ConfigParserSL",
)
