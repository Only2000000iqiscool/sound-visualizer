from __future__ import annotations

import os
import sys
import threading
from contextlib import contextmanager


@contextmanager
def _silence_native_stderr():
    if not sys.platform.startswith("linux"):
        yield
        return
    saved_stderr = os.dup(2)
    try:
        with open(os.devnull, "w") as devnull:
            os.dup2(devnull.fileno(), 2)
            yield
    finally:
        os.dup2(saved_stderr, 2)
        os.close(saved_stderr)


_pa = None
_lock = threading.Lock()


def get_pyaudio():
    global _pa
    if _pa is not None:
        return _pa
    with _lock:
        if _pa is None:
            try:
                import pyaudio
            except ImportError as exc:
                raise ImportError("PyAudio ist nicht installiert.") from exc
            with _silence_native_stderr():
                _pa = pyaudio.PyAudio()
        return _pa


def terminate_pyaudio() -> None:
    global _pa
    with _lock:
        if _pa is not None:
            try:
                with _silence_native_stderr():
                    _pa.terminate()
            except Exception:
                pass
            _pa = None
