:py:mod:`Config.base`
=====================


:py:class:`Config.base.ConfigData`
----------------------------------

:py:func:`Config.abc.ABCConfigData.from_data`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

套壳__init__，主要是为了方便内部快速创建与传入的ABCConfigData同类型的对象

例如：

.. code-block:: python

   type(instance)(data)

可以简写为

.. code-block:: python

   instance.from_data(data)

:py:func:`Config.base.ConfigData.retrieve`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
