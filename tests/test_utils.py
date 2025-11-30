from typing import Any
from typing import cast

from pytest import mark
from pytest import raises

from c41811.config import ComponentMember

# noinspection PyProtectedMember
from c41811.config.processor.component import _component_loader_kwargs_builder as component_loader_kwargs_builder
from c41811.config.utils import FrozenArguments
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
    # noinspection PyUnresolvedReferences
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


@mark.parametrize(
    "kwargs, member, expected",
    (
        ({}, None, {}),
        ({"config_formats": {None: "json"}, "extra": any}, None, {"config_formats": "json", "extra": any}),
        ({"config_formats": "json", "extra": any}, None, {"config_formats": "json", "extra": any}),
        ({"config_formats": {}, "extra": any}, None, {"extra": any}),
        ({"config_formats": {"foo.json": "json"}, "extra": any}, None, {"extra": any}),
        ({"config_formats": {"foo": "json"}, "extra": any}, None, {"extra": any}),
        ({}, ComponentMember("foo.json"), {}),
        (
            {"config_formats": "json", "extra": any},
            ComponentMember("foo.json"),
            {"config_formats": "json", "extra": any},
        ),
        (
            {"config_formats": "json", "extra": any},
            ComponentMember("foo.json", config_format="pickle"),
            {"config_formats": ["json", "pickle"], "extra": any},
        ),
        ({"config_formats": {None: "json"}, "extra": any}, ComponentMember("foo.json"), {"extra": any}),
        ({"config_formats": {}, "extra": any}, ComponentMember("foo.json"), {"extra": any}),
        (
            {"config_formats": {"foo.json": "json", "bar": None}, "extra": any},
            ComponentMember("foo.json"),
            {"config_formats": "json", "extra": any},
        ),
        (
            {"config_formats": {"foo": "json", "bar": ["python"]}},
            ComponentMember("foo.json", alias="bar", config_format="json"),
            {"config_formats": ["python", "json"]},
        ),
    ),
)
def test_component_loader_kwargs_builder(
    kwargs: dict[str, Any], member: ComponentMember | None, expected: dict[str, Any]
) -> None:
    result = component_loader_kwargs_builder(kwargs)(member)
    assert result == expected, f"{result} != {expected}"


def test_frozen_arguments() -> None:
    efa = FrozenArguments()
    assert efa.args == ()
    assert efa.kwargs == {}

    arg: tuple[()] = ()
    kwarg: dict[str, Any] = {}
    efa = FrozenArguments(arg, kwarg)
    assert tuple(efa) == (arg, kwarg)
    assert efa | ((), {}) == FrozenArguments(arg, kwarg)
    assert efa | ((), {"a": 1}) == FrozenArguments(arg, {"a": 1})
    assert efa | ((1,), {}) == FrozenArguments((1,), kwarg)
    assert efa | ((1,), {"a": 1}) == FrozenArguments((1,), {"a": 1})

    fa = FrozenArguments((1, 2, 3, 4), {"a": 1, "b": 2})
    assert fa.args == (1, 2, 3, 4)
    assert fa.kwargs == {"a": 1, "b": 2}
    assert tuple(fa) == ((1, 2, 3, 4), {"a": 1, "b": 2})
    assert fa | ((), {}) == fa
    assert fa | ((-1,), {}) == FrozenArguments((-1, 2, 3, 4), {"a": 1, "b": 2})
    assert fa | ((-1, -2), {"a": 0}) == FrozenArguments((-1, -2, 3, 4), {"a": 0, "b": 2})

    with raises(TypeError):
        fa | None  # type: ignore[operator]
    assert fa != NotImplemented
