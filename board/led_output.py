"""Send the latest complete LED frame without holding the game or USB locks."""
from __future__ import annotations

from dataclasses import dataclass
import logging
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)


class LedOutputError(ConnectionError):
    pass


@dataclass(frozen=True)
class LedFrame:
    updates: tuple[tuple[int, tuple[int, ...]], ...]
    brightness: int | None = None
    transition_ms: int | None = None


class LedOutput:
    """One writer, one desired frame, retries until superseded or closed.

    Submission acknowledges ownership of the frame, not delivery. USB input
    runs independently; wait_applied is for explicit output checks and closing.
    """

    def __init__(self, send: Callable[[LedFrame], bool], *, retry_s: float = .25) -> None:
        self._send = send
        self._retry_s = retry_s
        self._condition = threading.Condition()
        self._desired: LedFrame | None = None
        self._revision = 0
        self._applied = 0
        self._closed = False
        self._error = ''
        self._last_attempt: dict[str, object] = {}
        self._thread = threading.Thread(target=self._work, name='board-led-output', daemon=True)
        self._thread.start()

    def submit(self, frame: LedFrame) -> int:
        with self._condition:
            if self._closed:
                raise LedOutputError('Wysyłanie podświetlenia jest zamknięte.')
            if frame != self._desired:
                self._desired = frame
                self._revision += 1
                self._condition.notify_all()
            return self._revision

    @property
    def revision(self) -> int:
        with self._condition:
            return self._revision

    @property
    def status(self) -> dict[str, object]:
        with self._condition:
            return dict(revision=self._revision, applied_revision=self._applied,
                        pending=self._revision != self._applied, error=self._error,
                        last_attempt=dict(self._last_attempt))

    def wake(self) -> None:
        with self._condition:
            self._condition.notify_all()

    def wait_applied(self, revision: int, cancelled: threading.Event, *, timeout_s: float = 5) -> bool:
        deadline = time.monotonic() + timeout_s
        with self._condition:
            while True:
                if cancelled.is_set() or self._closed or revision != self._revision:
                    return False
                if self._applied == revision:
                    return True
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise LedOutputError('Nie potwierdzono podświetlenia planszy. Sprawdź WLED i ponów wybór.')
                self._condition.wait(remaining)

    def _work(self) -> None:
        last_warning = 0.0
        last_error = ''
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._closed or self._revision != self._applied)
                if self._closed:
                    return
                revision, frame = self._revision, self._desired
                assert frame is not None
            started = time.monotonic()
            error = ''
            try:
                ok = self._send(frame)
                if not ok:
                    error = 'WLED nie potwierdził ramki.'
            except Exception as exc:
                ok, error = False, str(exc)
            elapsed_ms = round((time.monotonic() - started) * 1000)
            now = time.monotonic()
            if (ok and elapsed_ms >= 250) or (not ok and (error != last_error or now - last_warning >= 5)):
                logger.warning('WLED frame revision=%s confirmed=%s elapsed_ms=%s error=%s',
                               revision, ok, elapsed_ms, error)
                last_warning = now
            last_error = error
            with self._condition:
                self._last_attempt = dict(revision=revision, confirmed=ok,
                                          elapsed_ms=elapsed_ms, error=error)
                if revision == self._revision:
                    self._error = error
                    if ok:
                        self._applied = revision
                self._condition.notify_all()
                if not ok and revision == self._revision and not self._closed:
                    self._condition.wait(self._retry_s)

    def close(self, *, timeout_s: float = 5) -> None:
        try:
            self.wait_applied(self.revision, threading.Event(), timeout_s=timeout_s)
        except LedOutputError:
            logger.warning('Zamknięcie WLED bez potwierdzenia ostatniej ramki.')
        finally:
            with self._condition:
                self._closed = True
                self._condition.notify_all()
            self._thread.join(timeout=timeout_s)
