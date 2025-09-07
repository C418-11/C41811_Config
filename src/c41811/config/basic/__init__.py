# cython: language_level = 3  # noqa: ERA001


"""
基本配置数据实现

.. versionchanged:: 0.2.0
   重构拆分 ``base.py`` 为多个文件

.. versionchanged:: 0.3.0
   重命名 ``base`` 为 ``basic``
"""

from typing import TYPE_CHECKING as __TYPE_CHECKING

if __TYPE_CHECKING:  # pragma: no cover
    from .component import ComponentConfigData
    from .component import ComponentMember
    from .component import ComponentMeta
    from .component import ComponentOrders
    from .core import BasicConfigData
    from .core import BasicConfigPool
    from .core import BasicIndexedConfigData
    from .core import BasicSingleConfigData
    from .core import ConfigFile
    from .core import PHelper
    from .environment import EnvironmentConfigData
    from .factory import ConfigDataFactory
    from .jproperties import JPropertiesConfigData
    from .mapping import MappingConfigData
    from .number import BoolConfigData
    from .number import NumberConfigData
    from .object import NoneConfigData
    from .object import ObjectConfigData
    from .sequence import SequenceConfigData
    from .sequence import StringConfigData

    __all__ = [
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
        "JPropertiesConfigData",
        "MappingConfigData",
        "NoneConfigData",
        "NumberConfigData",
        "ObjectConfigData",
        "PHelper",
        "SequenceConfigData",
        "StringConfigData",
    ]
else:
    from ..lazy_import import lazy_import as __lazy_import

    __all__, __getattr__ = __lazy_import(
        {
            "BasicConfigData": ".core",
            "BasicConfigPool": ".core",
            "BasicIndexedConfigData": ".core",
            "BasicSingleConfigData": ".core",
            "BoolConfigData": ".number",
            "ComponentConfigData": ".component",
            "ComponentMember": ".component",
            "ComponentMeta": ".component",
            "ComponentOrders": ".component",
            "ConfigFile": ".core",
            "EnvironmentConfigData": ".environment",
            "JPropertiesConfigData": ".jproperties",
            "MappingConfigData": ".mapping",
            "NoneConfigData": ".object",
            "NumberConfigData": ".number",
            "ObjectConfigData": ".object",
            "PHelper": ".core",
            "SequenceConfigData": ".sequence",
            "StringConfigData": ".sequence",
        }
    )
    __all__.append("ConfigDataFactory")

    def __cfg_data_factory_types_lazy_initializer() -> None:
        from builtins import object as __object  # noqa: PLC0415
        from collections import OrderedDict as __OrderedDict  # noqa: PLC0415
        from collections.abc import Mapping as __Mapping  # noqa: PLC0415
        from collections.abc import Sequence as __Sequence  # noqa: PLC0415
        from numbers import Number as __Number  # noqa: PLC0415

        from .mapping import MappingConfigData  # noqa: PLC0415
        from .number import BoolConfigData  # noqa: PLC0415
        from .number import NumberConfigData  # noqa: PLC0415
        from .object import NoneConfigData  # noqa: PLC0415
        from .object import ObjectConfigData  # noqa: PLC0415
        from .sequence import SequenceConfigData  # noqa: PLC0415
        from .sequence import StringConfigData  # noqa: PLC0415
        from ..abc import ABCConfigData  # noqa: PLC0415

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

    from .factory import ConfigDataFactory

    ConfigDataFactory._TYPES_LAZY_INITIALIZER = __cfg_data_factory_types_lazy_initializer  # noqa: SLF001
