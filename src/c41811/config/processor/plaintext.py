# cython: language_level = 3  # noqa: ERA001


"""
纯文本配置文件处理器

.. versionadded:: 0.2.0
"""

from typing import Any
from typing import TextIO
from typing import cast
from typing import override

from .._protocols import SupportsWrite
from ..abc import ABCConfigFile
from ..basic.core import ConfigFile
from ..basic.factory import ConfigDataFactory
from ..basic.sequence import SequenceConfigData
from ..basic.sequence import StringConfigData
from ..main import BasicLocalFileConfigSL


class PlainTextSL(BasicLocalFileConfigSL):
    """纯文本格式处理器"""

    @property
    @override
    def processor_reg_name(self) -> str:
        return "plaintext"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".md", ".markdown", ".rst", ".txt"

    supported_file_classes = [ConfigFile]  # noqa: RUF012

    @override
    def save_file(
        self,
        config_file: ABCConfigFile[StringConfigData[Any] | SequenceConfigData[Any]],
        target_file: SupportsWrite[str],
        *merged_args: Any,
        **merged_kwargs: Any,
    ) -> None:
        if isinstance(config_file.config, StringConfigData):
            with self.raises():
                target_file.write(config_file.config.data)
            return

        with self.raises():
            iter(config_file.config)

        linesep = merged_kwargs.get("linesep", "")
        for line in config_file.config:
            with self.raises():
                target_file.write(line + linesep)

    @override
    def load_file(
        self, source_file: TextIO, *merged_args: Any, **merged_kwargs: Any
    ) -> ConfigFile[StringConfigData[str] | SequenceConfigData[list[str]]]:
        if merged_kwargs.get("split_line"):
            with self.raises():
                content: list[str] = source_file.readlines()
            if merged_kwargs.get("remove_linesep"):
                for i, line in enumerate(content):
                    content[i] = line.removesuffix(merged_kwargs.get("remove_linesep", ""))
        else:
            with self.raises():
                content: str = source_file.read()  # type: ignore[no-redef]

        return ConfigFile(
            cast(StringConfigData[str] | SequenceConfigData[list[Any]], ConfigDataFactory(content)),
            config_format=self.reg_name,
        )


__all__ = ("PlainTextSL",)
