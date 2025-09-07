# cython: language_level = 3  # noqa: ERA001

# noinspection GrazieInspection
"""
SaveLoad处理器

.. versionchanged:: 0.2.0
   重命名 ``SLProcessors`` 为 ``processor``
"""

from typing import TYPE_CHECKING as __TYPE_CHECKING

if __TYPE_CHECKING:  # pragma: no cover
    from .cbor2 import CBOR2SL
    from .component import ComponentMetaParser
    from .component import ComponentSL
    from .hjson import HJsonSL
    from .jproperties import JPropertiesSL
    from .json import JsonSL
    from .os_env import OSEnvSL
    from .pickle import PickleSL
    from .plaintext import PlainTextSL
    from .python import PythonSL
    from .python_literal import PythonLiteralSL
    from .pyyaml import PyYamlSL
    from .rtoml import RTomlSL
    from .ruamel_yaml import RuamelYamlSL
    from .tarfile import TarCompressionTypes
    from .tarfile import TarFileSL
    from .tomlkit import TomlKitSL
    from .zipfile import ZipCompressionTypes
    from .zipfile import ZipFileSL

    __all__ = [
        "CBOR2SL",
        "ComponentMetaParser",
        "ComponentSL",
        "HJsonSL",
        "JPropertiesSL",
        "JsonSL",
        "OSEnvSL",
        "PickleSL",
        "PlainTextSL",
        "PyYamlSL",
        "PythonLiteralSL",
        "PythonSL",
        "RTomlSL",
        "RuamelYamlSL",
        "TarCompressionTypes",
        "TarFileSL",
        "TomlKitSL",
        "ZipCompressionTypes",
        "ZipFileSL",
    ]
else:
    from ..lazy_import import lazy_import as __lazy_import

    __all__, __getattr__ = __lazy_import(
        {
            "CBOR2SL": ".cbor2",
            "ComponentMetaParser": ".component",
            "ComponentSL": ".component",
            "HJsonSL": ".hjson",
            "JPropertiesSL": ".jproperties",
            "JsonSL": ".json",
            "OSEnvSL": ".os_env",
            "PickleSL": ".pickle",
            "PlainTextSL": ".plaintext",
            "PyYamlSL": ".pyyaml",
            "PythonLiteralSL": ".python_literal",
            "PythonSL": ".python",
            "RTomlSL": ".rtoml",
            "RuamelYamlSL": ".ruamel_yaml",
            "TarCompressionTypes": ".tarfile",
            "TarFileSL": ".tarfile",
            "TomlKitSL": ".tomlkit",
            "ZipCompressionTypes": ".zipfile",
            "ZipFileSL": ".zipfile",
        }
    )
