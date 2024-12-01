# -*- coding: utf-8 -*-
# cython: language_level = 3


from typing import Optional
from typing import TypeVar
from typing import override

from ..abc import ABCConfigFile
from ..errors import FailedProcessConfigFileError
from ..main import BaseConfigSL
from ..main import ConfigData

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    from ruamel.yaml import YAML
except ImportError:
    raise ImportError("ruamel.yaml is not installed. Please install it with `pip install ruamel.yaml`") from None

C = TypeVar("C", bound=ABCConfigFile)


class RuamelYamlSL(BaseConfigSL):
    """
    基于ruamel.yaml的yaml处理器

    默认尝试最大限度保留yaml中的额外信息(如注释
    """
    yaml = YAML(typ="rt", pure=True)

    @property
    @override
    def reg_name(self) -> str:
        return "ruamel_yaml"

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
        file_path = self._get_file_path(config_file, root_path, namespace, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            try:
                self.yaml.dump(config_file.data.data, f)
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
                data = self.yaml.load(f)
            except Exception as e:
                raise FailedProcessConfigFileError(e) from e

        obj = config_file_cls(ConfigData(data), namespace=namespace, file_name=file_name, config_format=self.reg_name)

        return obj


__all__ = (
    "RuamelYamlSL",
)
