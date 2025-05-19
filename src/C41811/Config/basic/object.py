# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

from typing import Literal
from typing import Optional
from typing import cast
from typing import override

from .core import BasicSingleConfigData


class NoneConfigData(BasicSingleConfigData[None]):
    """
    空的配置数据

    .. versionadded:: 0.2.0
    """

    def __init__(self, data: Optional[None] = None):
        """
        :param data: 配置的原始数据
        :type data: None
        """

        if data is not None:
            raise ValueError(f"{type(self).__name__} can only accept None as data")

        super().__init__(data)

    def __bool__(self) -> Literal[False]:
        return False


class ObjectConfigData[D: object](BasicSingleConfigData[D]):
    """
    对象配置数据
    """
    _data: D

    def __init__(self, data: D):
        """
        :param data: 配置的原始数据
        :type data: Any

        .. caution::
           未默认做深拷贝，可能导致非预期行为
        """
        super().__init__(cast(D, None))

        self._data: D = data

    @override
    @property
    def data_read_only(self) -> Literal[False]:
        return False

    @override
    @property
    def data(self) -> D:
        """
        配置的原始数据

        :return: 配置的原始数据
        :rtype: Any

        .. caution::
           直接返回了原始对象，未默认进行深拷贝
        """
        return self._data


__all__ = (
    "NoneConfigData",
    "ObjectConfigData",
)
