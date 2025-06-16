# cython: language_level = 3


"""
辅助生成

.. versionadded:: 0.2.0
"""

from collections.abc import Callable
from textwrap import dedent
from typing import Any
from typing import Self

import wrapt  # type: ignore[import-untyped]

from .core import BasicSingleConfigData
from .core import ConfigData
from .utils import check_read_only


def generate[C](cls: type[C]) -> type[C]:
    """
    为类生成操作符

    需要使用 :py:deco:`operate` 装饰器标记要自动生成的操作符

    :param cls: 类
    :type cls: type
    """
    for name, func in dict(vars(cls)).items():
        if not hasattr(func, "__generate_operators__"):
            continue
        operator_funcs = func.__generate_operators__
        delattr(func, "__generate_operators__")

        i_name = f"__i{name[2:-2]}__"
        r_name = f"__r{name[2:-2]}__"

        code = dedent(f"""
        def {name}(self, other: Any) -> Any:
            return ConfigData(operate_func(self._data, other))
        def {r_name}(self, other: Any) -> Any:
            return ConfigData(operate_func(other, self._data))
        def {i_name}(self, other: Any) -> Self:
            self._data = inplace_func(self._data, other)
            return self
        """)

        funcs: dict[str, Any] = {}
        exec(code, {**operator_funcs, "ConfigData": ConfigData, "Any": Any, "Self": Self}, funcs)

        funcs[name].__qualname__ = func.__qualname__
        funcs[r_name].__qualname__ = f"{cls.__qualname__}.{r_name}"
        funcs[i_name].__qualname__ = f"{cls.__qualname__}.{i_name}"

        @wrapt.decorator  # type: ignore[misc]
        def wrapper(wrapped: Callable[..., Any], _instance: C, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
            if isinstance(args[0], BasicSingleConfigData):
                args = args[0].data, *args[1:]
            return wrapped(*args, **kwargs)

        setattr(cls, name, wrapper(funcs[name]))
        setattr(cls, r_name, funcs[r_name])
        setattr(cls, i_name, wrapper(check_read_only(funcs[i_name])))

    return cls


def operate[F: Callable[[Any, Any], Any]](
    operate_func: Callable[[Any, Any], Any],
    inplace_func: Callable[[Any, Any], Any],
) -> Callable[[F], F]:
    """
    将方法标记为需要生成标记符

    :param operate_func: 操作函数
    :type operate_func: Callable[[Any, Any], Any]
    :param inplace_func: 原地操作函数
    :type inplace_func: Callable[[Any, Any], Any]

    :return: 装饰器
    :rtype: Callable[[F], F]
    """

    def decorator(func: F) -> F:
        func.__generate_operators__ = {  # type: ignore[attr-defined]
            "operate_func": operate_func,
            "inplace_func": inplace_func,
        }
        return func

    return decorator


__all__ = (
    "generate",
    "operate",
)
