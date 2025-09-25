# cython: language_level = 3  # noqa: ERA001


"""
Properties格式配置文件处理器

.. versionadded:: 0.3.0
"""

from typing import Any
from typing import override

from .._protocols import SupportsReadAndReadline
from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..basic.core import ConfigFile
from ..basic.jproperties import JPropertiesConfigData
from ..errors import DependencyNotFoundError
from ..main import BasicLocalFileConfigSL

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    import jproperties  # type: ignore[import-not-found]
except ImportError:
    dependency = "jproperties"
    raise DependencyNotFoundError(dependency) from None


class JPropertiesSL(BasicLocalFileConfigSL):
    """Properties格式处理器"""

    @property
    @override
    def processor_reg_name(self) -> str:
        return "jproperties"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return (".properties",)

    supported_file_classes = [ConfigFile]  # noqa: RUF012
    _s_open_kwargs = {"mode": "wb"}  # noqa: RUF012
    _l_open_kwargs = {"mode": "rb"}  # noqa: RUF012

    @override
    def save_file(
        self,
        config_file: ABCConfigFile[JPropertiesConfigData],
        target_file: SupportsWrite[bytes],
        *merged_args: Any,
        **merged_kwargs: Any,
    ) -> None:
        with self.raises():
            config_file.config.data.store(target_file, *merged_args, **merged_kwargs)

    @override
    def load_file(
        self, source_file: SupportsReadAndReadline[bytes], *merged_args: Any, **merged_kwargs: Any
    ) -> ConfigFile[JPropertiesConfigData]:
        with self.raises():
            data = jproperties.Properties()
            data.load(source_file, *merged_args, **merged_kwargs)

        return ConfigFile(JPropertiesConfigData(data), config_format=self.reg_name)


__all__ = ("JPropertiesSL",)
