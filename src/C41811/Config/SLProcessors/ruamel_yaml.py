# -*- coding: utf-8 -*-
# cython: language_level = 3


from typing import Optional
from typing import TypeVar
from typing import override

from ..abc import ABCConfig
from ..abc import ABCConfigSL
from ..errors import FailedProcessConfigFileError
from ..main import ConfigData

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    from ruamel.yaml import YAML
except ImportError:
    raise ImportError("ruamel.yaml is not installed. Please install it with `pip install ruamel.yaml`") from None

C = TypeVar("C", bound=ABCConfig)


class RuamelYamlSL(ABCConfigSL):
    """
    基于ruamel.yaml的yaml处理器

    默认尝试最大限度保留yaml中的额外信息(如注释
    """
    yaml = YAML(typ="rt", pure=True)

    @property
    @override
    def regName(self) -> str:
        return "ruamel_yaml"

    @property
    @override
    def fileExt(self) -> list[str]:
        return [".yaml"]

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
        file_path = self._getFilePath(config, root_path, namespace, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            try:
                self.yaml.dump(config.data.data, f)
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
        with open(self._norm_join(root_path, namespace, file_name), 'r', encoding="utf-8") as f:
            try:
                data = self.yaml.load(f)
            except Exception as e:
                raise FailedProcessConfigFileError(e) from e

        obj = config_cls(ConfigData(data), namespace=namespace, file_name=file_name, config_format=self.regName)

        return obj


def _register():
    return RuamelYamlSL()


__all__ = (
    "RuamelYamlSL",
)
