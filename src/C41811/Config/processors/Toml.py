# -*- coding: utf-8 -*-
# cython: language_level = 3


from typing import override

from .._protocols import SupportsReadAndReadline
from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..base import ConfigFile
from ..main import BasicLocalFileConfigSL

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    import toml
except ImportError:  # pragma: no cover
    raise ImportError("toml is not installed. Please install it with `pip install toml`") from None


class TomlSL(BasicLocalFileConfigSL):
    """
    Toml格式处理器
    """

    @property
    @override
    def processor_reg_name(self) -> str:
        return "toml"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".toml",

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
            toml.dump(config_file.data.data, target_file)

    @override
    def load_file(
            self,
            source_file: SupportsReadAndReadline[str],
            *merged_args,
            **merged_kwargs
    ) -> ConfigFile:
        with self.raises():
            data = toml.load(source_file)

        return ConfigFile(data, config_format=self.processor_reg_name)


__all__ = (
    "TomlSL",
)
