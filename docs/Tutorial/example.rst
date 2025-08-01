示例
=========

多个分散的配置文件
-------------------------

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
