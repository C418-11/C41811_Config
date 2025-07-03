# 贡献指南

## 环境准备

### 开发环境配置
```shell
# 创建虚拟环境（推荐）
python -m venv .venv

# 安装开发依赖
pip install -r requirements.txt
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
```shell
# 运行完整测试套件
tox

# 可用的tox环境: py312,py313,ruff,mypy
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
