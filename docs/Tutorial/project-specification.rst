项目规范
=========

文档字符串规范
--------------

.. code-block:: python
    :caption: 文档字符串模板

    """
    {函数/类简要描述}

    :param {参数名}: {参数描述}
    :type {参数名}: {类型提示}

    :return: {返回值描述}
    :rtype: {返回类型}

    :raise {异常类}: {异常触发条件}

    {功能特性说明（可选段落）}
    -------------

    .. note::
       {注意事项、特殊行为说明}

    .. 版本变更

    .. versionadded:: {x.x.x}

    .. versionchanged:: {x.x.x}
       {变更类型}：{具体变更描述}
       示例格式：
       - 添加参数 ``{arg_name}``
       - 重命名 ``{old_name}`` 为 ``{new_name}``
       - 重命名参数 ``{old_arg}`` 为 ``{new_arg}``
       - 删除参数 ``{arg_name}``
    """

.. rubric:: 文档字符串说明

1. 必须按照 `简要描述 + 参数 + 返回值 + 异常 + 详细描述 + 版本变更` 的顺序书写

2. 每个部分必须以空行分隔

3. 参数部分采用 `:param <arg_name>:` + `:type <arg_name>:` 配对声明

4. 返回值使用 `:return:` + `:rtype:` 配对声明

5. 异常声明使用 `:raise <Exception>:` 格式

6. 版本变更：

   - `.. versionadded::` 新增类，函数，文件等
   - `.. versionchanged::` 重命名，更改函数签名等

7. 变更描述规范：

   - 使用双反引号包裹被操作对象 \`\`...\`\`
   - 变更类型使用中文动词（重命名/删除/新增等）

8. 引用的对象必须使用sphinx的

   - `:py:mod:`
   - `:py:class:`
   - `:py:exc:`
   - `:py:meth:`
   - `:py:func:`
   - `:py:data:`
   - `:py:const:`
   - `:pep:`

   等语句创建合法的链接，过长的引用使用sphinx的 ``~`` 语法创建链接

引号
------

除仅包裹单字符的引号外，所有引号必须使用双引号 ``"``

包裹转义后为单字符的字符串也视为仅包裹单字符，如 ``'\n'``

包裹单字符的字符串可选使用单引号或双引号，推荐使用单引号 ``'``

导入
------

- 遵循 :pep:`8#imports` 规范

- 展开导入语句

  .. code-block:: python
     :caption: 例

      from typing import Any, Optional

      # 展开为

      from typing import Any
      from typing import Optional
