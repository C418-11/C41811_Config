常见问题
========

如何注册SL处理器/为什么死活在报UnsupportedConfigFormatError？
-------------------------------------------------------------

.. code-block:: python
    :caption: 例子：将JsonSL注册到配置池

    # 注册到默认配置池
    from c41811.config import JsonSL
    JsonSL().register_to()
    # 等同于
    from c41811.config import DefaultConfigPool
    JsonSL().register_to(DefaultConfigPool)
    # 注册到其他配置池
    from c41811.config import ConfigPool
    pool = ConfigPool()
    JsonSL().register_to(pool)

其他SL处理器同理

如果这不能解决问题，请检查是否为如 :py:class:`~config.processor.zipfile.ZipFileSL` 或
:py:class:`~config.processor.component.ComponentSL` 这类链式处理器，这类处理器在自动推断成员的配置格式时需求文件为类似
``filename.json.zip`` 或 ``component-config.json.component`` 的文件名以推导内部成员或其 :ref:`term-component-meta-config`
的配置格式

如何简单的管理配置默认值，类型验证？
------------------------------------

参见 :ref:`detail-requireConfig`


如何快速保存所有配置文件？
--------------------------

确保你要保存的配置文件都在 `同一个` 配置池中

 :py:const:`~config.main.requireConfig`
 :py:const:`~config.main.load`
 :py:const:`~config.main.get`
 都属于 :py:const:`~config.main.DefaultConfigPool` 配置池

 如果 ``ConfigFile`` 不是从这些地方得到的
 可以使用 :py:const:`~config.main.set_`
 (等同于 ``DefaultConfigPool.set``)
 或者任意配置池(``ABCConfigPool`` 子类) 的 ``set`` 方法将其添加到同一配置池中

 .. seealso::
     :py:func:`~config.abc.ABCConfigPool.set` 或提供 ``config`` 参数的 :py:func:`~config.abc.ABCConfigPool.save`

 .. code-block:: python
    :caption: 一些手动添加到配置池的方式

    # 添加到默认配置文件池
    from c41811.config import set_
    set_(...)
    # 等同于
    from c41811.config import DefaultConfigPool
    DefaultConfigPool.set(...)
    # 或者使用自定义的配置池
    from c41811.config import ConfigPool
    pool = ConfigPool()
    pool.set(...)

然后简单的调用saveAll

.. seealso::
   :py:func:`~config.abc.ABCConfigPool.save_all`


.. code-block:: python
   :caption: 保存所有配置文件

   # 保存所有默认配置文件池中的配置文件
   from c41811.config import saveAll
   saveAll(...)
   # 等同于
   from c41811.config import DefaultConfigPool
   DefaultConfigPool.save_all(...)
   # 使用自定义的配置池
   from c41811.config import ConfigPool
   pool = ConfigPool()
   pool.save_all(...)
