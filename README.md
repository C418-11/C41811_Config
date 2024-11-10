# C41811.Config

[English](README_EN.md) | 中文

[文档](https://C41811Config.readthedocs.io)

---


## 简介

C41811.Config 是一个功能强大且易于使用的配置管理包，旨在简化配置文件的读取和写入操作。它支持多种流行的配置格式，包括 JSON、YAML 和 Pickle，满足不同项目的需求。通过模块化的设计，C41811.Config 提供了可靠的配置处理解决方案，帮助开发者快速构建和维护高质量的应用程序。

## 安装

```commandline
pip install C41811.Config
```

## 快速开始

``` python
from C41811.Config import requireConfig

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
