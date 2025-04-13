# -*- coding: utf-8 -*-
# cython: language_level = 3


from collections.abc import Mapping
from collections.abc import MutableMapping
from typing import Any
from typing import cast
from typing import override

from .. import MappingConfigData
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
            config_file: ABCConfigFile[MappingConfigData[Mapping[str, Any]]],
            target_file: SupportsWrite[str],
            *merged_args: Any,
            **merged_kwargs: Any,
    ) -> None:
        with self.raises():
            toml.dump(config_file.config.data, target_file)

    @override
    def load_file(
            self,
            source_file: SupportsReadAndReadline[str],
            *merged_args: Any,
            **merged_kwargs: Any,
    ) -> ConfigFile[MappingConfigData[MutableMapping[str, Any]]]:
        with self.raises():
            data = toml.load(source_file)

        return cast(
            ConfigFile[MappingConfigData[MutableMapping[str, Any]]],
            ConfigFile(data, config_format=self.processor_reg_name)
        )


__all__ = (
    "TomlSL",
)
