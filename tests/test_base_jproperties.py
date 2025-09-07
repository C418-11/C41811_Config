from collections import OrderedDict
from collections.abc import Mapping

import jproperties  # type: ignore[import-not-found]
from pytest import mark

from c41811.config import JPropertiesConfigData


def test_init() -> None:
    assert JPropertiesConfigData().data.properties == {}
    data = {"key": "value", "foo": "bar", "test": "value"}
    assert JPropertiesConfigData(data).data.properties == data
    properties = jproperties.Properties()
    properties["key"] = "value"
    assert JPropertiesConfigData(properties).data.properties == {"key": "value"}
    ordered_properties = JPropertiesConfigData(OrderedDict({"a": "", "b": "", "c": ""}))
    assert ordered_properties.data._key_order == ["a", "b", "c"]  # noqa: SLF001


type PropertyData = Mapping[str, str | tuple[str, dict[str, str]]] | None


@mark.parametrize(
    "a, b, is_eq",
    [
        (None, None, True),
        ({}, {}, True),
        ({"key": "value"}, {"key": "value"}, True),
        ({"key": "value"}, {"key": "value2"}, False),
        ({"key": "value", "foo": "bar"}, {"key": "value", "foo": "bar"}, True),
        ({"key": ("value", {"meta": "data"}), "foo": "bar"}, {"key": ("value", {"meta": "data"}), "foo": "bar"}, True),
        (OrderedDict({"key": "value", "foo": "bar"}), OrderedDict({"key": "value", "foo": "bar"}), True),
        (OrderedDict({"key": "value", "foo": "bar"}), OrderedDict({"foo": "bar", "key": "value"}), False),
        (
            OrderedDict({"key": ("value", {"meta": "data"}), "foo": "bar"}),
            OrderedDict({"key": ("value", {"meta": "data"}), "foo": "bar"}),
            True,
        ),
        (
            OrderedDict({"key": ("value", {"meta": "data"}), "foo": "bar"}),
            OrderedDict({"foo": "bar", "key": ("value", {"meta": "data"})}),
            False,
        ),
    ],
)
def test_eq(a: PropertyData, b: PropertyData, is_eq: bool) -> None:  # noqa: FBT001
    assert JPropertiesConfigData(a) != NotImplemented
    assert JPropertiesConfigData(b) != NotImplemented
    assert (JPropertiesConfigData(a) == JPropertiesConfigData(b)) is is_eq


def test_repr() -> None:
    assert repr(JPropertiesConfigData()).count("{}") == 2
    assert repr(JPropertiesConfigData()).count("[]") == 1
    assert repr(JPropertiesConfigData()) == repr(JPropertiesConfigData())
    data = {"key": "value"}
    assert repr(data) in repr(JPropertiesConfigData(data))
    assert repr(list(data.keys())) in repr(JPropertiesConfigData(data))
