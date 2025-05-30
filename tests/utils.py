import contextlib
from collections.abc import Generator
from typing import Any

# noinspection PyProtectedMember
from _pytest._code import ExceptionInfo
from _pytest.recwarn import WarningsChecker
from pytest import raises
from pytest import warns

type EE = type[BaseException] | tuple[type[BaseException], ...] | None
type EW = type[Warning] | tuple[type[Warning], ...] | None


@contextlib.contextmanager
def safe_raises(
    expected_exception: EE, *args: Any, **kwargs: Any
) -> Generator[ExceptionInfo[BaseException] | None, Any, None]:
    if not expected_exception:
        yield None
        return

    with raises(expected_exception, *args, **kwargs) as err:
        yield err


@contextlib.contextmanager
def safe_warns(expected_warning: EW, *args: Any, **kwargs: Any) -> Generator[WarningsChecker | None, Any, None]:
    if not expected_warning:
        yield None
        return

    with warns(expected_warning, *args, **kwargs) as warn:
        yield warn


__all__ = (
    "EE",
    "EW",
    "safe_raises",
    "safe_warns",
)
