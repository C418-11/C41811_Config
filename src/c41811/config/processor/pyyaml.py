# cython: language_level = 3  # noqa: ERA001


"""基于PyYAML的YAML格式处理器"""

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
    import yaml
except ImportError:
    dependency = "PyYAML"
    raise DependencyNotFoundError(dependency) from None


class PyYamlSL(BasicLocalFileConfigSL):
    """基于PyYAML的YAML格式处理器"""

    @property
    @override
    def processor_reg_name(self) -> str:
        return "yaml"

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
            yaml.safe_dump(config_file.config.data, target_file, *merged_args, **merged_kwargs)

    @override
    def load_file(
        self, source_file: SupportsReadAndReadline[str], *merged_args: Any, **merged_kwargs: Any
    ) -> ConfigFile[Any]:
        with self.raises():
            data = yaml.safe_load(source_file)

        return ConfigFile(data, config_format=self.reg_name)


__all__ = ("PyYamlSL",)
