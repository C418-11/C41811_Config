# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

from typing import TextIO
from typing import override

from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..base import ConfigData
from ..base import ConfigFile
from ..base import SequenceConfigData
from ..base import StringConfigData
from ..main import BasicLocalFileConfigSL


class PlainTextSL(BasicLocalFileConfigSL):
    """
    纯文本格式处理器
    """

    @property
    @override
    def processor_reg_name(self) -> str:
        return "plaintext"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".txt",

    supported_file_classes = [ConfigFile]

    @override
    def save_file(
            self,
            config_file: ABCConfigFile[StringConfigData | SequenceConfigData],
            target_file: SupportsWrite[str],
            *merged_args,
            **merged_kwargs
    ) -> None:
        if isinstance(config_file.config, StringConfigData):
            with self.raises():
                target_file.write(config_file.config.data)
            return

        with self.raises():
            iter(config_file.config)

        linesep = merged_kwargs.get("linesep", '')
        for line in config_file.config:
            with self.raises():
                target_file.write(line + linesep)

    @override
    def load_file(
            self,
            source_file: TextIO,
            *merged_args,
            **merged_kwargs
    ) -> ConfigFile[StringConfigData[str] | SequenceConfigData[list]]:
        if merged_kwargs.get("split_line"):
            with self.raises():
                content = source_file.readlines()
            if merged_kwargs.get("remove_linesep"):
                for i, line in enumerate(content):
                    content[i] = line.removesuffix(merged_kwargs.get("remove_linesep"))
        else:
            with self.raises():
                content = source_file.read()

        return ConfigFile(ConfigData(content), config_format=self.processor_reg_name)


__all__ = (
    "PlainTextSL",
)
