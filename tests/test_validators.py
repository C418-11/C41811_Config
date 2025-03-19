# -*- coding: utf-8 -*-
# cython: language_level = 3

"""
大多数测试经过 :py:class:`RequiredPath` 包装后测试
所以存放在 `test_main.py`

.. versionadded:: 0.2.0
"""

from C41811.Config import FieldDefinition
from pytest import raises


def test_field_definition():
    FieldDefinition(str, "default")
    FieldDefinition(str | list, default_factory=list)
    with raises(ValueError):
        # noinspection PyArgumentList
        FieldDefinition(str | list, "default", default_factory=list)
