# -*- coding: utf-8 -*-


from pytest import raises

from C41811.Config import ConfigData
from C41811.Config import NoneConfigData
from C41811.Config import ObjectConfigData


def test_none_config_data() -> None:
    assert not NoneConfigData()

    with raises(ValueError):
        # noinspection PyTypeChecker
        NoneConfigData(NotImplemented)  # type: ignore[arg-type]


def test_object_config_data() -> None:
    class MyClass:
        ...

    obj = MyClass()
    data = ConfigData(obj)
    assert isinstance(data, ObjectConfigData)
    assert data.data == obj
    assert data.data_read_only is False
