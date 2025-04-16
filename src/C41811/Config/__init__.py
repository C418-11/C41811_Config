# -*- coding: utf-8 -*-
# cython: language_level = 3

"""
C41811.Config 旨在通过提供一套简洁的 API 和灵活的配置处理机制，来简化配置文件的管理。
无论是简单的键值对配置，还是复杂的嵌套结构，都能轻松应对。
它不仅支持多种配置格式，还提供了丰富的错误处理和验证功能，确保配置数据的准确性和一致性。

文档：https://C41811Config.readthedocs.io
"""

__author__ = "C418____11 <C418-11@qq.com>"

try:
    from ._version import __version__, __version_tuple__
except ImportError:  # pragma: no cover
    __version__ = ''
    __version_tuple__ = ()

import sys as __sys

if __sys.version_info < (3, 12):  # pragma: no cover
    raise RuntimeError("Python version must be >= 3.12")

from .base import *  # noqa: F401, F403
from .main import *  # noqa: F401, F403
from .path import *  # noqa: F401, F403
from .validators import *  # noqa: F401, F403
from .processor import *  # noqa: F401, F403
