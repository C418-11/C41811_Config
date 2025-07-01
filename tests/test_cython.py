import os
import re
import shutil
from collections.abc import Callable
from collections.abc import Iterable
from io import open_code
from pathlib import Path
from typing import cast

from pytest import importorskip
from pytest import mark
from pytest import skip

import C41811.Config

try:
    from setuptools import Extension
    from setuptools import setup
except ImportError:
    importorskip("setuptools")
    raise

try:
    from Cython.Build import cythonize  # type: ignore[attr-defined,import-not-found,unused-ignore]
except ImportError:
    importorskip("Cython.Build")
    raise

try:
    from mypyc.build import mypycify
except ImportError:
    importorskip("mypyc.build")
    raise


def src_files() -> Iterable[dict[str, str]]:
    source_dir = os.path.dirname(C41811.Config.__file__)

    for root, _, files in os.walk(source_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            yield {(file_path := os.path.join(root, file)): os.path.relpath(file_path, source_dir)}


def _compile(
    files: dict[str, str], tempdir: str, output_dir: str, *, compiler: Callable[[Iterable[str], str], list[Extension]]
) -> None:
    files_indexing = {os.path.splitext(os.path.splitroot(k)[2])[0]: k for k in files}
    # C:/root/path/to/file.py -> path/to/file

    extensions: list[Extension] = compiler(files.keys(), tempdir)

    for ext in extensions:
        for i, src in enumerate(ext.sources):
            rel_src, file_ext = os.path.splitext(os.path.relpath(src, tempdir))
            # temp/root/path/to/file.c -> path/to/file
            print("", files, files_indexing, rel_src, ext, sep="\n-------------------\n")  # noqa: T201
            rel_project = f"{tempdir}{os.sep}{files[files_indexing[rel_src]]}{file_ext}"
            # path/to/file -> C:/root/path/to/file.py -> temp/path/to/file.c

            ext.sources[i] = rel_project

            os.makedirs(os.path.dirname(rel_project), exist_ok=True)
            shutil.move(src, rel_project)

    setup(
        ext_modules=extensions,
        script_args=[
            "build_ext",
            "--build-temp",
            tempdir,
            "--build-lib",
            output_dir,
        ],
    )


@mark.parametrize("files", src_files())
def test_compile(tmpdir: Path, files: dict[str, str]) -> None:
    file_path = next(iter(files.keys()))

    tmpdir_len = len(str(tmpdir))
    if (tmpdir_len * 2 + len(file_path)) > 250:
        skip("path may longer than windows filesystem's default length")

    def _cython_compiler(fs: Iterable[str], target_dir: str) -> list[Extension]:
        return cast(
            list[Extension],
            cythonize(
                fs,
                nthreads=os.cpu_count() or 0,
                build_dir=target_dir,
                quiet=True,
            ),
        )

    def _mypyc_compiler(fs: Iterable[str], target_dir: str) -> list[Extension]:
        return mypycify(
            [*fs, "--check-untyped-defs"],
            target_dir=str(target_dir),
        )

    compiler = _cython_compiler
    with open_code(file_path) as f:
        if any(
            re.search(
                r"([a-zA-Z_][a-zA-Z0-9_]*\[[a-zA-Z_].*]\()"
                r"|(\[[a-zA-Z_][a-zA-Z0-9_]*:\s[^]]+])"
                r"|(type\s[a-zA-Z_][a-zA-Z0-9_]*\s=\s.+)",
                s.decode(),
            )
            for s in f
        ):
            # def func[T](arg: T) -> T: ...  # noqa: ERA001
            #         ^^^
            # def func[T: ...](arg: T) -> T: ...  # noqa: ERA001
            #         ^^^^^^^^
            # type D = Mapping | Sequence  # noqa: ERA001
            # ^^^^^^
            skip("cython unsupported syntax")
            compiler = _mypyc_compiler

    _compile(files, str(tmpdir), str(tmpdir), compiler=compiler)
