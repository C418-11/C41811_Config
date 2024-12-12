# -*- coding: utf-8 -*-
# cython: language_level = 3


import warnings
from typing import Generator
from typing import Iterable
from typing import Optional
from typing import Self
from typing import override

from .abc import ABCKey
from .abc import ABCPath
from .abc import ABCPathSyntaxParser
from .errors import ConfigDataPathSyntaxException
from .errors import TokenInfo
from .errors import UnknownTokenType


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


__all__ = (
    "AttrKey",
    "IndexKey",
    "Path",
    "PathSyntaxParser",
)
