# -*- coding: utf-8 -*-
# cython: language_level = 3


"""
.. versionadded:: 0.2.0
"""

import os
from abc import ABC
from abc import abstractmethod
from typing import Literal
from typing import Optional
from typing import override

from ..abc import ABCConfigFile
from ..abc import ABCConfigPool
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


class ABCMetaParser(ABC):
    """
    元信息解析器抽象类
    """

    @abstractmethod
    def from_config(self, meta_config: MappingConfigData) -> ComponentMeta:
        """
        解析元配置

        :param meta_config: 元配置
        :type meta_config: MappingConfigData

        :return: 元数据
        :rtype: ComponentMeta
        """

    @abstractmethod
    def from_meta(self, meta: ComponentMeta) -> MappingConfigData:
        """
        解析元数据

        :param meta: 元数据
        :type meta: ComponentMeta

        :return: 元配置
        :rtype: MappingConfigData
        """


class MetaParser(ABCMetaParser):
    """
    默认元信息解析器
    """
    validator = RequiredPath(
        {
            "members": list[str | ComponentMember],
            "order": list[str],
            "orders": dict[Literal["create", "read", "update", "delete"], list[str]]
        },
        static_config=ValidatorFactoryConfig(allow_modify=True, skip_missing=True)
    )

    @override
    def from_config(self, meta_config: MappingConfigData) -> ComponentMeta:
        meta = self.validator.filter(CellType(meta_config))

        members = meta.get("members", SequenceConfigData()).data
        for i, member in enumerate(members):
            if isinstance(member, str):
                members[i] = ComponentMember(member)
            elif isinstance(member, dict):
                members[i] = ComponentMember(**member)
            else:
                raise ValueError(f"unexpected member type {member}")

        orders: ComponentOrders = ComponentOrders(**meta.get("orders", MappingConfigData()).data)
        order = meta.setdefault("order",
            [member.alias if member.alias else member.filename for member in members]
        )
        if not isinstance(order, list):
            order = order.data
        for name in order:
            for attr in {"create", "read", "update", "delete"}:
                if name in getattr(orders, attr):
                    continue
                getattr(orders, attr).append(name)

        for attr in {"create", "read", "update", "delete"}:
            o = getattr(orders, attr)
            if len(set(o)) != len(o):
                raise ValueError(f"name(s) repeated in {attr} order")

        return ComponentMeta(meta, orders, members)

    @override
    def from_meta(self, meta: ComponentMeta) -> MappingConfigData:
        return meta.config


class ComponentSL(BasicChainConfigSL):
    """
    组件模式配置处理器
    """

    def __init__(
            self,
            *,
            reg_alias: Optional[str] = None,
            create_dir: bool = True,
            meta_parser: Optional[ABCMetaParser] = None
    ):
        super().__init__(reg_alias=reg_alias, create_dir=create_dir)

        if meta_parser is None:
            meta_parser = MetaParser()
        self.meta_parser = meta_parser

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
            config_file: ABCConfigFile[ComponentConfigData],
            namespace: str,
            file_name: str,
            *args, **kwargs
    ) -> None:
        config_data = config_file.config
        if isinstance(config_data, NoneConfigData):
            config_data = ComponentConfigData()
        elif not isinstance(config_data, ComponentConfigData):
            with self.raises(TypeError):
                raise TypeError(f"{namespace} is not a ComponentConfigData")

        meta_config = self.meta_parser.from_meta(config_data.meta)
        file_name, file_ext = os.path.splitext(file_name)
        super().save_file(config_pool, ConfigFile(meta_config), namespace, self.initial_file + file_ext, *args,
                          **kwargs)

        for filename, data in config_data.members.items():
            super().save_file(config_pool, ConfigFile(data), namespace, filename, *args, **kwargs)

    def load_file(
            self,
            config_pool: ABCConfigPool,
            namespace: str,
            file_name: str,
            *args,
            **kwargs
    ) -> ConfigFile[ComponentConfigData]:
        file_name, file_ext = os.path.splitext(file_name)

        initial_file = super().load_file(
            config_pool, namespace, self.initial_file + file_ext, *args, **kwargs
        )
        initial_data = initial_file.config

        if not isinstance(initial_data, MappingConfigData):
            with self.raises(TypeError):
                raise TypeError(f"{namespace} is not a MappingConfigData")

        meta = self.meta_parser.from_config(initial_data)
        members = {}
        for member in meta.members:
            members[member.filename] = super().load_file(
                config_pool, namespace, member.filename, *args, **kwargs
            ).config

        return ConfigFile(ComponentConfigData(meta, members))


__all__ = (
    "ABCMetaParser",
    "MetaParser",
    "ComponentSL",
)
