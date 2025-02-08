# -*- coding: utf-8 -*-
# cython: language_level = 3


import os
from contextlib import contextmanager, suppress

from pytest import raises

from C41811.Config.safe_writer import LockFlags
from C41811.Config.safe_writer import acquire_lock
from C41811.Config.safe_writer import release_lock


@contextmanager
def cleanup(file):
    try:
        yield file
    finally:
        file.close()
        with suppress(Exception):
            release_lock(file)
        with suppress(Exception):
            os.unlink(file.name)


def test_acquire_lock(tmp_path):
    with cleanup(open(tmp_path / "test.txt", mode="w")) as file:
        acquire_lock(file, LockFlags.EXCLUSIVE)
        if os.name == "nt":
            with raises(TimeoutError):
                acquire_lock(file, LockFlags.EXCLUSIVE, timeout=0)
    with cleanup(open(tmp_path / "test.txt", mode="w")) as file:
        acquire_lock(file, LockFlags.SHARED)
        acquire_lock(file, LockFlags.SHARED, timeout=0)
