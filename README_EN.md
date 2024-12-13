# C41811.Config

English | [中文](README.md)

---

[![PyPi version](https://badgen.net/pypi/v/c41811.config/)](https://pypi.org/project/C41811.Config)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)
[![Documentation Status](https://readthedocs.org/projects/c41811config/badge/?version=latest)](https://C41811Config.readthedocs.io)
[![PyPi license](https://badgen.net/pypi/license/c41811.config/)](https://pypi.org/project/C41811.Config/)
[![PyPI download month](https://img.shields.io/pypi/dm/c41811.config.svg)](https://pypi.python.org/pypi/C41811.Config/)
[![made-with-sphinx-doc](https://img.shields.io/badge/Made%20with-Sphinx-1f425f.svg)](https://www.sphinx-doc.org/)
[![Python CI](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml/badge.svg?branch=develop)](https://github.com/C418-11/C41811_Config/actions/workflows/python-ci.yml)

| Document    | https://C41811Config.readthedocs.io      |
|-------------|------------------------------------------|
| PyPI        | https://pypi.org/project/C41811.Config   |
| Source Code | https://github.com/C418-11/C41811_Config |

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

``` python
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
