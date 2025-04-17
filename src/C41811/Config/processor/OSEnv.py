# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

import os
from collections import OrderedDict
from copy import deepcopy
from typing import Any
from typing import override

from ..abc import ABCConfigFile
from ..abc import ABCSLProcessorPool
from ..base import ConfigFile
from ..base import EnvironmentConfigData
from ..main import BasicConfigSL


class OSEnvSL(BasicConfigSL):
    """
    :py:data:`os.environ` 格式处理器
    """

    @property
    @override
    def processor_reg_name(self) -> str:
        return "os.environ"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".os.env", ".os.environ"

    supported_file_classes = [ConfigFile]

    @override
    def save(
            self,
            processor_pool: ABCSLProcessorPool,
            config_file: ABCConfigFile[EnvironmentConfigData],
            root_path: str,
            namespace: str,
            file_name: str,
            *args: Any,
            **kwargs: Any
    ) -> None:
        cfg: EnvironmentConfigData = config_file.config
        diff = cfg.difference
        for updated in deepcopy(diff.updated):
            os.environ[updated] = cfg[updated]
            diff.updated.add(updated)
        for removed in deepcopy(diff.removed):
            del os.environ[removed]
            diff.removed.remove(removed)

    @override
    def load(
            self,
            processor_pool: ABCSLProcessorPool,
            root_path: str,
            namespace: str,
            file_name: str,
            *args: Any,
            **kwargs: Any
    ) -> ConfigFile[EnvironmentConfigData]:
        return ConfigFile(
            initial_config=EnvironmentConfigData(deepcopy(OrderedDict(os.environ))),
        )


__all__ = (
    "OSEnvSL",
)
