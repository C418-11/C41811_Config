# -*- coding: utf-8 -*-


from pytest import mark

from C41811.Config.types import TokenInfo


class TestTokenInfo:
    @staticmethod
    @mark.parametrize("info, raw_string", (
            (TokenInfo(["a", "b", "c"], "c", 2), "abc"),
            (TokenInfo(["ab", "c"], "c", 1), "abc"),
            (TokenInfo(["a", "bc"], "c", 1), "abc")
    ))
    def test_raw_string_attr(info, raw_string):
        assert info.raw_string == raw_string
