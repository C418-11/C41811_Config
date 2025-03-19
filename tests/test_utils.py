# -*- coding: utf-8 -*-
# cython: language_level = 3


from pytest import mark
from C41811.Config.utils import CellType
from C41811.Config.utils import singleton
from C41811.Config.utils import Unset
from C41811.Config.utils import UnsetType


@mark.parametrize("cls", [singleton(type("A", (), {})), UnsetType])
def test_singleton(cls):
    assert cls() is cls()

    assert type(cls()) is cls
    assert type(cls())() is cls()

    assert hasattr(cls, "__singleton_instance__")
    assert cls() is getattr(cls, "__singleton_instance__")


def test_unset_type():
    assert UnsetType() is Unset
    assert UnsetType() is Unset

    assert not Unset

    repr(Unset)


def test_cell_type():
    cell = CellType("abc")
    assert "abc" in repr(cell)
    cell.cell_contents = 321
    assert "321" in repr(cell)
