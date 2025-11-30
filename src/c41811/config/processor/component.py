# cython: language_level = 3  # noqa: ERA001


"""
组件配置处理器

.. versionadded:: 0.2.0
"""

import os
from collections.abc import Callable
from collections.abc import Mapping
from copy import deepcopy
from typing import Any
from typing import Literal
from typing import override

from ..abc import ABCConfigFile
from ..abc import ABCConfigPool
from ..abc import ABCMetaParser
from ..abc import ABCSLProcessorPool
from ..basic.component import ComponentConfigData
from ..basic.component import ComponentMember
from ..basic.component import ComponentMeta
from ..basic.component import ComponentOrders
from ..basic.core import ConfigFile
from ..basic.mapping import MappingConfigData
from ..basic.object import NoneConfigData
from ..basic.sequence import SequenceConfigData
from ..errors import ComponentMetadataException
from ..main import BasicChainConfigSL
from ..main import RequiredPath
from ..utils import Ref
from ..validators import ValidatorOptions


class ComponentMetaParser[D: MappingConfigData[Any]](ABCMetaParser[D, ComponentMeta[D]]):
    """默认元信息解析器"""

    _validator: RequiredPath[dict[str, Any], D] = RequiredPath(
        {
            "members": list[str | ComponentMember],
            "order": list[str],
            "orders": dict[Literal["create", "read", "update", "delete"], list[str]],
        },
        static_config=ValidatorOptions(allow_modify=True, skip_missing=True),
    )

    @override
    def convert_config2meta(self, meta_config: D) -> ComponentMeta[D]:
        """
        解析元配置

        :param meta_config: 元配置
        :type meta_config: D

        :return: 元数据
        :rtype: ComponentMeta[D]
        """
        meta = self._validator.filter(Ref(meta_config))

        members = meta.get("members", SequenceConfigData()).data
        for i, member in enumerate(members):
            if isinstance(member, str):
                members[i] = ComponentMember(member)
            elif isinstance(member, dict):
                members[i] = ComponentMember(**member)

        orders: ComponentOrders = ComponentOrders(**meta.get("orders", MappingConfigData()).data)
        order = meta.setdefault("order", [member.alias if member.alias else member.filename for member in members])
        if not isinstance(order, list):
            order = order.data
        for name in order:
            # noinspection PyUnresolvedReferences
            for attr in orders.__dataclass_fields__:
                if name in getattr(orders, attr):
                    continue
                getattr(orders, attr).append(name)

        # noinspection PyUnresolvedReferences
        for attr in orders.__dataclass_fields__:
            o = getattr(orders, attr)
            if len(set(o)) != len(o):
                msg = f"name(s) repeated in {attr} order"
                raise ComponentMetadataException(msg)

        return ComponentMeta(meta, orders, members, self)

    @override
    def convert_meta2config(self, meta: ComponentMeta[D]) -> D:
        """
        解析元数据

        :param meta: 元数据
        :type meta: ComponentMeta[D]

        :return: 元配置
        :rtype: D
        """
        return meta.config

    @override
    def validator(self, meta: ComponentMeta[D], *args: Any) -> ComponentMeta[D]:
        return self.convert_config2meta(meta.config)

    @override
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._validator == other._validator

    __hash__ = None  # type: ignore[assignment]


def _component_loader_kwargs_builder(kwargs: dict[str, Any]) -> Callable[[ComponentMember | None], dict[str, Any]]:
    # noinspection GrazieInspection
    """
    构建组件加载参数

    :param kwargs: 参数
    :type kwargs: dict[str, Any]
    :return: 构建器
    :rtype: Callable[[ComponentMember | None], dict[str, Any]]

    .. versionadded:: 0.3.0
    """
    format_mapping: Mapping[str | None, Any] | None = (
        fmt if isinstance((fmt := kwargs.get("config_formats")), Mapping) else None
    )

    def builder(member: ComponentMember | None) -> dict[str, Any]:
        new_kwargs = deepcopy(kwargs)  # 防止参数里有可变对象被load修改
        if format_mapping is not None:
            if member is None and None in format_mapping:
                new_kwargs["config_formats"] = format_mapping[None]
            elif isinstance(member, ComponentMember) and member.alias is not None and member.alias in format_mapping:
                new_kwargs["config_formats"] = format_mapping[member.alias]
            elif (
                isinstance(member, ComponentMember)
                and member.filename is not None
                and member.filename in format_mapping
            ):
                new_kwargs["config_formats"] = format_mapping[member.filename]
            else:
                # 更符合语义 即此项不存在视为load未提供config_formats参数
                # 虽然这种细微的语义差异只有可能在极少数情况下影响自定义子类
                del new_kwargs["config_formats"]
        if isinstance(member, ComponentMember) and member.config_format is not None:
            # noinspection PyUnreachableCode
            match config_formats := new_kwargs.get("config_formats", None):
                case str():
                    config_formats = [config_formats, member.config_format]
                case None:
                    config_formats = member.config_format
                case _:  # 处理 Iterable[str] 顺手报错
                    config_formats = list(config_formats)
                    if member.config_format not in config_formats:
                        config_formats.append(member.config_format)
            new_kwargs["config_formats"] = config_formats
        return new_kwargs

    return builder


class ComponentSL(BasicChainConfigSL):
    """组件模式配置处理器"""

    def __init__(
        self,
        *,
        reg_alias: str | None = None,
        create_dir: bool = True,
        meta_parser: ABCMetaParser[Any, ComponentMeta[Any]] | None = None,
        meta_file: str = "__meta__",
    ):
        """
        :param reg_alias: 处理器别名
        :type reg_alias: str | None
        :param create_dir: 是否创建目录
        :type create_dir: bool
        :param meta_parser: 元数据解析器
        :type meta_parser: ABCMetaParser[Any, ComponentMeta[Any]] | None
        :param meta_file: 元信息文件名
        :type meta_file: str

        .. versionchanged:: 0.3.0
           重构属性 ``initial_file`` 为参数 ``meta_file`` 并更改默认值 ``__init__`` 为 ``__meta__``
        """  # noqa: D205
        super().__init__(reg_alias=reg_alias, create_dir=create_dir)

        if meta_parser is None:
            meta_parser = ComponentMetaParser()

        self.meta_parser: ABCMetaParser[Any, ComponentMeta[Any]] = meta_parser
        self.meta_file = meta_file

    @property
    @override
    def processor_reg_name(self) -> str:
        return "component"

    @property
    @override
    def supported_file_patterns(self) -> tuple[str, ...]:
        return ".component", ".comp"

    @override
    def namespace_formatter(self, namespace: str, file_name: str) -> str:
        return os.path.normpath(os.path.join(namespace, self.filename_formatter(file_name)))

    supported_file_classes = [ConfigFile]  # noqa: RUF012

    @override
    def save_file(
        self,
        config_pool: ABCConfigPool,
        config_file: ABCConfigFile[ComponentConfigData[Any, Any] | NoneConfigData],
        namespace: str,
        file_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        config_data = config_file.config
        if isinstance(config_data, NoneConfigData):
            config_data = ComponentConfigData()
        elif not isinstance(config_data, ComponentConfigData):
            with self.raises(TypeError):
                msg = f"{namespace} is not a ComponentConfigData"
                raise TypeError(msg)

        meta_config = self.meta_parser.convert_meta2config(config_data.meta)
        file_name, file_ext = os.path.splitext(file_name)
        super().save_file(config_pool, ConfigFile(meta_config), namespace, self.meta_file + file_ext, *args, **kwargs)

        for member in config_data.meta.members:
            super().save_file(
                config_pool,
                ConfigFile(config_data[member.filename], config_format=member.config_format),
                namespace,
                member.filename,
                *args,
                **kwargs,
            )

    @override
    def load_file(
        self, config_pool: ABCConfigPool, namespace: str, file_name: str, *args: Any, **kwargs: Any
    ) -> ConfigFile[ComponentConfigData[Any, Any]]:
        # noinspection PyIncorrectDocstring
        """
        加载指定命名空间的配置

        :param config_pool: 配置池
        :type config_pool: ABCConfigPool
        :param namespace: 命名空间
        :type namespace: str
        :param file_name: 文件名
        :type file_name: str

        可选参数
        -----------
        :param config_formats: 指定成员配置格式
        :type config_formats: Mapping[str | None, Any]

        :return: 配置文件
        :rtype: ConfigFile[ComponentConfigData[Any, Any]]

        .. caution::
           传递SL处理前没有清理已经缓存在配置池里的配置文件，返回的可能不是最新数据

        .. versionchanged:: 0.3.0
           新增可选参数 ``config_formats`` 以支持指定成员的配置解析格式
        """  # noqa: RUF002
        file_name, file_ext = os.path.splitext(file_name)
        kwargs_builder = _component_loader_kwargs_builder(kwargs)

        initial_file = super().load_file(
            config_pool, namespace, self.meta_file + file_ext, *args, **kwargs_builder(None)
        )
        initial_data = initial_file.config

        if not isinstance(initial_data, MappingConfigData):
            with self.raises(TypeError):
                msg = f"{namespace} is not a MappingConfigData"
                raise TypeError(msg)

        meta = self.meta_parser.convert_config2meta(initial_data)
        members = {}
        for member in meta.members:
            members[member.filename] = (
                super().load_file(config_pool, namespace, member.filename, *args, **kwargs_builder(member)).config
            )

        return ConfigFile(ComponentConfigData(meta, members), config_format=self.reg_name)

    @override
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
