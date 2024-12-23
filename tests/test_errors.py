# -*- coding: utf-8 -*-


import re
from collections.abc import Mapping

from pytest import fixture
from pytest import mark
from pytest import raises

from C41811.Config import AttrKey
from C41811.Config import Path
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
def test_token_info(args, raw_string):
    ti = TokenInfo(*args)
    assert ti.raw_string == raw_string


@fixture
def token_info():
    return TokenInfo(["abc"], "abc", 0)


def test_config_data_path_syntax_exception(token_info):
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


def test_unknown_token_type_error(token_info):
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
def test_key_info(kwargs, relative_keys):
    ki = KeyInfo(**kwargs)
    assert ki.relative_keys == relative_keys


@fixture
def key_info():
    return KeyInfo(Path((AttrKey("foo3"),)), AttrKey("foo3"), 0)


def test_required_path_not_found_error(key_info):
    with raises(RequiredPathNotFoundError):
        raise RequiredPathNotFoundError(key_info)

    with raises(RequiredPathNotFoundError, match=ConfigOperate.Read.value):
        raise RequiredPathNotFoundError(key_info, ConfigOperate.Read)


def test_config_data_readonly_error():
    with raises(ConfigDataReadOnlyError, match="read-only"):
        raise ConfigDataReadOnlyError

    with raises(ConfigDataReadOnlyError, match=r"\$\$message\$\$"):
        raise ConfigDataReadOnlyError("$$message$$")


@mark.parametrize("required_type, now_type", (
        (int, str),
        (str, int),
        (list[str], str),
        (dict, KeyInfo),
        (Mapping, float),
))
def test_config_data_type_error(key_info, required_type, now_type):
    def _repr(t: type):
        return re.escape(repr(t))

    with raises(ConfigDataTypeError, match=f"{_repr(required_type)}.*{_repr(now_type)}"):
        raise ConfigDataTypeError(key_info, required_type, now_type)


def test_unknown_error_during_validate_error(key_info):
    with raises(UnknownErrorDuringValidateError, match="Args:.*Kwargs:.*"):
        raise UnknownErrorDuringValidateError


def test_unsupported_config_format_error():
    with raises(UnsupportedConfigFormatError, match="json"):
        raise UnsupportedConfigFormatError("json")

    cls = UnsupportedConfigFormatError
    assert cls("json") == cls("json")
    assert cls("json") != cls("pickle")


def test_failed_process_config_file_error():
    cls = FailedProcessConfigFileError
    with raises(cls, match="Failed to process config file"):
        raise cls(Exception())

    with raises(cls, match=r"1\n2\n3"):
        raise cls([Exception(1), Exception(2), Exception(3)])

    with raises(cls, match=r"1: 1\n2: 2\n3: 3"):
        raise cls({'1': Exception('1'), '2': Exception(2), '3': Exception(3)})
