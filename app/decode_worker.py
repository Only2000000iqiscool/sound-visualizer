from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from app.audio_engine import AudioEngineError, decode_file
from app.playback import prepare_pcm

logger = logging.getLogger(__name__)


_cache: OrderedDict[tuple[str, int, int], object] = OrderedDict()
_cache_lock = threading.Lock()


class DecodeWorker(QThread):
    finished_ok = pyqtSignal(object)
    failed = pyqtSignal(str)
    progress_changed = pyqtSignal(int, int, int, float, bool)

    def __init__(
        self,
        path: str,
        playback_spec: dict,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.path = path
        self.playback_spec = playback_spec

    def run(self) -> None:
        try:
            resolved = str(Path(self.path).resolve())
            logger.info("Decode worker started: %s", resolved)
            stat = Path(resolved).stat()
            key = (
                resolved,
                stat.st_mtime_ns,
                stat.st_size,
            )
            with _cache_lock:
                samples = _cache.get(key)
                if samples is not None:
                    _cache.move_to_end(key)

            if samples is not None:
                logger.info("Cache hit for %s", resolved)
                self.progress_changed.emit(
                    90,
                    samples.nbytes,
                    samples.nbytes,
                    0.0,
                    True,
                )
                self.progress_changed.emit(
                    94, samples.nbytes, samples.nbytes, 0.0, True
                )
                prepared = prepare_pcm(samples, self.playback_spec)
                self.progress_changed.emit(
                    96, samples.nbytes, samples.nbytes, 0.0, True
                )
                self.finished_ok.emit(prepared)
                return

            started = time.perf_counter()

            def report(percent: int, done: int, total: int) -> None:
                elapsed = time.perf_counter() - started
                if percent > 0:
                    eta = max(0.0, elapsed * (100 - percent) / percent)
                else:
                    eta = -1.0
                decode_percent = min(90, round(percent * 0.9))
                self.progress_changed.emit(
                    decode_percent,
                    done,
                    total,
                    eta,
                    False,
                )

            samples = decode_file(resolved, report)
            with _cache_lock:
                _cache[key] = samples
                _cache.move_to_end(key)
                while len(_cache) > 2:
                    _cache.popitem(last=False)
            self.progress_changed.emit(
                94, samples.nbytes, samples.nbytes, 0.0, False
            )
            prepared = prepare_pcm(samples, self.playback_spec)
            self.progress_changed.emit(
                96, samples.nbytes, samples.nbytes, 0.0, False
            )
            self.finished_ok.emit(prepared)
            logger.info("Decode worker finished: %s", resolved)
        except Exception as exc:
            logger.exception("Decode failed for %s", self.path)
            self.failed.emit(str(exc))
