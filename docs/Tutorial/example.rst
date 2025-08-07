示例
=========

多个分散的配置文件
-------------------------

基于命名空间与配置池机制将分散在代码各处的配置文件以配置池为中心进行统一调度管理。

.. code-block:: python
   :caption: main.py

   from c41811.config import JsonSL
   from c41811.config import requireConfig
   from c41811.config import MappingConfigData
   from c41811.config import saveAll

   JsonSL().register_to()
   cfg: MappingConfigData = requireConfig('', "main.json", {"plugins": ["database"]}).check()
   print(cfg)  # {'plugins': ['database']}

   saveAll()

.. code-block:: python
   :caption: plugins/database.py

   from c41811.config import JsonSL
   from c41811.config import requireConfig
   from c41811.config import MappingConfigData
   from c41811.config import save

   JsonSL(s_arg=dict(indent=4), reg_alias="plugin/database.json")

   cfg: MappingConfigData = requireConfig(
       "plugins/database", "cfg.json", {
           "port": 1234, "addr": "localhost"
       },
       config_formats="plugin/database.json",
   ).check()  # {'port': 1234, 'addr': 'localhost'}

.. code-block:: text
   :caption: 项目结构

   .
   ├── .config
   │   ├── main.json
   │   └── plugins
   │       └── database
   │           └── cfg.json
   ├── plugins
   │   └── database.py
   └── main.py

压缩配置文件
-------------

.. code-block:: python
   :caption: main.py

   from c41811.config import JsonSL
   from c41811.config import MappingConfigData
   from c41811.config import TarFileSL
   from c41811.config import requireConfig
   from c41811.config import saveAll

   TarFileSL().register_to()
   JsonSL().register_to()

   cfg: MappingConfigData = requireConfig(
       '', "config.json.tar", {
           "port": 8080,
           "host": "0.0.0.0",
           "interval": {
               "duration": 60,
               "random": 0
           },
       }
   ).check()

   saveAll()
   print(cfg)  # {'port': 8080, 'host': '0.0.0.0', 'interval': {'duration': 60, 'random': 0}}

.. code-block:: text
   :caption: 项目结构

   .
   ├── .config
   │   └── config.json.tar  # tarfile
   │       └── config.json
   └── main.py

组件配置文件
--------------

元数据驱动的自定义特殊覆盖顺序结构多文件组合配置文件。

.. code-block:: python
   :caption: main.py

   from c41811.config import ComponentSL
   from c41811.config import JsonSL
   from c41811.config import MappingConfigData
   from c41811.config import TarFileSL
   from c41811.config import requireConfig
   from c41811.config import saveAll

   ComponentSL().register_to()
   TarFileSL(compression="gz").register_to()
   JsonSL(s_arg=dict(indent=4)).register_to()

   cfg: MappingConfigData = requireConfig(
       '', "config.json.comp.tar.gz", {
           None: {
               "members": [
                   {"filename": "production.json", "alias": "product"},
                   {"filename": "develop.json", "alias": "dev"},
                   {"filename": "basic.json", "alias": "basic"},
                   {"filename": "default.json", "alias": "default"},
               ],
               "order": ["product"],
               "orders": {
                   "read": ["product", "basic", "default"],
               },
           },
           "default.json": {
               "project-name": "C41811.Config-Example",
               "re-try-interval": {
                   "duration": 10,
                   "unit": "second",
                   "random": 0
               },
           },
           "basic.json": {
               "project-name": "Example Document",
               "re-try-interval": {
                   "random": 3
               }
           },
           "production.json": {
               "project-name": "Product !",
               "re-try-interval": {
                   "duration": 2,
                   "unit": ".1s",
               }
           },
           "develop.json": {
               "project-name": "Develop !",
               "re-try-interval": {
                   "unit": "$breakpoint",
               },
               "debug": True,
           },
       },
       "component"
   ).check()

   print(cfg.retrieve(r"re-try-interval\.unit"))  # .1s
   print(cfg.retrieve(r"\{default\}\.re-try-interval\.unit"))  # second
   print(cfg.retrieve(r"\{dev\}\.re-try-interval\.unit")) # $breakpoint
   print(cfg.retrieve(r"\{develop.json\}\.re-try-interval\.unit")) # $breakpoint

   saveAll()
   print(cfg)
   # {
   #     'default.json': MappingConfigData({
   #         'project-name': 'C41811.Config-Example',
   #         're-try-interval': {
   #             'duration': 10,
   #             'unit': 'second',
   #             'random': 0
   #         }
   #     }),
   #     'basic.json': MappingConfigData({
   #         'project-name': 'Example Document',
   #         're-try-interval': {
   #             'random': 3
   #         }
   #     }),
   #     'production.json': MappingConfigData({
   #         'project-name': 'Product !',
   #         're-try-interval': {
   #             'duration': 2,
   #             'unit': '.1s'
   #         }
   #     }),
   #     'develop.json': MappingConfigData({
   #         'project-name': 'Develop !',
   #         're-try-interval': {
   #             'unit': '$breakpoint'
   #         },
   #         'debug': True
   #     })
   # }

.. code-block:: text
   :caption: 项目结构

   .
   ├── .config
   │   └── config.json.comp.tar.gz  # tarfile
   │       └── config.json  # dir
   │           ├── __init__.json
   │           ├── basic.json
   │           ├── default.json
   │           ├── develop.json
   │           └── production.json
   └── main.py

Python脚本配置文件
----------------------

将配置文件加载/保存控制权翻转交给外部配置文件脚本的特殊配置文件。

.. code-block:: python
   :caption: main.py

   from typing import Any

   from c41811.config import ConfigFile
   from c41811.config import DefaultConfigPool
   from c41811.config import MappingConfigData
   from c41811.config import PlainTextSL
   from c41811.config import PythonSL
   from c41811.config import StringConfigData
   from c41811.config import load
   from c41811.config import save

   PythonSL().register_to()
   PlainTextSL().register_to()

   cfg: MappingConfigData[Any] = load("", "custom.py").config
   print(cfg)
   # {
   #     'key': 'value',
   #     'length': 5,
   #     'repeated': 'valuevaluevaluevaluevalue',
   #     'time': datetime.datetime(xxxx, x, x, xx, xx, xx, xxxxx)
   # }

   cfg["file_path"] = DefaultConfigPool.helper.calc_path(DefaultConfigPool.root_path, "custom", "custom.txt")
   data = {"key": "value"}
   cfg["data"] = data
   save("", "custom.py", config=ConfigFile(cfg))

   custom_cfg: StringConfigData[str] = load("custom", "custom.txt").config
   print(custom_cfg)  # {'key': 'value'}

.. code-block:: python
   :caption: custom.py

   if __name__ == "__main__": raise NotImplementedError  # 避免被意外执行
   if locals():  # 如果正在尝试保存数据
       __data__ = locals()
       from pathlib import Path
       file_path = Path(__data__["file_path"])
       file_path.parent.mkdir(parents=True, exist_ok=True)
       with file_path.open("w", encoding="utf-8") as f:
           f.write(str(__data__["data"]))

   # 被加载的数据
   key = "value"
   length = len(key)
   repeated = key * length
   from datetime import datetime
   time = datetime.now()
   del datetime  # 避免污染命名空间

.. code-block:: text
   :caption: 项目结构

   .
   ├── .config
   │   ├── custom.py
   │   └── custom
   │       └── custom.txt
   └── main.py
