# cython: language_level = 3  # noqa: ERA001


"""配置验证器"""

import dataclasses
import re
import types
import warnings
from collections import OrderedDict
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Mapping
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import NamedTuple
from typing import Never
from typing import TypeAliasType
from typing import cast
from typing import overload
from typing import override

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import ValidationError
from pydantic import create_model

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from pydantic_core import core_schema

from .abc import ABCIndexedConfigData
from .abc import ABCPath
from .basic.component import ComponentConfigData
from .basic.mapping import MappingConfigData
from .basic.object import NoneConfigData
from .errors import ComponentMemberMismatchError
from .errors import ConfigDataTypeError
from .errors import ConfigOperate
from .errors import KeyInfo
from .errors import RequiredPathNotFoundError
from .errors import UnknownErrorDuringValidateError
from .path import AttrKey
from .path import IndexKey
from .path import Path
from .utils import Ref
from .utils import Unset
from .utils import UnsetType
from .utils import singleton


class ValidatorTypes(Enum):
    """验证器类型"""

    DEFAULT = None
    CUSTOM = "custom"
    """
    .. versionchanged:: 0.2.0
       重命名 ``IGNORE`` 为 ``NO_VALIDATION``

    .. versionchanged:: 0.3.0
       重命名 ``NO_VALIDATION`` 为 ``CUSTOM``
    """
    PYDANTIC = "pydantic"
    COMPONENT = "component"
    """
    .. versionadded:: 0.2.0
    """


@dataclass(kw_only=True)
class ValidatorOptions:
    # noinspection GrazieInspection
    """
    验证器选项

    .. versionchanged:: 0.3.0
       重命名 ``ValidatorFactoryConfig`` 为 ``ValidatorOptions``
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
type ICD = ABCIndexedConfigData[Any]


# noinspection PyNewStyleGenericSyntax
def _remove_skip_missing[D: dict[str, Any] | list[Any]](data: D) -> D:
    """
    递归删除值为 :py:const:`SkipMissing` 的项

    :param data: 配置数据
    :type data: dict | list

    .. versionadded:: 0.3.0
    """
    if isinstance(data, dict):
        return type(data)((k, _remove_skip_missing(v)) for k, v in data.items() if v is not SkipMissing)
    if isinstance(data, list):
        return type(data)(_remove_skip_missing(item) for item in data if item is not SkipMissing)
    return data


def _process_pydantic_exceptions(err: ValidationError) -> Exception:
    """
    转换包装 pydantic 的异常

    :param err: pydantic 的异常
    :type err: ValidationError

    :return: 转换后的异常
    :rtype: Exception
    """
    e = err.errors()[0]

    locate = list(e["loc"])
    locate_keys: list[AttrKey | IndexKey] = []
    for key in locate:
        if isinstance(key, str):
            locate_keys.append(AttrKey(key))
        elif isinstance(key, int):
            locate_keys.append(IndexKey(key))
        else:  # pragma: no cover
            msg = "Cannot convert pydantic index to string"
            raise UnknownErrorDuringValidateError(msg) from err

    kwargs: dict[str, Any] = {
        "key_info": KeyInfo(path=Path(locate_keys), current_key=locate_keys[-1], index=len(locate_keys) - 1)
    }

    class ErrInfo(NamedTuple):
        err_type: type[Exception] | Callable[..., Exception]
        kwargs: dict[str, Any]

    err_input = e["input"]
    err_msg = e["msg"]

    types_kwarg: dict[str, Callable[[], ErrInfo]] = {
        "missing": lambda: ErrInfo(RequiredPathNotFoundError, {"operate": ConfigOperate.Read}),
        "model_type": lambda: ErrInfo(
            ConfigDataTypeError,
            {
                "required_type": (
                    Never if (match := re.match(r"Input should be (.*)", err_msg)) is None else match.group(1)
                ),
                "current_type": type(err_input),
            },
        ),
        "int_type": lambda: ErrInfo(ConfigDataTypeError, {"required_type": int, "current_type": type(err_input)}),
        "int_parsing": lambda: ErrInfo(ConfigDataTypeError, {"required_type": int, "current_type": type(err_input)}),
        "string_type": lambda: ErrInfo(ConfigDataTypeError, {"required_type": str, "current_type": type(err_input)}),
        "dict_type": lambda: ErrInfo(ConfigDataTypeError, {"required_type": dict, "current_type": type(err_input)}),
        "literal_error": lambda: ErrInfo(RequiredPathNotFoundError, {"operate": ConfigOperate.Write}),
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

    @override
    def __str__(self) -> str:
        return "<SkipMissing>"

    @staticmethod
    def __get_pydantic_core_schema__(*_: Any) -> core_schema.ChainSchema:
        # 构造一个永远无法匹配的schema使 `SkipMissing | int` 可以正常工作 即被pydantic视为 `int`
        return core_schema.chain_schema([core_schema.none_schema(), core_schema.is_subclass_schema(type)])


SkipMissing = SkipMissingType()
type AnyTypeHint = type | types.UnionType | types.EllipsisType | types.GenericAlias | TypeAliasType


@dataclass(init=False)
class FieldDefinition[T: AnyTypeHint]:
    """
    字段定义，包含类型注解和默认值

    .. versionchanged:: 0.1.4
       新增 ``allow_recursive`` 字段

    .. versionchanged:: 0.3.0
       新增对 :py:class:`TypeAliasType` 支持
    """  # noqa: RUF002

    @overload
    def __init__(self, annotation: T, default: Any, *, allow_recursive: bool = True): ...

    @overload
    def __init__(self, annotation: T, *, default_factory: Callable[[], Any], allow_recursive: bool = True): ...

    def __init__(
        self,
        annotation: T,
        default: Any = Unset,
        *,
        default_factory: Callable[[], Any] | UnsetType = Unset,
        allow_recursive: bool = True,
    ):
        # noinspection GrazieInspection
        """
        :param annotation: 用于类型检查的类型
        :type annotation: T
        :param default: 字段默认值
        :type default: Any
        :param default_factory: 字段默认值工厂
        :type default_factory: Callable[[], Any] | UnsetType
        :param allow_recursive: 是否允许递归处理字段值
        :type allow_recursive: bool

        .. versionchanged:: 0.2.0
           重命名参数 ``type_`` 为 ``value``

           重命名参数 ``annotation`` 为 ``default``

           添加参数 ``default_factory``
        """  # noqa: D205
        kwargs: dict[str, Any] = {}
        if default is not Unset:
            kwargs["default"] = default
        if default_factory is not Unset:
            kwargs["default_factory"] = default_factory

        if len(kwargs) != 1:
            msg = "take one of arguments 'default' or 'default_factory'"
            raise ValueError(msg)

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


class NestedMapping(BaseModel):
    value: Mapping[str, Any]


def _is_mapping(typ: Any) -> bool:
    """
    判断是否为 :py:class`~collections.abc.Mapping` 类型

    :param typ: 待检测类型
    :type typ: Any

    :return: 是否为 :py:class`~collections.abc.Mapping` 类型
    :rtype: bool
    """
    if typ is Any:
        return True
    try:
        MappingType(value=typ)
    except (ValidationError, TypeError):
        return False
    return True


def _allow_recursive(typ: Any) -> bool:
    """
    判断是否允许递归处理字段值（键全为字符串则视为允许）

    :param typ: 待检测值
    :type typ: Any

    :return: 是否允许递归处理字段值
    :rtype: bool
    """  # noqa: RUF002
    try:
        NestedMapping(value=typ)
    except (ValidationError, TypeError):
        return False
    return True


def _check_overwriting_exists_path(
    key: str, value: Any, fmt_data: MappingConfigData[Any], typehint_types: tuple[type, ...]
) -> bool:
    """
    检查是否覆盖了验证器已存在的路径

    :param key: 路径
    :type key: str
    :param value: 新值
    :type value: Any
    :param fmt_data: 验证器
    :type fmt_data: MappingConfigData[Any]
    :param typehint_types: 类型提示类型
    :type typehint_types: tuple[type, ...]

    .. versionadded:: 0.3.0
    """
    # 如果传入了任意路径的父路径
    if key not in fmt_data:
        return False

    # 那就检查新值和旧值是否都为Mapping子类或Any
    target_value = fmt_data.retrieve(key)
    if not issubclass(type(target_value), typehint_types):
        target_value = type(target_value)

    # 如果是那就把父路径直接加入parent_set不进行后续操作
    if _is_mapping(value) and _is_mapping(target_value):
        return True

    # 否则发出警告提示意外地复写验证器路径
    warnings.warn(
        f"Overwriting exists validator path with unexpected type '{value}'(new) and '{target_value}'(exists)",
        stacklevel=2,
    )
    return False


@overload
def _convert2definition[D: FieldDefinition[Any]](value: D, typehint_types: tuple[type, ...]) -> D: ...


@overload
def _convert2definition(value: FieldInfo, typehint_types: tuple[type, ...]) -> FieldDefinition[Any]: ...


@overload
def _convert2definition[T: AnyTypeHint](value: T, typehint_types: tuple[type, ...]) -> FieldDefinition[T]: ...


def _convert2definition(value: Any, typehint_types: tuple[type, ...]) -> FieldDefinition[Any]:
    """
    将键值换为字段定义

    :param value: 键
    :type value: Any
    :param typehint_types: 类型提示类型
    :type typehint_types: tuple[type, ...]

    .. versionadded:: 0.3.0
    """
    # foo = FieldInfo()  # noqa: ERA001
    if isinstance(value, FieldInfo):
        # foo: FieldInfo().annotation = FieldInfo()  # noqa: ERA001
        return FieldDefinition(value.annotation, value)
    # foo: int  # noqa: ERA001
    # 如果是仅类型就填上空值
    if issubclass(type(value), typehint_types):
        # foo: int = FieldInfo()  # noqa: ERA001
        return FieldDefinition(value, FieldInfo())
    # foo = FieldDefinition(int, FieldInfo())  # noqa: ERA001
    # 已经是处理好的字段定义不需要特殊处理
    if isinstance(value, FieldDefinition):
        return value
    # foo = 1  # noqa: ERA001
    # 如果是仅默认值就补上类型
    # foo: int = 1  # noqa: ERA001
    return FieldDefinition(type(value), FieldInfo(default=value))


class DefaultValidatorFactory[D: MCD]:
    """默认的验证器工厂"""

    def __init__(self, validator: Iterable[str] | Mapping[str, Any], validator_options: ValidatorOptions):
        # noinspection GrazieInspection
        """
        :param validator: 用于生成验证器的数据
        :type validator: Iterable[str] | Mapping[str, Any]
        :param validator_options: 验证器选项
        :type validator_options: ValidatorOptions

        额外验证器选项
        -----------------------
        .. list-table::
           :widths: auto

           * - 键名
             - 描述
             - 默认值
             - 类型
           * - model_config_key
             - 内部编译 :py:mod:`pydantic` 的 :py:class:`~pydantic.main.BaseModel`
               时，模型配置是以嵌套字典的形式存储的，因此请确保此参数不与任何其中子模型名冲突
             - ".__model_config__"
             - Any

        .. versionchanged:: 0.1.2
           支持验证器混搭路径字符串和嵌套字典

        .. versionchanged:: 0.1.4
           支持验证器非字符串键 (含有非字符串键的子验证器不会被递归处理)
        """  # noqa: RUF002, D205
        validator = deepcopy(validator)
        if isinstance(validator, Mapping):  # 先检查Mapping因为Mapping可以是Iterable
            ...
        elif isinstance(validator, Iterable):
            # 预处理为
            # k: Any  # noqa: ERA001
            validator = OrderedDict((k, Any) for k in validator)
        else:
            msg = f"Invalid validator type '{type(validator).__name__}'"
            raise TypeError(msg)
        self.validator = validator
        self.validator_options = validator_options

        self.typehint_types = (type, types.UnionType, types.EllipsisType, types.GenericAlias, TypeAliasType)
        self.model_config_key = validator_options.extra.get("model_config_key", ".__model_config__")
        self._compile()
        self.model: type[BaseModel]

    def _fmt_mapping_key(self, validator: Mapping[str, Any]) -> tuple[Mapping[str, Any], set[str | ABCPath[Any]]]:
        # noinspection GrazieInspection
        """
        格式化验证器键

        :param validator: Mapping验证器
        :type validator: Mapping[str, Any]

        :return: 格式化后的映射键和被覆盖的Mapping父路径
        :rtype: tuple[Mapping[str, Any], set[str | ABCPath[Any]]]

        .. versionchanged:: 0.3.0
           拆分覆盖检查到函数 :py:func:`_check_overwriting_exists_path`
        """
        iterator = iter(validator.items())
        key: str = None  # type: ignore[assignment]
        value: Any = None

        def _next() -> bool:
            """
            获取下一个键值对

            :return: 是否耗尽迭代器
            :rtype: bool
            """
            nonlocal key, value
            with suppress(StopIteration):
                key, value = next(iterator)
                return False
            return True

        # 如果为空则提前返回
        if _next():
            return {}, set()

        fmt_data: MappingConfigData[OrderedDict[str, Any]] = MappingConfigData(OrderedDict())
        parent_set: set[str | ABCPath[Any]] = set()
        while True:
            # 如果传入了任意路径的父路径那就检查新值和旧值是否都为Mapping子类或Any
            # 如果是那就把父路径直接加入parent_set不进行后续操作
            if _check_overwriting_exists_path(key, value, fmt_data, self.typehint_types):
                parent_set.add(key)
                if _next():  # 更新键值对
                    break
                continue

            # 如果可以递归处理字段值那就递归处理
            if _allow_recursive(value):
                value, inner_path_set = self._fmt_mapping_key(value)
                parent_set.update(f"{key}\\.{inner_path}" for inner_path in inner_path_set)

            # 记录该键值对
            try:
                fmt_data.modify(key, value)
            except ConfigDataTypeError as err:  # 如果任意父路径不为Mapping
                relative_path = Path(err.key_info.relative_keys)
                # 如果旧类型为Mapping子类或Any那么就允许新的键创建
                if not _is_mapping(fmt_data.retrieve(relative_path)):
                    raise err from None
                fmt_data.modify(relative_path, OrderedDict())
                parent_set.add(relative_path)
                fmt_data.modify(key, value)  # 再次记录该键值对

            # 获取下一个键值对
            if _next():
                break

        return fmt_data.data, parent_set

    def _mapping2model(self, mapping: Mapping[str, Any], model_config: dict[str, Any]) -> type[BaseModel]:
        """
        将Mapping转换为Model

        :param mapping: 需要转换的Mapping
        :type mapping: Mapping[str, Any]

        :return: 转换后的Model
        :rtype: type[BaseModel]

        .. versionchanged:: 0.3.0
           拆分字段定义转换到函数 :py:func:`_convert2definition`
        """
        fmt_data: OrderedDict[str, Any] = OrderedDict()
        for key, value in mapping.items():
            # 将键值对转换为字段定义
            definition = _convert2definition(value, self.typehint_types)

            # 递归处理Mapping值
            if all(
                (
                    definition.allow_recursive,
                    _allow_recursive(definition.value.default),
                    # foo.bar = {}  # noqa: ERA001
                    # 这种情况下不进行递归解析 即捕获所有键(foo.bar.*)如果进行了解析就会忽略所有内容即返回foo.bar={}
                    definition.value.default,
                )
            ):
                model_cls = self._mapping2model(
                    mapping=definition.value.default, model_config=model_config.get(key, {})
                )
                definition = FieldDefinition(model_cls, FieldInfo(default_factory=model_cls))

            # 如果忽略不存在的键则填充特殊值
            if all((self.validator_options.skip_missing, definition.value.is_required())):
                definition = FieldDefinition(definition.annotation | SkipMissingType, FieldInfo(default=SkipMissing))

            fmt_data[key] = (definition.annotation, definition.value)

        # 创建验证模型
        # noinspection PyInvalidCast
        return create_model(
            f"{type(self).__name__}.RuntimeTemplate",
            __config__=cast(ConfigDict, model_config.get(self.model_config_key, {})),
            **fmt_data,
        )

    def _compile(self) -> None:
        """编译模板"""
        fmt_validator, parent_set = self._fmt_mapping_key(self.validator)
        # 所有重复存在的父路径都将允许其下存在多余的键
        model_config: MCD = MappingConfigData()
        for path in parent_set:
            model_config.modify(path, {self.model_config_key: {"extra": "allow"}})

        self.model = self._mapping2model(fmt_validator, model_config.data)

    # noinspection PyTypeHints
    def __call__(self, config_ref: Ref[D | NoneConfigData]) -> D:
        """
        验证配置数据

        :param config_ref: 配置数据引用
        :type config_ref: Ref[D | NoneConfigData]

        :return: 验证后的配置数据
        :rtype: D
        """
        if isinstance(config_ref.value, NoneConfigData):
            config_ref.value = MappingConfigData()  # type: ignore[assignment]
        data: D = config_ref.value  # type: ignore[assignment]

        try:
            dict_obj = self.model(**data.data).model_dump()
        except ValidationError as err:
            raise _process_pydantic_exceptions(err) from err

        # 处理 SkipMissing 项
        if self.validator_options.skip_missing:
            dict_obj = _remove_skip_missing(dict_obj)

        # 完全替换原始数据
        if self.validator_options.allow_modify:
            data._data = dict_obj  # noqa: SLF001
            return data
        return data.from_data(dict_obj)


# noinspection PyTypeHints
def pydantic_validator[D: MCD](
    validator: type[BaseModel], cfg: ValidatorOptions
) -> Callable[[Ref[D | NoneConfigData]], D]:
    """
    验证器选项 ``skip_missing`` 无效

    :param validator: :py:class:`~pydantic.main.BaseModel` 的子类
    :type validator: type[BaseModel]
    :param cfg: 验证器选项
    :type cfg: ValidatorOptions

    :return: 验证器
    :rtype: Callable[[Ref[D | NoneConfigData]], D]
    """
    if not issubclass(validator, BaseModel):
        msg = f"Expected a subclass of BaseModel for parameter 'validator', but got '{validator.__name__}'"
        raise TypeError(msg)
    if cfg.skip_missing:
        warnings.warn("skip_missing is not supported in pydantic validator", stacklevel=2)

    # noinspection PyTypeHints
    def _builder(config_ref: Ref[D | NoneConfigData]) -> D:
        """
        验证配置数据

        :param config_ref: 配置数据引用
        :type config_ref: Ref[D | NoneConfigData]

        :return: 验证后的配置数据
        :rtype: D
        """
        if isinstance(config_ref.value, NoneConfigData):
            config_ref.value = MappingConfigData()  # type: ignore[assignment]
        data: D = config_ref.value  # type: ignore[assignment]

        try:
            dict_obj = validator(**data).model_dump()
        except ValidationError as err:
            raise _process_pydantic_exceptions(err) from err

        # 完全替换原始数据
        if cfg.allow_modify:
            data._data = dict_obj  # noqa: SLF001
            return data
        return data.from_data(dict_obj)

    return _builder


class ComponentValidatorFactory[D: ComponentConfigData[Any, Any]]:
    """
    组件验证器工厂

    .. versionadded:: 0.2.0
    """

    def __init__(self, validator: Mapping[str | None, Callable[[Ref[ICD]], ICD]], validator_options: ValidatorOptions):
        """
        :param validator: 组件验证器
        :type validator: Mapping[str | None, Callable[[Ref[ICD]], ICD]]
        :param validator_options: 验证器选项
        :type validator_options: ValidatorOptions

        额外验证器选项
        -----------------------

        .. list-table::
           :widths: auto

           * - 键名
             - 描述
             - 默认值
             - 类型
           * - allow_initialize
             - 是否允许初始化不存在的组件成员(注意！ 现在的实现方式会强制初始化成员为 :py:class:`MappingConfigData`)
             - True
             - bool
           * - meta_validator
             - 组件元数据验证器
             - 尝试从传入的组件元数据获得，若不存在(值为None)则放弃验证
             - Callable[[ComponentMeta, ValidatorOptions], ComponentMeta]

        .. versionchanged:: 0.3.0
           更改参数 ``validator`` 类型为 ``Mapping[str | None, Callable[[Ref[ICD]], ICD]]``
           并移除因此冗余的移除额外验证器选项 ``validator_factory``
        """  # noqa: RUF002, D205
        self.validator_options = validator_options
        self.validators = validator

    def _validate_member_metadata(self, component_data: D) -> dict[str, ICD]:
        """
        验证组件成员元数据

        :param component_data: 组件数据
        :type component_data: D

        :return: 验证后的组件数据
        :rtype: dict[str | None, ICD]
        """
        validated_members: dict[str, ICD] = {}
        for member, validator in self.validators.items():
            if member is None:
                continue

            member_not_exists = member not in component_data
            member_data_ref: Ref[ICD]
            if member_not_exists and self.validator_options.extra.get("allow_initialize", True):
                member_data_ref = Ref(MappingConfigData())
                if self.validator_options.allow_modify:
                    component_data[member] = member_data_ref.value
            elif member_not_exists:
                raise ComponentMemberMismatchError(missing={member}, redundant=set())
            else:
                member_data_ref = Ref(component_data[member])
            validated_member = validator(member_data_ref)
            validated_members[member] = validated_member

            # 完全替换成员数据
            if self.validator_options.allow_modify:
                component_data[member] = validated_member
        return validated_members

    def __call__(self, config_ref: Ref[D | NoneConfigData]) -> D:
        """
        验证配置数据

        :param config_ref: 配置数据引用
        :type config_ref: Ref[D | NoneConfigData]

        :return: 验证后的配置数据
        :rtype: D

        .. versionchanged:: 0.3.0
           拆分验证成员元数据到方法 :py:meth:`_validate_member_metadata`
        """
        if isinstance(config_ref.value, NoneConfigData):
            config_ref.value = ComponentConfigData()  # type: ignore[assignment]

        component_ref: Ref[D] = config_ref  # type: ignore[assignment]
        component_data = component_ref.value

        validated_members: dict[str, ICD] = self._validate_member_metadata(component_data)

        meta = deepcopy(component_data.meta)
        if None in self.validators:
            meta.config = self.validators[None](Ref(meta.config))

            # noinspection PyUnresolvedReferences
            meta_validator = None if meta.parser is None else meta.parser.validator
            meta_validator = self.validator_options.extra.get("meta_validator", meta_validator)
            if meta_validator is not None:
                meta = meta_validator(meta, self.validator_options)

        # 完全替换元数据
        if self.validator_options.allow_modify:
            component_data._meta = meta  # noqa: SLF001

        return component_data.from_data(meta, validated_members)


__all__ = (
    "ComponentValidatorFactory",
    "DefaultValidatorFactory",
    "FieldDefinition",
    "ValidatorOptions",
    "ValidatorTypes",
    "pydantic_validator",
)
