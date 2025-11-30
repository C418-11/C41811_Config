详细文档
==============

.. _term-config-data-path-syntax:

配置数据路径语法
-----------------

一种简便的配置数据访问路径表示方法，
在一些高级方法如 :py:func:`~config.abc.ABCIndexedConfigData.retrieve` 中使用

由三种语法组成

.. rubric:: 属性键
   :name: term-attr-key

由 ``\.`` 开头，紧随的字符串组成

.. code-block:: python
   :caption: 例

   r"\.key1\.key2\.key3"

.. tip::

   如果路径字符串以 :ref:`term-attr-key` 开头可以省略 ``\.``

   .. code-block:: python
      :caption: 例

      r"key1\.key2\.key3"

      # 这将被视为

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

.. rubric:: 转义

键名或元信息中如有 ``\`` 需要转义 为 ``\\``

.. code-block:: python
   :caption: 例

   r"\{1\\2\}\.\\key\{2\\2\}\[0\]"

   # 这将解析为

   [AttrKey(r"\key", meta=r"1\2"), IndexKey(0, meta=r"2\2")]

可以简单的通过 ``str.replace("\\", "\\\\")`` 来转义

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
      :py:class:`~config.main.RequiredPath`

有手动调用和装饰器两种获取验证数据的方式

.. code-block:: python
    :caption: 手动调用和装饰器
    :linenos:

    from c41811.config import MappingConfigData
    from c41811.config import JsonSL
    from c41811.config import requireConfig

    JsonSL().register_to()

    require = requireConfig(
        "", "config.json", {
            "config": "data",
        },
    )

    # 调用check手动获取配置数据
    config: MappingConfigData = require.check()
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

.. hint::
   pydantic 验证器工厂不支持 ``skip_missing`` 选项
   这是因为pydantic自带该功能
   如果提供了该参数会产生一个警告 不会起到任何实际作用

``validator_factory`` 参数设为 :py:attr:`~config.validators.ValidatorTypes.PYDANTIC` 或 ``"pydantic"`` 时使用该验证工厂

``validator`` 参数为任意合法的 :py:class:`~pydantic.main.BaseModel`

.. code-block:: python
    :caption: 一个简单的pydantic验证器
    :linenos:

    from pydantic import BaseModel
    from pydantic import Field

    from c41811.config import MappingConfigData
    from c41811.config import ConfigFile
    from c41811.config import JsonSL
    from c41811.config import requireConfig
    from c41811.config import save

    JsonSL().register_to()

    save("", "test.json", config=ConfigFile(MappingConfigData({
        "key": "value"
    })))


    class Config(BaseModel):
        key: str = "default value"
        unknown_key: dict = Field(default_factory=dict)


    print(requireConfig("", "test.json", Config, "pydantic").check())
    # 打印：{'key': 'value', 'unknown_key': {}}


默认验证器工厂
^^^^^^^^^^^^^^

``validator_factory`` 参数设为 :py:attr:`~config.validators.ValidatorTypes.DEFAULT` 或 :py:const:`None` 时使用该验证工厂

``validator`` 参数可以为 ``Iterable[str]`` 或 ``Mapping[str | ABCPath, Any]``

:py:class:`~collections.abc.Iterable` 的元素或 :py:class:`~collections.abc.Mapping` 的键会被作为
:ref:`term-config-data-path-syntax` 解析，如非特殊配置结果将一定包含这些 :ref:`配置数据路径 <term-config-data-path-syntax>`

.. note::

    [path, path1, path2, ...] 与 {path: Any, path1: Any, path2: Any, ...} 等价

.. tip::
    :collapsible:

    如果validator同时包含路径和路径的父路径

    例： ``r"\.first\.second\.third"`` 与 ``r"\.first"`` 同时出现

    这时 ``first`` 中不仅包含 ``second`` ，还会允许任意额外的键

    .. code-block:: python
        :caption: 例
        :linenos:

        from c41811.config import MappingConfigData
        from c41811.config import ConfigFile
        from c41811.config import JsonSL
        from c41811.config import requireConfig
        from c41811.config import save

        JsonSL().register_to()

        save("", "test.json", config=ConfigFile(MappingConfigData({
            "first": {
                "second": {
                    "third": 111,
                    "foo": 222
                },
                "bar": 333
            },
            "baz": 444
        })))

        print(requireConfig("", "test.json", ["first", "first\\.second\\.third"]).check())
        # 打印：{'first': {'second': {'third': 111}, 'bar': 333}}

Iterable[str]
.................

一组需求的 :ref:`配置数据路径 <term-config-data-path-syntax>` ，会检查路径存在与否，不会校验数据类型

.. code-block:: python
    :caption: 例
    :linenos:

    from c41811.config import MappingConfigData
    from c41811.config import ConfigFile
    from c41811.config import JsonSL
    from c41811.config import requireConfig
    from c41811.config import save

    JsonSL().register_to()

    save("", "test.json", config=ConfigFile(MappingConfigData({
        "foo": {
            "bar": {
                "baz": "value"
            },
            "bar1": "value1"
        },
        "foo1": "value2"
    })))

    print(requireConfig("", "test.json", ["foo", "foo\\.bar\\.baz", "foo1"]).check())
    # 打印：{'foo': {'bar': {'baz': 'value'}, 'bar1': 'value1'}, 'foo1': 'value2'}

Mapping[str | ABCPath, Any]
.............................

键为 :ref:`配置数据路径 <term-config-data-path-syntax>` ，值为需求的数据类型，会检查路径存在与否，并校验数据类型

.. tip::
    :collapsible:

    ``r"first\.second\.third": int`` 与 ``"first": {"second": {"third": int}}`` 等价

    * 允许混用路径与嵌套字典

    .. code-block:: python
        :caption: 路径与嵌套字典的等价操作
        :linenos:

        from c41811.config import MappingConfigData
        from c41811.config import ConfigFile
        from c41811.config import JsonSL
        from c41811.config import requireConfig
        from c41811.config import save

        JsonSL().register_to()

        save("", "test.json", config=ConfigFile(MappingConfigData({
            "first": {
                "second": {
                    "third": 111,
                    "foo": 222
                },
                "bar": 333
            },
            "baz": 444
        })))

        paths = requireConfig("", "test.json", {
            r"first\.second\.third": int,
            r"first\.bar": int,
        }).check()
        nested_dict = requireConfig("", "test.json", {
            "first": {
                "second": {
                    "third": int
                },
                "bar": int
            }
        }).check()

        print(paths)  # 打印: {'first': {'second': {'third': 111}, 'bar': 333}}
        print(nested_dict)  # 打印: {'first': {'second': {'third': 111}, 'bar': 333}}
        print(paths == nested_dict)  # 打印: True

以下是两种验证器语法

.. code-block:: python
    :caption: 两种验证器语法
    :linenos:

    from c41811.config import MappingConfigData
    from c41811.config import ConfigFile
    from c41811.config import JsonSL
    from c41811.config import requireConfig
    from c41811.config import save

    JsonSL().register_to()

    save("", "test.json", config=ConfigFile(MappingConfigData({
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
    print(requireConfig("", "test.json", {
        "first\\.second\\.third": int,
        "first\\.bar": int,
    }).check())  # 打印：{'first': {'second': {'third': 111}, 'bar': 333}}

    # 使用嵌套字典
    print(requireConfig("", "test.json", {
        "first": {
            "second": {
                "third": int
            },
            "bar": int
        }
    }).check())  # 打印：{'first': {'second': {'third': 111}, 'bar': 333}}

    # 混搭
    print(requireConfig("", "test.json", {
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

    from c41811.config import MappingConfigData
    from c41811.config import ConfigFile
    from c41811.config import FieldDefinition
    from c41811.config import JsonSL
    from c41811.config import requireConfig
    from c41811.config import save
    from c41811.config.errors import ConfigDataTypeError

    JsonSL().register_to()

    save("", "test.json", config=ConfigFile(MappingConfigData({
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
    print(requireConfig("", "test.json", {
        "first\\.second": dict[str, int],
        "baz": list[int],
    }).check())  # 打印：{'first': {'second': {'third': 111, 'foo': 222}}, 'baz': [444]}

    try:
        requireConfig("", "test.json", {
            "first\\.second": dict[str, str]  # 类型不匹配
        }).check()
    except ConfigDataTypeError as err:
        print(err)  # 打印：\.first\.second\.third -> \.third (3 / 3) Must be '<class 'str'>', Not '<class 'int'>'

    try:
        requireConfig("", "test.json", {
            "baz": list[str]
        }).check()
    except ConfigDataTypeError as err:
        print(err)  # 打印：\.baz\[0\] -> \[0\] (2 / 2) Must be '<class 'str'>', Not '<class 'int'>'

    # 默认值，路径不存在时自动填充
    print(requireConfig("", "test.json", {
        "first\\.second\\.third": 999,  # 因为路径已存在所以不会填充
        "not\\.exists": 987
    }).check())  # 打印： {'first': {'second': {'third': 111}}, 'not': {'exists': 987}}

    # 在提供默认值的同时提供类型检查
    # 一般情况下用不着，因为会自动根据默认值的类型来设置类型检查
    # 一般在传入的默认值类型与类型检查的类型不同或规避特殊语法时使用
    print(requireConfig("", "test.json", {
        "first\\.second\\.third": FieldDefinition(int, 999),
        "not\\.exists": FieldDefinition(int, 987),
        "baz": FieldDefinition(Sequence[int], [654]),
    }).check())  # 打印：{'first': {'second': {'third': 111}}, 'not': {'exists': 987}, 'baz': [444]}
    print(requireConfig("", "test.json", {
        "first\\.second": FieldDefinition(dict, {"key": int}, allow_recursive=False),  # 并不会被递归处理，会被当作默认值处理
        "not exists": FieldDefinition(dict, {"key": int}, allow_recursive=False),
        "type": FieldDefinition(type, frozenset),
    }).check())
    # 打印：
    #  {'first': {'second': {'third': 111, 'foo': 222}}, 'not exists': {'key': <class 'int'>}, 'type': <class 'frozenset'>}

    # 含有非字符串键的子Mapping不会被递归处理
    print(requireConfig("", "test.json", {
        "first\\.second": {"third": str, 3: 4},
        # 效果等同于FieldDefinition(dict, {"third": str, 3: 4}, allow_recursive=False)
        "not exists": {1: 2},
    }).check())  # 打印：{'first': {'second': {'third': 111, 'foo': 222}}, 'not exists': {'key': <class 'int'>}}

几个关键字参数

.. code-block:: python
    :caption: 关键字参数
    :linenos:

    from c41811.config import MappingConfigData
    from c41811.config import ConfigFile
    from c41811.config import JsonSL
    from c41811.config import requireConfig
    from c41811.config import save
    from c41811.config.errors import RequiredPathNotFoundError

    JsonSL().register_to()

    raw_data = MappingConfigData({
        "first": {
            "second": {
                "third": 111,
                "foo": 222
            },
            "bar": 333
        },
        "baz": [444]
    })

    save("", "test.json", config=ConfigFile(raw_data))

    # allow_modify, 在填充默认值时将默认值填充到源数据
    requireConfig("", "test.json", {
        "not\\.exists": 987
    }).check(allow_modify=False)

    # 未提供allow_modify参数时不会影响源数据
    print(raw_data.exists("not\\.exists"))  # 打印：False

    # ConfigRequirementDecorator.__init__将allow_modify默认值设为True
    requireConfig("", "test.json", {
        "not\\.exists": 987
    }).check()

    print(raw_data.exists("not\\.exists"))  # 打印：True
    raw_data.delete("not\\.exists")

    # skip_missing, 在没提供默认值且键不存在时忽略
    try:
        requireConfig("", "test.json", {
            "not\\.exists": int
        }).check()
    except RequiredPathNotFoundError as err:
        print(err)  # 打印：\.not\.exists -> \.exists (2 / 2) Operate: Read

    data: MappingConfigData = requireConfig("", "test.json", {
        "not\\.exists": int
    }).check(skip_missing=True)

    print(data.exists("not\\.exists"))  # 打印：False

.. seealso::
   :py:class:`~config.validators.DefaultValidatorFactory`

自定义验证器
^^^^^^^^^^^^^^^^

``validator_factory`` 参数设为 :py:attr:`~config.validators.ValidatorTypes.CUSTOM` 或 ``"custom"`` 时采用该策略

这将直接把 ``validator`` 参数当作验证器 ``Callable[[Ref[D], ValidatorOptions], D]`` 来使用，如果 ``validator`` 为 ``None``
则验证器默认为 ``lambda ref:ref.value`` ，即无验证

.. code-block:: python
    :caption: 一个修改所有值为"modified!"的验证器
    :linenos:

    from copy import deepcopy
    from typing import Any

    from c41811.config import ConfigFile
    from c41811.config import JsonSL
    from c41811.config import MappingConfigData
    from c41811.config import ValidatorOptions
    from c41811.config import requireConfig
    from c41811.config import save
    from c41811.config.utils import Ref


    def modify_value_validator[D: MappingConfigData[Any]](ref: Ref[D], cfg: ValidatorOptions) -> D:
        data = deepcopy(ref.value)
        for path in data.keys(recursive=True, end_point_only=True):
            data.modify(path, "modified!")
        if cfg.allow_modify:
            ref.value = data
        return data


    JsonSL().register_to()

    save("", "test.json", config=ConfigFile(MappingConfigData({
        "key": "value"
    })))
    print(requireConfig("", "test.json", modify_value_validator, "custom").check())
    # 输出：{'key': 'modified!'}

.. _component-validator-factory:

组件验证工厂
^^^^^^^^^^^^^^^

``validator_factory`` 参数设为 :py:attr:`~config.validators.ValidatorTypes.COMPONENT` 或 ``"component"`` 时使用该验证工厂

``validator`` 参数为 ``Mapping[str | None, Any]``

键为组件成员文件名，值为成员对应的验证器，组件成员文件名为None则为元配置信息验证器

.. danger::
   永远不应该尝试验证 :py:class:`~config.basic.object.NoneConfigData` ，这将创建一个
   :py:attr:`~config.basic.component.ComponentMeta.parser` 为
   :py:const:`None` 的 :py:class:`~config.basic.component.ComponentMeta`，如果你没有在
   :py:class:`额外验证器选项 <Config.validators.ComponentValidatorFactory>` 传入默认的
   `组件元数据验证器` 这将可能导致(至少目前默认情况下会)无法将组件元配置同步到组件元信息，最终导致元信息和组件成员不匹配抛出错误

.. seealso::
   :py:class:`~config.validators.ComponentValidatorFactory`

ConfigDataFactory
------------------

此类本身不提供任何实际配置数据操作，仅根据传入的参数类型从注册表中选择对应的类实例化并返回

注册表存储在 :py:attr:`~config.basic.ConfigDataFactory.TYPES`

.. rubric:: 传入的数据类型及其对应类

优先级从上倒下，取初始化参数的第一个参数的类型进行判断，未传入参数时取 :py:const:`None`

.. list-table::
   :widths: auto
   :header-rows: 1

   * - 数据类型
     - 配置数据类

   * - :py:class:`~config.abc.ABCConfigData`
     - 原样返回

   * - :py:class:`types.NoneType`
     - :py:class:`~config.basic.object.NoneConfigData`

   * - :py:class:`~collections.abc.Mapping`
     - :py:class:`~config.basic.mapping.MappingConfigData`

   * - :py:class:`str` , :py:class:`bytes`
     - :py:class:`~config.basic.sequence.StringConfigData`

   * - :py:class:`~collections.abc.Sequence`
     - :py:class:`~config.basic.sequence.SequenceConfigData`

   * - :py:class:`bool`
     - :py:class:`~config.basic.number.BoolConfigData`

   * - :py:class:`numbers.Number`
     - :py:class:`~config.basic.number.NumberConfigData`

   * - :py:class:`object`
     - :py:class:`~config.basic.object.ObjectConfigData`

.. note::
   是的， :py:class:`~config.basic.component.ComponentConfigData` 不在这里面，仅由
   :py:class:`~config.processor.componentSL` 或
   :py:class:`~config.validators.ComponentValidatorFactory` 创建

   .. seealso::
      具体原因与 :ref:`component-validator-factory` 所述大同小异

.. rubric:: 若希望作为类型提示请考虑下表

.. list-table::
   :widths: auto
   :header-rows: 1

   * - 配置数据类型
     - 描述

   * - :py:class:`~config.abc.ABCConfigData`
     - 所有配置数据的抽象基类，仅提供了最基础的 :py:meth:`~config.abc.ABCConfigData.freeze`
       :py:meth:`~config.abc.ABCConfigData.from_data` 等方法

   * - :py:class:`~config.abc.ABCIndexedConfigData`
     - 支持复杂嵌套数据的抽象基类，提供了 :py:meth:`~config.abc.ABCIndexedConfigData.retrieve`
       :py:meth:`~config.abc.ABCIndexedConfigData.modify` 等高级嵌套数据访问方法

   * - :py:class:`~config.basic.core.BasicSingleConfigData`
     - 单文件配置数据的基类，提供的单文件配置数据的基本实现，如 :py:attr:`~config.basic.core.BasicSingleConfigData.data`

NoneConfigData
^^^^^^^^^^^^^^^^^^

无参数调用 :py:class:`~config.basic.ConfigDataFactory` 的默认值，也是 :py:meth:`~config.main.BasicConfigSL.initialize` 的默认返回值

初始化参数永远必须为 :py:const:`None` 或压根不传，允许传参更大是为了兼容父类接口

MappingConfigData
^^^^^^^^^^^^^^^^^^^

最常见的配置数据类型，提供了 :py:class:`~collections.abc.MutableMapping` 的完整实现。

:py:meth:`~config.abc.ABCIndexedConfigData.retrieve` 等高级方法当返回值为 :py:class:`~collections.abc.Mapping` 或
:py:class:`~collections.abc.Sequence` 时， :py:meth:`~config.abc.ABCIndexedConfigData.retrieve` 会返回
:py:class:`~config.basic.mapping.MappingConfigData` 或 :py:class:`~config.basic.sequence.SequenceConfigData`

SequenceConfigData
^^^^^^^^^^^^^^^^^^^

提供了 :py:class:`~collections.abc.MutableSequence` 的完整实现

:py:meth:`~config.abc.ABCIndexedConfigData.retrieve` 等高级方法当返回值为 :py:class:`~collections.abc.Mapping` 或
:py:class:`~collections.abc.Sequence` 时， :py:meth:`~config.abc.ABCIndexedConfigData.retrieve` 会返回
:py:class:`~config.basic.mapping.MappingConfigData` 或 :py:class:`~config.basic.sequence.SequenceConfigData`

StringConfigData
^^^^^^^^^^^^^^^^^^^

字符串与字节串的配置数据

尚未完整实现 :py:class:`~collections.UserString` 的接口

NumberConfigData
^^^^^^^^^^^^^^^^^^^

提供了 :py:class:`numbers.Integral` 与 :py:class:`numbers.Real` 的大部分实现

BoolConfigData
^^^^^^^^^^^^^^^^^^^

继承自 :py:class:`~config.basic.number.NumberConfigData` ，提供了 :py:class:`bool` 的实现

ComponentConfigData
^^^^^^^^^^^^^^^^^^^^

组件配置数据由元信息与成员配置组成

.. _component-meta:

元信息
...........

存储了 :ref:`term-component-meta-config` 、 :ref:`component-meta-member` 、 :ref:`component-meta-order` 、
:ref:`component-meta-parser` 几部分必须的值。

.. seealso::
   :py:class:`~config.basic.component.ComponentMeta`

.. rubric:: 元配置
   :name: term-component-meta-config

元信息默认存储在 ``__meta__`` 配置文件内，元配置就是 ``__meta__`` 内的原始配置数据，文件名由 :py:attr:`~config.processor.component.ComponentSL.meta_file` 指定

.. attention::
   原始配置数据结构完全由 :ref:`component-meta-parser` 定义，除非你能保证数据结构在你的预期内，否则不应该直接对其进行操作(不同
   :ref:`component-meta-parser` 的实现可能使用完全不同的数据结构甚至数据类型！)

以 :py:class:`~config.basic.mapping.MappingConfigData` 存储

.. rubric:: 成员定义
   :name: component-meta-member

成员 `文件名` ， `别名` ，及其 `配置格式`

`文件名` 应严格与 :ref:`component-member` 一一对应

`别名` 可以在 :ref:`component-meta-order` 中或 :ref:`component-member-path-meta-syntax` 中使用

`配置格式` 会在保存加载期间优先使用

.. seealso::
   :py:class:`~config.basic.component.ComponentMember`

.. rubric:: 处理顺序
   :name: component-meta-order

:py:meth:`~config.basic.ComponentConfigData.retrieve` 等方法从成员的搜索顺序，参见下表：

.. list-table::
   :widths: auto
   :header-rows: 1

   * - 顺序表
     - 使用该表的方法

   * - :py:attr:`~config.basic.component.ComponentOrders.create`
     - :py:meth:`~config.basic.ComponentConfigData.modify`
     - :py:meth:`~config.basic.ComponentConfigData.setdefault`

   * - :py:attr:`~config.basic.component.ComponentOrders.read`
     - :py:meth:`~config.basic.ComponentConfigData.retrieve`, :py:meth:`~config.basic.ComponentConfigData.exists`, :py:meth:`~config.basic.ComponentConfigData.get`, :py:meth:`~config.basic.ComponentConfigData.setdefault`

   * - :py:attr:`~config.basic.component.ComponentOrders.update`
     - :py:meth:`~config.basic.ComponentConfigData.modify`

   * - :py:attr:`~config.basic.component.ComponentOrders.delete`
     - :py:meth:`~config.basic.ComponentConfigData.delete`, :py:meth:`~config.basic.ComponentConfigData.unset`

.. seealso::
   :py:class:`~config.basic.component.ComponentOrders`

.. rubric:: 解析器
   :name: component-meta-parser

负责将 :ref:`term-component-meta-config` 与 :ref:`component-meta` 以一定格式互相转换，由
:py:class:`~config.basic.component.ComponentMeta.parser` 属性存储，可以在
:py:meth:`~config.processor.component.ComponentSL` 中通过初始化方法的 `meta_parser` 参数指定

.. seealso::
   默认实现： :py:class:`~config.processor.component.ComponentMetaParser` 讲解： :ref:`component-meta-parser-default-structure`

.. _component-member:

成员
...........

成员配置文件的配置数据，支持所有 :py:class:`~config.abc.ABCIndexedConfigData` 的子类

.. _component-member-path-meta-syntax:
.. rubric:: 键元信息语法指定成员进行操作

:py:meth:`~config.basic.ComponentConfigData.retrieve` 等方法支持使用 :ref:`键元信息 <term-key-meta>` 指定成员进行操作

.. code-block:: python
   :caption: 指定从成员member.json读取数据

   comp_data.retrieve(r"\{member.json\}\.key")
   # 如果有别名也可以使用别名
   comp_data.retrieve(r"\{alies-member\}\.key")
   # 如果成员为SequenceConfigData
   comp_data.retrieve(r"\{member.json\}\[0\]")

具体来说，会读取 ``path[0].meta`` ，所以只有第一个键的元信息起到作用

EnvironmentConfigData
^^^^^^^^^^^^^^^^^^^^^^^

继承自 :py:class:`~config.basic.mapping.MappingConfigData` ，内部维护了与初始化参数的键差异

.. seealso::
   :py:class:`~config.basic.environment.Difference`

SL处理器
-------------

项目中的 ``SL`` 都是 ``SaveLoad`` 的缩写

.. list-table::
   :widths: auto
   :header-rows: 1

   * - 配置格式
     - 处理器
     - 注册名
     - 支持的文件后缀
     - 简介

   * - JSON
     - :py:class:`~config.processor.json.JsonSL`
     - json
     - .json
     - 基于内置 :py:mod:`json` 模块

   * - HJSON
     - :py:class:`~config.processor.hjson.HJsonSL`
     - hjson
     - .hjson
     - 基于第三方库 ``hjson``

   * - Pickle
     - :py:class:`~config.processor.pickle.PickleSL`
     - pickle
     - .pickle .pkl
     - 基于内置 :py:mod:`pickle` 模块

   * - YAML
     - :py:class:`~config.processor.pyyaml.PyYamlSL`
     - yaml
     - .yaml .yml
     - 基于第三方库 ``PyYAML``

   * - YAML
     - :py:class:`~config.processor.ruamel_yaml.RuamelYamlSL`
     - ruamel_yaml
     - .yaml .yml
     - 基于第三方库 ``ruamel.yaml``

   * - TOML
     - :py:class:`~config.processor.rtoml.RTomlSL`
     - toml
     - .rtoml
     - 基于第三方库 ``rtoml``

   * - TOML
     - :py:class:`~config.processor.tomlkit.TomlKitSL`
     - tomlkit
     - .toml
     - 基于第三方库 ``tomlkit``

   * - CBOR
     - :py:class:`~config.processor.cbor2.CBOR2SL`
     - cbor2
     - .cbor
     - 基于第三方库 ``cbor2``

   * - Properties
     - :py:class:`~config.processor.jproperties.JPropertiesSL`
     - jproperties
     - .properties
     - 基于第三方库 ``jproperties``

   * - Python
     - :py:class:`~config.processor.python.PythonSL`
     - python
     - .py
     - 基于 :py:func:`exec`，尝试保存会将配置数据作为 :py:func:`locals` 传入 ，建议与
       :py:class:`~config.processor.plaintext` 搭配使用

   * - PythonLiteral
     - :py:class:`~config.processor.python_literal.PythonLiteralSL`
     - python_literal
     - .python_literal .pyl .py
     - 基于 :py:func:`~ast.literal_eval` 与 :py:func:`~pprint.pformat`

   * - PlainText
     - :py:class:`~config.processor.plaintext.PlainTextSL`
     - plaintext
     - .txt
     - 纯文本格式，支持额外参数
       ``linesep: str`` 在保存时额外添加换行符，
       ``split_line: bool`` 加载时使用 :py:meth:`~typing.TextIO.readlines`，
       ``remove_linesep: str`` 在加载时使用 :py:meth:`str.removesuffix` 移除换行符

   * - TarFile
     - :py:class:`~config.processor.tarfile.TarFileSL`
     - tarfile:$compression_shortname$
     - .tar .tar.$compression_shortname$ .tar.$compression_fullname$
     - 基于内置 :py:mod:`tarfile` 模块

   * - ZipFile
     - :py:class:`~config.processor.zipfile.ZipFileSL`
     - zipfile:$compression_shortname$-$compress_level$
     - .$compress_level$.zip .zip
       .$compress_level$.$compression_fullname$ .$compress_level$.$compression_shortname$
       .$compression_shortname$ .$compression_fullname$
     - 基于内置 :py:mod:`zipfile` 模块

   * - Component
     - :py:class:`~config.processor.component.ComponentSL`
     - component
     - .component .comp
     - 组合多个 :py:class:`~config.abc.ABCIndexedConfigData` 为一个 :py:class:`~config.basic.component.ComponentConfigData`

   * - OSEnv
     - :py:class:`~config.processor.os_env.OSEnvSL`
     - os.environ
     - .os.env .os.environ
     - 基于内置 :py:data:`os.environ`

ComponentMetaParser
--------------------

:py:class:`~config.processor.component.ComponentSL` 的默认 :ref:`term-component-meta-config` 解析器。

.. _component-meta-parser-default-structure:

.. rubric:: 元配置数据结构

.. code-block:: python
   :caption: 详解

   {
       "members": [  # 声明组件成员，此处声明的文件名必须与提供的组件成员严格匹配
           "filename.json",  # 可以直接提供文件名
           {
               "filename": "name",  # 也可以通过键值对声明
               # 通过键值对声明可以附带额外信息
               "alias": "na",  # 此成员别名为"na"，可被`键元信息`语法或下面的操作顺序使用
               "config_format": "ruamel_yaml",  # 此成员配置格式为ruamel.yaml的YAML解析器
           },
           {"filename": "my-member.pickle"},  # 当然上面这些额外信息是可选的
       ],
       # 操作顺序，并没有严格的检查，已经声明的组件成员可以不被使用但是禁止出现完全重复的名称
       "order": [  # 定义基础的操作顺序，若未提供则顺序敏感地使用members所声明的文件名(若存在则优先使用别名)，可以提供一个空列表以禁用默认行为
           # "filename.json",  # 越靠前优先级越高
           # "na",  # 这里是允许别名的
           # 这里order为空以禁用默认行为(只要提供了此项就会禁用默认行为，无论是否完全为空列表或只填充了部分/全部成员)
       ],
       "orders": {  # order会被同步追加到orders的create/read/update/delete，所以orders优先级最高
           # 会简单的检查将要追加的名称是否已经在表中(如果是则跳过)，这并不会同时检查文件名与别名是否同时存在
           "create": [],  # 禁止创建新的键，此项目控制setdefault方法在路径不存在时的写入顺序与modify无法替换一个现有的数据时来创建数据
           "read": ["filename.json", "my-member.pickle"],  # retrieve等方法仅按照此顺序读取配置数据
           "update": ["filename.json", "na"],  # 显然这是针对modify一类方法替换现有数据的
           "delete": ["filename.json", "my-member.pickle", "na"],  # delete,unset一类涉及删除路径的操作
           # 注意，当unset等方法最终得到的orders其中某项为空时(例如"delete": [])
           # 会抛出RequiredPathNotFoundError且未找到路径一定为根键
       },
   }  # 显然，以上的顺序表都是允许完全为空(且不必包含全部成员)的，这将导致永远无法通过普通的顺序查找检索到未在顺序表中成员，但是仍然可以通过`键元信息`语法指定成员访问
