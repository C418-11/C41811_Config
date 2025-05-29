

import re
from collections.abc import Mapping
from collections.abc import MutableMapping
from collections.abc import Sequence
from typing import Any
from typing import cast

from pytest import fixture
from pytest import mark
from pytest import raises

from C41811.Config import AttrKey
from C41811.Config import IndexKey
from C41811.Config import Path
from C41811.Config.abc import ABCPath
from C41811.Config.errors import ConfigDataPathSyntaxException
from C41811.Config.errors import ConfigDataReadOnlyError
from C41811.Config.errors import ConfigDataTypeError
from C41811.Config.errors import ConfigOperate
from C41811.Config.errors import FailedProcessConfigFileError
from C41811.Config.errors import KeyInfo
from C41811.Config.errors import RequiredPathNotFoundError
from C41811.Config.errors import TokenInfo
from C41811.Config.errors import UnknownErrorDuringValidateError
from C41811.Config.errors import UnknownTokenTypeError
from C41811.Config.errors import UnsupportedConfigFormatError


@mark.parametrize("args, raw_string", (
        ((["\\[2", "\\[3", "\\]"], "\\[3", 1), "\\[2\\[3\\]"),
        ((["\\[2", "\\]", "\\.3", "\\]"], "\\]", 3), "\\[2\\]\\.3\\]"),
        ((["\\[2", "\\.3"], ".3", 1), "\\[2\\.3"),
        ((["\\[2"], "\\[2", 0), "\\[2"),
        ((["\\[4", "\\]abc", "\\[9", "\\]"], "abc", 2), "\\[4\\]abc\\[9\\]"),
        ((["\\[5", "\\]", "abc"], "abc", 2), "\\[5\\]abc"),
        ((["abc", "\\[2", "\\]"], "abc", 0), "abc\\[2\\]"),
        ((["abc"], "abc", 0), "abc"),
        ((["\\a\\a"], "\\a\\a", 0), "\\a\\a"),
))
def test_token_info(args: tuple[tuple[str, ...], str, int], raw_string: str) -> None:
    ti = TokenInfo(*args)
    assert ti.raw_string == raw_string


@fixture
def token_info() -> TokenInfo:
    return TokenInfo(("abc",), "abc", 0)


def test_config_data_path_syntax_exception(token_info: TokenInfo) -> None:
    with raises(ConfigDataPathSyntaxException):
        raise ConfigDataPathSyntaxException(token_info)

    with raises(ConfigDataPathSyntaxException, match=r"\$\$message\$\$"):
        raise ConfigDataPathSyntaxException(token_info, "$$message$$")

    class Subclass(ConfigDataPathSyntaxException):
        msg = "$$subclass$$"

    with raises(ConfigDataPathSyntaxException, match=r"\$\$subclass\$\$"):
        raise Subclass(token_info)

    with raises(ConfigDataPathSyntaxException, match=r"\$\$override\$\$"):
        raise Subclass(token_info, "$$override$$")


def test_unknown_token_type_error(token_info: TokenInfo) -> None:
    with raises(UnknownTokenTypeError, match=UnknownTokenTypeError.msg):
        raise UnknownTokenTypeError(token_info)

    with raises(UnknownTokenTypeError, match=r"\$\$override\$\$"):
        raise UnknownTokenTypeError(token_info, "$$override$$")


@mark.parametrize("kwargs, relative_keys", (
        ({"path": Path((AttrKey("foo2"), AttrKey("bar"))), "current_key": AttrKey("bar"), "index": 1},
         (AttrKey("foo2"),)),
        ({"path": Path((AttrKey("foo3"),)), "current_key": AttrKey("foo3"), "index": 0}, ()),
        ({"path": Path((AttrKey("not exist"),)), "current_key": AttrKey("not exist"), "index": 0}, ()),
        ({"path": Path((AttrKey("foo.not exist"),)), "current_key": AttrKey("foo.not exist"), "index": 0}, ()),
        ({"path": Path((AttrKey("foo2"), AttrKey("not exist"))), "current_key": AttrKey("not exist"), "index": 1},
         (AttrKey("foo2"),)),

))
def test_key_info(kwargs: dict[str, Any], relative_keys: tuple[AttrKey | IndexKey, ...]) -> None:
    ki = KeyInfo(**kwargs)
    assert ki.relative_keys == Path(relative_keys)


@fixture
def key_info() -> KeyInfo[AttrKey]:
    return KeyInfo(
        cast(
            ABCPath[AttrKey],
            Path((AttrKey("foo3"),))
        ),
        AttrKey("foo3"),
        0
    )


def test_required_path_not_found_error(key_info: KeyInfo[Any]) -> None:
    with raises(RequiredPathNotFoundError):
        raise RequiredPathNotFoundError(key_info)

    with raises(RequiredPathNotFoundError, match=ConfigOperate.Read.value):
        raise RequiredPathNotFoundError(key_info, ConfigOperate.Read)


def test_config_data_readonly_error() -> None:
    with raises(ConfigDataReadOnlyError, match="read-only"):
        raise ConfigDataReadOnlyError

    with raises(ConfigDataReadOnlyError, match=r"\$\$message\$\$"):
        raise ConfigDataReadOnlyError("$$message$$")


@mark.parametrize("required_type, current_type", (
        (int, str),
        (str, int),
        (list[str], str),
        (dict, KeyInfo),
        (Mapping, float),
        ((int,), float),
        ((MutableMapping, Sequence), Mapping),
        ((str, bytes), float),
        ((bool, int, float), frozenset),
))
def test_config_data_type_error(key_info: KeyInfo[Any], required_type: tuple[type, ...], current_type: type) -> None:
    def _repr(t: tuple[type, ...] | type) -> str:
        if isinstance(t, tuple) and len(t) == 1:
            t = t[0]
        return re.escape(repr(t))

    with raises(ConfigDataTypeError, match=f"{_repr(required_type)}.*{_repr(current_type)}"):
        raise ConfigDataTypeError(key_info, required_type, current_type)


def test_unknown_error_during_validate_error() -> None:
    with raises(UnknownErrorDuringValidateError, match="Args:.*Kwargs:.*"):
        raise UnknownErrorDuringValidateError


def test_unsupported_config_format_error() -> None:
    with raises(UnsupportedConfigFormatError, match="json"):
        raise UnsupportedConfigFormatError("json")

    cls = UnsupportedConfigFormatError
    assert cls("json") == cls("json")
    assert cls("json") != cls("pickle")


def test_failed_process_config_file_error() -> None:
    cls = FailedProcessConfigFileError
    with raises(cls, match="Failed to process config file"):
        raise cls(Exception())

    with raises(cls, match=r"1\n2\n3"):
        raise cls([Exception(1), Exception(2), Exception(3)])

    with raises(cls, match=r"1: 1\n2: 2\n3: 3"):
        raise cls({'1': Exception('1'), '2': Exception(2), '3': Exception(3)})
