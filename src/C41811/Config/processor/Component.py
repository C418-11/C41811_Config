# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

import os
from copy import deepcopy
from typing import Any
from typing import Literal
from typing import Optional
from typing import override

from ..abc import ABCConfigFile
from ..abc import ABCConfigPool
from ..abc import ABCMetaParser
from ..abc import ABCSLProcessorPool
from ..base import ComponentConfigData
from ..base import ComponentMember
from ..base import ComponentMeta
from ..base import ComponentOrders
from ..base import ConfigFile
from ..base import MappingConfigData
from ..base import NoneConfigData
from ..base import SequenceConfigData
from ..main import BasicChainConfigSL
from ..main import RequiredPath
from ..utils import CellType
from ..validators import ValidatorFactoryConfig


class ComponentMetaParser[D: MappingConfigData[Any]](ABCMetaParser[D, ComponentMeta[D]]):
    """
    默认元信息解析器
    """
    _validator: RequiredPath[dict[str, Any], D] = RequiredPath(
        {
            "members": list[str | ComponentMember],
            "order": list[str],
            "orders": dict[Literal["create", "read", "update", "delete"], list[str]]
        },
        static_config=ValidatorFactoryConfig(allow_modify=True, skip_missing=True)
    )

    @override
    def convert_config2meta(self, meta_config: D) -> ComponentMeta[D]:
        """
        解析元配置

        :param meta_config: 元配置
        :type meta_config: base.mapping.MappingConfigData

        :return: 元数据
        :rtype: base.mapping.ComponentMeta
        """
        meta = self._validator.filter(CellType(meta_config))

        members = meta.get("members", SequenceConfigData()).data
        for i, member in enumerate(members):
            if isinstance(member, str):
                members[i] = ComponentMember(member)
            elif isinstance(member, dict):
                members[i] = ComponentMember(**member)

        orders: ComponentOrders = ComponentOrders(**meta.get("orders", MappingConfigData()).data)
        order = meta.setdefault(
            "order",
            [member.alias if member.alias else member.filename for member in members]
        )
        if not isinstance(order, list):
            order = order.data
        for name in order:
            for attr in getattr(orders, "__dataclass_fields__"):
                if name in getattr(orders, attr):
                    continue
                getattr(orders, attr).append(name)

        for attr in getattr(orders, "__dataclass_fields__"):
            o = getattr(orders, attr)
            if len(set(o)) != len(o):
                raise ValueError(f"name(s) repeated in {attr} order")

        return ComponentMeta(meta, orders, members, self)

    @override
    def convert_meta2config(self, meta: ComponentMeta[D]) -> D:
        """
        解析元数据

        :param meta: 元数据
        :type meta: base.mapping.ComponentMeta

        :return: 元配置
        :rtype: base.mapping.MappingConfigData
        """
        return meta.config

    def validator(self, meta: ComponentMeta[D], *args: Any) -> ComponentMeta[D]:
        return self.convert_config2meta(meta.config)


class ComponentSL(BasicChainConfigSL):
    """
    组件模式配置处理器
    """

    def __init__(
            self,
            *,
            reg_alias: Optional[str] = None,
            create_dir: bool = True,
            meta_parser: Optional[ABCMetaParser[Any, ComponentMeta[Any]]] = None
    ):
        super().__init__(reg_alias=reg_alias, create_dir=create_dir)

        if meta_parser is None:
            meta_parser = ComponentMetaParser()

        self.meta_parser: ABCMetaParser[Any, ComponentMeta[Any]] = meta_parser

    @property
    @override
    def processor_reg_name(self) -> str:
        return "component"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".component", ".comp"

    def namespace_formatter(self, namespace: str, file_name: str) -> str:
        return os.path.normpath(os.path.join(namespace, self.filename_formatter(file_name)))

    supported_file_classes = [ConfigFile]

    @property
    def initial_file(self) -> str:
        return "__init__"

    def save_file(
            self,
            config_pool: ABCConfigPool,
            config_file: ABCConfigFile[ComponentConfigData[Any, Any]],
            namespace: str,
            file_name: str,
            *args: Any, **kwargs: Any,
    ) -> None:
        config_data = config_file.config
        if isinstance(config_data, NoneConfigData):
            config_data = ComponentConfigData()
        elif not isinstance(config_data, ComponentConfigData):
            with self.raises(TypeError):
                raise TypeError(f"{namespace} is not a ComponentConfigData")

        meta_config = self.meta_parser.convert_meta2config(config_data.meta)
        file_name, file_ext = os.path.splitext(file_name)
        super().save_file(config_pool, ConfigFile(meta_config), namespace, self.initial_file + file_ext,
                          *args, **kwargs)

        for member in config_data.meta.members:
            super().save_file(
                config_pool,
                ConfigFile(config_data[member.filename], config_format=member.config_format),
                namespace,
                member.filename,
                *args,
                **kwargs,
            )

    def load_file(
            self,
            config_pool: ABCConfigPool,
            namespace: str,
            file_name: str,
            *args: Any,
            **kwargs: Any
    ) -> ConfigFile[ComponentConfigData[Any, Any]]:
        file_name, file_ext = os.path.splitext(file_name)

        initial_file = super().load_file(
            config_pool, namespace, self.initial_file + file_ext, *args, **kwargs
        )
        initial_data = initial_file.config

        if not isinstance(initial_data, MappingConfigData):
            with self.raises(TypeError):
                raise TypeError(f"{namespace} is not a MappingConfigData")

        meta = self.meta_parser.convert_config2meta(initial_data)
        members = {}
        for member in meta.members:
            merged_kwargs = deepcopy(kwargs)
            if member.config_format is not None:
                merged_kwargs.setdefault("config_formats", set()).add(member.config_format)
            members[member.filename] = super().load_file(
                config_pool, namespace, member.filename, *args, **merged_kwargs
            ).config

        return ConfigFile(ComponentConfigData(meta, members), config_format=self.reg_name)

    def initialize(
            self,
            processor_pool: ABCSLProcessorPool,
            root_path: str,
            namespace: str,
            file_name: str,
            *args: Any,
            **kwargs: Any,
    ) -> ConfigFile[ComponentConfigData[Any, Any]]:
        return ConfigFile(ComponentConfigData(ComponentMeta(parser=self.meta_parser)), config_format=self.reg_name)


__all__ = (
    "ComponentMetaParser",
    "ComponentSL",
)
