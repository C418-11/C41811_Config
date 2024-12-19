# -*- coding: utf-8 -*-
# cython: language_level = 3


from collections import OrderedDict
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from .abc import ABCKey
from .abc import ABCPath


@dataclass
class TokenInfo:
    tokens: list[str]
    """
    当前完整token列表
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
    def raw_string(self):  # pragma: no cover
        return ''.join(self.tokens)


class ConfigDataPathSyntaxException(Exception):
    """
    配置数据检索路径语法错误
    """

    def __init__(self, token_info: TokenInfo, msg: str = None):
        """
        :param token_info: token相关信息
        :type token_info: TokenInfo
        :param msg: 错误信息
        :type msg: str
        """
        self.token_info = token_info

        if not (msg is None and hasattr(self, "msg")):
            self.msg = msg

    def __str__(self):  # pragma: no cover
        return (
            f"{self.msg}"
            f"{self.token_info.raw_string} -> {self.token_info.current_token}"
            f" ({self.token_info.index + 1} / {len(self.token_info.tokens)})"
        )


class UnknownTokenType(ConfigDataPathSyntaxException):
    """
    未知的键类型
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
class KeyInfo:
    path: ABCPath
    """
    当前完整路径
    """
    current_key: ABCKey
    """
    当前键
    """
    index: int
    """
    current_key在full_path的下标
    """

    @property
    def relative_keys(self) -> list[ABCKey]:
        return self.path[:self.index]


class RequiredPathNotFoundError(KeyError):
    """
    需求的键未找到错误
    """

    def __init__(
            self,
            key_info: KeyInfo,
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

    def __str__(self):  # pragma: no cover
        string = (
            f"{self.key_info.path.unparse()} -> {self.key_info.current_key.unparse()}"
            f" ({self.key_info.index + 1} / {len(self.key_info.path)})"
        )
        if self.operate.value is not ConfigOperate.Unknown:
            string += f" Operate: {self.operate.value}"
        return string


class ConfigDataTypeError(ValueError):
    """
    配置数据类型错误
    """

    def __init__(
            self,
            key_info: KeyInfo,
            required_type: type[object],
            now_type: type[object],
    ):
        """
        :param key_info: 键相关信息
        :type key_info: KeyInfo
        :param required_type: 该键需求的数据类型
        :type required_type: type[object]
        :param now_type: 当前键的数据类型
        :type now_type: type[object]
        """
        self.key_info = key_info
        self.requited_type = required_type
        self.now_type = now_type

    def __str__(self):  # pragma: no cover
        return (
            f"{self.key_info.path.unparse()} -> {self.key_info.current_key.unparse()}"
            f" ({self.key_info.index + 1} / {len(self.key_info.relative_keys)})"
            f" Must be '{self.requited_type}'"
            f", Not '{self.now_type}'"
        )


class UnknownErrorDuringValidate(Exception):
    """
    在验证配置数据时发生未知错误
    """

    def __init__(self, *args, **kwargs):  # pragma: no cover
        """
        :param args: 未知错误信息
        :param kwargs: 未知错误信息
        """
        super().__init__(f"Args: {args}, Kwargs: {kwargs}")


class UnsupportedConfigFormatError(Exception):
    """
    不支持的配置文件格式错误
    """

    def __init__(self, _format: str):
        """
        :param _format: 不支持的配置的文件格式
        :type _format: str
        """
        super().__init__(f"Unsupported config format: {_format}")
        self.format = _format

    def __eq__(self, other):
        return isinstance(other, UnsupportedConfigFormatError) and self.format == other.format


class FailedProcessConfigFileError(Exception):
    """
    SL处理器无法正确处理当前配置文件
    """

    def __init__(
            self,
            reason: BaseException | Iterable[BaseException] | Mapping[str, BaseException],
            msg: str = "Failed to process config file"
    ):
        """
        :param reason: 处理配置文件失败的原因
        :type reason: BaseException | Iterable[BaseException] | Mapping[str, BaseException]
        """

        if isinstance(reason, Mapping):
            reason = OrderedDict(reason)
            super().__init__('\n'.join((
                msg,
                *map(lambda _: f"{_[0]}: {_[1]}", reason.items()))
            ))
        elif isinstance(reason, Iterable):  # pragma: no cover
            reason = tuple(reason)
            super().__init__('\n'.join((
                msg,
                *map(str, reason))
            ))
        else:
            reason = (reason,)
            super().__init__(f"{msg}: {reason}")

        self.reasons: tuple[BaseException] | OrderedDict[str, BaseException] = reason


__all__ = (
    "TokenInfo",
    "ConfigDataPathSyntaxException",
    "UnknownTokenType",
    "ConfigOperate",
    "KeyInfo",
    "RequiredPathNotFoundError",
    "ConfigDataTypeError",
    "UnsupportedConfigFormatError",
    "FailedProcessConfigFileError",
    "UnknownErrorDuringValidate"
)
