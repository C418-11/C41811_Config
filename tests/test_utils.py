from typing import cast

from pytest import mark

from C41811.Config.utils import Ref
from C41811.Config.utils import Unset
from C41811.Config.utils import UnsetType
from C41811.Config.utils import singleton


@mark.parametrize("cls", [singleton(cast(type[object], type("A", (), {}))), UnsetType])
def test_singleton(cls: type) -> None:
    assert cls() is cls()

    assert type(cls()) is cls
    assert type(cls())() is cls()

    assert hasattr(cls, "__singleton_instance__")
    assert cls() is cls.__singleton_instance__


def test_unset_type() -> None:
    assert UnsetType() is Unset
    assert UnsetType() is Unset

    assert not Unset

    repr(Unset)
    str(Unset)


def test_ref() -> None:
    ref = Ref("abc")
    assert "abc" in repr(ref)
    ref.value = 321  # type: ignore[assignment]
    assert "321" in repr(ref)
