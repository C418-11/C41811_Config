# C41811.Config

[English](README_EN.md) | 中文

---

[![支持的python版本](https://img.shields.io/pypi/pyversions/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)
[![开源许可证](https://img.shields.io/pypi/l/C41811.Config?color=blue)](https://github.com/C418-11/C41811_Config/blob/main/LICENSE)

|    文档     | [![文档状态](https://readthedocs.org/projects/c41811config/badge/?version=latest)](https://app.readthedocs.org/projects/c41811config/) [![新手教程](https://img.shields.io/badge/%E6%96%B0%E6%89%8B-%E6%95%99%E7%A8%8B-green?logo=googledocs&logoColor=white)](https://c41811config.readthedocs.io/zh-cn/latest/Tutorial/get-start.html) [![常见问题](https://img.shields.io/badge/%E5%B8%B8%E8%A7%81-%E9%97%AE%E9%A2%98-green?logo=googledocs&logoColor=white)](https://c41811config.readthedocs.io/zh-cn/latest/Tutorial/faq.html) |
|:---------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|   PyPI    |                                                                                           [![PyPI包版本](https://img.shields.io/pypi/v/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI - Wheel](https://img.shields.io/pypi/wheel/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI每月下载量](https://img.shields.io/pypi/dm/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)                                                                                           |
|    仓库     |                                                                                   [![Github仓库](https://img.shields.io/badge/Github-C41811.Config-green?logo=github)](https://github.com/C418-11/C41811_Config/) [![发布工作流状态](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-publish.yml?logo=github&label=Pubilsh)](https://github.com/C418-11/C41811_Config/actions/workflows/python-publish.yml)                                                                                    |
| 代码质量-主分支  |                                                                   [![CI状态](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-ci.yml?branch=main&logo=github&label=CI)](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml?query=branch%3Amain) [![CodeCov覆盖率](https://codecov.io/gh/C418-11/C41811_Config/branch/main/graph/badge.svg)](https://codecov.io/gh/C418-11/C41811_Config/tree/main)                                                                    |
| 代码质量-开发分支 |                                                             [![CI状态](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-ci.yml?branch=develop&logo=github&label=CI)](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml?query=branch%3Adevelop) [![CodeCov覆盖率](https://codecov.io/gh/C418-11/C41811_Config/branch/develop/graph/badge.svg)](https://codecov.io/gh/C418-11/C41811_Config/tree/develop)                                                              |

提示：点击徽章可转到相应页面。

## 简介

C41811.Config 旨在通过提供一套简洁的 API
和灵活的配置处理机制，来简化配置文件的管理。无论是简单的键值对配置，还是复杂的嵌套结构，都能轻松应对。它不仅支持多种配置格式，还提供了丰富的错误处理和验证功能，确保配置数据的准确性和一致性。

## 特性

* 多格式支持：支持多种流行的配置格式，包括 JSON、YAML、TOML 和 Pickle，满足不同项目的需求。
* 模块化设计：通过模块化的设计，提供了灵活地扩展机制，开发者可以根据需要添加自定义的配置处理器。
* 验证功能：支持通过验证器来验证配置数据的合法性，确保配置数据的正确性。
* 易于使用：提供了一套简洁的 API，开发者可以轻松地加载、修改和保存配置文件。

## 适用场景

C41811.Config 适用于多种配置管理场景，特别是以下几种情况：

* 大型项目：允许通过命名空间或配置池隔离项目各部分的配置，使得配置管理更加清晰和有序。
* 分散的配置文件：通过提供统一的接口和灵活地处理机制，使得分散的配置文件能够被集中管理和访问，提高了配置的效率和一致性。
* 复杂的数据模型：自动填充缺失的键默认值，并对配置数据进行类型验证，确保配置数据的完整性和准确性。
* 需要对配置进行复杂操作：提供了 get、setdefault、unset 等方法，简化了对配置数据的复杂操作。
* 多种配置格式混搭：支持根据文件后缀自动从注册的处理器中推断合适的配置格式，使得不同格式的配置文件可以无缝混用。
* 动态配置更新：支持在运行时动态更新配置，无需重启应用即可应用新的配置。

## 安装

```commandline
pip install C41811.Config
```

## 一个简单的示例

```python
from C41811.Config import MappingConfigData
from C41811.Config import JsonSL
from C41811.Config import requireConfig
from C41811.Config import saveAll

JsonSL().register_to()

cfg: MappingConfigData = requireConfig(
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
print(f"{cfg.setdefault("foo\\.bar\\.baz","qux")=}")
print(f"{cfg.get("foo\\.bar\\.baz", default="default")=}")
print(f"{cfg.modify("foo\\.bar\\.baz", [1, 2, 3]).retrieve("foo\\.bar\\.baz\\[1\\]")=}")
print(f"{cfg.delete("foo\\.bar\\.baz").get("foo\\.bar\\.baz", default="default")=}")
```
