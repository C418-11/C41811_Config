# -*- coding: utf-8 -*-
# cython: language_level = 3

"""
.. versionadded:: 0.1.6
"""


from contextlib import suppress


def singleton(cls):
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


__all__ = (
    "singleton",
)
