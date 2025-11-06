# C41811.Config

English | [中文](README.md)

---

[![PyPI pyversions](https://img.shields.io/pypi/pyversions/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)
[![GitHub License](https://img.shields.io/github/license/C418-11/C41811_Config?color=blue)](https://github.com/C418-11/C41811_Config/blob/main/LICENSE)
[![GitHub commits since latest release](https://img.shields.io/github/commits-since/C418-11/C41811_Config/latest/develop)](https://github.com/C418-11/C41811_Config/commits/develop/)

|     Documentation      | [![Documentation Status](https://readthedocs.org/projects/c41811config/badge/?version=latest)](https://app.readthedocs.org/projects/c41811config/) [![Get Start](https://img.shields.io/badge/Get-Start-green?logo=googledocs&logoColor=white)](https://c41811config.readthedocs.io/zh-cn/latest/Tutorial/get-start.html) [![FAQ](https://img.shields.io/badge/docs-FAQ-green?logo=googledocs&logoColor=white)](https://c41811config.readthedocs.io/zh-cn/latest/Tutorial/faq.html) |
|:----------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|          PyPI          |                                                                [![PyPI - Version](https://img.shields.io/pypi/v/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI - Wheel](https://img.shields.io/pypi/wheel/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI download month](https://img.shields.io/pypi/dm/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)                                                                |
|       Repository       |                                                              [![Github](https://img.shields.io/badge/Github-C41811.Config-green?logo=github)](https://github.com/C418-11/C41811_Config/) [![Publish Status](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-publish.yml?logo=github&label=Publish)](https://github.com/C418-11/C41811_Config/actions/workflows/python-publish.yml)                                                               |
|  Code Quality - Main   |                                                [![CI Status](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-ci.yml?branch=main&logo=github&label=CI)](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml?query=branch%3Amain) [![CodeCov](https://codecov.io/gh/C418-11/C41811_Config/branch/main/graph/badge.svg)](https://codecov.io/gh/C418-11/C41811_Config/tree/main)                                                |
| Code Quality - Develop |                                          [![CI Status](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-ci.yml?branch=develop&logo=github&label=CI)](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml?query=branch%3Adevelop) [![CodeCov](https://codecov.io/gh/C418-11/C41811_Config/branch/develop/graph/badge.svg)](https://codecov.io/gh/C418-11/C41811_Config/tree/develop)                                          |

Is the documentation too confusing? Try AI documentation! (not guaranteed to be correct)<br/>
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/C418-11/C41811_Config) [![Ask Zread](https://img.shields.io/badge/Ask_Zread-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff)](https://zread.ai/C418-11/C41811_Config)

Tip: Click the badge to goto the page.

## Description

C41811.Config aims to simplify the management of configuration files by providing a concise API and flexible
configuration processing mechanism. Whether it's simple key value pair configuration or complex nested structures, they
can be easily handled. It not only supports multiple configuration formats, but also provides rich error handling and
verification functions to ensure the accuracy and consistency of configuration data.

## Characteristics

* Multi format support: Supports 15+ configuration formats, including popular JSON, YAML, TOML, Pickle, and more, to
  meet the needs of different projects.
* Modular design: Through modular design, flexible extension mechanisms are provided, allowing developers to add custom
  configuration processors as needed.
* Verification function: Supports verifying the legitimacy of configuration data through validators to ensure the
  correctness of configuration data.
* Easy to use: Provides a concise API that allows developers to easily load, modify, and save configuration files.
* Component configuration data: Supports multiple sources of configuration data through "component configuration data"
  to achieve complex inheritance, override, and priority relationships.
* Easy to use: Provides a unified and concise API with comprehensive type annotation support, allowing developers to
  easily load, modify, and save configuration files.

## Characteristics

C41811.Config is suitable for a variety of configuration management scenarios, especially in the following situations:

* Large projects: Allows isolation of configuration for different parts of the project through namespaces or
  configuration pools, making configuration management clearer and more organized.
* Scattered configuration files: By providing a unified interface and flexible processing mechanisms, scattered
  configuration files can be centrally managed and accessed, improving the efficiency and consistency of configurations.
* Complex data models: Automatically fills in missing key default values and verifies the type of configuration data to
  ensure the integrity and accuracy of configuration data.
* Need for complex configuration operations: Provides methods such as get, setdefault, unset, etc., to simplify complex
  operations on configuration data.
* Mixing multiple configuration formats: Supports inferring the appropriate configuration format from registered
  processors based on file extensions, allowing seamless use of configuration files in different formats.
* Dynamic configuration updates: Supports dynamic updates to configurations at runtime without restarting the
  application to apply new configurations.
* Type safety: Provides comprehensive type annotation support, reducing boilerplate code and ensuring type-safe
  configuration access.

## Installation

```shell
pip install C41811.Config
```

## A simple example

```python
from c41811.config import MappingConfigData
from c41811.config import JsonSL
from c41811.config import requireConfig
from c41811.config import saveAll

JsonSL().register_to()

cfg: MappingConfigData = requireConfig(
    "", "Hello World.json",
    {  # Simple and powerful configuration data validator
        "Hello": "World",
        "foo": dict,  # Contains all keys under foo
        "foo\\.bar": {  # foo.bar contains only the baz key
            "baz": "qux"
        }
    }
).check()
saveAll()

print(f"{cfg=}")
print()
print("Identical data access method as dict")
print(f"{cfg["Hello"]=}")
print(f"{cfg["foo"]["bar"]=}")
print()
print("Accessing data through attributes")
print(f"{cfg.foo=}")
print(f"{cfg.foo.bar.baz=}")
print()
print("Accessing data through special syntax")
print(f"{cfg.retrieve("foo\\.bar\\.baz")=}")
print()
print("Some common methods")
print(f"{cfg.unset("foo\\.bar\\.baz").exists("foo\\.bar\\.baz")=}")
print(f"{cfg.get("foo\\.bar\\.baz")=}")
print(f"{cfg.setdefault("foo\\.bar\\.baz","qux")=}")
print(f"{cfg.get("foo\\.bar\\.baz", default="default")=}")
print(f"{cfg.modify("foo\\.bar\\.baz", [1, 2, 3]).retrieve("foo\\.bar\\.baz\\[1\\]")=}")
print(f"{cfg.delete("foo\\.bar\\.baz").get("foo\\.bar\\.baz", default="default")=}")
```
