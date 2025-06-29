"""
大多数测试经过 :py:class:`RequiredPath` 包装后测试所以存放在 `test_main.py`

.. versionadded:: 0.2.0
"""

from pytest import raises

from C41811.Config import FieldDefinition

# noinspection PyProtectedMember
from C41811.Config.validators import SkipMissing

# noinspection PyProtectedMember
from C41811.Config.validators import SkipMissingType


def test_field_definition() -> None:
    FieldDefinition(str, "default")
    FieldDefinition(str | list, default_factory=list)
    with raises(ValueError):
        # noinspection PyArgumentList
        FieldDefinition(str | list, "default", default_factory=list)  # type: ignore[call-overload]


def test_skip_missing() -> None:
    assert SkipMissingType() is SkipMissing

    str(SkipMissing)
