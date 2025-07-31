from pytest import raises

from c41811.config import ConfigDataFactory
from c41811.config import NoneConfigData
from c41811.config import ObjectConfigData


def test_none_config_data() -> None:
    assert not NoneConfigData()

    with raises(ValueError):
        # noinspection PyTypeChecker
        NoneConfigData(NotImplemented)  # type: ignore[arg-type]


def test_object_config_data() -> None:
    class MyClass: ...

    obj = MyClass()
    data = ConfigDataFactory(obj)
    assert isinstance(data, ObjectConfigData)
    assert data.data == obj
    assert data.data_read_only is False
