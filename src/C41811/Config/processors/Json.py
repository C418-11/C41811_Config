# -*- coding: utf-8 -*-
# cython: language_level = 3


import json
from typing import override

from .._protocols import SupportsReadAndReadline
from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..base import LocalConfigFile
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
    def file_match(self) -> tuple[str, ...]:
        return ".json",

    supported_file_classes = [LocalConfigFile]

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
    def load_file(
            self,
            source_file: SupportsReadAndReadline[str],
            *merged_args,
            **merged_kwargs
    ) -> LocalConfigFile:
        with self.raises():
            data = json.load(source_file, *merged_args, **merged_kwargs)

        return LocalConfigFile(data, config_format=self.processor_reg_name)


__all__ = (
    "JsonSL",
)
