# cython: language_level = 3  # noqa: ERA001


"""Pickle配置文件处理器"""

import pickle
from typing import Any
from typing import override

from .._protocols import SupportsReadAndReadline
from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..basic.core import ConfigFile
from ..main import BasicLocalFileConfigSL


class PickleSL(BasicLocalFileConfigSL):
    """
    pickle格式处理器

    .. versionchanged:: 0.2.0
       添加 ``.pkl`` 文件后缀支持
    """

    @property
    @override
    def processor_reg_name(self) -> str:
        return "pickle"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".pickle", ".pkl"

    supported_file_classes = [ConfigFile]  # noqa: RUF012
    _s_open_kwargs = {"mode": "wb"}  # noqa: RUF012
    _l_open_kwargs = {"mode": "rb"}  # noqa: RUF012

    @override
    def save_file(
        self,
        config_file: ABCConfigFile[Any],
        target_file: SupportsWrite[bytes],
        *merged_args: Any,
        **merged_kwargs: Any,
    ) -> None:
        with self.raises():
            pickle.dump(config_file.config.data, target_file, *merged_args, **merged_kwargs)

    @override
    def load_file(
        self,
        source_file: SupportsReadAndReadline[bytes],
        *merged_args: Any,
        **merged_kwargs: Any,
    ) -> ConfigFile[Any]:
        with self.raises():
            data = pickle.load(source_file, *merged_args, **merged_kwargs)  # noqa: S301

        return ConfigFile(data, config_format=self.reg_name)


__all__ = ("PickleSL",)
