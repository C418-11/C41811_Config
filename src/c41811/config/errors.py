# cython: language_level = 3  # noqa: ERA001


"""错误类"""

from collections import OrderedDict
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Never
from typing import Self
from typing import cast
from typing import override

from .abc import ABCPath
from .abc import AnyKey


class DependencyNotInstalledError(ImportError):
    """可选功能依赖缺失"""

    def __init__(self, dep_name: str):
        """
        :param dep_name: 依赖名称
        :type dep_name: str
        """  # noqa: D205
        self.dep_name = dep_name
        super().__init__(f"{dep_name} is not installed. Please install it with `pip install {dep_name}`")


class UnavailableAttribute:
    """占位代理对象，在任意访问时抛出异常"""  # noqa: RUF002

    __slots__ = ("_exception", "_name")

    def __init__(self, name: str, exception: DependencyNotInstalledError):
        """
        :param name: 属性名
        :type name: str
        :param exception: 抛出的异常
        :type exception: DependencyNotInstalledError
        """  # noqa: D205
        self._name = name
        self._exception = exception

    def __getattr__(self, name: str) -> Never:
        raise self._exception

    def __call__(self, *args: Any, **kwargs: Any) -> Never:  # noqa: ARG002, D102
        raise self._exception

    @override
    def __repr__(self) -> str:
        return f"<UnavailableAttribute {self._name} due to {self._exception}>"


@dataclass
class TokenInfo:
    """一段标记的相关信息 用于快速定位到指定标记"""

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
        """标记的原始字符串"""
        return "".join(self.tokens)


class ConfigDataPathSyntaxException(Exception):  # noqa: N818
    """配置数据检索路径语法错误"""

    msg: str

    def __init__(self, token_info: TokenInfo, msg: str | None = None):
        """
        :param token_info: token相关信息
        :type token_info: TokenInfo
        :param msg: 错误信息
        :type msg: str | None

        .. tip::
           错误信息获取优先级

           1.msg参数

           2.类字段msg (供快速创建子类)

        .. versionchanged:: 0.3.0
           现在传入的错误消息不再软要求带冒号
        """  # noqa: D205
        self.token_info = token_info

        if msg is not None:
            self.msg = msg
        elif not hasattr(self, "msg"):
            self.msg = "Configuration data path syntax error"

    @override
    def __str__(self) -> str:
        return (
            f"{self.msg}: "
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

    msg = "Unknown token type"


class ConfigOperate(Enum):
    """对配置的操作类型"""

    Delete = "Delete"
    Read = "Read"
    Write = "Write"
    Unknown = None


@dataclass
class KeyInfo[K: AnyKey]:
    """一段路径的相关信息 用于快速定位到指定键"""

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
        """从根到当前键的相对路径"""
        return self.path[: self.index]


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
        """  # noqa: D205
        self.key_info = key_info
        self.operate = ConfigOperate(operate)

    @override
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

    def __init__(self, msg: str | None = None):
        """
        :param msg: 错误信息
        :type msg: str | None
        """  # noqa: D205
        if msg is None:
            msg = "ConfigData is read-only"
        super().__init__(msg)


class ConfigDataTypeError(ValueError):
    """配置数据类型错误"""

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
        """  # noqa: D205
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
        :type key_info: KeyInfo[Any]
        """  # noqa: D205
        self.key_info = key_info

    @override
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
        """  # noqa: D205
        super().__init__(f"Args: {args}, Kwargs: {kwargs}")


class UnsupportedConfigFormatError(Exception):
    """
    不支持的配置文件格式错误

    .. note::
       :py:attr:`format` 可以为 :py:const:`None` 这表示 `未指定配置格式` 。
       在一些情况下 :py:const:`None` 是有效的配置格式，如表示 `默认` 。
       此错误以 :py:const:`None` 为参数抛出时表示 `我找到了配置格式None，但是我不支持None作为配置格式`
    """  # noqa: RUF002

    def __init__(self, _format: str | None):
        """
        :param _format: 不支持的配置的文件格式
        :type _format: str | None

        .. versionchanged:: 0.3.0
           重命名参数 ``format_`` 为 ``_format``
           更改 ``_format`` 参数类型为 ``str | None``
        """  # noqa: D205
        self._format = _format

    @property
    def format(self) -> str | None:
        """不支持的配置的文件格式"""
        return self._format

    @override
    def __str__(self) -> str:
        if self.format is None:
            return "Unspecified config format"
        return f"Unsupported config format: {self._format}"

    @override
    def __eq__(self, other: Any) -> bool:
        return isinstance(other, type(self)) and self._format == other._format

    @override
    def __hash__(self) -> int:
        """.. versionadded:: 0.3.0"""
        return hash(self._format)


class FailedProcessConfigFileError[E: BaseException](BaseExceptionGroup, Exception):
    """
    SL处理器无法正确处理当前配置文件

    .. versionchanged:: 0.1.4
       现在继承自BaseExceptionGroup
    """

    reasons: tuple[E, ...] | OrderedDict[str, E]

    @staticmethod
    def __new__(cls, reason: E | Iterable[E] | Mapping[str, E], msg: str = "Failed to process config file") -> Self:
        """
        :param reason: 处理配置文件失败的原因
        :type reason: E | Iterable[E] | Mapping[str, E]
        :param msg: 提示信息
        :type msg: str
        """  # noqa: D205
        reasons: tuple[E, ...] | OrderedDict[str, E]
        message: str
        exceptions: tuple[E, ...]
        if isinstance(reason, Mapping):
            reasons = OrderedDict(reason)
            message = "\n".join((msg, *(f"{k}: {v}" for k, v in reason.items())))
            exceptions = tuple(reason.values())
        elif isinstance(reason, Iterable):
            reasons = tuple(cast(Iterable[E], reason))
            message = "\n".join((msg, *map(str, reason)))
            exceptions = tuple(cast(Iterable[E], reason))
        else:
            reason: E  # type: ignore[no-redef]
            reasons = (reason,)
            message = f"{msg}: {reason}"
            exceptions = reasons

        obj = super().__new__(cls, message, exceptions)
        obj.reasons = reasons
        return obj


class ComponentMemberMismatchError(LookupError):
    """
    组件成员元数据与成员不匹配错误

    .. versionadded:: 0.3.0
    """

    def __init__(self, missing: set[str], redundant: set[str]):
        """
        :param missing: 缺少的成员
        :type missing: set[str]
        :param redundant: 冗余的成员
        :type redundant: set[str]
        """  # noqa: D205
        self.missing = missing
        self.redundant = redundant

    @override
    def __str__(self) -> str:
        msg = "Component member metadata does not match members"
        if self.missing:
            msg += f", Missing members: {self.missing}"
        if self.redundant:
            msg += f", Redundant members: {self.redundant}"
        return msg


__all__ = (
    "ComponentMemberMismatchError",
    "ConfigDataPathSyntaxException",
    "ConfigDataReadOnlyError",
    "ConfigDataTypeError",
    "ConfigOperate",
    "CyclicReferenceError",
    "DependencyNotInstalledError",
    "FailedProcessConfigFileError",
    "KeyInfo",
    "RequiredPathNotFoundError",
    "TokenInfo",
    "UnavailableAttribute",
    "UnknownErrorDuringValidateError",
    "UnknownTokenTypeError",
    "UnsupportedConfigFormatError",
)
