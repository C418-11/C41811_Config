# -*- coding: utf-8 -*-
# cython: language_level = 3


from setuptools import find_namespace_packages
from setuptools import setup

from src.C41811.Config import __version__

setup(
    name="C41811.Config",
    version=__version__,
    author="C418____11",
    author_email="553515788@qq.com",
    description="A useful config module.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/C418-11/C41811_Config",
    project_urls={
        "Bug Tracker": "https://github.com/C418-11/C41811_Config/issues",
        "Source Code": "https://github.com/C418-11/C41811_Config",
        "Documentation": "https://C41811Config.readthedocs.io",
    },
    packages=find_namespace_packages("./src/"),
    package_dir={"": "src"},
    python_requires=">=3.12",
    extra_require={
        "docs": [
            "sphinx",
            "sphinx-autoapi",
            "furo",
        ],
        "SLProcessorRequirements": [
            "PyYAML",
            "ruamel.yaml",
            "toml",
        ],
    },
    platforms="any",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: Chinese (Simplified)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
)
