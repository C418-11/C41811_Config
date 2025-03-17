# -*- coding: utf-8 -*-
# cython: language_level = 3


from C41811.Config.utils import singleton


def test_singleton():
    @singleton
    class A:
        ...

    assert A() is A()

    assert type(A()) is A
    assert type(A())() is A()

    assert hasattr(A, "__singleton_instance__")
    assert A() is getattr(A, "__singleton_instance__")
