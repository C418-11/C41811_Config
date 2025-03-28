详细文档
==============

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
requireConfig详细用法
-----------------------------

手动调用和装饰器两种获取验证数据的方式

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


.. note::

    [path, path1, path2, ...] 与 {path: Any, path1: Any, path2: Any, ...} 等价

.. tip::

    如果validator同时包含路径和路径的父路径

    例： ``"\.first\.second\.third"`` 与 ``"\.first"`` 同时出现

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
        "first\\.second": FieldDefinition(dict, {"key": int}, allow_recursive=False),  # 并不会被递归处理,会被当作默认处理
        "not exists": FieldDefinition(dict, {"key": int}, allow_recursive=False),
        "type": FieldDefinition(type, frozenset),
    }).check())
    # 打印：
    #  {'first': {'second': {'third': 111, 'foo': 222}}, 'not exists': {'key': <class 'int'>}, 'type': <class 'frozenset'>}

    # 含有非字符串键的验证器不会被递归处理
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

``static_config`` 提供该参数以获得更高的性能

.. seealso::
   :py:class:`~Config.RequiredPath`


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


组件配置数据
--------------

.. todo

TODO 待做
------------

元信息
^^^^^^^^

1.元配置存储

2.成员定义以及别名

3.组件顺序

4.解析器

成员
^^^^^^^^

1.处理顺序受元信息控制

2.使用元路径语法指定成员进行操作
