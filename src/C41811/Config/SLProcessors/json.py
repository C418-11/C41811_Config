# -*- coding: utf-8 -*-
# cython: language_level = 3


import json
from typing import override

from .._protocols import SupportsReadAndReadline
from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..base import ConfigData
from ..main import BaseLocalFileConfigSL


class JsonSL(BaseLocalFileConfigSL):
    """
    json格式处理器
    """

    @property
    @override
    def processor_reg_name(self) -> str:
        return "json"

    @property
    @override
    def file_ext(self) -> tuple[str, ...]:
        return ".json",

    @override
    def save_file(
            self,
            config_file: ABCConfigFile,
            target_file: SupportsWrite[str],
            *merged_args,
            **merged_kwargs
    ) -> None:
        with self.raises():
            json.dump(config_file.data.data, target_file, *merged_args, **merged_kwargs)

    @override
    def load_file[C: ABCConfigFile](
            self, config_file_cls: type[C],
            source_file: SupportsReadAndReadline[str],
            *merged_args,
            **merged_kwargs
    ) -> C:
        with self.raises():
            data = json.load(source_file, *merged_args, **merged_kwargs)

        return config_file_cls(ConfigData(data), config_format=self.processor_reg_name)


__all__ = (
    "JsonSL",
)
