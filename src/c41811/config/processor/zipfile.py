# cython: language_level = 3  # noqa: ERA001


"""
Zip压缩配置文件处理器

.. versionadded:: 0.2.0
"""

import itertools
import os
import zipfile
from dataclasses import dataclass
from enum import ReprEnum
from typing import Literal
from typing import cast
from typing import override

from ..basic.core import ConfigFile
from ..main import BasicCompressedConfigSL
from ..safe_writer import safe_open


@dataclass(frozen=True)
class ZipCompressionType:
    """压缩类型数据结构"""

    full_name: str
    short_name: str | None
    zipfile_constant: int


class ZipCompressionTypes(ZipCompressionType, ReprEnum):
    """压缩类型"""

    ONLY_STORAGE = ("only-storage", None, zipfile.ZIP_STORED)

    ZIP = ("zip", "zip", zipfile.ZIP_DEFLATED)
    BZIP2 = ("bzip2", "bz2", zipfile.ZIP_BZIP2)
    LZMA = ("lzma", "xz", zipfile.ZIP_LZMA)


class ZipFileSL(BasicCompressedConfigSL):
    """zip格式处理器"""

    def __init__(
        self,
        *,
        reg_alias: str | None = None,
        create_dir: bool = True,
        compression: ZipCompressionTypes | str | int | None = ZipCompressionTypes.ONLY_STORAGE,
        compress_level: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9] | int | None = None,
    ):
        """
        :param reg_alias: sl处理器注册别名
        :type reg_alias: str | None
        :param create_dir: 是否创建目录
        :type create_dir: bool
        :param compression: 压缩类型
        :type compression: ZipCompressionTypes | str | int | None
        :param compress_level: 压缩等级
        :type compress_level: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9] | int | None
        """  # noqa: D205
        super().__init__(reg_alias=reg_alias, create_dir=create_dir)

        if compression is None:
            compression = ZipCompressionTypes.ONLY_STORAGE
        elif isinstance(compression, str | int):
            for compression_type in ZipCompressionTypes:
                if compression in (
                    compression_type.full_name,
                    compression_type.short_name,
                    compression_type.zipfile_constant,
                ):
                    compression = compression_type
                    break

        self._compression: ZipCompressionType = cast(ZipCompressionTypes, compression)
        self._compress_level: int | None = compress_level
        self._short_name = "" if self._compression.short_name is None else self._compression.short_name

    @property
    @override
    def processor_reg_name(self) -> str:
        return f"zipfile:{self._short_name}-{self._compress_level}"

    @property
    @override
    def namespace_suffix(self) -> str:
        safe_name = self.processor_reg_name.replace(":", "-")
        return os.path.join(super().namespace_suffix, f"${safe_name}~")

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        if self._compression.short_name is None:
            return f".{self._compress_level}.zip", ".zip"
        return (
            f".{self._compress_level}.{self._compression.full_name}",
            f".{self._compress_level}.{self._compression.short_name}",
            f".{self._compression.short_name}",
            f".{self._compression.full_name}",
        )

    supported_file_classes = [ConfigFile]  # noqa: RUF012

    @override
    def compress_file(self, file_path: str, extract_dir: str) -> None:
        with (
            safe_open(file_path, "wb") as file,
            zipfile.ZipFile(
                file, mode="w", compression=self._compression.zipfile_constant, compresslevel=self._compress_level
            ) as zip_file,
        ):
            for root, dirs, files in os.walk(extract_dir):
                for item in itertools.chain(dirs, files):
                    path = os.path.normpath(os.path.join(root, item))
                    zip_file.write(path, arcname=os.path.relpath(path, extract_dir))

    @override
    def extract_file(self, file_path: str, extract_dir: str) -> None:
        with safe_open(file_path, "rb") as file, zipfile.ZipFile(file) as zip_file:
            zip_file.extractall(extract_dir)


__all__ = (
    "ZipCompressionType",
    "ZipCompressionTypes",
    "ZipFileSL",
)
