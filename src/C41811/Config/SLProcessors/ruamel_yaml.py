# -*- coding: utf-8 -*-
# cython: language_level = 3


from typing import override

from .._io_protocol import SupportsReadAndReadline
from .._io_protocol import SupportsWrite
from ..abc import ABCConfigFile
from ..base import ConfigData
from ..errors import FailedProcessConfigFileError
from ..main import BaseLocalFileConfigSL

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    from ruamel.yaml import YAML
except ImportError:
    raise ImportError("ruamel.yaml is not installed. Please install it with `pip install ruamel.yaml`") from None


class RuamelYamlSL(BaseLocalFileConfigSL):
    """
    基于ruamel.yaml的yaml处理器

    默认尝试最大限度保留yaml中的额外信息(如注释
    """
    yaml = YAML(typ="rt", pure=True)

    @property
    @override
    def processor_reg_name(self) -> str:
        return "ruamel_yaml"

    @property
    @override
    def file_ext(self) -> tuple[str, ...]:
        return ".yaml",

    def save_file(
            self,
            config_file: ABCConfigFile,
            target_file: SupportsWrite[str],
            *merged_args,
            **merged_kwargs
    ) -> None:
        try:
            self.yaml.dump(config_file.data.data, target_file)
        except Exception as e:
            raise FailedProcessConfigFileError(e) from e

    @override
    def load_file[C: ABCConfigFile](
            self, config_file_cls: type[C],
            source_file: SupportsReadAndReadline[str],
            *merged_args,
            **merged_kwargs
    ) -> C:
        try:
            data = self.yaml.load(source_file)
        except Exception as e:
            raise FailedProcessConfigFileError(e) from e

        return config_file_cls(ConfigData(data), config_format=self.processor_reg_name)


__all__ = (
    "RuamelYamlSL",
)
