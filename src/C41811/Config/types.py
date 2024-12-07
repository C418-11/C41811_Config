# -*- coding: utf-8 -*-
# cython: language_level = 3


from dataclasses import dataclass

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
    def raw_string(self):
        return ''.join(self.tokens)


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


__all__ = ("TokenInfo", "KeyInfo")
