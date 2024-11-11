# -*- coding: utf-8 -*-
# cython: language_level = 3

__author__ = "C418____11 <553515788@qq.com>"
__version__ = "0.0.1"

import sys as _sys

if _sys.version_info < (3, 12):
    raise RuntimeError("Python version must be >= 3.12")

from .main import *
from .errors import *

__all__ = (
    "abc",
    "errors",
    "main",
    "__version__",
)
