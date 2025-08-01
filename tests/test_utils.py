from typing import cast

from pytest import mark
from pytest import raises

from c41811.config.utils import Ref
from c41811.config.utils import Unset
from c41811.config.utils import UnsetType
from c41811.config.utils import singleton


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


def test_lazy_import() -> None:
    import fixtures.mock_lazy_import as mock_lazy_import  # noqa: PLC0415

    assert mock_lazy_import.__all__ == ["Available", "MissingDependency", "SubAvailable", "SubMissingDependency"]
    assert mock_lazy_import.sub_pkg.__all__ == ["SubAvailable", "SubMissingDependency"]

    from fixtures.mock_lazy_import import Available  # noqa: PLC0415

    assert Available == "Available"
    assert mock_lazy_import.__all__ == ["Available", "MissingDependency", "SubAvailable", "SubMissingDependency"]
    assert mock_lazy_import.sub_pkg.__all__ == ["SubAvailable", "SubMissingDependency"]

    with raises(ImportError, match="MissingDependency"):
        from fixtures.mock_lazy_import import MissingDependency  # noqa: PLC0415, F401
    assert mock_lazy_import.__all__ == ["Available", "SubAvailable", "SubMissingDependency"]
    assert mock_lazy_import.sub_pkg.__all__ == ["SubAvailable", "SubMissingDependency"]

    from fixtures.mock_lazy_import import SubAvailable  # noqa: PLC0415

    assert SubAvailable == "SubAvailable"
    assert mock_lazy_import.__all__ == ["Available", "SubAvailable", "SubMissingDependency"]
    assert mock_lazy_import.sub_pkg.__all__ == ["SubAvailable", "SubMissingDependency"]

    with raises(ImportError, match="SubMissingDependency"):
        from fixtures.mock_lazy_import import SubMissingDependency  # noqa: PLC0415, F401
    assert mock_lazy_import.__all__ == ["Available", "SubAvailable"]
    assert mock_lazy_import.sub_pkg.__all__ == ["SubAvailable"]
