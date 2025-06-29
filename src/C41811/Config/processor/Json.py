# cython: language_level = 3  # noqa: N999


"""Json配置文件处理器"""

import json
from typing import Any
from typing import override

from .._protocols import SupportsReadAndReadline
from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..basic import ConfigFile
from ..main import BasicLocalFileConfigSL


class JsonSL(BasicLocalFileConfigSL):
    """json格式处理器"""

    @property
    @override
    def processor_reg_name(self) -> str:
        return "json"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return (".json",)

    supported_file_classes = [ConfigFile]  # noqa: RUF012

    @override
    def save_file(
        self, config_file: ABCConfigFile[Any], target_file: SupportsWrite[str], *merged_args: Any, **merged_kwargs: Any
    ) -> None:
        with self.raises():
            json.dump(config_file.config.data, target_file, *merged_args, **merged_kwargs)

    @override
    def load_file(
        self, source_file: SupportsReadAndReadline[str], *merged_args: Any, **merged_kwargs: Any
    ) -> ConfigFile[Any]:
        with self.raises():
            data = json.load(source_file, *merged_args, **merged_kwargs)

        return ConfigFile(data, config_format=self.processor_reg_name)


__all__ = ("JsonSL",)
