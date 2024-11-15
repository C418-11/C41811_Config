# -*- coding: utf-8 -*-
# cython: language_level = 3

import functools
import inspect
import os.path
import re
import types
import warnings
from collections import OrderedDict
from collections.abc import Mapping
from collections.abc import MutableMapping
from copy import deepcopy
from enum import Enum
from typing import Any
from typing import Callable
from typing import Iterable
from typing import NamedTuple
from typing import Optional
from typing import Self
from typing import TypeVar
from typing import override

from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import create_model
# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from pydantic_core import core_schema

from .abc import ABCConfig
from .abc import ABCConfigData
from .abc import ABCConfigPool
from .abc import ABCSLProcessorPool
from .errors import ConfigDataTypeError
from .errors import ConfigOperate
from .errors import FailedProcessConfigFileError
from .errors import RequiredKeyNotFoundError
from .errors import UnknownErrorDuringValidate
from .errors import UnsupportedConfigFormatError


class ConfigData(ABCConfigData):

    def _process_path(self, path: str, process_check: Callable, process_return: Callable) -> Any:
        """
        处理键路径的通用函数阿

        :param path: 键路径
        :type path: str
        :param process_check: 检查并处理每个路径段，返回值非None时结束操作并返回值
        :type process_check: Callable[(now_data: Any, now_path: str, last_path: str, path_index: int), Any]
        :param process_return: 处理最终结果，该函数返回值会被直接返回
        :type process_return: Callable[(now_data: Any), Any]

        :return: 处理结果
        :rtype: Any
        """
        last_path = path
        now_data = self._data

        path_index = -1

        while last_path:
            path_index += 1
            try:
                now_path, last_path = last_path.split(self._sep_char, maxsplit=1)
            except ValueError:
                now_path, last_path = last_path, None

            check_result = process_check(now_data, now_path, last_path, path_index)
            if check_result is not None:
                return check_result

            now_data = now_data[now_path]

        return process_return(now_data)

    @override
    def getPathValue(self, path: str, *, get_raw: bool = False) -> Any:
        def checker(now_data, now_path, _last_path, path_index):
            if not isinstance(now_data, Mapping):
                raise ConfigDataTypeError(path, self._sep_char, now_path, path_index, Mapping, type(now_data))
            if now_path not in now_data:
                raise RequiredKeyNotFoundError(path, self._sep_char, now_path, path_index, ConfigOperate.Read)

        def process_return(now_data):
            if get_raw:
                return deepcopy(now_data)
            if isinstance(now_data, Mapping):
                return ConfigData(deepcopy(now_data))

            return deepcopy(now_data)

        return self._process_path(path, checker, process_return)

    @override
    def setPathValue(self, path: str, value: Any, *, allow_create: bool = True) -> Self:
        if self.read_only:
            raise TypeError("Config data is read-only")

        def checker(now_data, now_path, last_path, path_index):
            if not isinstance(now_data, MutableMapping):
                raise ConfigDataTypeError(path, self._sep_char, now_path, path_index, MutableMapping, type(now_data))
            if now_path not in now_data:
                if not allow_create:
                    raise RequiredKeyNotFoundError(path, self._sep_char, now_path, path_index, ConfigOperate.Write)
                now_data[now_path] = type(self._data)()

            if last_path is None:
                now_data[now_path] = value

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    def deletePath(self, path: str) -> Self:
        if self.read_only:
            raise TypeError("Config data is read-only")

        def checker(now_data, now_path, last_path, path_index):
            if not isinstance(now_data, MutableMapping):
                raise ConfigDataTypeError(path, self._sep_char, now_path, path_index, MutableMapping, type(now_data))
            if now_path not in now_data:
                raise RequiredKeyNotFoundError(path, self._sep_char, now_path, path_index, ConfigOperate.Delete)

            if last_path is None:
                del now_data[now_path]
                return True

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    def hasPath(self, path: str) -> bool:
        def checker(now_data, now_path, _last_path, path_index):
            if not isinstance(now_data, Mapping):
                raise ConfigDataTypeError(path, self._sep_char, now_path, path_index, Mapping, type(now_data))
            if now_path not in now_data:
                return False

        return self._process_path(path, checker, lambda *_: True)

    @override
    def get(self, path: str, default=None, *, get_raw: bool = False) -> Any:
        try:
            return self.getPathValue(path, get_raw=get_raw)
        except RequiredKeyNotFoundError:
            return default

    @override
    def set_default(self, path: str, default=None, *, get_raw: bool = False) -> Any:
        try:
            return self.getPathValue(path, get_raw=get_raw)
        except RequiredKeyNotFoundError:
            self.setPathValue(path, default)
            return default


class ValidatorTypes(Enum):
    """
    验证器类型
    """
    DEFAULT = None
    PYDANTIC = "pydantic"


class ValidatorConfig(NamedTuple):
    """
    验证器配置
    """
    allow_create: bool
    ignore_missing: bool

    extra: dict


def _fill_not_exits(raw_obj: ABCConfigData, obj: ABCConfigData):
    all_leaf = dict(recursive=True, end_point_only=True)
    diff_keys = obj.keys(**all_leaf) - raw_obj.keys(**all_leaf)
    for key in diff_keys:
        raw_obj[key] = obj[key]


def _process_pydantic_exceptions(err: ValidationError, raw_data: ABCConfigData) -> Exception:
    e = err.errors()[0]

    locate = list(e["loc"])
    for i, path in enumerate(locate):
        if isinstance(path, str):
            pass
        elif isinstance(path, int):
            locate[i] = f"$$Index$[{path}]$"
        else:
            raise UnknownErrorDuringValidate("Cannot convert pydantic index to string") from err

    kwargs: dict[str, Any] = dict(
        key=raw_data.sep_char.join(locate),
        sep_char=raw_data.sep_char,
        current_key=locate[-1],
        index=len(locate) - 1
    )

    class ErrInfo(NamedTuple):
        err_type: type[Exception] | Callable[[...], Exception]
        kwargs: dict[str, Any]

    err_input = e["input"]
    err_msg = e["msg"]

    types_kwarg: dict[str, Callable[[], ErrInfo]] = {
        "missing": lambda: ErrInfo(
            RequiredKeyNotFoundError,
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
    if err_type_processor is None:
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

    def __str__(self):
        return "<IgnoreMissing>"

    @staticmethod
    def __get_pydantic_core_schema__(*_) -> core_schema.AnySchema:
        return core_schema.any_schema()


IgnoreMissing = IgnoreMissingType()

D = TypeVar('D', bound=ABCConfigData)


class DefaultValidatorFactory:
    """
    默认的验证器工厂
    """

    def __init__(self, validator: Iterable[str] | Mapping[str, Any], validator_config: ValidatorConfig):
        """
        :param validator: 用于生成验证器的数据
        :type validator: Iterable[str] | Mapping[str, Any]
        :param validator_config: 验证器配置
        :type validator_config: ValidatorConfig
        """

        validator = deepcopy(validator)
        if isinstance(validator, (tuple, list, set, frozenset)):
            validator = OrderedDict((k, Any) for k in validator)
        elif not isinstance(validator, Mapping):
            raise TypeError(f"Invalid validator type '{type(validator).__name__}'")
        self.validator = validator
        self.validator_config = validator_config
        self.sep_char = validator_config.extra.get("sep_char", '.')

        self.typehint_types = (type, types.GenericAlias, types.UnionType, types.EllipsisType)
        self.model_config_key = f"{self.sep_char}__model_config__"
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

        fmt_data = ConfigData(OrderedDict(), sep_char=self.sep_char)
        iterator = iter(self.validator.items())

        try:
            key, value = next(iterator)
        except StopIteration:
            return fmt_data.data

        father_set: set = set()
        while True:
            try:
                fmt_data[key] = value
            except ConfigDataTypeError as err:
                # 如果旧类型为Mapping那么就允许新的键递归创建
                try:
                    MappingType(value=fmt_data[err.relative_key])
                except (ValidationError, TypeError):
                    raise err from None
                fmt_data[err.relative_key] = OrderedDict()
                father_set.add(err.relative_key)
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
                value = (value.annotation, value)
            # foo: int
            # 如果是仅类型就填上空值
            elif issubclass(type(value), self.typehint_types):
                # foo: int = FieldInfo()
                value = (value, FieldInfo())
            # foo = 1
            # 如果是仅默认值就补上类型
            elif not isinstance(value, tuple):
                # foo: int = 1
                value = (type(value), FieldInfo(default=value))

            # 递归处理
            if all((
                    isinstance(value[1], FieldInfo),
                    isinstance(value[1].default, Mapping),
                    # foo.bar = {}
                    # 这种情况下不进行递归解析，获取所有键(foo.bar.*)如果进行了解析就只会返回foo.bar={}
                    value[1].default
            )):
                model_cls = self._mapping2model(
                    mapping=value[1].default,
                    model_config=model_config[key] if key in model_config else {}
                )
                value = (
                    model_cls,
                    FieldInfo(default_factory=model_cls if self.validator_config.allow_create else None)
                )

            # 如果忽略不存在的键就填充特殊值
            if self.validator_config.ignore_missing and isinstance(value[1], FieldInfo) and value[1].is_required():
                value = (value[0] | IgnoreMissingType, FieldInfo(default=IgnoreMissing))

            fmt_data[key] = value

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
            model_config[path] = {self.model_config_key: {"extra": "allow"}}

        self.model = self._mapping2model(fmt_validator, model_config.data)

    def __call__(self, data: D) -> D:
        try:
            dict_obj = self.model(**data).model_dump()
        except ValidationError as err:
            raise _process_pydantic_exceptions(err, data) from None

        config_obj = data.new_data(dict_obj)
        for key in config_obj.keys(recursive=True, end_point_only=True):
            if config_obj[key] is IgnoreMissing:
                del config_obj[key]

        if self.validator_config.allow_create:
            _fill_not_exits(data, config_obj)
        return config_obj


def _pydantic_validator(validator: type[BaseModel], cfg: ValidatorConfig) -> Callable[[D], D]:
    """
    :param validator: pydantic.BaseModel的子类
    :type validator: type[BaseModel]
    :param cfg: 验证器配置
    :type cfg: ValidatorConfig
    """
    if not issubclass(validator, BaseModel):
        raise TypeError(f"Invalid validator type '{validator.__name__}'")
    if cfg.ignore_missing:
        warnings.warn("ignore_missing is not supported in pydantic validator")

    def _builder(data: D) -> D:
        try:
            dict_obj = validator(**data).model_dump()
        except ValidationError as err:
            raise _process_pydantic_exceptions(err, data) from None
        config_obj = data.new_data(dict_obj)
        if cfg.allow_create:
            _fill_not_exits(data, config_obj)
        return config_obj

    return _builder


class RequiredKey:
    """
    对需求的键进行存在检查、类型检查、填充默认值
    """

    def __init__(
            self,
            validator: Any,
            validator_factory: Optional[Callable | ValidatorTypes | str] = ValidatorTypes.DEFAULT
    ):
        """
        .. note::
           如果对性能有较高要求validator_factory建议使用 :py:attr:`ValidatorTypes.PYDANTIC`

        :param validator: 数据验证器
        :type validator: Any
        :param validator_factory: 数据验证器工厂
        :type validator_factory: Optional[Callable | ValidatorTypes]
        """
        if not callable(validator_factory):
            validator_factory = ValidatorTypes(validator_factory)
        if isinstance(validator_factory, ValidatorTypes):
            validator_factory = self.ValidatorFactories[validator_factory]

        self._validator: Iterable[str] | Mapping[str, type] = deepcopy(validator)
        self._validator_factory: Callable = validator_factory

    ValidatorFactories: dict[ValidatorTypes, Callable] = {
        ValidatorTypes.DEFAULT: DefaultValidatorFactory,
        ValidatorTypes.PYDANTIC: _pydantic_validator
    }

    def filter(
            self,
            data: ABCConfigData,
            *,
            allow_create: bool = False,
            ignore_missing: bool = False,
            **extra
    ) -> Any:
        """
        检查过滤需求的键

        .. attention::
           返回的配置数据是*快照*

        :param data: 要过滤的原始数据
        :type data: ABCConfigData
        :param allow_create: 是否允许值不存在时修改data参数对象填充默认值(即使为False仍然会在结果中填充默认值,但不会修改data参数对象)
        :type allow_create: bool
        :param ignore_missing: 忽略丢失的键
        :type ignore_missing: bool
        :param extra: 额外参数
        :type extra: Any

        :return: 处理后的配置数据*快照*
        :rtype: Any

        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredKeyNotFoundError: 必要的键未找到
        :raise UnknownErrorDuringValidate: 验证过程中发生未知错误
        """

        cfg = ValidatorConfig(allow_create=allow_create, ignore_missing=ignore_missing, extra=extra)

        validator = self._validator_factory(self._validator, cfg)
        return validator(data)


class Config(ABCConfig):
    """
    配置类
    """

    @override
    def save(
            self,
            config_pool: ABCSLProcessorPool,
            namespace: str | None = None,
            file_name: str | None = None,
            config_format: str | None = None,
            *processor_args,
            **processor_kwargs
    ) -> None:

        if config_format is None:
            config_format = self._config_format

        if config_format is None:
            raise UnsupportedConfigFormatError("Unknown")
        if config_format not in config_pool.SLProcessor:
            raise UnsupportedConfigFormatError(config_format)

        return config_pool.SLProcessor[config_format].save(
            self,
            config_pool.root_path,
            namespace,
            file_name,
            *processor_args,
            **processor_kwargs
        )

    @classmethod
    @override
    def load(
            cls,
            config_pool: ABCSLProcessorPool,
            namespace: str,
            file_name: str,
            config_format: str,
            *processor_args,
            **processor_kwargs
    ) -> Self:

        if config_format not in config_pool.SLProcessor:
            raise UnsupportedConfigFormatError(config_format)

        return config_pool.SLProcessor[
            config_format
        ].load(
            cls,
            config_pool.root_path,
            namespace,
            file_name,
            *processor_args,
            **processor_kwargs
        )


class ConfigPool(ABCConfigPool):

    def __init__(self, root_path="./.config"):
        super().__init__(root_path)
        self._configs: dict[str, dict[str, ABCConfig]] = {}

    @override
    def get(self, namespace: str, file_name: Optional[str] = None) -> dict[str, ABCConfig] | ABCConfig | None:
        if namespace not in self._configs:
            return None
        result = self._configs[namespace]

        if file_name is None:
            return result

        if file_name in result:
            return result[file_name]

        return None

    @override
    def set(self, namespace: str, file_name: str, config: ABCConfig) -> None:
        if namespace not in self._configs:
            self._configs[namespace] = {}

        self._configs[namespace][file_name] = config

    @override
    def saveAll(self, ignore_err: bool = False) -> None | dict[str, dict[str, tuple[ABCConfig, Exception]]]:
        """
        保存所有配置

        :param ignore_err: 是否忽略保存导致的错误
        :type ignore_err: bool

        :return: ignore_err为True时返回{Namespace: {FileName: (ConfigObj, Exception)}}，否则返回None
        :rtype: None | dict[str, dict[str, tuple[ABCConfig, Exception]]]
        """
        errors = {}
        for namespace, configs in self._configs.items():
            errors[namespace] = {}
            for file_name, config in configs.items():
                try:
                    config.save(self)
                except Exception as e:
                    if not ignore_err:
                        raise
                    errors[namespace][file_name] = (config, e)

        if not ignore_err:
            return None

        return {k: v for k, v in errors.items() if v}

    @override
    def requireConfig(
            self,
            namespace: str,
            file_name: str,
            required: list[str] | dict[str, Any],
            *args,
            **kwargs,
    ):
        return RequireConfigDecorator(self, namespace, file_name, RequiredKey(required), *args, **kwargs)

    def __getitem__(self, item):
        return deepcopy(self.configs[item])

    @property
    def configs(self):
        return deepcopy(self._configs)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.configs!r})"


def _is_method(func):
    arguments = inspect.getargs(func.__code__).args
    if len(arguments) < 1:
        return False
    return arguments[0] in {"self", "cls"}


class RequireConfigDecorator:
    """
    配置获取器，可作装饰器使用
    """

    def __init__(
            self,
            config_pool: ABCConfigPool,
            namespace: str,
            raw_file_name: str,
            required: RequiredKey,
            *,
            config_cls: type[ABCConfig] = Config,
            config_format: Optional[str] = None,
            cache_config: Optional[Callable[[Callable], Callable]] = None,
            allow_create: bool = True,
            filter_kwargs: Optional[dict[str, Any]] = None
    ):
        """
        :param config_pool: 所在的配置池
        :type config_pool: ConfigPool
        :param namespace: 命名空间
        :type namespace: str
        :param raw_file_name: 源文件名
        :type raw_file_name: str
        :param required: 需求的键
        :type required: RequiredKey
        :param config_format: 配置文件格式
        :type config_format: Optional[str]
        :param cache_config: 缓存配置的装饰器，默认为None，即不缓存
        :type cache_config: Optional[Callable[[Callable], Callable]]
        :param allow_create: 是否允许在文件不存在时新建文件
        :type allow_create: bool
        :param filter_kwargs: RequiredKey.filter要绑定的默认参数，默认为allow_create=True
        :type filter_kwargs: dict[str, Any]

        :raise UnsupportedConfigFormatError: 不支持的配置格式
        """
        format_set: set[str]
        if config_format is None:
            _, config_format = os.path.splitext(raw_file_name)
            if not config_format:
                raise UnsupportedConfigFormatError("Unknown")
            if config_format not in config_pool.FileExtProcessor:
                raise UnsupportedConfigFormatError(config_format)
            format_set = config_pool.FileExtProcessor[config_format]
        else:
            format_set = {config_format, }

        def _load_config(format_: str) -> ABCConfig:
            if format_ not in config_pool.SLProcessor:
                raise UnsupportedConfigFormatError(format_)

            result: ABCConfig | None = config_pool.get(namespace, raw_file_name)
            if result is None:
                try:
                    result = config_cls.load(config_pool, namespace, raw_file_name, format_)
                except FileNotFoundError:
                    if not allow_create:
                        raise
                    result = config_cls(
                        ConfigData(),
                        namespace=namespace,
                        file_name=raw_file_name,
                        config_format=format_
                    )

                config_pool.set(namespace, raw_file_name, result)
            return result

        errors = {}
        for f in format_set:
            try:
                ret = _load_config(f)
            except FailedProcessConfigFileError as err:
                errors[f] = err
                continue
            config: ABCConfig = ret
            break
        else:
            raise FailedProcessConfigFileError(errors)

        if filter_kwargs is None:
            filter_kwargs = {}

        self._config: ABCConfig = config
        self._required = required
        self._filter_kwargs = {"allow_create": True} | filter_kwargs
        self._cache_config: Callable = cache_config if cache_config is not None else lambda x: x

    def checkConfig(self, *, ignore_cache: bool = False, **filter_kwargs) -> Any:
        """
        手动检查配置

        :param ignore_cache: 是否忽略缓存
        :type ignore_cache: bool
        :param filter_kwargs: RequiredConfig.filter的参数
        :return: 得到的配置数据
        :rtype: Any
        """
        kwargs = self._filter_kwargs | filter_kwargs
        if ignore_cache:
            return self._required.filter(self._config.data, **kwargs)
        return self._wrapped_filter(**kwargs)

    def __call__(self, func):
        if _is_method(func):
            processor = self._method_processor
        else:
            processor = self._function_processor

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*processor(*args), **kwargs)

        return wrapper

    def _wrapped_filter(self, **kwargs):
        return self._cache_config(self._required.filter(self._config.data, **kwargs))

    def _function_processor(self, *args):
        return self._wrapped_filter(**self._filter_kwargs), *args

    def _method_processor(self, obj, *args):
        return obj, self._wrapped_filter(**self._filter_kwargs), *args


DefaultConfigPool = ConfigPool()
requireConfig = DefaultConfigPool.requireConfig

__all__ = (
    "ConfigData",
    "ValidatorTypes",
    "ValidatorConfig",
    "RequiredKey",
    "Config",
    "ConfigPool",
    "RequireConfigDecorator",

    "DefaultConfigPool",
    "requireConfig",
)
