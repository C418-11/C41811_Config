# -*- coding: utf-8 -*-
# cython: language_level = 3

from copy import deepcopy
from typing import Optional
from typing import override

from ..abc import ABCConfigFile
from ..errors import FailedProcessConfigFileError
from ..main import BaseConfigSL
from ..main import ConfigData

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    import yaml
except ImportError:
    raise ImportError("PyYaml is not installed. Please install it with `pip install PyYaml`") from None


class PyYamlSL(BaseConfigSL):
    """
    基于PyYaml的yaml处理器
    """

    @property
    @override
    def reg_name(self) -> str:
        return "yaml"

    @property
    @override
    def file_ext(self) -> list[str]:
        return [".yaml"]

    @override
    def save(
            self,
            config_file: ABCConfigFile,
            root_path: str,
            namespace: Optional[str],
            file_name: Optional[str],
            *args,
            **kwargs
    ) -> None:
        new_args = deepcopy(self.save_arg[0])[:len(args)] = args
        new_kwargs = deepcopy(self.save_arg[1]) | kwargs

        file_path = self._get_file_path(config_file, root_path, namespace, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            try:
                yaml.safe_dump(config_file.data.data, f, *new_args, **new_kwargs)
            except Exception as e:
                raise FailedProcessConfigFileError(e) from e

    @override
    def load[C: ABCConfigFile](
            self,
            config_file_cls: type[C],
            root_path: str,
            namespace: Optional[str],
            file_name: Optional[str],
            *args,
            **kwargs
    ) -> C:
        with open(self._norm_join(root_path, namespace, file_name), 'r', encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except Exception as e:
                raise FailedProcessConfigFileError(e) from e
        obj = config_file_cls(ConfigData(data), namespace=namespace, file_name=file_name, config_format=self.reg_name)

        return obj


__all__ = (
    "PyYamlSL",
)
