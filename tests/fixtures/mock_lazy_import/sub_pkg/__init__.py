from c41811.config.lazy_import import lazy_import

__all__, __getattr__ = lazy_import(
    {
        "SubAvailable": ".available",
        "SubMissingDependency": ".missing_dependency",
    }
)
