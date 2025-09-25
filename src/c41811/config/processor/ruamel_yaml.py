# cython: language_level = 3  # noqa: ERA001


"""基于ruamel.yaml的YAML格式处理器"""

from typing import Any
from typing import override

from .._protocols import SupportsReadAndReadline
from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..basic.core import ConfigFile
from ..errors import DependencyNotFoundError
from ..main import BasicLocalFileConfigSL

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    from ruamel.yaml import YAML
except ImportError:
    dependency = "ruamel.yaml"
    raise DependencyNotFoundError(dependency) from None


class RuamelYamlSL(BasicLocalFileConfigSL):
    """
    基于ruamel.yaml的YAML格式处理器

    默认尝试最大限度保留yaml中的额外信息(如注释
    """

    yaml = YAML(typ="rt", pure=True)

    @property
    @override
    def processor_reg_name(self) -> str:
        return "ruamel_yaml"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".yaml", ".yml"

    supported_file_classes = [ConfigFile]  # noqa: RUF012

    @override
    def save_file(
        self, config_file: ABCConfigFile[Any], target_file: SupportsWrite[str], *merged_args: Any, **merged_kwargs: Any
    ) -> None:
        with self.raises():
            self.yaml.dump(config_file.config.data, target_file)

    @override
    def load_file(
        self, source_file: SupportsReadAndReadline[str], *merged_args: Any, **merged_kwargs: Any
    ) -> ConfigFile[Any]:
        with self.raises():
            data = self.yaml.load(source_file)

        return ConfigFile(data, config_format=self.reg_name)


__all__ = ("RuamelYamlSL",)
