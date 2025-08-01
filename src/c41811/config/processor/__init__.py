# cython: language_level = 3  # noqa: ERA001

# noinspection GrazieInspection
"""
SaveLoad处理器

.. versionchanged:: 0.2.0
   重命名 ``SLProcessors`` 为 ``processor``
"""

from typing import TYPE_CHECKING as __TYPE_CHECKING

if __TYPE_CHECKING:  # pragma: no cover
    from .component import ComponentMetaParser  # noqa: F401
    from .component import ComponentSL  # noqa: F401
    from .hjson import HJsonSL  # noqa: F401
    from .json import JsonSL  # noqa: F401
    from .os_env import OSEnvSL  # noqa: F401
    from .pickle import PickleSL  # noqa: F401
    from .plaintext import PlainTextSL  # noqa: F401
    from .python import PythonSL  # noqa: F401
    from .python_literal import PythonLiteralSL  # noqa: F401
    from .pyyaml import PyYamlSL  # noqa: F401
    from .ruamel_yaml import RuamelYamlSL  # noqa: F401
    from .tarfile import TarCompressionTypes  # noqa: F401
    from .tarfile import TarFileSL  # noqa: F401
    from .toml import TomlSL  # noqa: F401
    from .zipfile import ZipCompressionTypes  # noqa: F401
    from .zipfile import ZipFileSL  # noqa: F401

else:
    from ..utils import lazy_import as __lazy_import

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
