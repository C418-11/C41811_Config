# cython: language_level = 3  # noqa: ERA001

"""
C41811.Config 旨在通过提供一套简洁的 API 和灵活的配置处理机制，来简化配置文件的管理。
无论是简单的键值对配置，还是复杂的嵌套结构，都能轻松应对。
它不仅支持多种配置格式，还提供了丰富的错误处理和验证功能，确保配置数据的准确性和一致性。

文档：https://C41811Config.readthedocs.io
"""  # noqa: RUF002, D205

__author__ = "C418____11 <C418-11@qq.com>"

from typing import TYPE_CHECKING as __TYPE_CHECKING

if __TYPE_CHECKING:  # pragma: no cover
    from .basic import *  # noqa: F403
    from .main import *  # noqa: F403
    from .path import *  # noqa: F403
    from .processor import *  # noqa: F403
    from .validators import *  # noqa: F403
else:
    from .basic import __all__ as __basic_all
    from .lazy_import import lazy_import as __lazy_import
    from .processor import __all__ as __processor_all

    __all__, __getattr__ = __lazy_import(
        {
            **dict.fromkeys(__processor_all, ".processor"),
            **dict.fromkeys(__basic_all, ".basic"),
            "__version__": "._version",
            "__version_tuple__": "._version",
            "BasicChainConfigSL": ".main",
            "BasicCompressedConfigSL": ".main",
            "BasicConfigSL": ".main",
            "BasicLocalFileConfigSL": ".main",
            "ConfigPool": ".main",
            "ConfigRequirementDecorator": ".main",
            "DefaultConfigPool": ".main",
            "RequiredPath": ".main",
            "get": ".main",
            "load": ".main",
            "raises": ".main",
            "requireConfig": ".main",
            "save": ".main",
            "saveAll": ".main",
            "set_": ".main",
            "AttrKey": ".path",
            "IndexKey": ".path",
            "Path": ".path",
            "PathSyntaxParser": ".path",
            "ComponentValidatorFactory": ".validators",
            "DefaultValidatorFactory": ".validators",
            "FieldDefinition": ".validators",
            "ValidatorOptions": ".validators",
            "ValidatorTypes": ".validators",
            "pydantic_validator": ".validators",
        }
    )
    __all__.remove("__version__")
    __all__.remove("__version_tuple__")
