# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

import itertools
import os
import tarfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import ReprEnum
from typing import Any
from typing import IO
from typing import Literal
from typing import Optional
from typing import cast
from typing import override

from ..base import ConfigFile
from ..main import BasicCompressedConfigSL
from ..safe_writer import safe_open


@dataclass(frozen=True)
class TarCompressionType:
    full_name: str
    short_name: str | None


class TarCompressionTypes(TarCompressionType, ReprEnum):
    """
    压缩类型
    """

    ONLY_STORAGE = ("only-storage", None)

    GZIP = ("gzip", "gz")
    BZIP2 = ("bzip2", "bz2")
    LZMA = ("lzma", "xz")


type ExtractionFilter = (Literal["fully_trusted", "tar", "data"]
                         | Callable[[tarfile.TarInfo, str], tarfile.TarInfo | None])


class TarFileSL(BasicCompressedConfigSL):
    """
    tar格式处理器
    """

    def __init__(
            self,
            *,
            reg_alias: Optional[str] = None,
            create_dir: bool = True,
            compression: TarCompressionTypes | str | None = TarCompressionTypes.ONLY_STORAGE,
            compress_level: Optional[Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9] | int] = None,
            extraction_filter: Optional[ExtractionFilter] = "data",
    ):
        """
        :param reg_alias: sl处理器注册别名
        :type reg_alias: Optional[str]
        :param create_dir: 是否创建目录
        :type create_dir: bool
        :param compression: 压缩类型
        :type compression: TarCompressionTypes | str | None
        :param compress_level: 压缩等级
        :type compress_level: Optional[Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9] | int]
        :param extraction_filter: 解压过滤器
        :type extraction_filter:
            Optional[Literal["fully_trusted", "tar", "data"] | Callable[[tarfile.TarInfo, str], tarfile.TarInfo | None]]
        """
        super().__init__(reg_alias=reg_alias, create_dir=create_dir)

        if compression is None:
            compression = TarCompressionTypes.ONLY_STORAGE
        elif isinstance(compression, str):
            for compression_type in TarCompressionTypes:
                if compression in (compression_type.full_name, compression_type.short_name):
                    compression = compression_type
                    break

        self._compression: TarCompressionType = cast(TarCompressionTypes, compression)
        self._compress_level: int | None = compress_level
        self._extraction_filter: ExtractionFilter | None = extraction_filter
        self._short_name = '' if self._compression.short_name is None else self._compression.short_name

    @property
    @override
    def processor_reg_name(self) -> str:
        return f"tarfile:{self._short_name}"

    @override
    @property
    def namespace_suffix(self) -> str:
        safe_name = self.processor_reg_name.replace(':', '-')
        return os.path.join(super().namespace_suffix, f"${safe_name}~")

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        if self._compression.short_name is None:
            return ".tar",
        return f".tar.{self._compression.short_name}", f".tar.{self._compression.full_name}"

    supported_file_classes = [ConfigFile]

    @override
    def compress_file(self, file_path: str, extract_dir: str) -> None:
        kwargs: dict[str, Any] = {}
        if self._compress_level is not None:
            # noinspection SpellCheckingInspection
            kwargs["compresslevel"] = self._compress_level
        with (
            safe_open(file_path, "wb") as file,
            tarfile.open(
                mode=cast(Literal["w:", "w:gz", "w:bz2", "w:xz"], f"w:{self._short_name}"),
                fileobj=cast(IO[bytes], file), **kwargs
            ) as tar
        ):
            for root, dirs, files in os.walk(extract_dir):
                for item in itertools.chain(dirs, files):
                    path = os.path.normpath(os.path.join(root, item))
                    tar.add(path, arcname=os.path.relpath(path, extract_dir), recursive=False)

    @override
    def extract_file(self, file_path: str, extract_dir: str) -> None:
        with (
            safe_open(file_path, "rb") as file,
            tarfile.open(
                mode=cast(Literal["r:", "r:gz", "r:bz2", "r:xz"], f"r:{self._short_name}"),
                fileobj=cast(IO[bytes], file)
            ) as tar
        ):
            # py3.12不传入filter会发出警告 https://peps.python.org/pep-0706/#defaults-and-their-configuration
            tar.extractall(extract_dir, filter=self._extraction_filter)


__all__ = (
    "TarCompressionType",
    "TarCompressionTypes",
    "TarFileSL",
)
