# cython: language_level = 3  # noqa: ERA001


"""
对象类型配置数据实现

.. versionadded:: 0.2.0
"""

from typing import Literal
from typing import override

from .core import BasicSingleConfigData


class NoneConfigData(BasicSingleConfigData[None]):
    """
    空的配置数据

    .. versionadded:: 0.2.0
    """

    def __init__(self, data: None = None):
        """
        :param data: 配置的原始数据
        :type data: None
        """  # noqa: D205
        if data is not None:
            msg = f"{type(self).__name__} can only accept None as data"
            raise ValueError(msg)

        super().__init__(data)


class ObjectConfigData[D: object](BasicSingleConfigData[D]):
    """对象配置数据"""

    _data: D

    def __init__(self, data: D):
        """
        :param data: 配置的原始数据
        :type data: D

        .. caution::
           未默认做深拷贝，可能导致非预期行为
        """  # noqa: RUF002, D205
        super().__init__(None)  # type: ignore[arg-type]

        self._data: D = data

    @property
    @override
    def data_read_only(self) -> Literal[False]:
        """
        配置数据是否为只读

        :return: 配置数据是否为只读
        :rtype: Literal[False]

        .. note::
           该配置数据类始终认为配置数据非只读，使其能正确作为配置数据容器使用
        """  # noqa: RUF002
        return False

    @property  # type: ignore[explicit-override]  # mypy抽风
    @override
    def data(self) -> D:
        """
        配置的原始数据

        .. caution::
           未默认做深拷贝，可能导致非预期的行为

        .. versionchanged:: 0.3.0
           现在是可写属性
        """  # noqa: RUF002
        return self._data

    @data.setter
    def data(self, data: D) -> None:
        self._data = data


__all__ = (
    "NoneConfigData",
    "ObjectConfigData",
)
