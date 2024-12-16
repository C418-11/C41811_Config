# C41811.Config

[English](README_EN.md) | 中文

---

[![PyPI pyversions](https://img.shields.io/pypi/pyversions/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)
[![PyPI - License](https://img.shields.io/pypi/l/C41811.Config?color=blue)](https://github.com/C418-11/C41811_Config/blob/main/LICENSE)

|  文档  |                                                                                                                                              [![Documentation Status](https://readthedocs.org/projects/c41811config/badge/?version=latest)](https://C41811Config.readthedocs.io) [![made-with-sphinx-doc](https://img.shields.io/badge/Made%20with-Sphinx-1f425f.svg)](https://www.sphinx-doc.org/)                                                                                                                                              |
|:----:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| PyPI |                                                                                              [![PyPI - Version](https://img.shields.io/pypi/v/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI - Wheel](https://img.shields.io/pypi/wheel/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI download month](https://img.shields.io/pypi/dm/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)                                                                                               |
|  源码  | [![Static Badge](https://img.shields.io/badge/Github-C41811.Config-green?logo=github)](https://github.com/C418-11/C41811_Config/) [![Python CI](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml/badge.svg?branch=develop)](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml) [![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-publish.yml)](https://github.com/C418-11/C41811_Config/actions/workflows/python-publish.yml) |

## 简介

C41811.Config 是一个功能强大且易于使用的配置管理包，旨在简化配置文件的读取和写入操作。它支持多种流行的配置格式，
包括 JSON、YAML、TOML 和 Pickle，满足不同项目的需求。通过模块化的设计，C41811.Config 提供了可靠的配置处理解决方案，
帮助开发者快速构建和维护高质量的应用程序。

## 安装

```commandline
pip install C41811.Config
```

## 一个简单的示例

```python
from C41811.Config import JsonSL
from C41811.Config import requireConfig
from C41811.Config import saveAll

JsonSL().register_to()

cfg = requireConfig(
    '', "Hello World.json",
    {
        "Hello": "World",
        "foo": dict,  # 包含foo下的所有键
        "foo\\.bar": {  # foo.bar仅包含baz键
            "baz": "qux"
        }
    }
).check()
saveAll()

print(cfg)
print()
print(f"{cfg["Hello"]=}")
print(cfg.foo)
print(cfg["foo"]["bar"])
print(cfg.foo.bar.baz)
```
