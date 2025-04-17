# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionchanged:: 0.2.0
   重构拆分 ``base.py`` 为多个文件
"""

import builtins
from collections import OrderedDict as __OrderedDict
from collections.abc import Mapping as __Mapping
from collections.abc import Sequence as __Sequence
from numbers import Number as __Number
from typing import Any as __Any

from .component import ComponentConfigData
from .component import ComponentMember
from .component import ComponentMeta
from .component import ComponentOrders
from .core import BasicConfigData
from .core import BasicConfigPool
from .core import BasicIndexedConfigData
from .core import BasicSingleConfigData
from .core import ConfigData
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
from ..abc import ABCIndexedConfigData

type AnyConfigData = (
        ABCConfigData[__Any]
        | ABCIndexedConfigData[__Any]
        | NoneConfigData
        | MappingConfigData[__Any]
        | StringConfigData[__Any]
        | SequenceConfigData[__Any]
        | BoolConfigData[__Any]
        | NumberConfigData[__Any]
        | ObjectConfigData[__Any]
)

ConfigData.TYPES = __OrderedDict((
    ((ABCConfigData,), lambda _: _),
    ((type(None),), NoneConfigData),
    ((__Mapping,), MappingConfigData),
    ((str, bytes), StringConfigData),
    ((__Sequence,), SequenceConfigData),
    ((bool,), BoolConfigData),
    ((__Number,), NumberConfigData),
    ((builtins.object,), ObjectConfigData),
))

ConfigData.register(NoneConfigData)
ConfigData.register(MappingConfigData)
ConfigData.register(SequenceConfigData)
ConfigData.register(NumberConfigData)
ConfigData.register(BoolConfigData)
ConfigData.register(StringConfigData)
ConfigData.register(ObjectConfigData)
ConfigData.register(ComponentConfigData)

__all__ = (
    "ComponentConfigData",
    "ComponentMember",
    "ComponentMeta",
    "ComponentOrders",

    "BasicConfigData",
    "BasicConfigPool",
    "BasicIndexedConfigData",
    "BasicSingleConfigData",
    "ConfigData",
    "ConfigFile",
    "PHelper",

    "EnvironmentConfigData",

    "MappingConfigData",

    "BoolConfigData",
    "NumberConfigData",

    "NoneConfigData",
    "ObjectConfigData",

    "SequenceConfigData",
    "StringConfigData",
)
