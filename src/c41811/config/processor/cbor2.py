# cython: language_level = 3  # noqa: ERA001


"""
CBOR配置文件处理器

.. versionadded:: 0.3.0
"""

from typing import IO
from typing import Any
from typing import override

from ..abc import ABCConfigFile
from ..basic.core import ConfigFile
from ..errors import DependencyNotFoundError
from ..main import BasicLocalFileConfigSL

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    import cbor2
except ImportError:
    dependency = "cbor2"
    raise DependencyNotFoundError(dependency) from None


class CBOR2SL(BasicLocalFileConfigSL):
    """CBOR格式处理器"""

    @property
    @override
    def processor_reg_name(self) -> str:
        return "cbor"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return (".cbor",)

    supported_file_classes = [ConfigFile]  # noqa: RUF012
    _s_open_kwargs = {"mode": "wb"}  # noqa: RUF012
    _l_open_kwargs = {"mode": "rb"}  # noqa: RUF012

    @override
    def save_file(
        self, config_file: ABCConfigFile[Any], target_file: IO[bytes], *merged_args: Any, **merged_kwargs: Any
    ) -> None:
        with self.raises():
            cbor2.dump(config_file.config.data, target_file, *merged_args, **merged_kwargs)

    @override
    def load_file(self, source_file: IO[bytes], *merged_args: Any, **merged_kwargs: Any) -> ConfigFile[Any]:
        with self.raises():
            data = cbor2.load(source_file, *merged_args, **merged_kwargs)

        return ConfigFile(data, config_format=self.reg_name)


__all__ = ("CBOR2SL",)
