# cython: language_level = 3  # noqa: ERA001


"""
基本配置数据实现

.. versionchanged:: 0.2.0
   重构拆分 ``base.py`` 为多个文件

.. versionchanged:: 0.3.0
   重命名 ``base`` 为 ``basic``
"""

from builtins import object as __object
from collections import OrderedDict as __OrderedDict
from collections.abc import Mapping as __Mapping
from collections.abc import Sequence as __Sequence
from numbers import Number as __Number

from .component import ComponentConfigData
from .component import ComponentMember
from .component import ComponentMeta
from .component import ComponentOrders
from .core import BasicConfigData
from .core import BasicConfigPool
from .core import BasicIndexedConfigData
from .core import BasicSingleConfigData
from .core import ConfigDataFactory
from .core import ConfigFile
from .core import PHelper
from .environment import EnvironmentConfigData
from .mapping import MappingConfigData
from .number import BoolConfigData
from .number import NumberConfigData
from .object import NoneConfigData
from .object import ObjectConfigData
from .sequence import SequenceConfigData
from .sequence import StringConfigData
from ..abc import ABCConfigData

ConfigDataFactory.TYPES = __OrderedDict(
    (
        ((ABCConfigData,), lambda _: _),
        ((type(None),), NoneConfigData),
        ((__Mapping,), MappingConfigData),
        ((str, bytes), StringConfigData),
        ((__Sequence,), SequenceConfigData),
        ((bool,), BoolConfigData),
        ((__Number,), NumberConfigData),
        ((__object,), ObjectConfigData),
    )
)

__all__ = (
    "BasicConfigData",
    "BasicConfigPool",
    "BasicIndexedConfigData",
    "BasicSingleConfigData",
    "BoolConfigData",
    "ComponentConfigData",
    "ComponentMember",
    "ComponentMeta",
    "ComponentOrders",
    "ConfigDataFactory",
    "ConfigFile",
    "EnvironmentConfigData",
    "MappingConfigData",
    "NoneConfigData",
    "NumberConfigData",
    "ObjectConfigData",
    "PHelper",
    "SequenceConfigData",
    "StringConfigData",
)
