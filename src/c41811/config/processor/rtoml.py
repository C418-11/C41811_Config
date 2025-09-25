# cython: language_level = 3  # noqa: ERA001


"""
基于rtoml的TOML格式处理器"

.. versionadded:: 0.3.0
"""

from collections.abc import Mapping
from collections.abc import MutableMapping
from typing import Any
from typing import TextIO
from typing import cast
from typing import override

from ..abc import ABCConfigFile
from ..basic.core import ConfigFile
from ..basic.mapping import MappingConfigData
from ..errors import DependencyNotFoundError
from ..main import BasicLocalFileConfigSL

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    import rtoml
except ImportError:
    dependency = "rtoml"
    raise DependencyNotFoundError(dependency) from None


class RTomlSL(BasicLocalFileConfigSL):
    """基于rtoml的TOML格式处理器"""

    @property
    @override
    def processor_reg_name(self) -> str:
        return "rtoml"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return (".toml",)

    supported_file_classes = [ConfigFile]  # noqa: RUF012

    @override
    def save_file(
        self,
        config_file: ABCConfigFile[MappingConfigData[Mapping[str, Any]]],
        target_file: TextIO,
        *merged_args: Any,
        **merged_kwargs: Any,
    ) -> None:
        with self.raises():
            rtoml.dump(config_file.config.data, target_file, *merged_args, **merged_kwargs)

    @override
    def load_file(
        self,
        source_file: TextIO,
        *merged_args: Any,
        **merged_kwargs: Any,
    ) -> ConfigFile[MappingConfigData[MutableMapping[str, Any]]]:
        with self.raises():
            data = rtoml.load(source_file, *merged_args, **merged_kwargs)

        return cast(
            ConfigFile[MappingConfigData[MutableMapping[str, Any]]],
            ConfigFile(data, config_format=self.reg_name),
        )


__all__ = ("RTomlSL",)
