# -*- coding: utf-8 -*-
# cython: language_level = 3


import dataclasses
import os.path
import re
import types
import warnings
from abc import ABC
from collections import OrderedDict
from collections.abc import Mapping
from collections.abc import MutableMapping
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import Literal
from typing import NamedTuple
from typing import Optional
from typing import Self
from typing import override

import wrapt
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import create_model
# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from pydantic_core import core_schema

from .abc import ABCConfigData
from .abc import ABCConfigFile
from .abc import ABCConfigPool
from .abc import ABCConfigSL
from .abc import ABCKey
from .abc import ABCPath
from .abc import ABCPathSyntaxParser
from .abc import ABCSLProcessorPool
from .errors import ConfigDataPathSyntaxException
from .errors import ConfigDataTypeError
from .errors import ConfigOperate
from .errors import FailedProcessConfigFileError
from .errors import RequiredPathNotFoundError
from .errors import UnknownErrorDuringValidate
from .errors import UnknownTokenType
from .errors import UnsupportedConfigFormatError
from .types import KeyInfo
from .types import TokenInfo


class AttrKey(ABCKey):
    def __init__(self, key: str):
        super().__init__(key)

    def __len__(self):
        return len(self._key)

    def __eq__(self, other):
        if isinstance(other, str):
            return self._key == other
        return super().__eq__(other)

    def __hash__(self):
        return super().__hash__()


class IndexKey(ABCKey):
    def __init__(self, key: int):
        super().__init__(key)


class Path(ABCPath):
    @classmethod
    def from_str(cls, string: str) -> Self:
        return cls(PathSyntaxParser.parse(string))

    @classmethod
    def from_locate(cls, locate: Iterable[str | int]) -> Self:
        keys: list[ABCKey] = []
        for loc in locate:
            if isinstance(loc, int):
                keys.append(IndexKey(loc))
                continue
            if isinstance(loc, str):
                keys.append(AttrKey(loc))
                continue
            raise ValueError("locate element must be 'int' or 'str'")
        return cls(keys)


class PathSyntaxParser(ABCPathSyntaxParser):
    """
    路径语法解析器
    """

    @staticmethod
    @override
    def tokenize(string: str) -> Generator[str, None, None]:
        token_cache = []
        if not string.startswith('\\'):
            chunk, sep, string = string.partition('\\')
            yield chunk
            if not sep:
                return

        while string:
            chunk, _, string = string.partition('\\')
            try:
                next_char = string[0]
            except IndexError:
                next_char = ''

            if not chunk:
                continue

            token_cache.append('\\')

            if chunk[0] == ']':
                yield "\\]"
                chunk = chunk[1:]
                token_cache.pop()
                if not chunk:
                    continue

            token_cache.append(chunk)

            if next_char not in set("\\.[]") | {''}:
                warnings.warn(
                    rf"invalid escape sequence '\{next_char}'",
                    SyntaxWarning
                )
                continue

            if next_char == '\\':
                string = string[1:]
                token_cache.append('\\')
                continue

            yield ''.join(token_cache)
            token_cache = []

    @classmethod
    @override
    def parse(cls, string: str) -> list[ABCKey]:
        path: list[ABCKey] = []
        item: Optional[str] = None

        tokenized_path = list(cls.tokenize(string))
        for i, token in enumerate(tokenized_path):
            if not token.startswith('\\'):
                raise UnknownTokenType(TokenInfo(tokenized_path, token, i))

            token_type = token[1]
            context = token[2:].replace("\\\\", '\\')

            if token_type == ']':
                if not item:
                    raise ConfigDataPathSyntaxException(
                        TokenInfo(tokenized_path, token, i),
                        "unmatched ']': "
                    )
                try:
                    path.append(IndexKey(int(item)))
                except ValueError:
                    raise ValueError("index key must be int")
                item = None
                continue
            if item:
                raise ConfigDataPathSyntaxException(TokenInfo(tokenized_path, token, i), "'[' was never closed: ")
            if token_type == '[':
                item = context
                continue
            if token_type == '.':
                path.append(AttrKey(context))
                continue

            raise UnknownTokenType(TokenInfo(tokenized_path, token, i))

        if item:
            raise ConfigDataPathSyntaxException(
                TokenInfo(tokenized_path, tokenized_path[-1], len(tokenized_path) - 1),
                "'[' was never closed: "
            )

        return path


def _fmt_path(path: str | ABCPath) -> ABCPath:
    if isinstance(path, ABCPath):
        return path
    if not path.startswith('\\'):
        path = rf"\.{path}"
    return Path.from_str(path)


class ConfigData(ABCConfigData):

    def _process_path(
            self,
            path: ABCPath,
            process_check: Callable[[Mapping | MutableMapping, ABCKey, list[ABCKey], int], Any],
            process_return: Callable[[Mapping | MutableMapping], Any]
    ) -> Any:
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
        now_data = self._data

        for key_index, now_key in enumerate(path):
            now_key: ABCKey
            last_key: list[ABCKey] = path[key_index + 1:]

            check_result = process_check(now_data, now_key, last_key, key_index)
            if check_result is not None:
                return check_result

            now_data = now_data[now_key]

        return process_return(now_data)

    @override
    def retrieve(self, path: str | ABCPath, *, get_raw: bool = False) -> Any:
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, _last_key: list[ABCKey], key_index: int):
            if not isinstance(now_data, Mapping):
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), Mapping, type(now_data))
            if now_key not in now_data:
                raise RequiredPathNotFoundError(KeyInfo(path, now_key, key_index), ConfigOperate.Read)

        def process_return(now_data):
            if get_raw:
                return deepcopy(now_data)
            if isinstance(now_data, Mapping):
                return ConfigData(now_data)

            return deepcopy(now_data)

        return self._process_path(path, checker, process_return)

    @override
    def modify(self, path: str | ABCPath, value: Any, *, allow_create: bool = True) -> Self:
        if self.read_only:
            raise TypeError("Config data is read-only")
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, last_key: list[ABCKey], key_index: int):
            if not isinstance(now_data, MutableMapping):
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), MutableMapping, type(now_data))
            if now_key not in now_data:
                if not allow_create:
                    raise RequiredPathNotFoundError(KeyInfo(path, now_key, key_index), ConfigOperate.Write)
                now_data[now_key.key] = type(self._data)()

            if not last_key:
                now_data[now_key.key] = value

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    def delete(self, path: str | ABCPath) -> Self:
        if self.read_only:
            raise TypeError("Config data is read-only")
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, last_key: list[ABCKey], key_index: int):
            if not isinstance(now_data, MutableMapping):
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), MutableMapping, type(now_data))
            if now_key not in now_data:
                raise RequiredPathNotFoundError(KeyInfo(path, now_key, key_index), ConfigOperate.Delete)

            if not last_key:
                del now_data[now_key]
                return True

        self._process_path(path, checker, lambda *_: None)
        return self

    @override
    def exists(self, path: str | ABCPath, *, ignore_wrong_type: bool = False) -> bool:
        path = _fmt_path(path)

        def checker(now_data, now_key: ABCKey, _last_key: list[ABCKey], key_index: int):
            if not isinstance(now_data, Mapping):
                if ignore_wrong_type:
                    return False
                raise ConfigDataTypeError(KeyInfo(path, now_key, key_index), Mapping, type(now_data))
            if now_key not in now_data:
                return False

        return self._process_path(path, checker, lambda *_: True)

    @override
    def get(self, path: str | ABCPath, default=None, *, get_raw: bool = False) -> Any:
        try:
            return self.retrieve(path, get_raw=get_raw)
        except RequiredPathNotFoundError:
            return default

    @override
    def set_default(self, path: str | ABCPath, default=None, *, get_raw: bool = False) -> Any:
        try:
            return self.retrieve(path, get_raw=get_raw)
        except RequiredPathNotFoundError:
            self.modify(path, default)
            return default


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
        if isinstance(validator, (tuple, list, set, frozenset)):
            validator = OrderedDict((k, Any) for k in validator)
        elif not isinstance(validator, Mapping):
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


def _pydantic_validator[D: ABCConfigData](validator: type[BaseModel], cfg: ValidatorFactoryConfig) -> Callable[[D], D]:
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


class RequiredPath:
    """
    对需求的键进行存在检查、类型检查、填充默认值
    """

    def __init__[V: Any, D: ABCConfigData](
            self,
            validator: V,
            validator_factory: Optional[
                Callable[[V, ValidatorFactoryConfig], Callable[[D], D]] | ValidatorTypes | Literal["ignore", "pydantic"]
                ] = ValidatorTypes.DEFAULT,
            static_config: Optional[ValidatorFactoryConfig] = None
    ):
        """
        .. tip::
           提供static_config参数，可以避免在filter中反复调用validator_factory(filter配置一切都为默认值的前提下)

        :param validator: 数据验证器
        :type validator: Any
        :param validator_factory: 数据验证器工厂
        :type validator_factory:
            Optional[Callable[[Any, ValidatorFactoryConfig], Callable[[ABCConfigData], ABCConfigData] | ValidatorTypes
        :param static_config: 静态配置
        :type static_config: Optional[ValidatorFactoryConfig]
        """
        if not callable(validator_factory):
            validator_factory = ValidatorTypes(validator_factory)
        if isinstance(validator_factory, ValidatorTypes):
            validator_factory = self.ValidatorFactories[validator_factory]

        self._validator: Iterable[str] | Mapping[str, type] = deepcopy(validator)
        self._validator_factory: Callable[[V, ValidatorFactoryConfig], Callable[[D], D]] = validator_factory
        if static_config is not None:
            self._static_validator: Optional[Callable[[D], D]] = self._validator_factory(self._validator, static_config)
        else:
            self._static_validator = None

    ValidatorFactories: dict[
        ValidatorTypes,
        Callable[[Any, ValidatorFactoryConfig], Callable[[ABCConfigData], ABCConfigData]]
    ] = {
        ValidatorTypes.DEFAULT: DefaultValidatorFactory,
        ValidatorTypes.IGNORE: lambda v, *_: v,
        ValidatorTypes.PYDANTIC: _pydantic_validator,
    }

    def filter[D: ABCConfigData](
            self,
            data: D,
            *,
            allow_create: Optional[bool] = None,
            ignore_missing: Optional[bool] = None,
            **extra
    ) -> D:
        """
        检查过滤需求的键

        .. attention::
           返回的配置数据是*快照*

        .. caution::
           提供了任意配置参数(`allow_create`, `ignore_missing`, ...)时,这次调用将完全舍弃static_config使用当前提供的配置参数

           这会导致调用validator_factory产生额外开销(如果你提供static_config参数是为了避免反复调用validator_factory的话)

        :param data: 要过滤的原始数据
        :type data: ABCConfigData
        :param allow_create: 是否允许值不存在时修改data参数对象填充默认值(即使为False仍然会在结果中填充默认值,但不会修改data参数对象)
        :type allow_create: bool
        :param ignore_missing: 忽略丢失的键
        :type ignore_missing: bool
        :param extra: 额外参数
        :type extra: Any

        :return: 处理后的配置数据*快照*
        :rtype: ABCConfigData

        :raise ConfigDataTypeError: 配置数据类型错误
        :raise RequiredPathNotFoundError: 必要的键未找到
        :raise UnknownErrorDuringValidate: 验证过程中发生未知错误
        """
        config_kwargs = {}
        if allow_create is not None:
            config_kwargs["allow_create"] = allow_create
        if ignore_missing is not None:
            config_kwargs["ignore_missing"] = ignore_missing
        if extra:
            config_kwargs["extra"] = extra

        if (self._static_validator is None) or config_kwargs:
            config = ValidatorFactoryConfig(**config_kwargs)
            validator: Callable[[ABCConfigData], ABCConfigData] = self._validator_factory(self._validator, config)
        else:
            validator = self._static_validator

        return validator(data)


class ConfigFile(ABCConfigFile):
    """
    配置文件类
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

        return config_pool.SLProcessor[config_format].save(self, config_pool.root_path, namespace, file_name,
                                                           *processor_args, **processor_kwargs)

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
        ].load(cls, config_pool.root_path, namespace, file_name, *processor_args, **processor_kwargs)


class ConfigPool(ABCConfigPool):

    def __init__(self, root_path="./.config"):
        super().__init__(root_path)
        self._configs: dict[str, dict[str, ABCConfigFile]] = {}

    @override
    def get(self, namespace: str, file_name: Optional[str] = None) -> dict[str, ABCConfigFile] | ABCConfigFile | None:
        if namespace not in self._configs:
            return None
        result = self._configs[namespace]

        if file_name is None:
            return result

        if file_name in result:
            return result[file_name]

        return None

    @override
    def set(self, namespace: str, file_name: str, config: ABCConfigFile) -> None:
        if namespace not in self._configs:
            self._configs[namespace] = {}

        self._configs[namespace][file_name] = config

    @override
    def save_all(self, ignore_err: bool = False) -> None | dict[str, dict[str, tuple[ABCConfigFile, Exception]]]:
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
    def require(
            self,
            namespace: str,
            file_name: str,
            validator: Any,
            validator_factory: Any,
            *args, **kwargs
    ):
        return RequireConfigDecorator(
            self,
            namespace,
            file_name,
            RequiredPath(validator, validator_factory),
            *args,
            **kwargs
        )

    def __getitem__(self, item):
        return deepcopy(self.configs[item])

    @property
    def configs(self):
        return deepcopy(self._configs)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.configs!r})"


class RequireConfigDecorator:
    """
    配置获取器，可作装饰器使用
    """

    def __init__(
            self,
            config_pool: ABCConfigPool,
            namespace: str,
            raw_file_name: str,
            required: RequiredPath,
            *,
            config_cls: type[ABCConfigFile] = ConfigFile,
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
        :type required: RequiredPath
        :param config_format: 配置文件格式
        :type config_format: Optional[str]
        :param cache_config: 缓存配置的装饰器，默认为None，即不缓存
        :type cache_config: Optional[Callable[[Callable], Callable]]
        :param allow_create: 是否允许在文件不存在时新建文件
        :type allow_create: bool
        :param filter_kwargs: :py:func:`RequiredPath.filter` 要绑定的默认参数，默认为allow_create=True
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

        def _load_config(format_: str) -> ABCConfigFile:
            if format_ not in config_pool.SLProcessor:
                raise UnsupportedConfigFormatError(format_)

            result: ABCConfigFile | None = config_pool.get(namespace, raw_file_name)
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
            config: ABCConfigFile = ret
            break
        else:
            raise FailedProcessConfigFileError(errors)

        if filter_kwargs is None:
            filter_kwargs = {}

        self._config: ABCConfigFile = config
        self._required = required
        self._filter_kwargs = {"allow_create": True} | filter_kwargs
        self._cache_config: Callable = cache_config if cache_config is not None else lambda x: x

    def check(self, *, ignore_cache: bool = False, **filter_kwargs) -> Any:
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
        @wrapt.decorator
        def wrapper(wrapped, _instance, args, kwargs):
            config_data = self._wrapped_filter(**self._filter_kwargs)

            return wrapped(
                *(config_data, *args),
                **kwargs
            )

        return wrapper

    def _wrapped_filter(self, **kwargs):
        return self._cache_config(self._required.filter(self._config.data, **kwargs))

    def _function_processor(self, *args):
        return self._wrapped_filter(**self._filter_kwargs), *args

    def _method_processor(self, obj, *args):
        return obj, self._wrapped_filter(**self._filter_kwargs), *args


DefaultConfigPool = ConfigPool()
requireConfig = DefaultConfigPool.require
saveAll = DefaultConfigPool.save_all
getConfig = DefaultConfigPool.get
setConfig = DefaultConfigPool.set


class BaseConfigSL(ABCConfigSL, ABC):
    @override
    def register_to(self, config_pool: Optional[ABCSLProcessorPool] = None) -> None:
        """
        注册到配置池中

        :param config_pool: 配置池
        :type config_pool: Optional[ABCSLProcessorPool]
        """
        if config_pool is None:
            config_pool = DefaultConfigPool

        super().register_to(config_pool)


__all__ = (
    "AttrKey",
    "IndexKey",
    "Path",
    "PathSyntaxParser",
    "ConfigData",
    "ValidatorTypes",
    "ValidatorFactoryConfig",
    "RequiredPath",
    "ConfigFile",
    "ConfigPool",
    "RequireConfigDecorator",
    "BaseConfigSL",

    "DefaultConfigPool",
    "requireConfig",
)
