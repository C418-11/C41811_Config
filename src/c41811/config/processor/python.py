# cython: language_level = 3  # noqa: ERA001


"""
Python脚本配置文件处理器

.. versionadded:: 0.2.0
"""

from typing import Any
from typing import cast
from typing import override

from .._protocols import SupportsReadAndReadline
from ..abc import ABCConfigFile
from ..basic.core import ConfigFile
from ..basic.mapping import MappingConfigData
from ..main import BasicLocalFileConfigSL


class PythonSL(BasicLocalFileConfigSL):
    """
    Python格式处理器

    .. caution::
       非安全沙箱执行！确保文件为受信任来源！

    .. hint::
       仅作抛砖引玉，实际并不见得好用，但是你可以参考这个实现自己的自定义SL处理器

    .. versionchanged:: 0.3.0
       支持配置文件保存
    """  # noqa: RUF002

    @property
    @override
    def processor_reg_name(self) -> str:
        return "python"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return (".py",)

    supported_file_classes = [ConfigFile]  # noqa: RUF012
    _s_open_kwargs = {"mode": "r", "encoding": "utf-8"}  # noqa: RUF012

    @override
    def save_file(
        self,
        config_file: ABCConfigFile[MappingConfigData[dict[str, Any]]],
        target_file: SupportsReadAndReadline[str],
        *merged_args: Any,
        **merged_kwargs: Any,
    ) -> None:
        with self.raises():
            exec(target_file.read(), {}, config_file.config.data)  # noqa: S102

    @override
    def load_file(
        self, source_file: SupportsReadAndReadline[str], *merged_args: Any, **merged_kwargs: Any
    ) -> ConfigFile[MappingConfigData[dict[str, Any]]]:
        names: dict[str, Any] = {}
        with self.raises():
            exec(source_file.read(), {}, names)  # noqa: S102

        return cast(ConfigFile[MappingConfigData[dict[str, Any]]], ConfigFile(names, config_format=self.reg_name))


__all__ = ("PythonSL",)
