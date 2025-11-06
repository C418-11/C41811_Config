# cython: language_level = 3  # noqa: ERA001


"""
辅助生成

.. versionadded:: 0.2.0
"""

from collections.abc import Callable
from functools import update_wrapper
from typing import Any

import wrapt

from .core import BasicSingleConfigData
from .factory import ConfigDataFactory
from .utils import check_read_only

type Operator = Callable[[Any, Any], Any]
type InplaceOperator[S] = Callable[[S, Any], S]


def _generate_operators[S: Any](
    operate_func: Operator, inplace_func: InplaceOperator[S]
) -> tuple[Operator, Operator, InplaceOperator[S]]:
    """
    闭包绑定操作函数

    :param operate_func: 操作函数
    :type operate_func: Operator
    :param inplace_func: 原地操作函数
    :type inplace_func: InplaceOperator[S]

    :return: 绑定后的操作符实现
    :rtype: tuple[Operator, Operator, InplaceOperator[S]]
    """

    def forward_op(self: Any, other: Any) -> Any:
        return ConfigDataFactory(operate_func(self._data, other))

    def reverse_op(self: Any, other: Any) -> Any:
        return ConfigDataFactory(operate_func(other, self._data))

    # noinspection PyTypeHints
    def inplace_op(self: S, other: Any) -> S:
        self._data = inplace_func(self._data, other)
        return self

    return forward_op, reverse_op, inplace_op


def generate[C](cls: type[C]) -> type[C]:
    """
    为类生成操作符

    需要使用 :py:deco:`operate` 装饰器标记要自动生成的操作符

    :param cls: 目标类
    :type cls: type[C]

    :return: 原样返回类
    :rtype: type[C]
    """
    for name, func in dict(vars(cls)).items():
        if not hasattr(func, "__generate_operators__"):
            continue
        operator_funcs = func.__generate_operators__
        delattr(func, "__generate_operators__")

        # 动态创建函数
        forward_op, reverse_op, inplace_op = _generate_operators(
            operator_funcs["operate_func"], operator_funcs["inplace_func"]
        )

        # 设置函数标识符
        i_name = f"__i{name[2:-2]}__"
        r_name = f"__r{name[2:-2]}__"
        forward_op.__qualname__ = func.__qualname__
        reverse_op.__qualname__ = f"{cls.__qualname__}.{r_name}"
        inplace_op.__qualname__ = f"{cls.__qualname__}.{i_name}"

        # 应用装饰器
        @wrapt.decorator
        def wrapper(wrapped: Callable[..., Any], _instance: C, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
            if isinstance(args[0], BasicSingleConfigData):
                args = (args[0].data, *args[1:])
            return wrapped(*args, **kwargs)

        setattr(cls, name, update_wrapper(wrapper(forward_op), forward_op))
        setattr(cls, r_name, reverse_op)
        setattr(cls, i_name, update_wrapper(wrapper(check_read_only(inplace_op)), inplace_op))

    return cls


def operate[F: Operator](
    operate_func: Operator,
    inplace_func: InplaceOperator[Any],
) -> Callable[[F], F]:
    """
    将方法标记为需要生成标记符

    :param operate_func: 操作函数
    :type operate_func: Operator
    :param inplace_func: 原地操作函数
    :type inplace_func: InplaceOperator[Any]

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
