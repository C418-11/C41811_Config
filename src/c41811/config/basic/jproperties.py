# cython: language_level = 3  # noqa: ERA001


# noinspection GrazieInspection
"""
:py:class:`~jproperties.Properties` 类型配置数据实现

.. versionadded:: 0.3.0
"""

from collections.abc import Mapping
from typing import Any
from typing import override

from .mapping import MappingConfigData
from ..errors import DependencyNotFoundError

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    import jproperties  # type: ignore[import-not-found]
except ImportError:
    dependency = "jproperties"
    raise DependencyNotFoundError(dependency) from None


class JPropertiesConfigData(MappingConfigData[jproperties.Properties]):
    """:py:class:`~jproperties.Properties` 类型配置数据"""

    def __init__(self, data: jproperties.Properties | Mapping[str, str | tuple[str, dict[str, str]]] | None = None):
        """
        :param data: 配置的原始数据
        :type data: jproperties.Properties | Mapping[str, str | tuple[str, dict[str, str]]] | None

        .. caution::
           未默认做深拷贝，可能导致非预期行为
        """  # noqa: RUF002, D205
        super().__init__()

        prop = data
        is_none = data is None
        not_property = not isinstance(data, jproperties.Properties)
        if is_none or not_property:
            prop = jproperties.Properties()
        if is_none:
            data = {}
        if not_property:
            for key, value in data.items():  # type: ignore[union-attr]
                prop[key] = value  # type: ignore[index]
                # noinspection PyProtectedMember
                prop._key_order.append(key)  # type: ignore[union-attr]  # noqa: SLF001

        self._data: jproperties.Properties = prop

    @override
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return all(
            getattr(self._data, attr) == getattr(other._data, attr)  # noqa: SLF001
            for attr in ("properties", "_metadata", "_key_order")
        )

    __hash__ = None  # type: ignore[assignment]

    @override
    def __repr__(self) -> str:
        repr_ls = []
        for name, attr in zip(
            ("properties", "metadata", "key_order"), ("properties", "_metadata", "_key_order"), strict=False
        ):
            repr_ls.append(f"{name}={getattr(self._data, attr)!r}")
        return f"{self.__class__.__name__}({', '.join(repr_ls)})"


__all__ = ("JPropertiesConfigData",)
