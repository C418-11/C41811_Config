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
from typing import override

from .abc import ABCKey
from .abc import ABCPath
from .errors import ConfigDataPathSyntaxException
from .errors import TokenInfo
from .errors import UnknownTokenTypeError


class IndexMixin(ABCKey, ABC):
    """
    混入类，提供对Index操作的支持

    .. versionchanged:: 0.1.5
       从ItemMixin重命名为IndexMixin
    """

    @override
    def __get_inner_element__[T: Any](self, data: T) -> T:
        return data[self._key]

    @override
    def __set_inner_element__(self, data: Any, value: Any) -> None:
        data[self._key] = value

    @override
    def __delete_inner_element__(self, data: Any) -> None:
        del data[self._key]


class AttrKey(IndexMixin, ABCKey):
    """
    属性键
    """
    _key: str

    def __init__(self, key: str):
        """
        :param key: 键名
        :type key: str

        :raise TypeError: key不为str时抛出
        """
        if not isinstance(key, str):
            raise TypeError(f"key must be str, not {type(key).__name__}")
        super().__init__(key)

    @override
    def __contains_inner_element__(self, data: Mapping) -> bool:
        return self._key in data

    @override
    def __supports__(self, data: Any) -> tuple:
        return () if isinstance(data, Mapping) else (Mapping,)

    @override
    def __supports_modify__(self, data: Any) -> tuple:
        return () if isinstance(data, MutableMapping) else (MutableMapping,)

    @override
    def unparse(self) -> str:
        return f"\\.{self._key.replace('\\', "\\\\")}"

    def __len__(self):
        return len(self._key)

    def __eq__(self, other):
        if isinstance(other, str):
            return self._key == other
        return super().__eq__(other)

    def __hash__(self):
        return super().__hash__()


class IndexKey(IndexMixin, ABCKey):
    """
    下标键
    """
    _key: int

    def __init__(self, key: int):
        """
        :param key: 索引值
        :type key: int

        :raise TypeError: key不为int时抛出
        """
        if not isinstance(key, int):
            raise TypeError(f"key must be int, not {type(key).__name__}")
        super().__init__(key)

    @override
    def __contains_inner_element__(self, data: Sequence) -> bool:
        try:
            data[self._key]
        except IndexError:
            return False
        return True

    @override
    def __supports__(self, data: Any) -> tuple:
        return () if isinstance(data, Sequence) else (Sequence,)

    @override
    def __supports_modify__(self, data: Any) -> tuple:
        return () if isinstance(data, MutableSequence) else (MutableSequence,)

    @override
    def unparse(self) -> str:
        return f"\\[{self._key}\\]"


class Path(ABCPath):
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

    def to_locate(self) -> list[str | int]:
        """
        转换为列表

        .. versionadded:: 0.1.1
        """
        return [key.key for key in self._keys]

    @override
    def unparse(self) -> str:
        return ''.join(key.unparse() for key in self._keys)


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
        if not string.startswith((r"\.", r"\[")):
            string = rf"\.{string}"

        tokens: list[str] = ['']
        while string:
            string, sep, token = string.rpartition('\\')

            # 处理r"\\"防止转义
            if not token:
                token += tokens.pop()

            # 对不存在的转义进行警告
            elif sep and (token[0] not in {'.', '\\', '[', ']'}):
                def _count_backslash(s: str) -> int:
                    count = 1
                    while s and (s[-1] == '\\'):
                        count += 1
                        s = s[:-1]
                    return count

                # 检查这个转义符号是否已经被转义
                if _count_backslash(string) % 2:
                    warnings.warn(
                        rf"invalid escape sequence '\{token[0]}'",
                        SyntaxWarning
                    )

            # 连接不应单独存在的token
            index_safe = (len(tokens) > 0) and (len(tokens[-1]) > 1)
            if index_safe and (tokens[-1][1] not in {'.', '[', ']'}):
                token += tokens.pop()

            # 将r"\\]"后面紧随的字符单独切割出来
            if token.startswith(']') and token[1:]:
                tokens.append(token[1:])
                token = token[:1]

            tokens.append(sep + token)

        tokens.reverse()
        if tokens[-1] == '':
            tokens.pop()

        return tuple(tokens)

    @classmethod
    def parse(cls, string: str) -> list[ABCKey]:
        """
        解析字符串为键列表

        :param string: 待解析字符串
        :type string: str

        :return: 键列表
        :rtype: list[ABCKey]
        """
        path: list[ABCKey] = []
        item: Optional[str] = None

        tokenized_path = cls.tokenize(string)
        for i, token in enumerate(tokenized_path):
            if not token.startswith('\\'):
                raise UnknownTokenTypeError(TokenInfo(tokenized_path, token, i))

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

            raise UnknownTokenTypeError(TokenInfo(tokenized_path, token, i))

        if item:
            raise ConfigDataPathSyntaxException(
                TokenInfo(tokenized_path, tokenized_path[-1], len(tokenized_path) - 1),
                "'[' was never closed: "
            )

        return path


__all__ = (
    "AttrKey",
    "IndexKey",
    "Path",
    "PathSyntaxParser",
)
