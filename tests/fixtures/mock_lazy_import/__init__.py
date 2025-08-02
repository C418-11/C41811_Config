from c41811.config.lazy_import import lazy_import

from .sub_pkg import __all__ as __sub_pkg_all

__all__, __getattr__ = lazy_import(
    {
        "Available": ".available",
        "MissingDependency": ".missing_dependency",
        **dict.fromkeys(__sub_pkg_all, ".sub_pkg"),
    }
)
