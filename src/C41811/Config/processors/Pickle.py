# -*- coding: utf-8 -*-
# cython: language_level = 3


import pickle
from typing import override

from .._protocols import SupportsReadAndReadline
from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..base import ConfigFile
from ..main import BasicLocalFileConfigSL


class PickleSL(BasicLocalFileConfigSL):
    """
    pickle格式处理器
    """

    @property
    @override
    def processor_reg_name(self) -> str:
        return "pickle"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".pickle",

    supported_file_classes = [ConfigFile]

    _s_open_kwargs = dict(mode="wb")

    @override
    def save_file(
            self,
            config_file: ABCConfigFile,
            target_file: SupportsWrite[bytes],
            *merged_args,
            **merged_kwargs
    ) -> None:
        with self.raises():
            pickle.dump(config_file.config.data, target_file, *merged_args, **merged_kwargs)

    _l_open_kwargs = dict(mode="rb")

    @override
    def load_file(
            self,
            source_file: SupportsReadAndReadline[bytes],
            *merged_args,
            **merged_kwargs
    ) -> ConfigFile:
        with self.raises():
            data = pickle.load(source_file, *merged_args, **merged_kwargs)

        return ConfigFile(data, config_format=self.processor_reg_name)


__all__ = (
    "PickleSL",
)
