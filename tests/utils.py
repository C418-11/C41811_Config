# -*- coding: utf-8 -*-


import contextlib

from pytest import raises
from pytest import warns


@contextlib.contextmanager
def safe_raises(expected_exception, *args, **kwargs):
    if not expected_exception:
        yield None
        return

    with raises(expected_exception, *args, **kwargs) as err:
        yield err


@contextlib.contextmanager
def safe_warns(expected_warning, *args, **kwargs):
    if not expected_warning:
        yield None
        return

    with warns(expected_warning, *args, **kwargs) as warn:
        yield warn


__all__ = (
    "safe_raises",
    "safe_warns",
)
