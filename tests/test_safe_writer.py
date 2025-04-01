# -*- coding: utf-8 -*-


import os
from contextlib import contextmanager
from contextlib import suppress
from typing import IO

from pytest import mark
from pytest import raises

from C41811.Config.safe_writer import LockFlags
from C41811.Config.safe_writer import acquire_lock
from C41811.Config.safe_writer import release_lock
from C41811.Config.safe_writer import safe_open


@contextmanager
def cleanup(file: IO):
    try:
        yield file
    finally:
        file.close()
        with suppress(Exception):
            release_lock(file)
        with suppress(Exception):
            os.unlink(file.name)


@mark.parametrize("flag", [LockFlags.EXCLUSIVE, LockFlags.SHARED])
def test_acquire_lock(tmp_path, flag):
    with cleanup(open(tmp_path / "test.txt", mode="w")) as file:
        acquire_lock(file, flag)


def test_repeat_acquire_lock(tmp_path):
    with cleanup(open(tmp_path / "test.txt", mode="w")) as file:
        acquire_lock(file, LockFlags.SHARED)
        acquire_lock(file, LockFlags.SHARED)


def test_acquire_lock_immediately_release(tmp_path):
    with cleanup(open(tmp_path / "test.txt", mode="w")) as file:
        acquire_lock(file, LockFlags.EXCLUSIVE, immediately_release=True)
        acquire_lock(file, LockFlags.EXCLUSIVE, immediately_release=True)


if os.name == "nt":
    @mark.parametrize("timeout", [0, 0.05, 0.1])
    def test_acquire_timeout(tmp_path, timeout):
        with cleanup(open(tmp_path / "test.txt", mode="w")) as file:
            acquire_lock(file, LockFlags.EXCLUSIVE)
            with raises(TimeoutError):
                acquire_lock(file, LockFlags.EXCLUSIVE, timeout=timeout)


class TestSafeOpen:
    def test_atomic(self, tmp_path):
        with suppress(RuntimeError), safe_open(tmp_path / "test.txt", mode="w") as file:
            file.write("test")
            raise RuntimeError
        with cleanup(file):
            assert not os.path.exists(tmp_path / "test.txt")

    if os.name == "nt":
        def test_lock(self, tmp_path):
            with safe_open(tmp_path / "test.txt", mode="w") as file:
                file.write("foo")
                with raises(TimeoutError), safe_open(tmp_path / "test.txt", mode="w", timeout=.1) as file2:
                    file2.write("bar")
            with cleanup(file), open(tmp_path / "test.txt") as file:
                assert file.read() == "foo"
