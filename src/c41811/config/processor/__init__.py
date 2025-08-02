# cython: language_level = 3  # noqa: ERA001

# noinspection GrazieInspection
"""
SaveLoad处理器

.. versionchanged:: 0.2.0
   重命名 ``SLProcessors`` 为 ``processor``
"""

from typing import TYPE_CHECKING as __TYPE_CHECKING

if __TYPE_CHECKING:  # pragma: no cover
    from .component import ComponentMetaParser
    from .component import ComponentSL
    from .hjson import HJsonSL
    from .json import JsonSL
    from .os_env import OSEnvSL
    from .pickle import PickleSL
    from .plaintext import PlainTextSL
    from .python import PythonSL
    from .python_literal import PythonLiteralSL
    from .pyyaml import PyYamlSL
    from .ruamel_yaml import RuamelYamlSL
    from .tarfile import TarCompressionTypes
    from .tarfile import TarFileSL
    from .toml import TomlSL
    from .zipfile import ZipCompressionTypes
    from .zipfile import ZipFileSL

    __all__ = [
        "ComponentMetaParser",
        "ComponentSL",
        "HJsonSL",
        "JsonSL",
        "OSEnvSL",
        "PickleSL",
        "PlainTextSL",
        "PyYamlSL",
        "PythonLiteralSL",
        "PythonSL",
        "RuamelYamlSL",
        "TarCompressionTypes",
        "TarFileSL",
        "TomlSL",
        "ZipCompressionTypes",
        "ZipFileSL",
    ]
else:
    from ..lazy_import import lazy_import as __lazy_import

    __all__, __getattr__ = __lazy_import(
        {
            "ComponentSL": ".component",
            "ComponentMetaParser": ".component",
            "HJsonSL": ".hjson",
            "JsonSL": ".json",
            "OSEnvSL": ".os_env",
            "PickleSL": ".pickle",
            "PlainTextSL": ".plaintext",
            "PythonSL": ".python",
            "PythonLiteralSL": ".python_literal",
            "PyYamlSL": ".pyyaml",
            "RuamelYamlSL": ".ruamel_yaml",
            "TarFileSL": ".tarfile",
            "TarCompressionTypes": ".tarfile",
            "TomlSL": ".toml",
            "ZipFileSL": ".zipfile",
            "ZipCompressionTypes": ".zipfile",
        }
    )
