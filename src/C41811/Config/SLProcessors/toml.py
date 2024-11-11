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
    import toml
except ImportError:
    raise ImportError("toml is not installed. Please install it with `pip install toml`") from None


C = TypeVar("C", bound=ABCConfig)


class TomlSL(ABCConfigSL):
    """
    Toml格式处理器
    """

    @property
    @override
    def regName(self) -> str:
        return "toml"

    @property
    @override
    def fileExt(self) -> list[str]:
        return [".toml"]

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
                toml.dump(config.data.data, f)
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
                data = toml.load(f)
            except Exception as e:
                raise FailedProcessConfigFileError(e) from e

        obj = config_cls(ConfigData(data), namespace=namespace, file_name=file_name, config_format=self.regName)

        return obj


def _register():
    return TomlSL()


__all__ = (
    "TomlSL",
)
