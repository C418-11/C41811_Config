开始使用
============

.. rubric:: 从一个简单的例子开始

.. code-block:: python
   :caption: 管理一个名为config.json的配置文件
   :linenos:

   from C41811.Config import JsonSL
   from C41811.Config import requireConfig

   # 注册JSON格式处理器
   JsonSL().register_to()

   # 加载并验证配置文件
   cfg = requireConfig(
       # 命名空间，文件名
       '', "config.json",  # 自动从文件后缀推断处理器
       {  # 配置验证规则
           "hello": "world"  # hello字段必须为字符串且默认值为"world"
       },
   ).check()

   print(cfg)  # 打印: {'hello': 'world'}

.. rubric:: 这段代码干了什么

1. 实例化并注册了一个JSON格式处理器
2. 使用 :py:func:`~Config.main.requireConfig` 构建了一个对于文件 ``config.json`` 的 `配置需求器`
3. 对 `配置需求器` 调用 :py:meth:`~Config.main.ConfigRequirementDecorator.check` 读取并验证配置文件
