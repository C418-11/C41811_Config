# -*- coding: utf-8 -*-
# cython: language_level = 3


import pprint
from ast import literal_eval
from typing import Any
from typing import override

from .._protocols import SupportsReadAndReadline
from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..base import ConfigFile
from ..main import BasicLocalFileConfigSL


class PythonLiteralSL(BasicLocalFileConfigSL):
    """
    Python 字面量序列化处理器
    """

    @property
    @override
    def processor_reg_name(self) -> str:
        return "python_literal"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".python_literal", ".pyl", ".py"

    supported_file_classes = [ConfigFile]

    @override
    def save_file(
            self,
            config_file: ABCConfigFile[Any],
            target_file: SupportsWrite[str],
            *merged_args: Any,
            **merged_kwargs: Any
    ) -> None:
        with self.raises():
            target_file.write(pprint.pformat(config_file.config.data, *merged_args, **merged_kwargs))

    @override
    def load_file(
            self,
            source_file: SupportsReadAndReadline[str],
            *merged_args: Any,
            **merged_kwargs: Any
    ) -> ConfigFile[Any]:
        with self.raises():
            data = literal_eval(source_file.read())

        return ConfigFile(data, config_format=self.processor_reg_name)


__all__ = (
    "PythonLiteralSL",
)
