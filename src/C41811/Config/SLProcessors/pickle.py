# -*- coding: utf-8 -*-
# cython: language_level = 3


import pickle
from copy import deepcopy
from typing import Optional
from typing import TypeVar
from typing import override

from ..abc import ABCConfigFile
from ..errors import FailedProcessConfigFileError
from ..main import BaseConfigSL
from ..main import ConfigData

C = TypeVar("C", bound=ABCConfigFile)


class PickleSL(BaseConfigSL):
    """
    pickle格式处理器
    """

    @property
    @override
    def reg_name(self) -> str:
        return "pickle"

    @property
    @override
    def file_ext(self) -> list[str]:
        return [".pickle"]

    @override
    def save(
            self,
            config: ABCConfigFile,
            root_path: str,
            namespace: Optional[str],
            file_name: Optional[str],
            *args,
            **kwargs
    ) -> None:
        new_args = deepcopy(self.save_arg[0])[:len(args)] = args
        new_kwargs = deepcopy(self.save_arg[1]) | kwargs

        file_path = self._get_file_path(config, root_path, namespace, file_name)
        with open(file_path, "wb") as f:
            try:
                pickle.dump(config.data.data, f, *new_args, **new_kwargs)
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
        new_args = deepcopy(self.load_arg[0])[len(args)] = args
        new_kwargs = deepcopy(self.load_arg[1]) | kwargs

        with open(self._norm_join(root_path, namespace, file_name), "rb") as f:
            try:
                data = pickle.load(f, *new_args, **new_kwargs)
            except Exception as e:
                raise FailedProcessConfigFileError(e) from e

        obj = config_cls(ConfigData(data), namespace=namespace, file_name=file_name, config_format=self.reg_name)

        return obj


__all__ = (
    "PickleSL",
)
