# 贡献指南

## 环境准备

### 开发环境配置

创建虚拟环境（推荐）

```shell
python -m venv .venv
```

激活虚拟环境

```shell
source .venv/bin/activate  # Linux/MacOS
```

或

```shell
.venv\Scripts\activate  # Windows
```

安装开发依赖

```shell
pip install -r requirements.txt
```

初始化pre-commit（推荐）

```shell
pre-commit install
```

## 开发流程

### Git分支管理

- 从`develop`分支创建特性分支
- 分支命名格式：`feature/short-desc` 或 `fix/[issue-number]-desc`

## 质量保障

### 代码规范

- 严格遵守[项目规范](docs/project-specification.rst)
- 在线文档：[最新规范](https://c41811config.readthedocs.io/zh-cn/latest/project-specification.html)

### 测试要求

运行完整测试套件

```shell
tox
```

或者用更快地并行检查

```shell
tox -p
```

可用的tox环境：

|  环境名   | 说明            |
|:------:|:--------------|
| py312  | 在Py3.12运行单元测试 |
| py313  | 在Py3.13运行单元测试 |
|  lint  | 代码检查          |
| format | 代码格式化         |
|  mypy  | 运行mypy类型检查    |

```shell
# 例: 单独运行mypy类型检查
tox -e mypy
```

❌ 禁止合并未通过全部测试的PR

## 文档贡献

```shell
# 本地构建文档
tox -e doc
```

构建完成后，文档位于 [`docs/_build/`](docs/_build/index.html) 目录下。

## 很酷的代码覆盖率！

![覆盖率状态](https://codecov.io/gh/C418-11/C41811_Config/branch/develop/graphs/tree.svg)
