# -*- coding: utf-8 -*-
# cython: language_level = 3


from collections import OrderedDict
from enum import Enum
from typing import Iterable
from typing import Mapping


class ConfigOperate(Enum):
    """
    对配置的操作类型
    """
    Delete = "Delete"
    Read = "Read"
    Write = "Write"
    Unknown = None


class RequiredPathNotFoundError(KeyError):
    """
    需求的键未找到错误
    """

    def __init__(
            self,
            path: str,
            sep_char: str,
            current_key: str,
            index: int,
            operate: ConfigOperate = ConfigOperate.Unknown,
    ):
        """
        :param path: 完整键路径
        :type path: str
        :param sep_char: 键路径的分隔符
        :type sep_char: str
        :param current_key: 当前正在访问的键
        :type current_key: str
        :param index: 当前访问的键在完整键路径中的索引
        :type index: int
        :param operate: 何种操作过程中发生的该错误
        :type operate: ConfigOperate
        """
        super().__init__(current_key)

        self.path = path
        self.sep_char = sep_char
        self.current_key = current_key
        self.index = index
        self.operate = ConfigOperate(operate)

    def __str__(self):
        string = f"{self.path} -> {self.current_key} ({self.index + 1} / {len(self.path.split(self.sep_char))})"
        if self.operate.value is not ConfigOperate.Unknown:
            string += f" Operate: {self.operate.value}"
        return string


class ConfigDataTypeError(ValueError):
    """
    配置数据类型错误
    """

    def __init__(
            self,
            path: str,
            sep_char: str,
            current_key: str,
            index: int,
            required_type: type[object],
            now_type: type[object],
    ):
        """
        :param path: 完整键路径
        :type path: str
        :param sep_char: 键路径的分隔符
        :type sep_char: str
        :param current_key: 当前正在访问的键
        :type current_key: str
        :param index: 当前访问的键在完整键路径中的索引
        :type index: int
        :param required_type: 该键需求的数据类型
        :type required_type: type[object]
        :param now_type: 当前键的数据类型
        :type now_type: type[object]
        """
        super().__init__(current_key)

        self.path = path
        self.sep_char = sep_char
        self.current_key = current_key
        self.index = index
        self.requited_type = required_type
        self.now_type = now_type

        self.relative_key = self.sep_char.join(self.path.split(self.sep_char)[:self.index])

    def __str__(self):
        return (
            f"{self.path} -> {self.current_key} ({self.index + 1} / {len(self.path.split(self.sep_char))})"
            f" Must be '{self.requited_type}'"
            f", Not '{self.now_type}'"
        )


class UnknownErrorDuringValidate(Exception):
    """
    在验证配置数据时发生未知错误
    """

    def __init__(self, *args, **kwargs):
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
        elif isinstance(reason, Iterable):
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
    "ConfigOperate",
    "RequiredPathNotFoundError",
    "ConfigDataTypeError",
    "UnsupportedConfigFormatError",
    "FailedProcessConfigFileError",
    "UnknownErrorDuringValidate"
)
