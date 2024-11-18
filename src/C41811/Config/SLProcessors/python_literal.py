# -*- coding: utf-8 -*-
# cython: language_level = 3


from ast import literal_eval
from typing import Optional
from typing import TypeVar
from typing import override

from ..abc import ABCConfig
from ..errors import FailedProcessConfigFileError
from ..main import BaseConfigSL
from ..main import ConfigData

C = TypeVar("C", bound=ABCConfig)


class PythonLiteralSL(BaseConfigSL):
    """
    Python 字面量序列化处理器
    """

    @property
    @override
    def regName(self) -> str:
        return "python_literal"

    @property
    @override
    def fileExt(self) -> list[str]:
        return [".py", ".python_literal", ".pyl"]

    @override
    def save(
            self,
            config: ABCConfig,
            root_path: str,
            namespace: Optional[str],
            file_name: Optional[str],
            *args,
            **kwargs
    ) -> None:

        file_path = self._getFilePath(config, root_path, namespace, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            try:
                f.write(str(config.data))
            except Exception as e:
                raise FailedProcessConfigFileError(e) from e

    @override
    def load(
            self,
            config_cls: type[C],
            root_path: str,
            namespace: Optional[str],
            file_name: Optional[str],
            *args,
            **kwargs
    ) -> C:

        with open(self._norm_join(root_path, namespace, file_name), "r", encoding="utf-8") as f:
            try:
                data = literal_eval(f.read())
            except Exception as e:
                raise FailedProcessConfigFileError(e) from e

        obj = config_cls(ConfigData(data), namespace=namespace, file_name=file_name, config_format=self.regName)

        return obj


__all__ = (
    "PythonLiteralSL",
)
