# -*- coding: utf-8 -*-
# cython: language_level = 3


import json
from copy import deepcopy
from typing import Optional
from typing import TypeVar
from typing import override

from ..abc import ABCConfig
from ..abc import ABCConfigSL
from ..errors import FailedProcessConfigFileError
from ..main import ConfigData

C = TypeVar("C", bound=ABCConfig)


class JsonSL(ABCConfigSL):
    """
    json格式处理器
    """

    @property
    @override
    def regName(self) -> str:
        return "json"

    @property
    @override
    def fileExt(self) -> list[str]:
        return [".json"]

    @override
    def save(
            self,
            config: ABCConfig,
            root_path: str,
            namespace: Optional[str],
            file_name: Optional[str],
            *args,
            **kwargs
    ) -> None:
        new_args = deepcopy(self.save_arg[0])[:len(args)] = args
        new_kwargs = deepcopy(self.save_arg[1]) | kwargs

        file_path = self._getFilePath(config, root_path, namespace, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            try:
                json.dump(config.data.data, f, *new_args, **new_kwargs)
            except Exception as e:
                raise FailedProcessConfigFileError(e) from e

    @override
    def load(
            self,
            config_cls: type[C],
            root_path: str,
            namespace: Optional[str],
            file_name: Optional[str],
            *args,
            **kwargs
    ) -> C:
        new_args = deepcopy(self.load_arg[0])[:len(args)] = args
        new_kwargs = deepcopy(self.load_arg[1]) | kwargs

        with open(self._norm_join(root_path, namespace, file_name), "r", encoding="utf-8") as f:
            try:
                data = json.load(f, *new_args, **new_kwargs)
            except Exception as e:
                raise FailedProcessConfigFileError(e) from e

        obj = config_cls(ConfigData(data), namespace=namespace, file_name=file_name, config_format=self.regName)

        return obj


__all__ = (
    "JsonSL",
)
