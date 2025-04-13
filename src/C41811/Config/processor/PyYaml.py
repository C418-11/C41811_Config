# -*- coding: utf-8 -*-
# cython: language_level = 3


from typing import Any
from typing import override

from .._protocols import SupportsReadAndReadline
from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..base import ConfigFile
from ..main import BasicLocalFileConfigSL

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    import yaml
except ImportError:  # pragma: no cover
    raise ImportError("PyYaml is not installed. Please install it with `pip install PyYaml`") from None


class PyYamlSL(BasicLocalFileConfigSL):
    """
    基于PyYaml的yaml处理器
    """

    @property
    @override
    def processor_reg_name(self) -> str:
        return "yaml"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".yaml", ".yml"

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
            yaml.safe_dump(config_file.config.data, target_file, *merged_args, **merged_kwargs)

    @override
    def load_file(
            self,
            source_file: SupportsReadAndReadline[str],
            *merged_args: Any,
            **merged_kwargs: Any
    ) -> ConfigFile[Any]:
        with self.raises():
            data = yaml.safe_load(source_file)

        return ConfigFile(data, config_format=self.processor_reg_name)


__all__ = (
    "PyYamlSL",
)
