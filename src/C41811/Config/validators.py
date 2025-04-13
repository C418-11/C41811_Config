# -*- coding: utf-8 -*-
# cython: language_level = 3


import dataclasses
import re
import types
import warnings
from collections import OrderedDict
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import MutableMapping
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import NamedTuple
from typing import Never
from typing import cast
from typing import overload

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import ValidationError
from pydantic import create_model
# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from pydantic_core import core_schema

from .abc import ABCPath
from .base import ComponentConfigData
from .base import ConfigData
from .base import MappingConfigData
from .base import NoneConfigData
from .errors import ConfigDataTypeError
from .errors import ConfigOperate
from .errors import KeyInfo
from .errors import RequiredPathNotFoundError
from .errors import UnknownErrorDuringValidateError
from .path import AttrKey
from .path import IndexKey
from .path import Path
from .utils import CellType
from .utils import Unset
from .utils import UnsetType
from .utils import singleton


class ValidatorTypes(Enum):
    """
    验证器类型
    """
    DEFAULT = None
    NO_VALIDATION = "no-validation"
    """
    .. versionchanged:: 0.2.0
       重命名 ``IGNORE`` 为 ``NO_VALIDATION``
    """
    PYDANTIC = "pydantic"
    COMPONENT = "component"
    """
    .. versionadded:: 0.2.0
    """


@dataclass(kw_only=True)
class ValidatorFactoryConfig:
    """
    验证器配置
    """
    allow_modify: bool = True
    """
    是否允许在填充默认值时同步填充源数据

    .. versionchanged:: 0.1.2
       重命名 ``allow_create`` 为 ``allow_modify``

    .. versionchanged:: 0.2.0
       现在默认为 :py:const:`True`
    """
    skip_missing: bool = False
    """
    是否忽略不存在的路径

    .. versionchanged:: 0.2.0
       重命名 ``ignore_missing`` 为 ``skip_missing``
    """

    extra: dict[str, Any] = dataclasses.field(default_factory=dict)


type MCD = MappingConfigData[Any]


def _fill_not_exits(raw_obj: MCD, obj: MCD) -> None:
    all_leaf = dict(recursive=True, end_point_only=True)
    diff_keys = obj.keys(**all_leaf) - raw_obj.keys(**all_leaf)
    for key in diff_keys:
        raw_obj.modify(key, obj.retrieve(key, return_raw_value=True))


def _process_pydantic_exceptions(err: ValidationError) -> Exception:
    e = err.errors()[0]

    locate = list(e["loc"])
    locate_keys: list[AttrKey | IndexKey] = []
    for key in locate:
        if isinstance(key, str):
            locate_keys.append(AttrKey(key))
        elif isinstance(key, int):
            locate_keys.append(IndexKey(key))
        else:  # pragma: no cover
            raise UnknownErrorDuringValidateError("Cannot convert pydantic index to string") from err

    kwargs: dict[str, Any] = dict(
        key_info=KeyInfo(
            path=Path(locate_keys),
            current_key=locate_keys[-1],
            index=len(locate_keys) - 1
        )
    )

    class ErrInfo(NamedTuple):
        err_type: type[Exception] | Callable[..., Exception]
        kwargs: dict[str, Any]

    err_input = e["input"]
    err_msg = e["msg"]

    types_kwarg: dict[str, Callable[[], ErrInfo]] = {
        "missing": lambda: ErrInfo(
            RequiredPathNotFoundError,
            dict(operate=ConfigOperate.Read)
        ),
        "model_type": lambda: ErrInfo(
            ConfigDataTypeError,
            dict(
                required_type=(
                    Never if (match := re.match(r"Input should be (.*)", err_msg)) is None else match.group(1)),
                current_type=type(err_input)
            )
        ),
        "int_type": lambda: ErrInfo(
            ConfigDataTypeError,
            dict(required_type=int, current_type=type(err_input))
        ),
        "int_parsing": lambda: ErrInfo(
            ConfigDataTypeError,
            dict(required_type=int, current_type=type(err_input))
        ),
        "string_type": lambda: ErrInfo(
            ConfigDataTypeError,
            dict(required_type=str, current_type=type(err_input))
        ),
        "dict_type": lambda: ErrInfo(
            ConfigDataTypeError,
            dict(required_type=dict, current_type=type(err_input))
        ),
        "literal_error": lambda: ErrInfo(
            RequiredPathNotFoundError,
            dict(operate=ConfigOperate.Write)
        ),
    }

    err_type_processor = types_kwarg.get(e["type"])
    if err_type_processor is None:  # pragma: no cover
        raise UnknownErrorDuringValidateError(**kwargs, error=e) from err
    err_info = err_type_processor()
    return err_info.err_type(**(kwargs | err_info.kwargs))


@singleton
class SkipMissingType:
    """
    用于表明值可以缺失特殊值

    .. versionchanged:: 0.2.0
       重命名 ``IgnoreMissingType`` 为 ``SkipMissingType``
    """

    def __str__(self) -> str:
        return "<SkipMissing>"

    @staticmethod
    def __get_pydantic_core_schema__(*_: Any) -> core_schema.ChainSchema:
        # 构造一个永远无法匹配的schema, 使 SkipMissing | int 可以正常工作
        return core_schema.chain_schema(
            [core_schema.none_schema(), core_schema.is_subclass_schema(type)]
        )


SkipMissing = SkipMissingType()


@dataclass(init=False)
class FieldDefinition[T: type | types.UnionType | types.EllipsisType | types.GenericAlias]:
    """
    字段定义，包含类型注解和默认值

    .. versionchanged:: 0.1.4
       新增 ``allow_recursive`` 字段
    """

    @overload  # @formatter:off
    def __init__(self, annotation: T, default: Any, *, allow_recursive: bool = True): ...

    @overload
    def __init__(self, annotation: T, *, default_factory: Callable[[], Any], allow_recursive: bool = True): ...
    # @formatter:on

    def __init__(
            self,
            annotation: T,
            default: Any = Unset,
            *,
            default_factory: Callable[[], Any] | UnsetType = Unset,
            allow_recursive: bool = True
    ):
        # noinspection GrazieInspection
        """
        :param annotation: 用于类型检查的类型
        :type annotation: type | types.UnionType | types.EllipsisType | types.GenericAlias
        :param default: 字段默认值
        :type default: Any
        :param default_factory: 字段默认值工厂
        :type default_factory: Callable[[], Any]
        :param allow_recursive: 是否允许递归处理字段值
        :type allow_recursive: bool

        .. versionchanged:: 0.2.0
           重命名参数 ``type_`` 为 ``value``

           重命名参数 ``annotation`` 为 ``default``

           添加参数 ``default_factory``
        """
        kwargs: dict[str, Any] = {}
        if default is not Unset:
            kwargs["default"] = default
        if default_factory is not Unset:
            kwargs["default_factory"] = default_factory

        if len(kwargs) != 1:
            raise ValueError("take one of arguments 'default' or 'default_factory'")

        value = default
        if not isinstance(default, FieldInfo):
            value = FieldInfo(**kwargs)

        self.annotation = annotation
        self.value = value
        self.allow_recursive = allow_recursive

    annotation: T
    """
    用于类型检查的类型
    """
    value: FieldInfo
    """
    字段值
    """
    allow_recursive: bool
    """
    是否允许递归处理字段值

    .. versionadded:: 0.1.4
    """


class MappingType(BaseModel):
    value: type[Mapping]  # type: ignore[type-arg]
    # pydantic.errors.PydanticUserError:
    #     Subscripting `type[]` with an already parametrized type is not supported.
    #     Instead of using type[collections.abc.Mapping[typing.Any, typing.Any]], use type[Mapping].


class RecursiveMapping(BaseModel):
    value: Mapping[str, Any]


def _is_mapping(typ: Any) -> bool:
    if typ is Any:
        return True
    try:
        MappingType(value=typ)
        return True
    except (ValidationError, TypeError):
        return False


def _allow_recursive(typ: Any) -> bool:
    try:
        RecursiveMapping(value=typ)
        return True
    except (ValidationError, TypeError):
        return False


class DefaultValidatorFactory[D: MCD | NoneConfigData]:
    """
    默认的验证器工厂
    """

    def __init__(self, validator: Iterable[str] | Mapping[str, Any], validator_config: ValidatorFactoryConfig):
        # noinspection GrazieInspection
        """
        :param validator: 用于生成验证器的数据
        :type validator: Iterable[str] | Mapping[str, Any]
        :param validator_config: 验证器配置
        :type validator_config: ValidatorFactoryConfig

        额外验证器工厂配置参数
        -----------------------
        .. list-table::
           :widths: auto

           * - 键名
             - 描述
             - 默认值
             - 类型
           * - model_config_key
             - 内部编译 :py:mod:`pydantic` 的 :py:class:`~pydantic.main.BaseModel` 时，模型配置是以嵌套字典的形式存储的，
               因此请确保此参数不与任何其中子模型名冲突
             - ".__model_config__"
             - Any

        .. versionchanged:: 0.1.2
           支持验证器混搭路径字符串和嵌套字典

        .. versionchanged:: 0.1.4
           支持验证器非字符串键 (含有非字符串键的子验证器不会被递归处理)
        """

        validator = deepcopy(validator)
        if isinstance(validator, Mapping):  # 先检查Mapping因为Mapping可以是Iterable
            ...
        elif isinstance(validator, Iterable):
            # 预处理为
            # k: Any
            validator = OrderedDict((k, Any) for k in validator)
        else:
            raise TypeError(f"Invalid validator type '{type(validator).__name__}'")
        self.validator = validator
        self.validator_config = validator_config

        self.typehint_types = (type, types.GenericAlias, types.UnionType, types.EllipsisType)
        self.model_config_key = validator_config.extra.get("model_config_key", ".__model_config__")
        self._compile()
        self.model: type[BaseModel]

    def _fmt_mapping_key(  # noqa: C901 (ignore complexity)
            self, validator: Mapping[str, Any]
    ) -> tuple[Mapping[str, Any], set[str | ABCPath[Any]]]:
        """
        格式化验证器键

        :param validator: Mapping验证器
        :type validator: Mapping[str, Any]

        :return: 格式化后的映射键和被覆盖的Mapping父路径
        :rtype: tuple[Mapping[str, Any], set[str]]
        """

        iterator = iter(validator.items())
        key: str = ''  # 能通过类型检查的默认值，但此值不当被使用
        value: Any = None

        def _next() -> bool:
            nonlocal key, value
            try:
                key, value = next(iterator)
            except StopIteration:
                return True
            return False

        if _next():
            return {}, set()

        fmt_data: MappingConfigData[OrderedDict[str, Any]] = cast(
            MappingConfigData[OrderedDict[Any, Any]],
            ConfigData(OrderedDict())
        )
        father_set: set[str | ABCPath[Any]] = set()
        while True:
            # 如果传入了任意路径的父路径那就检查新值和旧值是否都为Mapping
            # 如果是那就把父路径直接加入father_set不进行后续操作
            # 否则发出警告提示意外的复写验证器路径
            if key in fmt_data:
                target_value = fmt_data.retrieve(key)
                if not issubclass(type(target_value), self.typehint_types):
                    target_value = type(target_value)

                if _is_mapping(value) and _is_mapping(target_value):
                    father_set.add(key)
                    if _next():
                        break
                    continue

                warnings.warn((
                    f"Overwriting exists validator path with unexpected type"
                    f" '{value}'(new) and '{target_value}'(exists)"
                ))

            if _allow_recursive(value):
                value, sub_fpath = self._fmt_mapping_key(value)
                father_set.update(f"{key}\\.{sf_path}" for sf_path in sub_fpath)

            try:
                fmt_data.modify(key, value)
            except ConfigDataTypeError as err:
                relative_path = Path(err.key_info.relative_keys)
                # 如果旧类型为Mapping, Any那么就允许新的键创建
                if not _is_mapping(fmt_data.retrieve(relative_path)):
                    raise err from None
                fmt_data.modify(relative_path, OrderedDict())
                father_set.add(relative_path)
                continue

            if _next():
                break

        return fmt_data.data, father_set

    def _mapping2model(self, mapping: Mapping[str, Any], model_config: dict[str, Any]) -> type[BaseModel]:
        """
        将Mapping转换为Model

        :param mapping: 需要转换的Mapping
        :type mapping: Mapping[str, Any]

        :return: 转换后的Model
        :rtype: type[BaseModel]
        """
        fmt_data: OrderedDict[str, Any] = OrderedDict()
        for key, value in mapping.items():
            definition: FieldDefinition[Any]
            # foo = FieldInfo()
            if isinstance(value, FieldInfo):
                # foo: FieldInfo().annotation = FieldInfo()
                definition = FieldDefinition(value.annotation, value)
            # foo: int
            # 如果是仅类型就填上空值
            elif issubclass(type(value), self.typehint_types):
                # foo: int = FieldInfo()
                definition = FieldDefinition(value, FieldInfo())
            # foo = FieldDefinition(int, FieldInfo())
            # 已经是处理好的字段定义，不需要特殊处理
            elif isinstance(value, FieldDefinition):
                definition = value
            # foo = 1
            # 如果是仅默认值就补上类型
            else:
                # foo: int = 1
                definition = FieldDefinition(type(value), FieldInfo(default=value))

            # 递归处理
            if all((
                    definition.allow_recursive,
                    _allow_recursive(definition.value.default),
                    # foo.bar = {}
                    # 这种情况下不进行递归解析，获取所有键(foo.bar.*)如果进行了解析就只会返回foo.bar={}
                    definition.value.default,
            )):
                model_cls = self._mapping2model(
                    mapping=definition.value.default,
                    model_config=model_config.get(key, {})
                )
                definition = FieldDefinition(
                    model_cls,
                    FieldInfo(default_factory=model_cls)
                )

            # 如果忽略不存在的键就填充特殊值
            if all((
                    self.validator_config.skip_missing,
                    definition.value.is_required()
            )):
                definition = FieldDefinition(definition.annotation | SkipMissingType, FieldInfo(default=SkipMissing))

            fmt_data[key] = (definition.annotation, definition.value)

        return cast(
            type[BaseModel],
            create_model(
                f"{type(self).__name__}.RuntimeTemplate",
                __config__=cast(ConfigDict, model_config.get(self.model_config_key, {})),
                **fmt_data,
            ),
        )

    def _compile(self) -> None:
        """
        编译模板
        """
        fmt_validator, father_set = self._fmt_mapping_key(self.validator)
        # 所有重复存在的父路径都将允许其下存在多余的键
        model_config: MCD = MappingConfigData()
        for path in father_set:
            model_config.modify(path, {self.model_config_key: {"extra": "allow"}})

        self.model = self._mapping2model(fmt_validator, model_config.data)

    def __call__(self, cell: CellType[D]) -> D:
        if isinstance(cell.cell_contents, NoneConfigData):
            cell.cell_contents = MappingConfigData()  # type: ignore[assignment]
        data: MCD = cell.cell_contents  # type: ignore[assignment]

        try:
            dict_obj = self.model(**data.data).model_dump()
        except ValidationError as err:
            raise _process_pydantic_exceptions(err) from err

        # noinspection PyTypeChecker
        config_obj: MCD = data.from_data(dict_obj)
        if self.validator_config.skip_missing:
            for key in config_obj.keys(recursive=True, end_point_only=True):
                if config_obj.retrieve(key) is SkipMissing:
                    config_obj.delete(key)

        if self.validator_config.allow_modify:
            _fill_not_exits(data, config_obj)
        return cast(D, config_obj)


def pydantic_validator[D: MCD | NoneConfigData](
        validator: type[BaseModel], cfg: ValidatorFactoryConfig
) -> Callable[[CellType[D]], D]:
    """
    验证器工厂配置 ``skip_missing`` 无效

    :param validator: :py:class:`~pydantic.main.BaseModel` 的子类
    :type validator: type[BaseModel]
    :param cfg: 验证器配置
    :type cfg: ValidatorFactoryConfig
    """
    if not issubclass(validator, BaseModel):
        raise TypeError(f"Expected a subclass of BaseModel for parameter 'validator', but got '{validator.__name__}'")
    if cfg.skip_missing:
        warnings.warn("skip_missing is not supported in pydantic validator")

    def _builder(cell: CellType[D]) -> D:
        if isinstance(cell.cell_contents, NoneConfigData):
            cell.cell_contents = MappingConfigData()  # type: ignore[assignment]
        data: MCD = cell.cell_contents  # type: ignore[assignment]

        try:
            dict_obj = validator(**data).model_dump()
        except ValidationError as err:
            raise _process_pydantic_exceptions(err) from err

        # noinspection PyTypeChecker
        config_obj: MCD = data.from_data(dict_obj)
        if cfg.allow_modify:
            _fill_not_exits(data, config_obj)
        return cast(D, config_obj)

    return _builder


class ComponentValidatorFactory[D: ComponentConfigData[Any, Any] | NoneConfigData]:
    """
    组件验证器工厂

    .. versionadded:: 0.2.0
    """

    def __init__(self, validator: Mapping[str | None, Any], validator_config: ValidatorFactoryConfig):
        """
        :param validator: 组件验证器
        :type validator: Mapping[str | None, Any]
        :param validator_config: 验证器配置
        :type validator_config: ValidatorFactoryConfig

        额外验证器工厂配置参数
        -----------------------

        .. list-table::
           :widths: auto

           * - 键名
             - 描述
             - 默认值
             - 类型
           * - validator_factory
             - 处理组件成员的验证器工厂
             - :py:class:`DefaultValidatorFactory`
             - Callable[[Any, ValidatorFactoryConfig], Callable[[ComponentConfigData], ComponentConfigData]]
           * - allow_initialize
             - 是否允许初始化不存在的组件成员(注意！ 现在的实现方式会强制初始化成员为 :py:class:`MappingConfigData`)
             - True
             - bool
           * - meta_validator
             - 组件元数据验证器
             - 尝试从传入的组件元数据获得，若不存在(值为None)则放弃验证
             - Callable[[ComponentMeta, ValidatorFactoryConfig], ComponentMeta]
        """

        self.validator = validator
        self.validator_config = validator_config

        self.validator_factory = validator_config.extra.get("validator_factory", DefaultValidatorFactory)
        self.validators: MutableMapping[
            str | None,
            Callable[[CellType[MCD]], MCD]
        ] = {}

        self._compile()

    def _compile(self) -> None:
        for member, validator in self.validator.items():
            self.validators[member] = self.validator_factory(validator, self.validator_config)

    def __call__(self, raw_cell: CellType[D]) -> D:
        if isinstance(raw_cell.cell_contents, NoneConfigData):
            raw_cell.cell_contents = ComponentConfigData()  # type: ignore[assignment]

        cell = cast(CellType[ComponentConfigData[Any, Any]], raw_cell)
        data = cell.cell_contents

        validation_meta: bool = False
        members: dict[str | None, MCD] = {}
        for member, validator in self.validators.items():
            if member is None:
                validation_meta = True
                continue

            if (member not in data) and self.validator_config.extra.get("allow_initialize", True):
                data[member] = MappingConfigData()
            data_cell = CellType(data[member])
            members[member] = validator(data_cell)
            if self.validator_config.allow_modify:
                cell.cell_contents[member] = data_cell.cell_contents

        meta = deepcopy(data.meta)
        if validation_meta:
            meta.config = self.validators[None](CellType(meta.config))

            meta_validator = None if meta.parser is None else meta.parser.validator
            meta_validator = self.validator_config.extra.get("meta_validator", meta_validator)
            if meta_validator is not None:
                meta = meta_validator(meta, self.validator_config)
        if self.validator_config.allow_modify:
            cell.cell_contents._meta = meta

        return cast(D, data.from_data(meta, members))


__all__ = (
    "ValidatorTypes",
    "ValidatorFactoryConfig",
    "FieldDefinition",
    "DefaultValidatorFactory",
    "pydantic_validator",
    "ComponentValidatorFactory",
)
