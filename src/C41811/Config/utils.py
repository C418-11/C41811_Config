# -*- coding: utf-8 -*-
# cython: language_level = 3

"""
.. versionadded:: 0.2.0
"""

from contextlib import suppress
from typing import Any


def singleton(cls):
    """
    单例模式类装饰器
    """

    def __new__(c, *args, **kwargs):
        if not hasattr(c, "__singleton_instance__"):
            c.__singleton_instance__ = c.__singleton_new__(c, *args, **kwargs)

        # noinspection PyProtectedMember
        return c.__singleton_instance__

    __new__.__name__ = cls.__new__.__name__
    __new__.__qualname__ = cls.__new__.__qualname__
    __new__.__doc__ = cls.__new__.__doc__
    __new__.__module__ = cls.__new__.__module__
    with suppress(AttributeError):
        __new__.__annotations__ = cls.__new__.__annotations__

    cls.__singleton_new__ = cls.__new__
    cls.__new__ = __new__

    return cls


@singleton
class UnsetType:
    """
    用于填充默认值的特殊值
    """

    def __str__(self):
        return "<Unset Argument>"

    def __bool__(self):
        return False


Unset = UnsetType()
"""
用于填充默认值的特殊值
"""


class CellType[C: Any]:
    """
    间接持有对象引用
    """

    def __init__(self, contents: C):
        self.cell_contents = contents

    def __repr__(self):
        return f"<{type(self).__name__} ({self.cell_contents!r})>"


__all__ = (
    "singleton",
    "UnsetType",
    "Unset",
    "CellType",
)
