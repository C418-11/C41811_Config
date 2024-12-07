# C41811.Config

[English](README_EN.md) | 中文

---

[![PyPi version](https://badgen.net/pypi/v/c41811.config/)](https://pypi.org/project/C41811.Config)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)
[![Documentation Status](https://readthedocs.org/projects/c41811config/badge/?version=latest)](https://C41811Config.readthedocs.io)
[![PyPi license](https://badgen.net/pypi/license/c41811.config/)](https://pypi.org/project/C41811.Config/)
[![PyPI download month](https://img.shields.io/pypi/dm/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)
[![made-with-sphinx-doc](https://img.shields.io/badge/Made%20with-Sphinx-1f425f.svg)](https://www.sphinx-doc.org/)

| 文档   | https://C41811Config.readthedocs.io      |
|------|------------------------------------------|
| PyPI | https://pypi.org/project/C41811.Config   |
| 源码   | https://github.com/C418-11/C41811_Config |

## 简介

C41811.Config 是一个功能强大且易于使用的配置管理包，旨在简化配置文件的读取和写入操作。它支持多种流行的配置格式，
包括 JSON、YAML、TOML 和 Pickle，满足不同项目的需求。通过模块化的设计，C41811.Config 提供了可靠的配置处理解决方案，
帮助开发者快速构建和维护高质量的应用程序。

## 安装

```commandline
pip install C41811.Config
```

## 一个简单的示例

``` python
from C41811.Config import JsonSL
from C41811.Config import DefaultConfigPool
from C41811.Config import requireConfig


JsonSL().registerTo()

cfg = requireConfig(
    '', "Hello World.json",
    {
        "Hello": "World",
        "foo": dict,  # 包含foo下的所有键
        "foo\\.bar": {  # foo.bar仅包含baz键
            "baz": "qux"
        }
    }
).checkConfig()
DefaultConfigPool.saveAll()

print(cfg)
print()
print(f"{cfg["Hello"]=}")
print(cfg.foo)
print(cfg["foo"]["bar"])
print(cfg.foo.bar.baz)
```
