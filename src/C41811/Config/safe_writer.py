# -*- coding: utf-8 -*-
# cython: language_level = 3


# noinspection SpellCheckingInspection, GrazieInspection
"""
  从 https://github.com/untitaker/python-atomicwrites 修改而来

  .. code-block:: text
    :caption: 原始版权声明

    Copyright (c) 2015-2016 Markus Unterwaditzer

    Permission is hereby granted, free of charge, to any person obtaining a copy of
    this software and associated documentation files (the "Software"), to deal in
    the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is furnished to do
    so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

.. versionadded:: 0.2.0
"""

import os
import shutil
import sys
import time
from abc import ABC
from abc import abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from contextlib import suppress
from enum import IntEnum
from numbers import Real
from pathlib import Path
from threading import Lock
from typing import Any
from typing import ContextManager
from typing import IO
from typing import Optional
from typing import TextIO
from typing import cast
from typing import override
from weakref import WeakValueDictionary

import portalocker

try:
    import fcntl
except ImportError:  # pragma: no cover
    # noinspection SpellCheckingInspection
    fcntl = None  # type: ignore[assignment]

try:
    from os import fspath
except ImportError:  # pragma: no cover
    fspath = None  # type: ignore[assignment]

type PathLike = str | Path
type AIO = IO[Any]


def _path2str(x: PathLike) -> str:  # pragma: no cover
    if isinstance(x, Path):
        return str(x)
    return x


_proper_fsync = os.fsync

if sys.platform != "win32":  # pragma: no cover  # noqa: C901 (ignore complexity)
    # noinspection SpellCheckingInspection
    if hasattr(fcntl, "F_FULLFSYNC"):
        def _proper_fsync(fd: int) -> None:  # type: ignore[misc]  # noqa: F811, E303
            # https://lists.apple.com/archives/darwin-dev/2005/Feb/msg00072.html
            # https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man2/fsync.2.html
            # https://github.com/untitaker/python-atomicwrites/issues/6
            fcntl.fcntl(fd, fcntl.F_FULLFSYNC)  # type: ignore[attr-defined]


    def _sync_directory(directory: str) -> None:  # noqa: E303
        # Ensure that filenames are written to disk
        fd = os.open(directory, 0)
        try:
            _proper_fsync(fd)
        finally:
            os.close(fd)


    def _replace_atomic(src: PathLike, dst: PathLike) -> None:  # noqa: E303
        os.rename(src, dst)
        _sync_directory(os.path.normpath(os.path.dirname(dst)))


    def _move_atomic(src: PathLike, dst: PathLike) -> None:  # noqa: E303
        os.link(src, dst)
        os.unlink(src)

        src_dir = os.path.normpath(os.path.dirname(src))
        dst_dir = os.path.normpath(os.path.dirname(dst))
        _sync_directory(dst_dir)
        if src_dir != dst_dir:
            _sync_directory(src_dir)
else:  # pragma: no cover
    from ctypes import WinError
    from ctypes import windll

    _MOVEFILE_REPLACE_EXISTING = 0x1
    _MOVEFILE_WRITE_THROUGH = 0x8
    _windows_default_flags = _MOVEFILE_WRITE_THROUGH


    def _handle_errors(rv: Any) -> None:  # noqa: E303
        if not rv:
            raise WinError()


    def _replace_atomic(src: PathLike, dst: PathLike) -> None:  # noqa: E303
        _handle_errors(windll.kernel32.MoveFileExW(
            _path2str(src), _path2str(dst),
            _windows_default_flags | _MOVEFILE_REPLACE_EXISTING
        ))


    def _move_atomic(src: PathLike, dst: PathLike) -> None:  # noqa: E303
        _handle_errors(windll.kernel32.MoveFileExW(
            _path2str(src), _path2str(dst),
            _windows_default_flags
        ))


def replace_atomic(src: PathLike, dst: PathLike) -> None:
    """
    移动 ``src`` 到 ``dst`` 。如果 ``dst`` 存在，它将被静默覆盖。

    两个路径必须位于同一个文件系统上，这样操作才能是原子的。

    :param src: 源
    :type src: str
    :param dst: 目标
    :type dst: str
    """
    _replace_atomic(src, dst)


def move_atomic(src: PathLike, dst: PathLike) -> None:  # pragma: no cover
    """
    移动 ``src`` 到 ``dst`` 。可能存在两个文件系统条目同时存在的时间窗口。如果 ``dst`` 已经存在，将引发：py:exc: ‘ FileExistsError ’。

    两个路径必须位于同一个文件系统上，这样操作才能是原子的。

    :param src: 源
    :type src: str
    :param dst: 目标
    :type dst: str
    """
    _move_atomic(src, dst)


class ABCTempIOManager[F: AIO](ABC):
    """
    管理临时文件。
    """

    @abstractmethod
    def from_file(self, file: F) -> F:
        """
        为给定的文件创建一个临时文件。
        """

    @abstractmethod
    def from_path(self, path: Path | str, mode: str) -> F:
        """
        为给定的路径创建一个临时文件。
        """

    @staticmethod
    @abstractmethod
    def sync(file: F) -> None:
        """
        负责在提交之前清除尽可能多的文件缓存。
        """

    @staticmethod
    @abstractmethod
    def rollback(file: F) -> None:
        """
        清理所有临时资源。
        """

    @staticmethod
    @abstractmethod
    def commit(temp_file: F, file: F) -> None:
        """
        将临时文件移动到目标位置。
        """

    @staticmethod
    @abstractmethod
    def commit_by_path(temp_file: F, path: PathLike, mode: str) -> None:
        """
        将临时文件移动到目标位置。
        """


class TempTextIOManager[F: TextIO](ABCTempIOManager[F]):
    """
    管理 ``TextIO`` 对象。
    """

    def __init__(self, prefix: str = '', suffix: str = ".tmp", **open_kwargs: Any):
        """
        :param prefix: 临时文件前缀
        :type prefix: str
        :param suffix: 临时文件后缀
        :type suffix: str
        :param open_kwargs: 传递给 ``open`` 的额外参数
        """
        self._prefix = prefix
        self._suffix = suffix
        self._open_kwargs = open_kwargs

    @override
    def from_file(self, file: F) -> F:  # pragma: no cover # 用不上 暂不维护
        path, name = os.path.split(cast(TextIO, file).name)
        f = open(
            os.path.join(path, f"{self._prefix}{name}{self._suffix}"),
            mode=cast(TextIO, file).mode, **self._open_kwargs
        )
        shutil.copyfile(cast(TextIO, file).name, f.name)
        return cast(F, f)

    @override
    def from_path(self, path: Path | str, mode: str) -> F:
        f_path = f"{path}{self._suffix}"
        if os.path.exists(path):
            shutil.copyfile(path, f_path)
        return cast(F, open(f_path, mode=mode, **self._open_kwargs))

    @staticmethod
    @override
    def sync(file: F) -> None:
        if not file.writable():
            return
        file.flush()
        _proper_fsync(file.fileno())

    @staticmethod
    @override
    def rollback(file: F) -> None:
        os.unlink(cast(TextIO, file).name)

    @classmethod
    @override
    def commit(cls, temp_file: F, file: F) -> None:  # pragma: no cover # 用不上 暂不维护
        if not file.writable():
            return
        cls.commit_by_path(
            temp_file,
            cast(TextIO, file).name,
            cast(TextIO, file).mode
        )

    @classmethod
    @override
    def commit_by_path(cls, temp_file: F, path: PathLike, mode: str) -> None:
        writeable = any(x in mode for x in "wax+")
        if not writeable:
            cls.rollback(temp_file)
            return

        overwrite = True
        if 'x' in mode:  # pragma: no cover
            overwrite = False
        if ('r' in mode) and ('+' not in mode):  # pragma: no cover
            overwrite = False

        if overwrite:
            replace_atomic(cast(TextIO, temp_file).name, path)
        else:  # pragma: no cover
            move_atomic(cast(TextIO, temp_file).name, path)


class LockFlags(IntEnum):
    """
    文件锁标志
    """
    EXCLUSIVE = portalocker.LOCK_EX | portalocker.LOCK_NB
    SHARED = portalocker.LOCK_SH | portalocker.LOCK_NB


FileLocks: WeakValueDictionary[str, Lock] = WeakValueDictionary()
"""
存储文件名对应的锁
"""
GlobalModifyLock = Lock()
"""
防止修改 ``FileLocks`` 时发生竞态条件
"""


class SafeOpen[F: AIO]:
    """
    安全的打开文件
    """

    def __init__(
            self,
            io_manager: ABCTempIOManager[Any],
            timeout: Optional[float] = 1,
            flag: LockFlags = LockFlags.EXCLUSIVE
    ) -> None:
        """
        :param io_manager: IO管理器
        :type io_manager: ABCTempIOManager
        :param timeout: 超时时间
        :type timeout: Optional[float]
        :param flag: 锁标志
        :type flag: LockFlags
        """

        self._manager = io_manager
        self._timeout = timeout
        self._flag = flag

    @contextmanager
    def open_path(self, path: str | Path, mode: str) -> Generator[F | None, Any, None]:
        """
        打开路径 (上下文管理器)

        :param path: 文件路径
        :type path: str | pathlib.Path
        :param mode: 打开模式
        :type mode: str
        :return: 返回值为IO对象的上下文管理器
        """
        with GlobalModifyLock:
            lock = FileLocks.setdefault(_path2str(path), Lock())

        if not lock.acquire(timeout=-1 if self._timeout is None else self._timeout):  # pragma: no cover
            raise TimeoutError("Timeout waiting for file lock")

        f: Optional[F] = None
        try:
            f = self._manager.from_path(path, mode)
            acquire_lock(cast(AIO, f), self._flag, timeout=cast(Real | None, self._timeout))
            with cast(AIO, f):
                yield f
                self._manager.sync(cast(AIO, f))
                release_lock(cast(AIO, f))
            self._manager.commit_by_path(cast(AIO, f), path, mode)
        except BaseException as err:
            if f is not None:
                try:
                    self._manager.rollback(f)
                except Exception:  # pragma: no cover
                    raise err from None
            raise
        finally:
            lock.release()
            with suppress(Exception):
                release_lock(f)  # type: ignore[arg-type]

    @contextmanager
    def open_file(self, file: F) -> Generator[F | None, Any, None]:  # pragma: no cover # 用不上 暂不维护
        """
        打开文件 (上下文管理器)

        :param file: 文件对象
        :type file: IO
        :return: 返回值为IO对象的上下文管理器
        """
        with GlobalModifyLock:
            lock = FileLocks.setdefault(cast(TextIO, file).name, Lock())

        if not lock.acquire(timeout=-1 if self._timeout is None else self._timeout):
            raise TimeoutError("Timeout waiting for file lock")

        acquire_lock(file, self._flag, timeout=cast(Real | None, self._timeout), immediately_release=True)
        f: Optional[F] = None
        try:
            f = self._manager.from_file(file)
            acquire_lock(file, self._flag, timeout=cast(Real | None, self._timeout))
            with cast(AIO, f):
                yield f
                self._manager.sync(cast(AIO, f))
            release_lock(file)
            self._manager.commit(cast(AIO, f), file)
        except BaseException as err:
            if f is not None:
                try:
                    self._manager.rollback(f)
                except Exception:
                    raise err from None
            raise
        finally:
            lock.release()
            with suppress(Exception):
                release_lock(file)


def _timeout_checker(
        timeout: Optional[Real] = None,
        interval_increase_speed: Real = .03,  # type: ignore[assignment]
        max_interval: Real = .5,  # type: ignore[assignment]
) -> Generator[None, Any, Any]:  # pragma: no cover # 除了windows其他平台压根不会触发timeout
    def _calc_interval(interval: Real) -> Real:
        interval = min(cast(Real, interval + interval_increase_speed), max_interval)
        time.sleep(float(interval))
        return interval

    def _inf_loop() -> Generator[None, Any, Any]:
        interval: Real = 0  # type: ignore[assignment]
        while True:
            yield
            interval = _calc_interval(interval)

    def _timeout_loop() -> Generator[None, Any, Any]:
        start = time.time() + float(interval_increase_speed)
        interval: Real = 0  # type: ignore[assignment]
        while cast(Real, time.time() - start) < timeout:
            yield
            interval = _calc_interval(interval)
        raise TimeoutError("Timeout waiting for file lock")

    if timeout is None:
        return _inf_loop()
    return _timeout_loop()


def acquire_lock(
        file: AIO,
        flags: LockFlags,
        *,
        timeout: Optional[Real] = 1,  # type: ignore[assignment]
        immediately_release: bool = False
) -> None:
    """
    获取文件锁

    :param file: 文件对象
    :type file: IO
    :param flags: 锁类型
    :type flags: LockFlags
    :param timeout: 超时时间
    :type timeout: Optional[float]
    :param immediately_release: 是否立即释放锁
    :type immediately_release: bool
    """
    for _ in _timeout_checker(timeout):
        with suppress(portalocker.AlreadyLocked):
            portalocker.lock(file, cast(portalocker.LockFlags, flags))
            break
    if immediately_release:
        release_lock(file)


def release_lock(file: AIO) -> None:
    """
    释放文件锁

    :param file: 文件对象
    :type file: IO
    """
    portalocker.unlock(file)


def safe_open(
        path: str | Path,
        mode: str,
        *,
        timeout: Optional[float] = 1,
        flag: LockFlags = LockFlags.EXCLUSIVE,
        io_manager: Optional[ABCTempIOManager[Any]] = None,
        **manager_kwargs: Any
) -> ContextManager[AIO | TextIO]:
    """
    安全打开文件

    :param path: 文件路径
    :type path: str | pathlib.Path
    :param mode: 打开模式
    :type mode: str
    :param timeout: 超时时间
    :type timeout: Optional[float]
    :param flag: 锁类型
    :type flag: LockFlags
    :param io_manager: 临时文件管理器
    :type io_manager: Optional[ABCTempIOManager]
    :param manager_kwargs: 临时文件管理器参数
    :type manager_kwargs: dict

    :return: 返回IO对象的上下文管理器
    :rtype: ContextManager[IO | TextIO]
    """
    if io_manager is None:
        io_manager = TempTextIOManager(**manager_kwargs)
    return cast(
        ContextManager[AIO | TextIO],
        SafeOpen(io_manager, timeout, flag).open_path(path, mode)
    )


__all__ = (
    "FileLocks",
    "SafeOpen",
    "safe_open",
    "acquire_lock",
    "release_lock",
    "LockFlags",
    "GlobalModifyLock",
)
