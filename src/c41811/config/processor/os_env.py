# cython: language_level = 3  # noqa: ERA001


"""
环境变量配置数据处理器

.. versionadded:: 0.2.0
"""

import os
from collections import OrderedDict
from copy import deepcopy
from typing import Any
from typing import override

from ..abc import ABCConfigFile
from ..abc import ABCSLProcessorPool
from ..basic.core import ConfigFile
from ..basic.environment import EnvironmentConfigData
from ..main import BasicConfigSL


class OSEnvSL(BasicConfigSL):
    """:py:data:`os.environ` 格式处理器"""

    def __init__(self, *, reg_alias: str | None = None, prefix: str = "", strip_prefix: bool = False):
        """
        :param reg_alias: sl处理器注册别名
        :type reg_alias: str | None
        :param prefix: (从环境变量)导出的环境变量前缀，留空则为所有
        :type prefix: str
        :param strip_prefix: (从环境变量)导出时是否去除前缀，导入(到环境变量)时会自动加回
        :type strip_prefix: bool

        .. versionchanged:: 0.3.0
           添加参数 ``prefix``
           添加参数 ``strip_prefix``
        """  # noqa: RUF002, D205
        super().__init__(reg_alias=reg_alias)
        self.prefix = prefix
        self.strip_prefix = strip_prefix

    @property
    @override
    def processor_reg_name(self) -> str:
        return "os.environ"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".os.env", ".os.environ"

    supported_file_classes = [ConfigFile]  # noqa: RUF012

    @override
    def save(
        self,
        processor_pool: ABCSLProcessorPool,
        config_file: ABCConfigFile[EnvironmentConfigData],
        root_path: str,
        namespace: str,
        file_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        cfg: EnvironmentConfigData = config_file.config
        diff = cfg.difference
        is_striped = self.strip_prefix and self.prefix

        for updated in deepcopy(diff.updated):
            env_key = f"{self.prefix}{updated}" if is_striped else updated
            os.environ[env_key] = cfg[updated]
            diff.updated.add(updated)
        for removed in deepcopy(diff.removed):
            env_key = f"{self.prefix}{removed}" if is_striped else removed
            del os.environ[env_key]
            diff.removed.remove(removed)

    @override
    def load(
        self,
        processor_pool: ABCSLProcessorPool,
        root_path: str,
        namespace: str,
        file_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> ConfigFile[EnvironmentConfigData]:
        if not self.prefix:
            return ConfigFile(EnvironmentConfigData(OrderedDict(os.environ)))
        filtered_env = OrderedDict()
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                config_key = key[len(self.prefix) :] if self.strip_prefix else key
                filtered_env[config_key] = value

        return ConfigFile(EnvironmentConfigData(filtered_env))


__all__ = ("OSEnvSL",)
