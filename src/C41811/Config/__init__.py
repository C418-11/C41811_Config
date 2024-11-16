# -*- coding: utf-8 -*-
# cython: language_level = 3

"""
一个功能强大且易于使用的配置管理包，简化配置文件的读取和写入操作。
支持多种流行的配置格式，如 JSON、YAML、TOML 和 Pickle

文档：https://C41811Config.readthedocs.io
"""

__author__ = "C418____11 <553515788@qq.com>"

try:
    from ._version import __version__, __version_tuple__
except ImportError:
    __version__ = ''
    __version_tuple__ = ()

import sys as _sys

if _sys.version_info < (3, 12):
    raise RuntimeError("Python version must be >= 3.12")

from .SLProcessors import *
from .main import *
