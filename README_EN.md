# C41811.Config

English | [中文](README.md)

---

[![PyPI pyversions](https://img.shields.io/pypi/pyversions/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)
[![PyPI - License](https://img.shields.io/pypi/l/C41811.Config?color=blue)](https://github.com/C418-11/C41811_Config/blob/main/LICENSE)

| Documentation |                       [![Documentation Status](https://readthedocs.org/projects/c41811config/badge/?version=latest)](https://C41811Config.readthedocs.io) [![Common Usage](https://img.shields.io/badge/Common-Usage-green?logo=googledocs&logoColor=white)](https://c41811config.readthedocs.io/zh-cn/latest/CommonUsage.html)  [![made-with-sphinx-doc](https://img.shields.io/badge/Made%20with-Sphinx-1f425f.svg)](https://www.sphinx-doc.org/)                        |
|:-------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|     PyPI      |                                                           [![PyPI - Version](https://img.shields.io/pypi/v/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI - Wheel](https://img.shields.io/pypi/wheel/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI download month](https://img.shields.io/pypi/dm/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)                                                            |
|  Repository   |                                                             [![Github](https://img.shields.io/badge/Github-C41811.Config-green?logo=github)](https://github.com/C418-11/C41811_Config/) [![Publish](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-publish.yml?logo=github&label=Publish)](https://github.com/C418-11/C41811_Config/actions/workflows/python-publish.yml)                                                              |
| Code Quality  | [![pytest](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-pytest.yml?logo=github&label=pytest)](https://github.com/C418-11/C41811_Config/actions/workflows/python-pytest.yml) [![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-flake8.yml?branch=develop&logo=github&label=flake8)](https://github.com/C418-11/C41811_Config/actions/workflows/python-flake8.yml) |

## Description

C41811.Config aims to simplify the management of configuration files by providing a concise API and flexible
configuration processing mechanism. Whether it's simple key value pair configuration or complex nested structures, they
can be easily handled. It not only supports multiple configuration formats, but also provides rich error handling and
verification functions to ensure the accuracy and consistency of configuration data.

## Characteristics

* Multi format support: Supports multiple popular configuration formats, including JSON, YAML, TOML, and Pickle, to meet
  the needs of different projects.
* Modular design: Through modular design, flexible extension mechanisms are provided, allowing developers to add custom
  configuration processors as needed.
* Verification function: Supports verifying the legitimacy of configuration data through validators to ensure the
  correctness of configuration data.
* Easy to use: Provides a concise API that allows developers to easily load, modify, and save configuration files.

## Characteristics

C41811.Config is suitable for a variety of configuration management scenarios, especially in the following situations:

* Large projects: Allows isolation of configuration for different parts of the project through namespaces or
  configuration pools, making configuration management clearer and more organized.
* Scattered configuration files: By providing a unified interface and flexible processing mechanisms, scattered
  configuration files can be centrally managed and accessed, improving the efficiency and consistency of configurations.
* Complex data models: Automatically fills in missing key default values and verifies the type of configuration data to
  ensure the integrity and accuracy of configuration data.
* Need for complex configuration operations: Provides methods such as get, set_default, unset, etc., to simplify complex
  operations on configuration data.
* Mixing multiple configuration formats: Supports inferring the appropriate configuration format from registered
  processors based on file extensions, allowing seamless use of configuration files in different formats.
* Dynamic configuration updates: Supports dynamic updates to configurations at runtime without restarting the
  application to apply new configurations.

## Installation

```commandline
pip install C41811.Config
```

## A simple example

```python
from C41811.Config import MappingConfigData
from C41811.Config import JsonSL
from C41811.Config import requireConfig
from C41811.Config import saveAll

JsonSL().register_to()

cfg: MappingConfigData = requireConfig(
    '', "Hello World.json",
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
print(f"{cfg.set_default("foo\\.bar\\.baz", "qux")=}")
print(f"{cfg.get("foo\\.bar\\.baz", default="default")=}")
print(f"{cfg.modify("foo\\.bar\\.baz", [1, 2, 3]).retrieve("foo\\.bar\\.baz\\[1\\]")=}")
print(f"{cfg.delete("foo\\.bar\\.baz").get("foo\\.bar\\.baz", default="default")=}")
```
