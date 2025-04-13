# -*- coding: utf-8 -*-
# cython: language_level = 3


import warnings
from abc import ABC
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import MutableMapping
from collections.abc import MutableSequence
from collections.abc import Sequence
from functools import lru_cache
from typing import Any
from typing import Optional
from typing import Self
from typing import cast
from typing import override

from ._protocols import Indexed
from .abc import ABCKey
from .abc import ABCPath
from .errors import ConfigDataPathSyntaxException
from .errors import TokenInfo
from .errors import UnknownTokenTypeError


class IndexMixin[K, D: Indexed[Any, Any]](ABCKey[K, D], ABC):
    """
    混入类，提供对Index操作的支持

    .. versionchanged:: 0.1.5
       重命名 ``ItemMixin`` 为 ``IndexMixin``
    """

    @override
    def __get_inner_element__(self, data: D) -> D:
        return cast(D, data[self._key])

    @override
    def __set_inner_element__(self, data: D, value: Any) -> None:
        data[self._key] = value  # type: ignore[index]

    @override
    def __delete_inner_element__(self, data: D) -> None:
        del data[self._key]  # type: ignore[attr-defined]


class AttrKey(IndexMixin[str, Mapping[str, Any]], ABCKey[str, Mapping[str, Any]]):
    """
    属性键
    """
    _key: str

    def __init__(self, key: str, meta: Optional[str] = None):
        """
        :param key: 键名
        :type key: str
        :param meta: 元信息
        :type meta: Optional[str]

        :raise TypeError: key不为str时抛出
        """
        if not isinstance(key, str):
            raise TypeError(f"key must be str, not {type(key).__name__}")
        super().__init__(key, meta)

    @override
    def __contains_inner_element__(self, data: Mapping[Any, Any]) -> bool:
        return self._key in data

    @override
    def __supports__(self, data: Any) -> tuple[Any, ...]:
        return () if isinstance(data, Mapping) else (Mapping,)

    @override
    def __supports_modify__(self, data: Any) -> tuple[Any, ...]:
        return () if isinstance(data, MutableMapping) else (MutableMapping,)

    @override
    def unparse(self) -> str:
        meta = '' if self._meta is None else f"\\{{{self._meta.replace('\\', "\\\\")}\\}}"
        return f"{meta}\\.{self._key.replace('\\', "\\\\")}"

    def __len__(self) -> int:
        return len(self._key)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self._key == other
        return super().__eq__(other)

    def __hash__(self) -> int:
        return super().__hash__()


class IndexKey(IndexMixin[int, Sequence[Any]], ABCKey[int, Sequence[Any]]):
    """
    下标键
    """
    _key: int

    def __init__(self, key: int, meta: Optional[str] = None):
        """
        :param key: 索引值
        :type key: int
        :param meta: 元信息
        :type meta: Optional[str]

        :raise TypeError: key不为int时抛出
        """
        if not isinstance(key, int):
            raise TypeError(f"key must be int, not {type(key).__name__}")
        super().__init__(key, meta)

    @override
    def __contains_inner_element__(self, data: Sequence[Any]) -> bool:
        try:
            data[self._key]
        except IndexError:
            return False
        return True

    @override
    def __supports__(self, data: Any) -> tuple[Any, ...]:
        return () if isinstance(data, Sequence) else (Sequence,)

    @override
    def __supports_modify__(self, data: Any) -> tuple[Any, ...]:
        return () if isinstance(data, MutableSequence) else (MutableSequence,)

    @override
    def unparse(self) -> str:
        meta = '' if self._meta is None else f"\\{{{self._meta.replace('\\', "\\\\")}\\}}"
        return f"{meta}\\[{self._key}\\]"


class Path(ABCPath[AttrKey | IndexKey]):
    @classmethod
    def from_str(cls, string: str) -> Self:
        """
        从字符串解析路径

        :param string: 路径字符串
        :type string: str

        :return: 解析后的路径
        :rtype: Path
        """
        return cls(PathSyntaxParser.parse(string))

    @classmethod
    def from_locate(cls, locate: Iterable[str | int]) -> Self:
        """
        从列表解析路径

        :param locate: 键列表
        :type locate: Iterable[str | int]

        :return: 解析后的路径
        :rtype: Path
        """
        keys: list[AttrKey | IndexKey] = []
        for loc in locate:
            if isinstance(loc, int):
                keys.append(IndexKey(loc))
                continue
            if isinstance(loc, str):
                keys.append(AttrKey(loc))
                continue
            raise ValueError("locate element must be 'int' or 'str'")
        return cls(keys)

    def to_locate(self) -> list[str | int]:
        """
        转换为列表

        .. versionadded:: 0.1.1
        """
        return [key.key for key in self._keys]

    @override
    def unparse(self) -> str:
        return ''.join(key.unparse() for key in self._keys)


def _count_backslash(s: str) -> int:
    count = 1
    while s and (s[-1] == '\\'):
        count += 1
        s = s[:-1]
    return count


class PathSyntaxParser:
    """
    路径语法解析器
    """

    @staticmethod
    @lru_cache
    def tokenize(string: str) -> tuple[str, ...]:
        # noinspection GrazieInspection
        r"""
        将字符串分词为以\开头的有意义片段

        .. note::
           可以省略字符串开头的 ``\.``

           例如：

           ``r"\.first\.second\.third“``

           可以简写为

           ``r"first\.second\.third"``

        :param string: 待分词字符串
        :type string: str

        :return: 分词结果
        :rtype: tuple[str, ...]

        .. versionchanged:: 0.1.4
           允许省略字符串开头的 ``\.``

           更改返回值类型为 ``tuple[str, ...]``

           添加缓存
        """
        # 开头默认为AttrKey
        if not string.startswith((r"\.", r"\[", r"\{")):
            string = rf"\.{string}"

        tokens: list[str] = ['']
        while string:
            string, sep, token = string.rpartition('\\')

            # 处理r"\\"防止转义
            if not token:
                token += tokens.pop()

            # 对不存在的转义进行警告
            elif sep and (token[0] not in {'.', '\\', '[', ']', '{', '}'}):
                # 检查这个转义符号是否已经被转义
                if _count_backslash(string) % 2:
                    warnings.warn(
                        rf"invalid escape sequence '\{token[0]}'",
                        SyntaxWarning
                    )

            # 连接不应单独存在的token
            index_safe = (len(tokens) > 0) and (len(tokens[-1]) > 1)
            if index_safe and (tokens[-1][1] not in {'.', '[', ']', '{', '}'}):
                token += tokens.pop()

            # 将r"\]"，r"\}"后面紧随的字符单独切割出来
            if token.startswith((']', '}')) and token[1:]:
                tokens.append(token[1:])
                token = token[:1]

            tokens.append(sep + token)

        tokens.reverse()
        if tokens[-1] == '':
            tokens.pop()

        return tuple(tokens)

    @classmethod
    def parse(cls, string: str) -> list[AttrKey | IndexKey]:  # noqa: C901 (ignore complexity)
        """
        解析字符串为键列表

        :param string: 待解析字符串
        :type string: str

        :return: 键列表
        :rtype: list[ABCKey]
        """
        path: list[AttrKey | IndexKey] = []
        item: None | str = None
        meta: None | str = None
        token_stack: list[str] = []

        tokenized_path = cls.tokenize(string)
        for i, token in enumerate(tokenized_path):
            if not token.startswith('\\'):
                raise UnknownTokenTypeError(TokenInfo(tokenized_path, token, i))

            token_type = token[1]
            content = token[2:].replace("\\\\", '\\')

            def _token_closed(tk_typ: str, tk_close: str) -> None:
                try:
                    top = token_stack.pop()
                except IndexError:
                    raise ConfigDataPathSyntaxException(
                        TokenInfo(tokenized_path, token, i),
                        f"unmatched '{tk_close}': "
                    ) from None
                if top != tk_typ:
                    raise ConfigDataPathSyntaxException(
                        TokenInfo(tokenized_path, token, i),
                        f"closing parenthesis '{tk_close}' does not match opening parenthesis '{top}': "
                    )

            if token_type == '}':
                _token_closed('{', '}')
                continue
            if token_type == ']':
                _token_closed('[', ']')
                try:
                    path.append(IndexKey(int(cast(str, item)), meta))
                except ValueError:
                    raise ValueError("index key must be int")
                item = None
                meta = None
                continue

            if token_stack:
                raise ConfigDataPathSyntaxException(
                    TokenInfo(tokenized_path, token, i),
                    f"'{token_stack.pop()}' was never closed: "
                )

            if token_type == '[':
                token_stack.append('[')
                item = content
                continue
            if token_type == '{':
                token_stack.append('{')
                meta = content
                continue
            if token_type == '.':
                path.append(AttrKey(content, meta))
                meta = None
                continue

            raise UnknownTokenTypeError(TokenInfo(tokenized_path, token, i))

        if token_stack:
            raise ConfigDataPathSyntaxException(
                TokenInfo(tokenized_path, tokenized_path[-1], len(tokenized_path) - 1),
                f"'{token_stack.pop()}' was never closed: "
            )

        return path


__all__ = (
    "AttrKey",
    "IndexKey",
    "Path",
    "PathSyntaxParser",
)
