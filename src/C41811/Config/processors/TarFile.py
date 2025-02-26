# -*- coding: utf-8 -*-
# cython: language_level = 3


import itertools
import os
import tarfile
from dataclasses import dataclass
from enum import ReprEnum
from typing import override, Optional

from ..base import ConfigFile
from ..main import BasicCompressedConfigSL
from ..safe_writer import safe_open


@dataclass(frozen=True)
class CompressionType:
    full_name: str
    short_name: str | None


class CompressionTypes(CompressionType, ReprEnum):
    """
    压缩类型
    """

    ONLY_STORAGE = ("only-storage", None)

    GZIP = ("gzip", "gz")
    BZIP2 = ("bzip2", "bz2")
    LZMA = ("lzma", "xz")


class TarFileSL(BasicCompressedConfigSL):
    """
    tar格式处理器
    """

    def __init__(
            self,
            *,
            reg_alias: Optional[str] = None,
            create_dir: bool = True,
            compression: CompressionTypes | str | None | tuple[str, str | None] = CompressionTypes.ONLY_STORAGE
    ):
        """
        :param reg_alias: sl处理器注册别名
        :type reg_alias: Optional[str]
        :param create_dir: 是否创建目录
        :type create_dir: bool
        """
        super().__init__(reg_alias=reg_alias, create_dir=create_dir)

        if compression is None:
            compression = CompressionTypes.ONLY_STORAGE
        elif isinstance(compression, str):
            for compression_type in CompressionTypes:
                if compression in (compression_type.full_name, compression_type.short_name):
                    compression = compression_type
                    break
        self._compression: CompressionType = compression
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
    def compress_file(self, file_path: str, extract_dir: str):
        with (
            safe_open(file_path, "wb") as file,
            tarfile.open(mode=f"w:{self._short_name}", fileobj=file) as tar
        ):
            items = []
            for _, *items in os.walk(extract_dir):
                break
            for item in itertools.chain(*items):
                path = os.path.normpath(os.path.join(extract_dir, item))
                tar.add(path, arcname=item)

    @override
    def extract_file(self, file_path: str, extract_dir: str):
        with (
            safe_open(file_path, "rb") as file,
            tarfile.open(mode=f"r:{self._short_name}", fileobj=file) as tar
        ):
            tar.extractall(extract_dir)


__all__ = (
    "CompressionType",
    "CompressionTypes",
    "TarFileSL",
)
