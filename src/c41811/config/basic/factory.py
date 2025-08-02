# cython: language_level = 3  # noqa: ERA001


"""
配置数据工厂

.. versionadded:: 0.3.0
"""

from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

if TYPE_CHECKING:
    from collections import OrderedDict
    from collections.abc import Callable

    from ..abc import ABCConfigData
else:
    from collections import OrderedDict
    from collections.abc import Callable

    ABCConfigData = Any


class ConfigDataFactory:
    """
    配置数据工厂类

    .. versionchanged:: 0.1.5
       会自动根据传入的数据类型选择对应的配置数据类

    .. versionchanged:: 0.3.0
       不再作为所有 `ConfigData` 的虚拟父类
       重命名 ``ConfigData`` 为 ``ConfigDataFactory``
    """

    TYPES: ClassVar[OrderedDict[tuple[type, ...], Callable[[Any], ABCConfigData] | type]]
    """
    存储配置数据类型对应的子类

    .. versionchanged:: 0.2.0
       现在使用 ``OrderedDict`` 来保证顺序
    """

    _TYPES_LAZY_INITIALIZER: ClassVar[Callable[[], None]]
    """
    用于初始化 :py:attr:`TYPES` 的函数

    .. versionadded:: 0.3.0
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> ABCConfigData:  # type: ignore[misc]
        """
        将根据第一个位置参数决定配置数据类型

        :param args: 配置数据
        :type args: Any
        :param kwargs: 配置数据
        :type kwargs: Any

        :return: 配置数据类
        :rtype: ABCConfigData
        """
        if not hasattr(cls, "TYPES"):
            cls._TYPES_LAZY_INITIALIZER()

        if not args:
            args = (None,)
        for types, config_data_cls in cls.TYPES.items():
            if not isinstance(args[0], types):
                continue
            return config_data_cls(*args, **kwargs)
        msg = f"Unsupported type: {args[0]}"
        raise TypeError(msg)


__all__ = ("ConfigDataFactory",)
