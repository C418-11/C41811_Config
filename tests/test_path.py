# -*- coding: utf-8 -*-


from copy import deepcopy

from pytest import fixture
from pytest import mark

from C41811.Config import AttrKey
from C41811.Config import IndexKey
from C41811.Config import Path
from C41811.Config import PathSyntaxParser
from C41811.Config.errors import ConfigDataPathSyntaxException
from C41811.Config.errors import UnknownTokenType
from utils import safe_raises
from utils import safe_warns


class TestKey:
    @staticmethod
    @mark.parametrize("key, other", (
            (IndexKey(0), 0),
            (IndexKey(99), 99),
            (AttrKey("aaa"), "aaa"),
            (AttrKey("bcd"), "bcd"),
    ))
    def test_both(key, other):
        assert key.key == other
        assert hash(key) == hash(other)
        assert str(key) == str(other)
        assert key == deepcopy(key)
        assert key != NotImplemented

    @staticmethod
    @mark.parametrize("key, other", (
            (AttrKey("aaa"), "aaa"),
            (AttrKey("bcd"), "bcd"),
    ))
    def test_attr_key(key, other):
        assert len(key) == len(other)
        assert key == other


class TestPath:
    @staticmethod
    @fixture
    def path():
        return Path.from_str(r"\.aaa\.bbb\.ccc\[0\]\.ddd\.eee\[1\]")

    @staticmethod
    @mark.parametrize("locate, keys, ignore_excs", (
            (["aaa", 0, "bbb"], [AttrKey("aaa"), IndexKey(0), AttrKey("bbb")], ()),
            ([2, "aaa"], [IndexKey(2), AttrKey("aaa")], ()),
            ([4, 2, "aaa"], [IndexKey(4), IndexKey(2), AttrKey("aaa")], ()),
            (["a", 1, None], None, (ValueError,)),
    ))
    def test_from_locate(locate, keys, ignore_excs):
        with safe_raises(ignore_excs) as info:
            path = Path.from_locate(locate)
        if not info:
            assert path == Path(keys)

    @staticmethod
    @mark.parametrize("index, value", (
            (0, AttrKey("aaa")),
            (1, AttrKey("bbb")),
            (2, AttrKey("ccc")),
            (3, IndexKey(0)),
            (4, AttrKey("ddd")),
            (5, AttrKey("eee")),
            (6, IndexKey(1)),
    ))
    def test_getitem(path, index, value):
        assert path[index] == value

    @staticmethod
    @mark.parametrize("key, is_contained", (
            (IndexKey(0), True),
            (IndexKey(1), True),
            (IndexKey(3), False),
            (AttrKey("aaa"), True),
            (AttrKey("bbb"), True),
            (AttrKey("ccc"), True),
            (AttrKey("ddd"), True),
            (AttrKey("eee"), True),
            (AttrKey("fff"), False),
    ))
    def test_contains(path, key, is_contained):
        assert (key in path) == is_contained

    @staticmethod
    @mark.parametrize("path, length", (
            (r"\.aaa", 1),
            (r"\[1\]\.ccc\[2\]", 3),
            (r"\.aaa\.bbb\.ccc\[0\]", 4),
            (r"\.aaa\.bbb\.ccc\[0\]\.ddd", 5),
            (r"\.aaa\.bbb\.ccc\[0\]\.ddd\.eee\[1\]\.fff", 8),
    ))
    def test_len(path, length):
        assert len(Path.from_str(path)) == length

    @staticmethod
    @mark.parametrize("path, keys", (
            (r"\.aaa", [AttrKey("aaa")]),
            (r"\[1\]\.ccc\[2\]", [IndexKey(1), AttrKey("ccc"), IndexKey(2)]),
            (r"\.aaa\.bbb\.ccc\[0\]", [AttrKey("aaa"), AttrKey("bbb"), AttrKey("ccc"), IndexKey(0)]),
            (r"\.aaa\.bbb\.ccc\[0\]\.ddd",
             [AttrKey("aaa"), AttrKey("bbb"), AttrKey("ccc"), IndexKey(0), AttrKey("ddd")]),
    ))
    def test_iter(path, keys):
        assert list(Path.from_str(path)) == keys

    @staticmethod
    @mark.parametrize("path", (
            r"\.aaa",
            r"\[1\]\.ccc\[2\]",
            r"\.aaa\.bbb\.ccc\[0\]",
            r"\.aaa\.bbb\.ccc\[0\]\.ddd",
    ))
    def test_eq(path):
        p = Path.from_str(path)
        assert p == deepcopy(p)
        assert p != NotImplemented


class TestPathSyntaxParser:
    @staticmethod
    @fixture
    def parser():
        return PathSyntaxParser()

    TokenizeTests = (
        "string, result, ignore_warns", (
            (
                r"\.a.a\\.a\.b\[c\]\[2\]\.e",
                [r"\.a.a\\.a", r"\.b", r"\[c", r"\]", r"\[2", r"\]", r"\.e"],
                ()
            ),
            (r"\[c\]\[d\]", [r"\[c", r"\]", r"\[d", r"\]"], ()),
            (r"\[c\]abc\[4\]", [r"\[c", r"\]", "abc", r"\[4", r"\]"], ()),
            (r"\[d\]abc", [r"\[d", r"\]", "abc"], ()),
            (r"abc\[e\]", ["abc", r"\[e", r"\]"], ()),
            ("abc", ["abc"], ()),
            (r"\.\a", [r"\.\a"], (SyntaxWarning,)),
            (r"\a\a", [r"\a\a"], (SyntaxWarning,)),
        )
    )

    @staticmethod
    @mark.parametrize(*TokenizeTests)
    def test_tokenize(parser, string, result, ignore_warns):
        with safe_warns(ignore_warns):
            tokenized = list(parser.tokenize(string))
        assert tokenized == result

    ParseTests = (
        "string, path_obj, ignore_excs, ignore_warns", (
            (
                r"\.a.a\\.a\.b\[18\]\[07\]\.e",
                [AttrKey(r"a.a\.a"), AttrKey('b'), IndexKey(18), IndexKey(7), AttrKey('e')],
                (), ()
            ),
            (r"\[2\]\[3\]", [IndexKey(2), IndexKey(3)], (), ()),
            (r"\[2\[3\]", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[2\]\.3\]", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[2\.3", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[2", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[a\]", None, (ValueError,), ()),
            (r"\.a\[2\]\.b\[3\]", [AttrKey('a'), IndexKey(2), AttrKey('b'), IndexKey(3)], (), ()),
            (r"\[4\]abc\[9\]", None, (UnknownTokenType,), ()),
            (r"\[5\]abc", None, (UnknownTokenType,), ()),
            (r"abc\[2\]", None, (UnknownTokenType,), ()),
            (r"abc", None, (UnknownTokenType,), ()),
            (r"\.\a", [AttrKey(r"\a")], (), (SyntaxWarning,)),
            (r"\a\a", None, (UnknownTokenType,), (SyntaxWarning,)),
        )
    )

    @staticmethod
    @mark.parametrize(*ParseTests)
    def test_parse(parser, string, path_obj, ignore_excs, ignore_warns):
        with safe_raises(ignore_excs) as e_info, safe_warns(ignore_warns):
            path = parser.parse(string)
        if not e_info:
            assert path == path_obj