# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

from typing import override

from .._protocols import SupportsReadAndReadline
from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..base import ConfigFile
from ..main import BasicLocalFileConfigSL


class PythonSL(BasicLocalFileConfigSL):
    """
    pyhon格式处理器
    """

    @property
    @override
    def processor_reg_name(self) -> str:
        return "python"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".py",

    supported_file_classes = [ConfigFile]

    @override
    def save_file(
            self,
            config_file: ABCConfigFile,
            target_file: SupportsWrite[str],
            *merged_args,
            **merged_kwargs
    ) -> None:
        with self.raises():
            raise NotImplementedError

    @override
    def load_file(
            self,
            source_file: SupportsReadAndReadline[str],
            *merged_args,
            **merged_kwargs
    ) -> ConfigFile:
        names = {}
        with self.raises():
            exec(source_file.read(), {}, names)

        return ConfigFile(names, config_format=self.processor_reg_name)


__all__ = (
    "PythonSL",
)
