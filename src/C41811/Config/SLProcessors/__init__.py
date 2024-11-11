# -*- coding: utf-8 -*-
# cython: language_level = 3

from .json import JsonSL
from .pickle import PickleSL


def _import_modules(module_names):
    """
    给定一个模块名称列表，尝试导入这些模块，并将模块中的所有公开名称添加到全局命名空间中。

    参数:
    - module_names: 一个包含模块名称的列表。
    """
    for module_name in module_names:
        try:
            exec(f"from .{module_name} import *", globals())
        except ImportError:
            pass


_import_modules([
    "pyyaml",
    "ruamel_yaml",
    "toml",
])
