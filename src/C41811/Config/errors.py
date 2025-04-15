# -*- coding: utf-8 -*-
# cython: language_level = 3


from collections import OrderedDict
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Optional
from typing import Self
from typing import cast

from .abc import ABCPath
from .abc import AnyKey


@dataclass
class TokenInfo:
    """
    一段标记的相关信息 用于快速定位到指定标记
    """
    tokens: tuple[str, ...]
    """
    当前完整标记列表
    """
    current_token: str
    """
    当前标记
    """
    index: int
    """
    current_token在tokens的下标
    """

    @property
    def raw_string(self) -> str:
        return ''.join(self.tokens)


class ConfigDataPathSyntaxException(Exception):
    """
    配置数据检索路径语法错误
    """

    def __init__(self, token_info: TokenInfo, msg: Optional[str] = None):
        """
        :param token_info: token相关信息
        :type token_info: TokenInfo
        :param msg: 错误信息
        :type msg: Optional[str]

        .. tip::
           错误信息获取优先级

           1.msg参数

           2.类字段msg (供快速创建子类)
        """
        self.token_info = token_info

        if not (msg is None and hasattr(self, "msg")):
            self.msg = msg

    def __str__(self) -> str:
        return (
            f"{self.msg}"
            f"{self.token_info.raw_string} -> {self.token_info.current_token}"
            f" ({self.token_info.index + 1} / {len(self.token_info.tokens)})"
        )


class UnknownTokenTypeError(ConfigDataPathSyntaxException):
    # noinspection GrazieInspection
    """
    未知的标志类型

    .. versionchanged:: 0.1.3
       重命名 ``UnknownTokenType`` 为 ``UnknownTokenTypeError``
    """

    msg = "Unknown token type: "


class ConfigOperate(Enum):
    """
    对配置的操作类型
    """
    Delete = "Delete"
    Read = "Read"
    Write = "Write"
    Unknown = None


@dataclass
class KeyInfo[K: AnyKey]:
    """
    一段路径的相关信息 用于快速定位到指定键
    """
    path: ABCPath[K]
    """
    当前完整路径
    """
    current_key: K
    """
    当前键
    """
    index: int
    """
    current_key在path的下标
    """

    @property
    def relative_keys(self) -> Iterable[K]:
        return self.path[:self.index]


class RequiredPathNotFoundError(LookupError):
    """
    需求的键未找到错误

    .. versionchanged:: 0.1.5
       现在继承自LookupError
    """

    def __init__(
            self,
            key_info: KeyInfo[Any],
            operate: ConfigOperate = ConfigOperate.Unknown,
    ):
        """
        :param key_info: 键相关信息
        :type key_info: KeyInfo
        :param operate: 何种操作过程中发生的该错误
        :type operate: ConfigOperate
        """
        self.key_info = key_info
        self.operate = ConfigOperate(operate)

    def __str__(self) -> str:
        string = (
            f"{self.key_info.path.unparse()} -> {self.key_info.current_key.unparse()}"
            f" ({self.key_info.index + 1} / {len(self.key_info.path)})"
        )
        if self.operate.value is not ConfigOperate.Unknown:
            string += f" Operate: {self.operate.value}"
        return string


class ConfigDataReadOnlyError(TypeError):
    """
    配置数据为只读

    .. versionadded:: 0.1.3
    """

    def __init__(self, msg: Optional[str] = None):
        """
        :param msg: 错误信息
        :type msg: Optional[str]
        """
        if msg is None:
            msg = "ConfigData is read-only"
        super().__init__(msg)


class ConfigDataTypeError(ValueError):
    """
    配置数据类型错误
    """

    def __init__(
            self,
            key_info: KeyInfo[Any],
            required_type: tuple[type, ...] | type,
            current_type: type,
    ):
        """
        :param key_info: 键相关信息
        :type key_info: KeyInfo
        :param required_type: 该键需求的数据类型
        :type required_type: tuple[type, ...] | type
        :param current_type: 当前键的数据类型
        :type current_type: type

        .. versionchanged:: 0.1.4
           ``required_type`` 支持传入多个需求的数据类型

        .. versionchanged:: 0.2.0
           重命名参数 ``now_type`` 为 ``current_type``
        """
        if isinstance(required_type, Sequence) and (len(required_type) == 1):
            required_type = required_type[0]

        self.key_info = key_info
        self.requited_type = required_type
        self.current_type = current_type

        super().__init__(
            f"{self.key_info.path.unparse()} -> {self.key_info.current_key.unparse()}"
            f" ({self.key_info.index + 1} / {len(self.key_info.path)})"
            f" Must be '{self.requited_type}'"
            f", Not '{self.current_type}'"
        )


class CyclicReferenceError(ValueError):
    """
    配置数据存在循环引用错误

    .. versionadded:: 0.2.0
    """

    def __init__(self, key_info: KeyInfo[Any]):
        """
        :param key_info: 检测到循环引用的键信息
        """
        self.key_info = key_info

    def __str__(self) -> str:
        return (
            f"Cyclic reference detected at {self.key_info.path.unparse()} -> {self.key_info.current_key.unparse()}"
            f" ({self.key_info.index + 1}/{len(self.key_info.path)})"
        )


class UnknownErrorDuringValidateError(Exception):
    # noinspection GrazieInspection
    """
    在验证配置数据时发生未知错误

    .. versionchanged:: 0.1.3
       重命名 ``UnknownErrorDuringValidate`` 为 ``UnknownErrorDuringValidateError``
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """
        :param args: 未知错误信息
        :param kwargs: 未知错误信息
        """
        super().__init__(f"Args: {args}, Kwargs: {kwargs}")


class UnsupportedConfigFormatError(Exception):
    """
    不支持的配置文件格式错误
    """

    def __init__(self, format_: str):
        """
        :param format_: 不支持的配置的文件格式
        :type format_: str
        """
        super().__init__(f"Unsupported config format: {format_}")
        self.format = format_

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, UnsupportedConfigFormatError) and self.format == other.format


class FailedProcessConfigFileError[E: BaseException](BaseExceptionGroup, Exception):
    """
    SL处理器无法正确处理当前配置文件

    .. versionchanged:: 0.1.4
       现在继承自BaseExceptionGroup
    """

    reasons: tuple[E, ...] | OrderedDict[str, E]

    @staticmethod
    def __new__(
            cls,
            reason: E | Iterable[E] | Mapping[str, E],
            msg: str = "Failed to process config file"
    ) -> Self:
        """
        :param reason: 处理配置文件失败的原因
        :type reason: BaseException | Iterable[BaseException] | Mapping[str, BaseException]
        :param msg: 提示信息
        :type msg: str
        """

        reasons: tuple[E, ...] | OrderedDict[str, E]
        message: str
        exceptions: tuple[E, ...]
        if isinstance(reason, Mapping):
            reasons = OrderedDict(reason)
            message = '\n'.join((
                msg,
                *map(lambda _: f"{_[0]}: {_[1]}", reason.items())))
            exceptions = tuple(reason.values())
        elif isinstance(reason, Iterable):
            reasons = tuple(cast(Iterable[E], reason))
            message = '\n'.join((
                msg,
                *map(str, reason))
            )
            exceptions = tuple(cast(Iterable[E], reason))
        else:
            reason: E  # type: ignore[no-redef]
            reasons = (reason,)
            message = f"{msg}: {reason}"
            exceptions = reasons

        obj = super().__new__(
            cls,
            message,
            exceptions
        )
        obj.reasons = reasons
        return obj


__all__ = (
    "TokenInfo",
    "ConfigDataPathSyntaxException",
    "UnknownTokenTypeError",
    "ConfigOperate",
    "KeyInfo",
    "RequiredPathNotFoundError",
    "ConfigDataReadOnlyError",
    "ConfigDataTypeError",
    "CyclicReferenceError",
    "UnsupportedConfigFormatError",
    "FailedProcessConfigFileError",
    "UnknownErrorDuringValidateError"
)
