# -*- coding: utf-8 -*-
# cython: language_level = 3


import pprint
from ast import literal_eval
from typing import override

from .._io_protocol import SupportsReadAndReadline
from .._io_protocol import SupportsWrite
from ..abc import ABCConfigFile
from ..base import ConfigData
from ..main import BaseLocalFileConfigSL


class PythonLiteralSL(BaseLocalFileConfigSL):
    """
    Python 字面量序列化处理器
    """

    @property
    @override
    def processor_reg_name(self) -> str:
        return "python_literal"

    @property
    @override
    def file_ext(self) -> tuple[str, ...]:
        return ".python_literal", ".pyl", ".py"

    @override
    def save_file(
            self,
            config_file: ABCConfigFile,
            target_file: SupportsWrite[str],
            *merged_args,
            **merged_kwargs
    ) -> None:
        with self.raises():
            target_file.write(pprint.pformat(config_file.data.data, *merged_args, **merged_kwargs))

    @override
    def load_file[C: ABCConfigFile](
            self, config_file_cls: type[C],
            source_file: SupportsReadAndReadline[str],
            *merged_args,
            **merged_kwargs
    ) -> C:
        with self.raises():
            data = literal_eval(source_file.read())

        return config_file_cls(ConfigData(data), config_format=self.processor_reg_name)


__all__ = (
    "PythonLiteralSL",
)
