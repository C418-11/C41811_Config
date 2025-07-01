from copy import deepcopy
from typing import Any

from pytest import fixture
from pytest import mark
from pytest import raises
from utils import EE
from utils import EW
from utils import safe_raises
from utils import safe_warns

from C41811.Config import AttrKey
from C41811.Config import IndexKey
from C41811.Config import Path
from C41811.Config import PathSyntaxParser
from C41811.Config.abc import AnyKey
from C41811.Config.errors import ConfigDataPathSyntaxException
from C41811.Config.errors import UnknownTokenTypeError


class TestKey:
    @staticmethod
    @mark.parametrize(
        "key, other",
        (
            (IndexKey(0), 0),
            (IndexKey(99), 99),
            (AttrKey("aaa"), "aaa"),
            (AttrKey("bcd"), "bcd"),
            (AttrKey(r"z\\z"), r"z\\z"),
        ),
    )
    def test_both(key: AnyKey, other: Any) -> None:
        assert key.key == other
        assert hash(key) != hash(other)
        assert str(key) == str(other)
        assert key == deepcopy(key)
        assert key != NotImplemented
        assert key == PathSyntaxParser.parse(key.unparse())[0]
        with raises(TypeError, match="key must be "):
            type(key)(NotImplemented)

        assert str(key.key) in str(key)
        assert str(key.key) in repr(key)

    @staticmethod
    @mark.parametrize(
        "key, meta",
        (
            (IndexKey(0, "meta data"), "meta data"),
            (AttrKey("uhh", "abcde"), "abcde"),
        ),
    )
    def test_meta(key: AnyKey, meta: str) -> None:
        assert key.meta == meta
        with raises(AttributeError):
            # noinspection PyPropertyAccess
            key.meta = None  # type: ignore[misc]

    @staticmethod
    @mark.parametrize(
        "key, other",
        (
            (AttrKey("aaa"), "aaa"),
            (AttrKey("bcd"), "bcd"),
            (AttrKey(r"z\\z"), r"z\\z"),
        ),
    )
    def test_attr_key(key: AttrKey, other: str) -> None:
        assert len(key) == len(other)
        assert key == other


class TestPath:
    @staticmethod
    @fixture
    def path() -> Path:
        return Path.from_str(r"\.aaa\.bbb\{attr meta\}\.ccc\{index meta\}\[0\]\.ddd\.eee\[1\]")

    @staticmethod
    @mark.parametrize(
        "string",
        (
            r"\.aaa\.bbb\.ccc\[0\]\.ddd\.eee\[1\]",
            r"\.aaa\.bbb\.ccc\[0\]\.ddd\.eee\[1\]",
            r"\{meta a\}\.aaa\{meta b\}\.bbb\.ccc\{meta index\}\[0\]\.ddd\.eee\[1\]",
            r"\.a\[2\]\.b\[3\]",
            r"\.a.a\\.a\.b\[18\]\[7\]\.e",
            r"\[2\]\[3\]",
        ),
    )
    def test_string(string: str) -> None:
        assert string == Path.from_str(string).unparse()

    @staticmethod
    @mark.parametrize(
        "locate, keys, ignore_excs",
        (
            (["aaa", 0, "bbb"], [AttrKey("aaa"), IndexKey(0), AttrKey("bbb")], ()),
            ([2, "aaa"], [IndexKey(2), AttrKey("aaa")], ()),
            ([4, 2, "aaa"], [IndexKey(4), IndexKey(2), AttrKey("aaa")], ()),
            (["a", 1, None], None, (ValueError,)),
        ),
    )
    def test_locate(locate: list[Any], keys: list[AttrKey | IndexKey], ignore_excs: EE) -> None:
        with safe_raises(ignore_excs) as info:
            path = Path.from_locate(locate)
        if not info:
            assert path == Path(keys)
            assert path == path.from_locate(path.to_locate())

    @staticmethod
    @mark.parametrize(
        "path, keys",
        (
            (Path.from_locate(["aaa", 0, "bbb"]), (AttrKey("aaa"), IndexKey(0), AttrKey("bbb"))),
            (Path.from_locate([2, "aaa"]), (IndexKey(2), AttrKey("aaa"))),
            (Path.from_locate([4, 2, "aaa"]), (IndexKey(4), IndexKey(2), AttrKey("aaa"))),
        ),
    )
    def test_keys(path: Path, keys: tuple[AttrKey | IndexKey, ...]) -> None:
        assert path.keys == keys

    @staticmethod
    @mark.parametrize(
        "index, value",
        (
            (0, AttrKey("aaa")),
            (1, AttrKey("bbb")),
            (2, AttrKey("ccc", "attr meta")),
            (3, IndexKey(0, "index meta")),
            (4, AttrKey("ddd")),
            (5, AttrKey("eee")),
            (6, IndexKey(1)),
        ),
    )
    def test_getitem(path: Path, index: int, value: AnyKey) -> None:
        assert path[index] == value

    @staticmethod
    @mark.parametrize(
        "key, is_contained",
        (
            (IndexKey(0), False),
            (IndexKey(0, "index meta"), True),
            (IndexKey(1), True),
            (IndexKey(3), False),
            (AttrKey("aaa"), True),
            (AttrKey("bbb"), True),
            (AttrKey("ccc"), False),
            (AttrKey("ccc", "attr meta"), True),
            (AttrKey("ddd"), True),
            (AttrKey("eee"), True),
            (AttrKey("fff"), False),
        ),
    )
    def test_contains(path: Path, key: AnyKey, is_contained: bool) -> None:  # noqa: FBT001
        assert (key in path) == is_contained

    @staticmethod
    @mark.parametrize(
        "path, length",
        (
            (r"\.aaa", 1),
            (r"aaa", 1),
            (r"\[1\]\.ccc\[2\]", 3),
            (r"\.aaa\.bbb\.ccc\[0\]", 4),
            (r"\.aaa\.bbb\.ccc\[0\]\.ddd", 5),
            (r"\.aaa\.bbb\.ccc\{meta\}\[0\]\{meta\}\.ddd", 5),
            (r"\.aaa\.bbb\.ccc\[0\]\.ddd\.eee\[1\]\.fff", 8),
        ),
    )
    def test_len(path: str, length: int) -> None:
        assert len(Path.from_str(path)) == length

    @staticmethod
    @mark.parametrize(
        "path, keys",
        (
            (r"\.aaa", [AttrKey("aaa")]),
            (r"aaa", [AttrKey("aaa")]),
            (r"\{meta\}\.aaa\{meta\}\[0\]", [AttrKey("aaa", "meta"), IndexKey(0, "meta")]),
            (r"\[1\]\.ccc\[2\]", [IndexKey(1), AttrKey("ccc"), IndexKey(2)]),
            (r"\.aaa\.bbb\.ccc\[0\]", [AttrKey("aaa"), AttrKey("bbb"), AttrKey("ccc"), IndexKey(0)]),
            (
                r"\.aaa\.bbb\.ccc\[0\]\.ddd",
                [AttrKey("aaa"), AttrKey("bbb"), AttrKey("ccc"), IndexKey(0), AttrKey("ddd")],
            ),
        ),
    )
    def test_iter(path: str, keys: list[AnyKey]) -> None:
        assert list(Path.from_str(path)) == keys

    @staticmethod
    @mark.parametrize(
        "path",
        (
            r"\.aaa",
            r"aaa",
            r"\{meta\}\.aaa\{meta\}\[0\]"
            r"\[1\]\.ccc\[2\]",
            r"\.aaa\.bbb\.ccc\[0\]",
            r"\.aaa\.bbb\.ccc\[0\]\.ddd",
        ),
    )
    def test_eq(path: str) -> None:
        p = Path.from_str(path)
        assert p == deepcopy(p)
        assert p != NotImplemented

    @staticmethod
    @mark.parametrize(
        "path",
        (
            r"\.aaa",
            r"aaa",
            r"\{meta\}\.aaa\{meta\}\[0\]"
            r"\[1\]\.ccc\[2\]",
            r"\.aaa\.bbb\.ccc\[0\]",
            r"\.aaa\.bbb\.ccc\[0\]\.ddd",
        ),
    )
    def test_repr(path: str) -> None:
        keys = PathSyntaxParser.parse(path)
        assert repr(keys)[1:-1] in repr(Path(keys))


class TestPathSyntaxParser:
    @staticmethod
    @fixture
    def parser() -> PathSyntaxParser:
        return PathSyntaxParser()

    @staticmethod
    @fixture(autouse=True, scope="function")
    def _clear_cache() -> None:
        PathSyntaxParser.tokenize.cache_clear()

    TokenizeTests: tuple[str, tuple[tuple[str, list[str], EW], ...]] = (
        "string, result, ignore_warns",
        (
            (r"\.a.a\\.a\.b\[c\]\[2\]\.e", [r"\.a.a\\.a", r"\.b", r"\[c", r"\]", r"\[2", r"\]", r"\.e"], ()),
            (r"\\\\", [r"\.\\\\"], ()),
            (r"\[c\]\[d\]", [r"\[c", r"\]", r"\[d", r"\]"], ()),
            (r"\[c\]abc\[4\]", [r"\[c", r"\]", "abc", r"\[4", r"\]"], ()),
            (r"\[d\]abc", [r"\[d", r"\]", "abc"], ()),
            (r"\[d\]\abc", [r"\[d", r"\]", r"\abc"], (SyntaxWarning,)),
            (r"abc\[e\]", [r"\.abc", r"\[e", r"\]"], ()),
            (r"abc", [r"\.abc"], ()),
            (r"\{meta info\}\.abc", [r"\{meta info", r"\}", r"\.abc"], ()),
            (r"\{meta info\}abc", [r"\{meta info", r"\}", r"abc"], ()),
            (r"\\abc", [r"\.\\abc"], ()),
            (r"\.\a", [r"\.\a"], (SyntaxWarning,)),
            (r"\a\a", [r"\.\a\a"], (SyntaxWarning,)),
        ),
    )

    @staticmethod
    @mark.parametrize(*TokenizeTests)
    def test_tokenize(parser: PathSyntaxParser, string: str, result: list[str], ignore_warns: EW) -> None:
        with safe_warns(ignore_warns):
            tokenized = list(parser.tokenize(string))
        assert tokenized == result

    ParseTests: tuple[str, tuple[tuple[str, list[AnyKey] | None, EE, EW], ...]] = (
        "string, path_obj, ignore_excs, ignore_warns",
        (
            (
                r"\.a.a\\.a\.b\[18\]\[07\]\.e",
                [AttrKey(r"a.a\.a"), AttrKey("b"), IndexKey(18), IndexKey(7), AttrKey("e")],
                (),
                (),
            ),
            (r"abc\[2\]", [AttrKey("abc"), IndexKey(2)], (), ()),
            (r"\.abc\[2\]", [AttrKey("abc"), IndexKey(2)], (), ()),
            (r"\{meta\}\.aaa\{meta\}\[0\]", [AttrKey("aaa", "meta"), IndexKey(0, "meta")], (), ()),
            (r"abc", [AttrKey("abc")], (), ()),
            (r"\\abc", [AttrKey(r"\abc")], (), ()),
            (r"\.abc", [AttrKey("abc")], (), ()),
            (r"\[2\]\[3\]", [IndexKey(2), IndexKey(3)], (), ()),
            (r"[2]\[3\]", [AttrKey(r"[2]"), IndexKey(3)], (), ()),
            (r"\.a\[2\]\.b\[3\]", [AttrKey("a"), IndexKey(2), AttrKey("b"), IndexKey(3)], (), ()),
            (r"\{any thing\}", [], (), ()),
            (r"\.\a", [AttrKey(r"\a")], (), (SyntaxWarning,)),
            (r"\a", [AttrKey(r"\a")], (), (SyntaxWarning,)),
            (r"\a\a", [AttrKey(r"\a\a")], (), (SyntaxWarning,)),
            (r"\{", None, (ConfigDataPathSyntaxException,), ()),
            (r"\{\{", None, (ConfigDataPathSyntaxException,), ()),
            (r"\{\[", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[\{", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[\}", None, (ConfigDataPathSyntaxException,), ()),
            (r"\{\]", None, (ConfigDataPathSyntaxException,), ()),
            (r"\}", None, (ConfigDataPathSyntaxException,), ()),
            (r"[2\]\[3\]", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[2\[3\]", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[2\]\.3\]", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[2\.3", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[2", None, (ConfigDataPathSyntaxException,), ()),
            (r"\[a\]", None, (ValueError,), ()),
            (r"\[4\]abc\[9\]", None, (UnknownTokenTypeError,), ()),
            (r"\[5\]abc", None, (UnknownTokenTypeError,), ()),
            (r"\[5\]\abc", None, (UnknownTokenTypeError,), (SyntaxWarning,)),
            (r"\{meta\}aaa", None, (UnknownTokenTypeError,), ()),
        ),
    )

    @staticmethod
    @mark.parametrize(*ParseTests)
    def test_parse(parser: PathSyntaxParser, string: str, path_obj: Path, ignore_excs: EE, ignore_warns: EW) -> None:
        with safe_raises(ignore_excs) as e_info, safe_warns(ignore_warns):
            path = parser.parse(string)
        if not e_info:
            assert path == path_obj
