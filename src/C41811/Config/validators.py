# -*- coding: utf-8 -*-
# cython: language_level = 3


import dataclasses
import re
import types
import warnings
from collections import OrderedDict
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Callable
from typing import Iterable
from typing import NamedTuple

from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import create_model
# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from pydantic_core import core_schema

from .abc import ABCConfigData
from .abc import ABCKey
from .base import ConfigData
from .errors import ConfigDataTypeError
from .errors import ConfigOperate
from .errors import KeyInfo
from .errors import RequiredPathNotFoundError
from .errors import UnknownErrorDuringValidate
from .path import AttrKey
from .path import IndexKey
from .path import Path


class ValidatorTypes(Enum):
    """
    验证器类型
    """
    DEFAULT = None
    IGNORE = "ignore"
    PYDANTIC = "pydantic"


@dataclass
class ValidatorFactoryConfig:
    """
    验证器配置
    """
    allow_create: bool = False
    ignore_missing: bool = False

    extra: dict = dataclasses.field(default_factory=dict)


def _fill_not_exits(raw_obj: ABCConfigData, obj: ABCConfigData):
    all_leaf = dict(recursive=True, end_point_only=True)
    diff_keys = obj.keys(**all_leaf) - raw_obj.keys(**all_leaf)
    for key in diff_keys:
        raw_obj.modify(key, obj.retrieve(key))


def _process_pydantic_exceptions(err: ValidationError) -> Exception:
    e = err.errors()[0]

    locate = list(e["loc"])
    locate_keys: list[ABCKey] = []
    for key in locate:
        if isinstance(key, str):
            locate_keys.append(AttrKey(key))
        elif isinstance(key, int):
            locate_keys.append(IndexKey(key))
        else:  # pragma: no cover
            raise UnknownErrorDuringValidate("Cannot convert pydantic index to string") from err

    kwargs: dict[str, Any] = dict(
        key_info=KeyInfo(
            path=Path(locate_keys),
            current_key=locate_keys[-1],
            index=len(locate_keys) - 1
        )
    )

    class ErrInfo(NamedTuple):
        err_type: type[Exception] | Callable[[...], Exception]
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
                required_type=re.match(r"Input should be (.*)", err_msg).group(1),
                now_type=type(err_input)
            )
        ),
        "int_type": lambda: ErrInfo(
            ConfigDataTypeError,
            dict(required_type=int, now_type=type(err_input))
        ),
        "int_parsing": lambda: ErrInfo(
            ConfigDataTypeError,
            dict(required_type=int, now_type=type(err_input))
        ),
        "string_type": lambda: ErrInfo(
            ConfigDataTypeError,
            dict(required_type=str, now_type=type(err_input))
        ),
        "dict_type": lambda: ErrInfo(
            ConfigDataTypeError,
            dict(required_type=dict, now_type=type(err_input))
        ),
    }

    err_type_processor = types_kwarg.get(e["type"], None)
    if err_type_processor is None:  # pragma: no cover
        raise UnknownErrorDuringValidate(**kwargs, error=e) from err
    err_info = err_type_processor()
    return err_info.err_type(**(kwargs | err_info.kwargs))


class IgnoreMissingType:
    """
    用于表明值可以缺失特殊值
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __str__(self):  # pragma: no cover
        return "<IgnoreMissing>"

    @staticmethod
    def __get_pydantic_core_schema__(*_):
        # 构造一个永远无法匹配的schema, 使 IgnoreMissing | int 可以正常工作
        return core_schema.chain_schema(
            [core_schema.none_schema(), core_schema.is_subclass_schema(type)]
        )


IgnoreMissing = IgnoreMissingType()


@dataclass
class FieldDefinition:
    """
    字段定义，包含类型注解和默认值
    """
    type: type | types.UnionType | types.EllipsisType | types.GenericAlias
    value: FieldInfo


class DefaultValidatorFactory:
    """
    默认的验证器工厂
    """

    def __init__(self, validator: Iterable[str] | Mapping[str, Any], validator_config: ValidatorFactoryConfig):
        """
        :param validator: 用于生成验证器的数据
        :type validator: Iterable[str] | Mapping[str, Any]
        :param validator_config: 验证器配置
        :type validator_config: ValidatorFactoryConfig
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
        self.model_config_key = validator_config.extra.get("model_config_key", f".__model_config__")
        self._compile()
        self.model: BaseModel

    def _fmt_mapping_key(self) -> tuple[Mapping[str, Any], set[str]]:
        """
        格式化映射键

        :return: 格式化后的映射键和被覆盖的Mapping父路径
        :rtype: tuple[Mapping[str, Any], set[str]]
        """

        class MappingType(BaseModel):
            value: type[Mapping]

        fmt_data = ConfigData(OrderedDict())
        iterator = iter(self.validator.items())

        try:
            key, value = next(iterator)
        except StopIteration:
            return {}, set()

        father_set: set = set()
        while True:
            try:
                fmt_data.modify(key, value)
            except ConfigDataTypeError as err:
                relative_path = Path(err.key_info.relative_keys)
                # 如果旧类型为Mapping, Any那么就允许新的键创建
                try:
                    MappingType(value=fmt_data.retrieve(relative_path))
                except (ValidationError, TypeError):
                    if fmt_data.retrieve(relative_path) is not Any:
                        raise err from None
                fmt_data.modify(relative_path, OrderedDict())
                father_set.add(relative_path)
                continue

            try:
                key, value = next(iterator)
            except StopIteration:
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
        fmt_data = OrderedDict()
        for key, value in mapping.items():
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
                    isinstance(definition.value, FieldInfo),
                    isinstance(definition.value.default, Mapping),
                    # foo.bar = {}
                    # 这种情况下不进行递归解析，获取所有键(foo.bar.*)如果进行了解析就只会返回foo.bar={}
                    definition.value.default
            )):
                model_cls = self._mapping2model(
                    mapping=definition.value.default,
                    model_config=model_config[key] if key in model_config else {}
                )
                definition = FieldDefinition(
                    model_cls,
                    FieldInfo(default_factory=model_cls if self.validator_config.allow_create else None)
                )

            # 如果忽略不存在的键就填充特殊值
            if all((
                    self.validator_config.ignore_missing,
                    isinstance(definition.value, FieldInfo),
                    definition.value.is_required()
            )):
                definition = FieldDefinition(definition.type | IgnoreMissingType, FieldInfo(default=IgnoreMissing))

            fmt_data[key] = (definition.type, definition.value)

        return create_model(
            f"{type(self).__name__}.RuntimeTemplate",
            __config__=model_config[self.model_config_key] if self.model_config_key in model_config else {},
            **fmt_data
        )

    def _compile(self) -> None:
        """
        编译模板
        """
        fmt_validator, father_set = self._fmt_mapping_key()
        model_config = ConfigData()
        for path in father_set:
            model_config.modify(path, {self.model_config_key: {"extra": "allow"}})

        self.model = self._mapping2model(fmt_validator, model_config.data)

    def __call__[D: ABCConfigData](self, data: D) -> D:
        try:
            dict_obj = self.model(**data.data).model_dump()
        except ValidationError as err:
            raise _process_pydantic_exceptions(err) from None

        config_obj: ABCConfigData = data.from_data(dict_obj)
        if self.validator_config.ignore_missing:
            for key in config_obj.keys(recursive=True, end_point_only=True):
                if config_obj.retrieve(key) is IgnoreMissing:
                    config_obj.delete(key)

        if self.validator_config.allow_create:
            _fill_not_exits(data, config_obj)
        return config_obj


def pydantic_validator[D: ABCConfigData](validator: type[BaseModel], cfg: ValidatorFactoryConfig) -> Callable[[D], D]:
    """
    :param validator: pydantic.BaseModel的子类
    :type validator: type[BaseModel]
    :param cfg: 验证器配置
    :type cfg: ValidatorFactoryConfig
    """
    if not issubclass(validator, BaseModel):
        raise TypeError(f"Expected a subclass of BaseModel for parameter 'validator', but got '{validator.__name__}'")
    if cfg.ignore_missing:
        warnings.warn("ignore_missing is not supported in pydantic validator")

    def _builder(data: D) -> D:
        try:
            dict_obj = validator(**data).model_dump()
        except ValidationError as err:
            raise _process_pydantic_exceptions(err) from None
        config_obj = data.from_data(dict_obj)
        if cfg.allow_create:
            _fill_not_exits(data, config_obj)
        return config_obj

    return _builder


__all__ = (
    "ValidatorTypes",
    "ValidatorFactoryConfig",
    "FieldDefinition",
    "DefaultValidatorFactory",
    "pydantic_validator",
)