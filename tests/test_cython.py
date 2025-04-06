# -*- coding: utf-8 -*-

import os
import re
import shutil
from collections.abc import Iterable
from io import open_code

from pytest import importorskip
from pytest import mark
from pytest import skip

import C41811.Config

try:
    from setuptools import setup
    from setuptools import Extension
except ImportError:
    importorskip("setuptools")
    raise

try:
    from Cython.Build import cythonize
except ImportError:
    importorskip("Cython.Build")
    raise


def src_files() -> Iterable[dict[str, str]]:
    source_dir = os.path.dirname(C41811.Config.__file__)

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            yield {(file_path := os.path.join(root, file)): os.path.relpath(file_path, source_dir)}


def _compile(files: dict[str, str], tempdir: str, output_dir: str):
    files_indexing = {os.path.splitext(os.path.splitroot(k)[2])[0]: k for k in files}
    # C:/root/path/to/file.py -> path/to/file

    extensions: list[Extension] = cythonize(
        files.keys(),
        nthreads=os.cpu_count() or 0,
        build_dir=tempdir,
        quiet=True,
    )

    for ext in extensions:
        for i, src in enumerate(ext.sources):
            rel_src, file_ext = os.path.splitext(os.path.relpath(src, tempdir))
            # temp/root/path/to/file.c -> path/to/file
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
def test_compile(tmpdir, files):
    file_path = list(files.keys())[0]

    tmpdir_len = len(str(tmpdir))
    if (tmpdir_len * 2 + len(file_path)) > 250:
        skip("path may longer than windows filesystem's default length")
    with open_code(file_path) as f:
        if any((re.search(r"(\[[A-Z_]+:\s[^]]+])|(type\s[a-zA-Z_][a-zA-Z0-9_]*\s=\s.+)", s.decode()) for s in f)):
            # def func[T: Any](arg: T) -> T: ...
            #         ^^^^^^^^
            # type D = Mapping | Sequence
            # ^^^^^^
            skip("cython unsupported syntax")

    _compile(files, tmpdir, tmpdir)
