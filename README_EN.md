# C41811.Config

English | [中文](README.md)

[Document](https://C41811Config.readthedocs.io)

---


## Description

C41811.Config is a powerful and easy-to-use configuration management package designed to simplify reading and writing configuration files. It supports several popular configuration formats, including JSON, YAML, TOML and Pickle, to meet the needs of different projects. With its modular design, C41811.Config provides a reliable configuration processing solution to help developers quickly build and maintain high-quality applications.

## Installation

```commandline
pip install C41811.Config
```

## Quick Start

``` python
from C41811.Config import JsonSL
from C41811.Config import DefaultConfigPool
from C41811.Config import requireConfig


JsonSL.registerTo(DefaultConfigPool)

cfg = reqireConfig(
    '', "Hello World.json",
    {
        “Hello”: "World",
        "foo": {
            "bar": 123
        }
    }
).checkConfig()

print(cfg)
print()
print(cfg["foo.bar"])
print(cfg.foo.bar)
```
