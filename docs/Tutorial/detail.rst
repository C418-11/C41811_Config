详细文档
==============

.. _term-config-data-path-syntax:
配置数据路径语法
-----------------

由三种类型组成

.. rubric:: 属性键
   :name: term-attr-key

由 ``\.`` 开头，紧随的字符串组成

.. code-block:: python
   :caption: 例

   r"\.key1\.key2\.key3"

.. rubric:: 索引键

由 ``\[`` 开头，紧随的数字与 ``\]`` 组成

.. code-block:: python
   :caption: 例

   r"\[0\]"

.. rubric:: 元信息
   :name: term-key-meta

由 ``\{`` 开头，紧随的字符串与 ``\}`` 组成

元信息会被附加到紧随的键上

.. code-block:: python
   :caption: 例

   r"\{meta 1\}\.key\{meta 2\}\[0\]"

   # 这相当于

   [AttrKey("key", meta="meta 1"), IndexKey(0, meta="meta 2")]

如果路径字符串以 :ref:`term-attr-key` 开头可以省略 ``\.``

.. code-block:: python
   :caption: 例

   r"key1\.key2\.key3"

   # 这将被视为

   r"\.key1\.key2\.key3"

.. rubric:: 转义

键名或元信息中如有 ``\`` 需要转义 为 ``\\``

.. code-block:: python
   :caption: 例

   r"\{1\\2\}\.\\key\{2\\2\}\[0\]"

   # 这将解析为

   [AttrKey(r"\key", meta=r"1\2"), IndexKey(0, meta=r"2\2")]

可以简单的通过 ``str.replace('\\', '\\\\')`` 来转义

.. attention::
   如果没有转义，且 ``\`` 后面的字符不是以上特殊转义字符，则会原样保留并发出警告

   不应依赖此行为

.. _detail-requireConfig:
requireConfig
-----------------------------

用于加载并验证配置数据的高层方法

.. tip::

   提供参数 ``static_config`` 以获得更高性能

   .. seealso::
      :py:class:`~Config.main.RequiredPath`

有手动调用和装饰器两种获取验证数据的方式

.. code-block:: python
    :caption: 手动调用和装饰器
    :linenos:

    from C41811.Config import ConfigData
    from C41811.Config import JsonSL
    from C41811.Config import requireConfig

    JsonSL().register_to()

    require = requireConfig(
        '', "config.json", {
            "config": "data",
        },
    )

    # 调用check手动获取配置数据
    config: ConfigData = require.check()
    print(config)  # 打印：{'config': 'data'}


    # 使用装饰器自动注入配置数据
    @require
    def test(cfg):
        print(cfg)  # 打印：{'config': 'data'}


    test()


    class Test:
        @require
        def __init__(self, cfg):
            print(self, cfg)  # 打印：<__main__.Test object at 0x0000025B37D812E0> {'config': 'data'}

        @classmethod
        @require
        def cls_func(cls, cfg):
            print(cls, cfg)  # 打印：<class '__main__.Test'> {'config': 'data'}
            return cls

        @staticmethod
        @require
        def static_func(cfg):
            print(cfg)  # 打印：{'config': 'data'}


    Test().cls_func().static_func()

Pydantic验证器工厂
^^^^^^^^^^^^^^^^^^

.. important::
   pydantic 验证器工厂不支持 ``skip_missing`` 配置选项
   这是因为pydantic自带该功能
   如果提供了该参数会产生一个警告 不会起到任何实际作用

``validator_factory`` 参数设为 :py:attr:`~Config.validators.ValidatorTypes.PYDANTIC` 或 ``"pydantic"`` 时使用该验证工厂

``validator`` 参数为任意合法的 ``pydantic.BaseModel``

.. code-block:: python
    :caption: 一个简单的pydantic验证器
    :linenos:

    from pydantic import BaseModel
    from pydantic import Field

    from C41811.Config import ConfigData
    from C41811.Config import ConfigFile
    from C41811.Config import JsonSL
    from C41811.Config import requireConfig
    from C41811.Config import save

    JsonSL().register_to()

    save('', "test.json", config=ConfigFile(ConfigData({
        "key": "value"
    })))


    class Config(BaseModel):
        key: str = "default value"
        unknown_key: dict = Field(default_factory=dict)


    print(requireConfig('', "test.json", Config, "pydantic").check())
    # 打印：{'key': 'value', 'unknown_key': {}}


默认验证器工厂
^^^^^^^^^^^^^^

``validator_factory`` 参数设为 :py:attr:`~Config.validators.ValidatorTypes.DEFAULT` 或 ``None`` 时使用该验证工厂

``validator`` 参数可以为 ``Iterable[str]`` 或 ``Mapping[str | ABCPath, Any]``

``Iterable`` 的元素或 ``Mapping`` 的键会被作为 :ref:`term-config-data-path-syntax` 解析，
如非特殊配置结果将一定包含这些 :ref:`配置数据路径 <term-config-data-path-syntax>`

.. note::

    [path, path1, path2, ...] 与 {path: Any, path1: Any, path2: Any, ...} 等价

.. tip::

    如果validator同时包含路径和路径的父路径

    例： ``r"\.first\.second\.third"`` 与 ``r"\.first"`` 同时出现

    这时 ``first`` 中不仅包含 ``second`` ，还会允许任意额外的键

    .. code-block:: python
        :caption: 例
        :linenos:

        from C41811.Config import ConfigData
        from C41811.Config import ConfigFile
        from C41811.Config import JsonSL
        from C41811.Config import requireConfig
        from C41811.Config import save

        JsonSL().register_to()

        save('', "test.json", config=ConfigFile(ConfigData({
            "first": {
                "second": {
                    "third": 111,
                    "foo": 222
                },
                "bar": 333
            },
            "baz": 444
        })))

        print(requireConfig('', "test.json", ["first", "first\\.second\\.third"]).check())
        # 打印：{'first': {'second': {'third': 111}, 'bar': 333}}

Iterable[str]
.................

.. code-block:: python
    :caption: 例
    :linenos:

    from C41811.Config import ConfigData
    from C41811.Config import ConfigFile
    from C41811.Config import JsonSL
    from C41811.Config import requireConfig
    from C41811.Config import save

    JsonSL().register_to()

    save('', "test.json", config=ConfigFile(ConfigData({
        "foo": {
            "bar": {
                "baz": "value"
            },
            "bar1": "value1"
        },
        "foo1": "value2"
    })))

    print(requireConfig('', "test.json", ["foo", "foo\\.bar\\.baz", "foo1"]).check())
    # 打印：{'foo': {'bar': {'baz': 'value'}, 'bar1': 'value1'}, 'foo1': 'value2'}

Mapping[str | ABCPath, Any]
.............................

.. tip::
    ``r"first\.second\.third": int`` 与 ``"first": {"second": {"third": int}}`` 等价

    * 允许混用路径与嵌套字典

    .. code-block:: python
        :caption: 路径与嵌套字典的等价操作
        :linenos:

        from C41811.Config import ConfigData
        from C41811.Config import ConfigFile
        from C41811.Config import JsonSL
        from C41811.Config import requireConfig
        from C41811.Config import save

        JsonSL().register_to()

        save('', "test.json", config=ConfigFile(ConfigData({
            "first": {
                "second": {
                    "third": 111,
                    "foo": 222
                },
                "bar": 333
            },
            "baz": 444
        })))

        paths = requireConfig('', "test.json", {
            r"first\.second\.third": int,
            r"first\.bar": int,
        }).check()
        recursive_dict = requireConfig('', "test.json", {
            "first": {
                "second": {
                    "third": int
                },
                "bar": int
            }
        }).check()

        print(paths)  # 打印: {'first': {'second': {'third': 111}, 'bar': 333}}
        print(recursive_dict)  # 打印: {'first': {'second': {'third': 111}, 'bar': 333}}
        print(paths == recursive_dict)  # 打印: True

以下是两种验证器语法

.. code-block:: python
    :caption: 两种验证器语法
    :linenos:

    from C41811.Config import ConfigData
    from C41811.Config import ConfigFile
    from C41811.Config import JsonSL
    from C41811.Config import requireConfig
    from C41811.Config import save

    JsonSL().register_to()

    save('', "test.json", config=ConfigFile(ConfigData({
        "first": {
            "second": {
                "third": 111,
                "foo": 222
            },
            "bar": 333
        },
        "baz": 444
    })))

    # 使用路径字符串
    print(requireConfig('', "test.json", {
        "first\\.second\\.third": int,
        "first\\.bar": int,
    }).check())  # 打印：{'first': {'second': {'third': 111}, 'bar': 333}}

    # 使用嵌套字典
    print(requireConfig('', "test.json", {
        "first": {
            "second": {
                "third": int
            },
            "bar": int
        }
    }).check())  # 打印：{'first': {'second': {'third': 111}, 'bar': 333}}

    # 混搭
    print(requireConfig('', "test.json", {
        "first": {
            "second\\.third": int,
            "second": dict,
            "bar": int
        },
        "baz": int
    }).check())  # 打印： {'first': {'second': {'third': 111, 'foo': 222}, 'bar': 333}, 'baz': 444}

类型检查和填充默认值功能

.. code-block:: python
    :caption: 类型检查和填充默认值
    :linenos:

    from typing import Sequence

    from C41811.Config import ConfigData
    from C41811.Config import ConfigFile
    from C41811.Config import FieldDefinition
    from C41811.Config import JsonSL
    from C41811.Config import requireConfig
    from C41811.Config import save
    from C41811.Config.errors import ConfigDataTypeError

    JsonSL().register_to()

    save('', "test.json", config=ConfigFile(ConfigData({
        "first": {
            "second": {
                "third": 111,
                "foo": 222
            },
            "bar": 333
        },
        "baz": [444]
    })))

    # 类型检查，如果不满足会报错
    print(requireConfig('', "test.json", {
        "first\\.second": dict[str, int],
        "baz": list[int],
    }).check())  # 打印：{'first': {'second': {'third': 111, 'foo': 222}}, 'baz': [444]}

    try:
        requireConfig('', "test.json", {
            "first\\.second": dict[str, str]  # 类型不匹配
        }).check()
    except ConfigDataTypeError as err:
        print(err)  # 打印：\.first\.second\.third -> \.third (3 / 3) Must be '<class 'str'>', Not '<class 'int'>'

    try:
        requireConfig('', "test.json", {
            "baz": list[str]
        }).check()
    except ConfigDataTypeError as err:
        print(err)  # 打印：\.baz\[0\] -> \[0\] (2 / 2) Must be '<class 'str'>', Not '<class 'int'>'

    # 默认值，路径不存在时自动填充
    print(requireConfig('', "test.json", {
        "first\\.second\\.third": 999,  # 因为路径已存在所以不会填充
        "not\\.exists": 987
    }).check())  # 打印： {'first': {'second': {'third': 111}}, 'not': {'exists': 987}}

    # 在提供默认值的同时提供类型检查
    # 一般情况下用不着，因为会自动根据默认值的类型来设置类型检查
    # 一般在传入的默认值类型与类型检查的类型不同或规避特殊语法时使用
    print(requireConfig('', "test.json", {
        "first\\.second\\.third": FieldDefinition(int, 999),
        "not\\.exists": FieldDefinition(int, 987),
        "baz": FieldDefinition(Sequence[int], [654]),
    }).check())  # 打印：{'first': {'second': {'third': 111}}, 'not': {'exists': 987}, 'baz': [444]}
    print(requireConfig('', "test.json", {
        "first\\.second": FieldDefinition(dict, {"key": int}, allow_recursive=False),  # 并不会被递归处理，会被当作默认值处理
        "not exists": FieldDefinition(dict, {"key": int}, allow_recursive=False),
        "type": FieldDefinition(type, frozenset),
    }).check())
    # 打印：
    #  {'first': {'second': {'third': 111, 'foo': 222}}, 'not exists': {'key': <class 'int'>}, 'type': <class 'frozenset'>}

    # 含有非字符串键的子Mapping不会被递归处理
    print(requireConfig('', "test.json", {
        "first\\.second": {"third": str, 3: 4},
        # 效果等同于FieldDefinition(dict, {"third": str, 3: 4}, allow_recursive=False)
        "not exists": {1: 2},
    }).check())  # 打印：{'first': {'second': {'third': 111, 'foo': 222}}, 'not exists': {'key': <class 'int'>}}

几个关键字参数

.. code-block:: python
    :caption: 关键字参数
    :linenos:

    from C41811.Config import ConfigData
    from C41811.Config import ConfigFile
    from C41811.Config import JsonSL
    from C41811.Config import requireConfig
    from C41811.Config import save
    from C41811.Config.errors import RequiredPathNotFoundError

    JsonSL().register_to()

    raw_data = ConfigData({
        "first": {
            "second": {
                "third": 111,
                "foo": 222
            },
            "bar": 333
        },
        "baz": [444]
    })

    save('', "test.json", config=ConfigFile(raw_data))

    # allow_modify, 在填充默认值时将默认值填充到源数据
    requireConfig('', "test.json", {
        "not\\.exists": 987
    }).check(allow_modify=False)

    # 未提供allow_modify参数时不会影响源数据
    print(raw_data.exists("not\\.exists"))  # 打印：False

    # ConfigRequirementDecorator.__init__将allow_modify默认值设为True
    requireConfig('', "test.json", {
        "not\\.exists": 987
    }).check()

    print(raw_data.exists("not\\.exists"))  # 打印：True
    raw_data.delete("not\\.exists")

    # skip_missing, 在没提供默认值且键不存在时忽略
    try:
        requireConfig('', "test.json", {
            "not\\.exists": int
        }).check()
    except RequiredPathNotFoundError as err:
        print(err)  # 打印：\.not\.exists -> \.exists (2 / 2) Operate: Read

    data: ConfigData = requireConfig('', "test.json", {
        "not\\.exists": int
    }).check(skip_missing=True)

    print(data.exists("not\\.exists"))  # 打印：False

.. seealso::
   :py:class:`~Config.validators.DefaultValidatorFactory`

不使用验证器工厂
^^^^^^^^^^^^^^^^

``validator_factory`` 参数设为 :py:attr:`~Config.validators.ValidatorTypes.NO_VALIDATION` 或 ``"no-validation"`` 时采用该策略

这将直接把 ``validator`` 参数当作 ``Callable[[ABCConfigData], ABCConfigData]`` 来使用

.. code-block:: python
    :caption: 一个修改所有值为"modified!"的验证器
    :linenos:

    from C41811.Config import ConfigData
    from C41811.Config import ConfigFile
    from C41811.Config import JsonSL
    from C41811.Config import requireConfig
    from C41811.Config import save
    from C41811.Config.abc import ABCConfigData


    def modify_value_validator[D: ABCConfigData](data: D) -> D:
        for path in data.keys(recursive=True, end_point_only=True):
            data.modify(path, "modified!")
        return data


    JsonSL().register_to()

    save('', "test.json", config=ConfigFile(ConfigData({
        "key": "value"
    })))
    print(requireConfig('', "test.json", modify_value_validator, "ignore").check())
    # 输出：{'key': 'modified!'}

组件验证工厂
^^^^^^^^^^^^^^^

``validator_factory`` 参数设为 :py:attr:`~Config.validators.ValidatorTypes.COMPONENT` 或 ``"component"`` 时使用该验证工厂

``validator`` 参数为 ``Mapping[str | None, Any]``

键为组件成员文件名，值为成员对应的验证器，组件成员文件名为None则为元配置信息验证器

.. warning::
   :name: component-validator-factory-none-config-data-warning

   永远不应该尝试验证 :py:class:`~Config.base.NoneConfigData` ，这将创建一个 :py:attr:`~Config.base.ComponentMeta.parser` 为
   ``None`` 的 :py:class:`~Config.base.ComponentMeta`，如果你没有在 :ref:`component-validator-factory-extra-config` 传入新的
   `组件元数据验证器` 这将可能导致(至少目前默认情况下会)无法将组件元配置同步到组件元信息，最终导致元信息和组件成员不匹配抛出错误

.. seealso::
   :py:class:`~Config.validators.ComponentValidatorFactory`

ConfigData
------------------

此类本身不提供任何实际配置数据操作，仅根据传入的参数类型从注册表中选择对应的子类实例化并返回

注册表存储在 :py:attr:`~Config.base.ConfigData.TYPES`

.. rubric:: 传入的数据类型及其对应子类

优先级从上倒下，ConfigData未传入参数时取 ``None`` ，取初始化参数的第一个参数的类型进行判断

.. list-table::
   :widths: auto
   :header-rows: 1

   * - 数据类型
     - 子类

   * - :py:class:`~Config.abc.ABCConfigData`
     - 原样返回

   * - :py:class:`types.NoneType`
     - :py:class:`~Config.base.NoneConfigData`

   * - :py:class:`collections.abc.Mapping`
     - :py:class:`~Config.base.MappingConfigData`

   * - :py:class:`~builtins.str` , :py:class:`~builtins.bytes`
     - :py:class:`~Config.base.StringConfigData`

   * - :py:class:`collections.abc.Sequence`
     - :py:class:`~Config.base.SequenceConfigData`

   * - :py:class:`~builtins.bool`
     - :py:class:`~Config.base.BoolConfigData`

   * - :py:class:`numbers.Number`
     - :py:class:`~Config.base.NumberConfigData`

   * - :py:class:`~builtins.object`
     - :py:class:`~Config.base.ObjectConfigData`

.. note::
   是的， :py:class:`~Config.base.ComponentConfigData` 不在这里面，仅由
   :py:class:`~Config.processor.ComponentSL` 或
   :py:class:`~Config.validators.ComponentValidatorFactory` 创建

   .. seealso::
      具体原因与 :ref:`component-validator-factory-none-config-data-warning` 大同小异

.. rubric:: 若希望作为类型提示请考虑下表

.. list-table::
   :widths: auto
   :header-rows: 1

   * - 配置数据类型
     - 描述

   * - :py:class:`~Config.abc.ABCConfigData`
     - 所有配置数据的抽象基类，仅提供了最基础的 :py:meth:`~Config.abc.ABCConfigData.freeze`
       :py:meth:`~Config.abc.ABCConfigData.from_data` 等方法

   * - :py:class:`~Config.abc.ABCIndexedConfigData`
     - 支持复杂嵌套数据的抽象基类，提供了 :py:meth:`~Config.abc.ABCIndexedConfigData.retrieve`
       :py:meth:`~Config.abc.ABCIndexedConfigData.modify` 等高级嵌套数据访问方法

   * - :py:class:`~Config.base.BasicSingleConfigData`
     - 单文件配置数据的基类，提供的单文件配置数据的基本实现，如 :py:attr:`~Config.base.BasicSingleConfigData.data`

NoneConfigData
^^^^^^^^^^^^^^^^^^

无参数调用 :py:class:`~Config.base.ConfigData` 的默认值，也是 :py:meth:`~Config.main.BasicConfigSL.initialize` 的默认返回值

初始化参数永远必须为 ``None`` 或压根不传，允许传参更大是为了兼容父类接口

MappingConfigData
^^^^^^^^^^^^^^^^^^^

.. todo

SequenceConfigData
^^^^^^^^^^^^^^^^^^^

StringConfigData
^^^^^^^^^^^^^^^^^^^

NumberConfigData
^^^^^^^^^^^^^^^^^^^

BooleanConfigData
^^^^^^^^^^^^^^^^^^^

ComponentConfigData
^^^^^^^^^^^^^^^^^^^^

组件配置数据由元信息与成员配置组成

.. _component-meta:
元信息
...........

存储了 :ref:`component-meta-config` 、 :ref:`component-meta-member` 、 :ref:`component-meta-order` 、
:ref:`component-meta-parser` 几部分必须的值。

.. seealso::
   :py:class:`~Config.base.ComponentMeta`

.. rubric:: 元配置
   :name: component-meta-config

元信息默认存储在 ``__init__`` 配置文件内，元配置就是 ``__init__`` 内的原始配置数据

.. attention::
   原始配置数据结构完全由 :ref:`component-meta-parser` 定义，除非是处理额外附加数据，否则不应该直接对其进行操作

目前是以 :py:class:`~Config.base.MappingConfigData` 存储

.. rubric:: 成员定义
   :name: component-meta-member

成员 `文件名` ， `别名` ，及其 `配置格式`

`文件名` 应严格与 :ref:`component-member` 一一对应

`别名` 可以在 :ref:`component-meta-order` 中或 :ref:`component-member-path-meta-syntax` 中使用

`配置格式` 会在保存加载期间优先使用

.. seealso::
   :py:class:`~Config.base.ComponentMember`

.. rubric:: 处理顺序
   :name: component-meta-order

:py:meth:`~Config.base.ComponentConfigData.retrieve` 等方法从成员的搜索顺序

.. seealso::
   :py:class:`~Config.base.ComponentOrder`

.. rubric:: 解析器
   :name: component-meta-parser

负责将 :ref:`component-meta-config` 与 :ref:`component-meta` 以一定格式互相转换

.. seealso::
   :py:class:`~Config.processor.Component.ComponentMetaParser`

.. _component-member:
成员
...........

成员配置文件的配置数据

.. _component-member-path-meta-syntax:
.. rubric:: 键元信息语法指定成员进行操作

:py:meth:`~Config.base.ComponentConfigData.retrieve` 等方法支持使用 :ref:`键元信息 <term-key-meta>` 指定成员进行操作

.. code-block:: python
   :caption: 指定从成员member.json读取数据

   comp_data.retrieve(r"\{member.json\}\.key")
   # 如果有别名也可以使用别名
   comp_data.retrieve(r"\{alies-member\}\.key")

具体来说，会读取 ``path[0].meta`` ，所以只有第一个键的元信息起到作用

SL处理器
-------------

.. todo

.. list-table::
   :widths: auto
