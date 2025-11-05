# 0.3.0 \[unreleased]

## 新增

* 引入pre-commit工具提升开发反馈速度
* 引入ruff工具进行严格的代码检查与格式化
* 引入zizmor工具对GitHub工作流进行安全分析
* 引入懒加载特性避免不必要的导入
* 新增CBOR2SL以处理低体积的cbor格式
* 新增dependabot支持自动依赖更新
* 新增gitee同步工作流镜像备份仓库
* 新增HJsonSL以处理人类更可读的Json
* 新增JPropertiesSL以处理properties格式
* 新增RTomlSL以更快的处理toml格式
* 新增sphinx扩展sphinx.ext.doctest
* 新增TomlKitSL以更完善的处理toml格式
* 新增tox环境format以使用ruff检测并格式化代码
* 新增参数OSEnvSL.__init__的prefix,strip_prefix以实现导出特定前缀环境变量
* 新增反馈错误issue模板
* 新增可选参数ComponentSL.load_file的config_formats以支持指定成员的配置解析格式
* 新增哈希支持UnsupportedConfigFormatError
* 新增安全策略文档
* 新增属性Ref.\_\_slots\_\_
* 新增属性UnsetType.\_\_slots\_\_
* 新增异常类ComponentMemberMismatchError完善组件错误处理系统
* 新增异常类ComponentMetadataException以处理更广泛的组件元数据异常
* 新增异常类DependencyNotFoundError以更精确的描述依赖项未满足
* 新增支持TypeAliasType在DefaultValidatorFactory
* 新增方法BasicSingleConfigData.\_\_bool\_\_以实现对内容配置数据的真值检查
* 新增特殊类UnavailableAttribute以作为懒加载发现依赖未满足无法导入时的占位符
* 新增贡献指南
* 补充emoji图标到工作流

## 变更

* 优化所有的装饰器对元信息的处理
* 单元测试报告和项目规范页面移至文档根目录
* 合并工作流mypy,pytest,ruff为python-ci
* 合并工作流testpypi到publish
* 工作流提升工作流运行速度使用setup-python内置依赖缓存
* 工作流添加缓存mypy检查
* 更改为关键字参数ABCConfigPool.save_all的ignore_err
* 更改参数类型FailedProcessConfigFileError.__new__的reason从BaseException改为Exception
* 更改参数类型UnsupportedConfigFormatError.__init__的_format为`str | None`
* 更改只读属性NumberConfigData.data为可写
* 更改只读属性ObjectConfigData.data为可写
* 更改只读属性StringConfigData.data为可写
* 更改属性为只读UnsupportedConfigFormatError.format
* 更改泛型NumberConfigData的D为`int | float | Number`
* 更改自定义验证器工厂使其逻辑更符合预期,validator为`None`时不进行验证否则将验证器作为`Callable[[Ref[D], ValidatorFactoryConfig], D]`
* 更符合最佳实践的tox依赖安装
* 消除类操作符生成装饰器generate内的exec
* 统一所有文档命令行高亮为shell
* 统一行为在DefaultValidatorFactory,pydantic_validator,ComponentFactory的allow_modify
* 自动更新的依赖项由dependabot
* 返回当前实例以便链式调用ABCConfigSL.register_to
* 采用更严格的mypy检查
* 重命名CellType为Ref
* 重命名tox环境ruff为lint
* 重命名包/文件为小写遵循PEP8
* 重命名参数UnsupportedConfigFormatError.__init__的format_为_format
* 重命名子包base为basic
* 重命名字段CellType.cell_contents为value
* 重命名属性ComponentSL.initial_file为参数meta_file并变更默认值`__init__`为`__meta__`
* 重命名枚举ValidatorTypes.NO_VALIDATION为CUSTOM

## 移除

* 不再使用flake8进行代码检查
* 移除冗余属性FailedProcessConfigFileError.reasons
* 移除功能不完善的TomlSL

## 修复

* ABCConfigData移除冗余泛型
* ConfigDataPathSyntaxException现在传入的错误消息不再软要求带冒号
* ConfigRequirementDecorator现在会在每一次获取配置数据时尝试加载配置而不是仅在初始化时尝试加载
* FailedProcessConfigFileError现在正确的继承自ExceptionGroup
* 修正子类方法类型注解ABCIndexedConfigData.get,setdefault
* 统一各个SL处理器返回所使用的配置格式为self.reg_name
* 重命名文件pygments_darcula为.pygments_darcula以避免sphinx构建结果包含未编译文件

## 常规

* 补充修正一些文档
* 补充修正一些测试用例
* 补充修正类型注解

# 0.2.0

## 新增

* 排除目录.config
* 新增ComponentSL,ComponentConfigData,ComponentMeta,...处理组件配置文件
* 新增EnvironmentConfigData以适配计算环境变量变更
* 新增OSEnvSL以将环境变量作为配置文件
* 新增PlainTextSL以处理纯文本配置文件
* 新增PythonSL以转换python脚本为配置数据
* 新增safe_writer以安全的读写文件
* 新增sphinx扩展sphinx.ext.intersphinx
* 新增TarFileSL,ZipFileSL处理压缩配置文件
* 新增中间类BasicCachedConfigSL以提供配置文件SL处理缓存基础操作
* 新增中间类BasicChainConfigSL以提供连锁配置文件SL处理基础操作
* 新增中间类BasicCompressedConfigSL以提供压缩配置文件SL处理基础操作
* 新增中间类BasicSingleConfigData以提供单文件配置数据基础操作
* 新增依赖mypy-extensions~=1.0.0
* 新增依赖portalocker~=3.1.1
* 新增参数FieldDefinition.\_\_init\_\_.default_factory以支持默认值工厂函数
* 新增参数MappingConfigData.keys的strict以切换处理循环引用的行为
* 新增只读字段ABCSLProcessorPool.helper
* 新增字段ABCPath.keys提供便捷的键获取接口
* 新增异常类CyclicReferenceError为循环引用的配置数据提供更好的报错信息
* 新增接口ABCConfigFile.initialize以初始化一个符合配置格式的配置文件
* 新增接口ABCConfigPool.initialize以初始化一个符合配置格式的配置文件
* 新增接口ABCConfigSL.initialize以初始化一个符合配置格式的配置文件
* 新增接口ABCConfigSL.supported_file_classes以获取支持的配置文件类
* 新增方法ABCConfigPool.discard以简化配置池操作
* 新增类ABCProcessorHelper,PHelper用于辅助配置处理器处理配置
* 新增类NoneConfigData用于表示空或者为None的配置数据
* 新增详细，示例，项目规范文档
* 新增配置数据路径键元信息语法 `\{meta info\}`
* 补充MappingConfigData对MutableMapping的实现

## 变更

* 对mypy支持
* 更改接口ABCConfigSL.file_ext为supported_file_patterns以支持endswith和正则匹配
* 更改类方法签名ABCConfigData.from_data现在会自适应初始化参数
* 添加参数ABCConfigSL.save,load的processor_pool以支持传递处理操作
* 移动保存加载器参数相关处理至BasicLocalFileConfigSL
* 移动单元测试报告页面到Reports目录下
* 移除参数ABCConfigPool.load的config_file_cls
* 移除参数ABCConfigSL.load的config_file_cls
* 重命名参数ABCConfigFile.\_\_init\_\_的config_data为initial_config
* 重命名参数ABCConfigFile.save,load的config_pool为processor_pool以满足LSP
* 重命名参数ABCConfigPool.load的allow_create为allow_initialize
* 重命名参数ConfigRequirementDecorator.\_\_init\_\_的cache_config为config_cacher
* 重命名参数retrieve,get等高级方法get_raw为return_raw_value
* 重命名字段ABCConfigFile.data为config
* 重命名字段ABCSLProcessorPool.FileExtProcessor为FileNameProcessors
* 重命名字段ABCSLProcessorPool.SLProcessor为SLProcessors
* 重命名字段FieldDefinition.type为annotation
* 重命名字段ValidatorFactoryConfig.ignore_missing为skip_missing
* 重命名方法ABCConfigPool.delete为remove
* 重命名目录SLProcessors为processor
* 重命名类\*SupportsIndex\*为\*Indexed\*
* 重命名类Base\*为Basic\*
* 重命名类RequireConfigDecorator为ConfigRequirementDecorator
* 重构拆分base.py为多个文件
* 验证器通过CellType以支持同步类型更改至外界传入参数
* ConfigData.TYPES现在使用OrderedDict以保证顺序
* 优化局部变量命名
* 圈复杂度检查阈值现在为10
* 更改字段默认值BasicConfigData.data_read_only为True
* 更改字段默认值ValidatorFactoryConfig.allow_midify为True
* 更改方法ABCConfigPool.set,save等返回值为Self以便链式调用
* 更新pyproject.toml为最新格式
* 更新文档代码高亮样式
* 更新第三方依赖版本
* 现在CI测试会同时在ubuntu-latest, macos-latest, windows-latest上进行

## 移除

* 常见用法|CommonUsage.rst

## 修复

* 修正文档引用
* 现在allow_modify的验证器能正确填充类型为Mapping和Sequence的默认值

补充文档以及一些杂七杂八的小优化...

**Full Changelog**: https://github.com/C418-11/C41811_Config/compare/v0.1.5...v0.2.0

# 0.1.5

* ABCConfigData新增freeze方法
* ABCConfigData在__format__对'r'进行了支持
* 拆分ConfigData为MappingConfigData、SequenceConfigData、NumberConfigData、BoolConfigData、ObjectConfigData
* RequiredPathNotFoundError现在继承自LookupError
* 补充py.typed文件
* 补充文档、优化工作流、修复遗留问题

**Full Changelog**: https://github.com/C418-11/C41811_Config/compare/v0.1.4...v0.1.5

# 0.1.4

* FieldDefinition新增allow_recursive字段
* 正式支持IndexKey语法\\\[index\\\]
* FailedProcessConfigFileError现在同时继承自BaseExceptionGroup
* 默认验证器工厂支持键非字符串的子验证器
* 修复ConfigDataTypeError提示信息
* ConfigDataTypeError.__init__的参数required_type现在支持传入多个需求的数据类型
* PathSyntaxParser.tokenize添加缓存
* PathSyntaxParser.tokenize更改返回值类型为tuple[str, ...]
* 修复ABCConfigData.exists缺失ignore_wrong_type参数
* 补充文档、优化工作流、修复遗留问题

**Full Changelog**: https://github.com/C418-11/C41811_Config/compare/v0.1.3...v0.1.4

# 0.1.3

* 重命名UnknownErrorDuringValidate为UnknownErrorDuringValidateError
* 重命名UnknownTokenType为UnknownTokenTypeError
* 新增ConfigDataReadOnlyError
* 修复python字面量SL处理器
* 修复了一些BUG,补充了一些文档

**Full Changelog**: https://github.com/C418-11/C41811_Config/compare/v0.1.2...v0.1.3

# 0.1.2

* 重命名ValidatorFactoryConfig.allow_create为allow_modify
* FieldDefinition更加符合预期
* DefaultValidatorFactory支持混合路径字符串和嵌套字典
* ABCConfigPool.save支持像load一样推断SL处理器
* ABCConfigPool.save新增config可选参数
* BaseConfigPool 支持 __contains__
* ABCConfigData新增方法unset用于简化确保路径不存在
* 修复了一些BUG,补充了一些文档

**Full Changelog**: https://github.com/C418-11/C41811_Config/compare/v0.1.1...v0.1.2

# 0.1.1

使路径对象可以还原为转义字符串
修复连续双斜杠的转义问题

**Full Changelog**: https://github.com/C418-11/C41811_Config/compare/v0.1.0...v0.1.1

# 0.1.0

初始版本
