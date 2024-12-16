# C41811.Config

English | [中文](README.md)

---

[![PyPI pyversions](https://img.shields.io/pypi/pyversions/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)
[![PyPI - License](https://img.shields.io/pypi/l/C41811.Config?color=blue)](https://github.com/C418-11/C41811_Config/blob/main/LICENSE)

|  Document   |                                                                                                                                              [![Documentation Status](https://readthedocs.org/projects/c41811config/badge/?version=latest)](https://C41811Config.readthedocs.io) [![made-with-sphinx-doc](https://img.shields.io/badge/Made%20with-Sphinx-1f425f.svg)](https://www.sphinx-doc.org/)                                                                                                                                              |
|:-----------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|    PyPI     |                                                                                              [![PyPI - Version](https://img.shields.io/pypi/v/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI - Wheel](https://img.shields.io/pypi/wheel/C41811.Config)](https://pypi.python.org/pypi/C41811.Config/) [![PyPI download month](https://img.shields.io/pypi/dm/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)                                                                                               |
| Source Code | [![Static Badge](https://img.shields.io/badge/Github-C41811.Config-green?logo=github)](https://github.com/C418-11/C41811_Config/) [![Python CI](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml/badge.svg?branch=develop)](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml) [![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/C418-11/C41811_Config/python-publish.yml)](https://github.com/C418-11/C41811_Config/actions/workflows/python-publish.yml) |

## Description

C41811.Config is a powerful and easy-to-use configuration management package designed to simplify reading and writing
configuration files. It supports several popular configuration formats, including JSON, YAML, TOML and Pickle, to meet
the needs of different projects. With its modular design, C41811.Config provides a reliable configuration processing
solution to help developers quickly build and maintain high-quality applications.

## Installation

```commandline
pip install C41811.Config
```

## A simple example

```python
from C41811.Config import JsonSL
from C41811.Config import requireConfig
from C41811.Config import saveAll

JsonSL().register_to()

cfg = requireConfig(
    '', "Hello World.json",
    {
        "Hello": "World",
        "foo": dict,  # contains all keys under foo
        "foo\\.bar": {  # foo.bar contains only the baz key
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
