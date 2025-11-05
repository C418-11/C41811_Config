import re
from collections.abc import Mapping
from collections.abc import MutableMapping
from collections.abc import Sequence
from typing import Any
from typing import cast

from pytest import fixture
from pytest import mark
from pytest import raises

from c41811.config import AttrKey
from c41811.config import IndexKey
from c41811.config import Path
from c41811.config.abc import ABCPath
from c41811.config.errors import ComponentMemberMismatchError
from c41811.config.errors import ConfigDataPathSyntaxException
from c41811.config.errors import ConfigDataReadOnlyError
from c41811.config.errors import ConfigDataTypeError
from c41811.config.errors import ConfigOperate
from c41811.config.errors import DependencyNotFoundError
from c41811.config.errors import FailedProcessConfigFileError
from c41811.config.errors import KeyInfo
from c41811.config.errors import RequiredPathNotFoundError
from c41811.config.errors import TokenInfo
from c41811.config.errors import UnavailableAttribute
from c41811.config.errors import UnknownErrorDuringValidateError
from c41811.config.errors import UnknownTokenTypeError
from c41811.config.errors import UnsupportedConfigFormatError


# noinspection PyUnreachableCode
def test_unavailable_attribute() -> None:
    err = DependencyNotFoundError("dependency", "${dep_name}$ For Test!")
    unavailable_attribute = UnavailableAttribute("attribute", err)

    assert "attribute" in repr(unavailable_attribute)

    with raises(DependencyNotFoundError, match=r"\$dependency\$ For Test!"):
        unavailable_attribute("any", "arguments")

    with raises(DependencyNotFoundError, match=r"\$dependency\$ For Test!"):
        # noinspection PyStatementEffect
        unavailable_attribute.any_attribute  # noqa: B018


@mark.parametrize(
    "args, raw_string",
    (
        ((["\\[2", "\\[3", "\\]"], "\\[3", 1), "\\[2\\[3\\]"),
        ((["\\[2", "\\]", "\\.3", "\\]"], "\\]", 3), "\\[2\\]\\.3\\]"),
        ((["\\[2", "\\.3"], ".3", 1), "\\[2\\.3"),
        ((["\\[2"], "\\[2", 0), "\\[2"),
        ((["\\[4", "\\]abc", "\\[9", "\\]"], "abc", 2), "\\[4\\]abc\\[9\\]"),
        ((["\\[5", "\\]", "abc"], "abc", 2), "\\[5\\]abc"),
        ((["abc", "\\[2", "\\]"], "abc", 0), "abc\\[2\\]"),
        ((["abc"], "abc", 0), "abc"),
        ((["\\a\\a"], "\\a\\a", 0), "\\a\\a"),
    ),
)
def test_token_info(args: tuple[tuple[str, ...], str, int], raw_string: str) -> None:
    ti = TokenInfo(*args)
    assert ti.raw_string == raw_string


@fixture
def token_info() -> TokenInfo:
    return TokenInfo(("abc",), "abc", 0)


# noinspection PyUnreachableCode
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


# noinspection PyUnreachableCode
def test_unknown_token_type_error(token_info: TokenInfo) -> None:
    with raises(UnknownTokenTypeError, match=UnknownTokenTypeError.msg):
        raise UnknownTokenTypeError(token_info)

    with raises(UnknownTokenTypeError, match=r"\$\$override\$\$"):
        raise UnknownTokenTypeError(token_info, "$$override$$")


@mark.parametrize(
    "kwargs, relative_keys",
    (
        (
            {"path": Path((AttrKey("foo2"), AttrKey("bar"))), "current_key": AttrKey("bar"), "index": 1},
            (AttrKey("foo2"),),
        ),
        ({"path": Path((AttrKey("foo3"),)), "current_key": AttrKey("foo3"), "index": 0}, ()),
        ({"path": Path((AttrKey("not exist"),)), "current_key": AttrKey("not exist"), "index": 0}, ()),
        ({"path": Path((AttrKey("foo.not exist"),)), "current_key": AttrKey("foo.not exist"), "index": 0}, ()),
        (
            {"path": Path((AttrKey("foo2"), AttrKey("not exist"))), "current_key": AttrKey("not exist"), "index": 1},
            (AttrKey("foo2"),),
        ),
    ),
)
def test_key_info(kwargs: dict[str, Any], relative_keys: tuple[AttrKey | IndexKey, ...]) -> None:
    ki = KeyInfo(**kwargs)
    assert ki.relative_keys == Path(relative_keys)


@fixture
def key_info() -> KeyInfo[AttrKey]:
    return KeyInfo(cast(ABCPath[AttrKey], Path((AttrKey("foo3"),))), AttrKey("foo3"), 0)


# noinspection PyUnreachableCode
def test_required_path_not_found_error(key_info: KeyInfo[Any]) -> None:
    with raises(RequiredPathNotFoundError):
        raise RequiredPathNotFoundError(key_info)

    with raises(RequiredPathNotFoundError, match=ConfigOperate.Read.value):
        raise RequiredPathNotFoundError(key_info, ConfigOperate.Read)


# noinspection PyUnreachableCode
def test_config_data_readonly_error() -> None:
    with raises(ConfigDataReadOnlyError, match="read-only"):
        raise ConfigDataReadOnlyError

    with raises(ConfigDataReadOnlyError, match=r"\$\$message\$\$"):
        raise ConfigDataReadOnlyError("$$message$$")  # noqa: EM101


@mark.parametrize(
    "required_type, current_type",
    (
        (int, str),
        (str, int),
        (list[str], str),
        (dict, KeyInfo),
        (Mapping, float),
        ((int,), float),
        ((MutableMapping, Sequence), Mapping),
        ((str, bytes), float),
        ((bool, int, float), frozenset),
    ),
)
def test_config_data_type_error(key_info: KeyInfo[Any], required_type: tuple[type, ...], current_type: type) -> None:
    def _repr(t: tuple[type, ...] | type) -> str:
        if isinstance(t, tuple) and len(t) == 1:
            t = t[0]
        return re.escape(repr(t))

    with raises(ConfigDataTypeError, match=f"{_repr(required_type)}.*{_repr(current_type)}"):
        raise ConfigDataTypeError(key_info, required_type, current_type)


def test_unknown_error_during_validate_error() -> None:
    with raises(UnknownErrorDuringValidateError, match=re.compile(r"Args:.*Kwargs:.*")):
        raise UnknownErrorDuringValidateError


# noinspection PyUnreachableCode
def test_unsupported_config_format_error() -> None:
    cls = UnsupportedConfigFormatError
    with raises(cls, match="json"):
        raise cls("json")  # noqa: EM101

    with raises(AttributeError, match="object has no setter"):
        # noinspection PyPropertyAccess
        cls("json").format = "readonly"  # type: ignore[misc]

    assert cls("json").format == "json"
    assert cls("json") == cls("json")
    assert cls("json") != cls("pickle")
    assert hash(cls("json")) == hash(cls("json"))
    assert hash(cls("json")) != hash(cls("pickle"))


# noinspection PyUnreachableCode
def test_failed_process_config_file_error() -> None:
    cls = FailedProcessConfigFileError
    with raises(cls, match="Failed to process config file"):
        raise cls(Exception())

    with raises(cls, match=r"1\n2\n3"):
        raise cls([Exception(1), Exception(2), Exception(3)])

    with raises(cls, match=r"1: 1\n2: 2\n3: 3"):
        raise cls({"1": Exception("1"), "2": Exception(2), "3": Exception(3)})


# noinspection PyUnreachableCode
def test_component_member_mismatch_error() -> None:
    cls = ComponentMemberMismatchError
    with raises(cls, match="Missing"):
        raise cls(missing={"foo"}, redundant=set())

    with raises(cls, match="Redundant"):
        raise cls(missing=set(), redundant={"foo"})

    with raises(cls, match=re.compile(r"Missing .+ Redundant")):
        raise cls(missing={"foo", "bar"}, redundant={"foo"})
