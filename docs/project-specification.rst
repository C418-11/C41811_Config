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

    {复杂功能特性说明（可选段落）}
    -------------

    {功能特性等详细描述，如：多数据源时的优先级列表}

    .. {注意事项、特殊行为说明（可选段落）} (这是个注释是给你读的不是要写到文档字符串里的)
    .. note::
       {详细描述}

    .. 版本变更 (同上为注释)

    .. versionadded:: {x.x.x}

    .. versionchanged:: {x.x.x}
       {变更类型} {具体变更描述}
       示例格式：
       - 添加参数 ``{arg_name}``
       - 重命名 ``{old_name}`` 为 ``{new_name}``
       - 重命名参数 ``{old_arg}`` 为 ``{new_arg}``
       - 删除参数 ``{arg_name}``
    """

.. rubric:: 文档字符串说明

1. 必须按照 `简要描述 + 参数 + 返回值 + 异常 + 功能特性说明 + 注意事项 + 版本变更` 的顺序书写

2. 每个部分必须以空行分隔

3. 参数部分采用 `:param <arg_name>:` + `:type <arg_name>:` 配对声明

4. 返回值使用 `:return:` + `:rtype:` 配对声明，如果返回值固定为 :py:const:`None` 则不需要使用 `:return:` + `:rtype:` 进行声明

5. 属性即 :py:deco:`property` 装饰的函数不需要使用 `:return:` + `:rtype:` 声明，直接描述行为/作用即可

6. 异常声明使用 `:raise <Exception>:` 格式


7. 警告、提示，重要等必须使用

   - `.. tip::`
   - `.. hint::`
   - `.. note::`
   - `.. attention::`
   - `.. important::`
   - `.. caution::`
   - `.. warning::`
   - `.. danger::`
   - `.. error::`

   等语句创建合法的注解

   .. seealso::
      `段落级标记 <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#paragraph-level-markup>`_

8. 版本变更使用的语句和在何时使用参下描述：

   - `.. versionadded::` 新增类，函数，文件等
   - `.. versionchanged::` 重命名，更改函数签名等

   .. seealso::
      `描述版本之间的变化 <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#describing-changes-between-versions>`_

9. 版本变更只需要标注被变更的对象，不用标注所有相关对象，如：

   - 子模块重命名只需要在该模块的 ``__init__.py`` 文件中标注，而不必在其中的每一个文件每一个文档字符串标注
   - 类重命名只需要在该类文档重标注，而不必在其每一个方法中标注

10. 变更描述规范：

   - 使用双反引号包裹被操作对象 \`\`...\`\`
   - 变更类型使用中文动词（重命名/删除/新增等）

11. 引用的对象必须使用

   - `:py:mod:`
   - `:py:class:`
   - `:py:exc:`
   - `:py:meth:`
   - `:py:func:`
   - `:py:deco:`
   - `:py:attr:`
   - `:py:data:`
   - `:py:const:`
   - `:py:type:`
   - `:py:obj:`
   - `:pep:`

   等语句创建合法的链接，过长的引用使用sphinx的 ``~`` 语法创建链接

   .. seealso::
      `交叉引用任意位置 <https://www.sphinx-doc.org/en/master/usage/referencing.html#cross-referencing-arbitrary-locations>`_

      `交叉引用Python对象 <https://www.sphinx-doc.org/en/master/usage/domains/python.html#python-xref-roles>`_

.. rubric:: 参考

.. code-block:: python
   :caption: 文档字符串示例

   def func(arg1: str, arg2: int) -> None:
       """
       函数描述

       :param arg1: 参数1描述
       :type arg1: str
       :param arg2: 参数2描述
       :type arg2: int

       .. versionadded:: 0.2.0
       """

   def func2(arg1: str, arg2: int) -> SomeType:
       """
       函数描述

       :param arg1: 参数1描述
       :type arg1: str
       :param arg2: 参数2描述
       :type arg2: int

       :return: 返回值描述
       :rtype: SomeType

       .. versionchanged:: 0.3.1
          更改返回值类型 ``Any`` 为 ``SomeType``
       """

   class Cls:
       """
       类描述

       .. versionadded:: 0.2.0

       .. versionchanged:: 0.3.1
          重命名 ``MyClass`` 为 ``Cls``
       """

       def method(self, some_obj: SomeType) -> None:
           """
           方法描述

           :param some_obj: 参数
           :type some_obj: SomeType

           .. caution::
              未默认做深拷贝，可能导致非预期行为
           """

引号
------

所有用于表示字符串的 `非内容` 引号必须使用双引号 ``"``

* `非内容` 指引号本身不包含在字符串内容中

导入
------

- 遵循 :pep:`8#imports` 规范

- 在此基础上展开导入语句

  .. code-block:: python
     :caption: 例

      from typing import Any, Literal

      # 展开为

      from typing import Any
      from typing import Literal

自动格式化
------------

此项目使用 ``ruff`` 进行代码格式化

.. rubric:: 安装

.. important::
   记得更新你的 ``pip`` 版本！过旧的版本没有 ``--group`` 参数

.. code-block:: shell
   :caption: 安装ruff

   pip install -e . --group ruff

.. rubric:: 使用

.. important::
   格式化后的代码可能存在错误，请先使用以下命令检查格式化后的代码是否正确并运行 ``tox`` 进行全面测试

.. code-block:: shell
   :caption: 检查并格式化代码但是输出diff而不是修改文件

   ruff check --diff
   ruff format --diff

运行以下命令以格式化代码

.. code-block:: shell
   :caption: 检查并格式化代码

   ruff check
   ruff format

如果你只是想检查代码是否符合规范可以运行以下代码检查

.. caution::
   `这不会检查文档字符串是否符合上述规范！`

.. important::
   以防你忘了安装项目开发依赖，我把安装开发依赖的命令放在了下面

   .. code-block:: shell
      :caption: 安装项目开发依赖

      pip install -e .[dev]

.. code-block:: shell
   :caption: 检查代码

   tox -e ruff
