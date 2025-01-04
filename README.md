# C41811.Config

[English](README_EN.md) | 中文

---

[![PyPI pyversions](https://img.shields.io/pypi/pyversions/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)
[![PyPI - License](https://img.shields.io/pypi/l/C41811.Config?color=blue)](https://github.com/C418-11/C41811_Config/blob/main/LICENSE)

|  文档  |                                           [![Documentation Status](https://readthedocs.org/projects/c41811config/badge/?version=latest)](https://C41811Config.readthedocs.io) [![Common Usage](https://img.shields.io/badge/%E5%B8%B8%E8%A7%81-%E7%94%A8%E6%B3%95-green?logo=googledocs&logoColor=white)](https://c41811config.readthedocs.io/zh-cn/latest/CommonUsage.html)  [![made-with-sphinx-doc](https://img.shields.io/badge/Made%20with-Sphinx-1f425f.svg)](https://www.sphinx-doc.org/)                                           |
|:----:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| PyPI |                                                                                           [![PyPI - Version](https://img.shields.io/pypi/v/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI - Wheel](https://img.shields.io/pypi/wheel/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI download month](https://img.shields.io/pypi/dm/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)                                                                                            |
|  源码  | [![Github](https://img.shields.io/badge/Github-C41811.Config-green?logo=github)](https://github.com/C418-11/C41811_Config/) [![Python CI](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml/badge.svg?branch=develop)](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml) [![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-publish.yml)](https://github.com/C418-11/C41811_Config/actions/workflows/python-publish.yml) |

## 简介

C41811.Config 旨在通过提供一套简洁的 API
和灵活的配置处理机制，来简化配置文件的管理。无论是简单的键值对配置，还是复杂的嵌套结构，都能轻松应对。它不仅支持多种配置格式，还提供了丰富的错误处理和验证功能，确保配置数据的准确性和一致性。

## 特性

* 多格式支持：支持多种流行的配置格式，包括 JSON、YAML、TOML 和 Pickle，满足不同项目的需求。
* 模块化设计：通过模块化的设计，提供了灵活地扩展机制，开发者可以根据需要添加自定义的配置处理器。
* 验证功能：支持通过验证器来验证配置数据的合法性，确保配置数据的正确性。
* 易于使用：提供了一套简洁的 API，开发者可以轻松地加载、修改和保存配置文件。

## 安装

```commandline
pip install C41811.Config
```

## 一个简单的示例

```python
from C41811.Config import ConfigData
from C41811.Config import JsonSL
from C41811.Config import requireConfig
from C41811.Config import saveAll

JsonSL().register_to()

cfg: ConfigData = requireConfig(
    '', "Hello World.json",
    {  # 简单且强大的配置数据验证器
        "Hello": "World",
        "foo": dict,  # 包含foo下的所有键
        "foo\\.bar": {  # foo.bar仅包含baz键
            "baz": "qux"
        }
    }
).check()
saveAll()

print(f"{cfg=}")
print()
print("与dict完全相同的数据访问方式")
print(f"{cfg["Hello"]=}")
print(f"{cfg["foo"]["bar"]=}")
print()
print("通过属性访问数据")
print(f"{cfg.foo=}")
print(f"{cfg.foo.bar.baz=}")
print()
print("通过特殊语法访问数据")
print(f"{cfg.retrieve("foo\\.bar\\.baz")=}")
print()
print("一些常用方法")
print(f"{cfg.unset("foo\\.bar\\.baz").exists("foo\\.bar\\.baz")=}")
print(f"{cfg.get("foo\\.bar\\.baz")=}")
print(f"{cfg.set_default("foo\\.bar\\.baz", "qux")=}")
print(f"{cfg.get("foo\\.bar\\.baz", default="default")=}")
print(f"{cfg.modify("foo\\.bar\\.baz", [1, 2, 3]).retrieve("foo\\.bar\\.baz\\[1\\]")=}")
print(f"{cfg.delete("foo\\.bar\\.baz").get("foo\\.bar\\.baz", default="default")=}")
```
