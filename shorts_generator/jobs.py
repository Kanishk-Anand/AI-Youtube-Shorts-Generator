"""Run the pipeline as a job: structured progress events and cooperative cancellation.

Two ways to use it:

  * Synchronously: pass `on_event` and/or `cancel` to `generate_shorts(...)`.
  * In the background (what a GUI wants): `start_job(url, ...)` returns a `Job` you can
    iterate for events, `cancel()`, and ask for the `result()`.

The pipeline code never needs a context object passed around: it calls the module-level
`emit`, `checkpoint` and `sleep` helpers, which look up the job running on the current thread
and do nothing when there isn't one (so plain library and CLI use cost nothing).

Cancellation is cooperative: it takes effect at the next checkpoint, so a request that is already
in flight (for example one LLM call) finishes first. ffmpeg runs and downloads stop promptly.
`CancelledError` derives from BaseException, like asyncio's, so a stray `except Exception` in the
pipeline cannot swallow a cancel.
"""
from __future__ import annotations

import contextlib
import contextvars
import queue
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Iterator, Optional


class CancelledError(BaseException):
    """Raised inside the pipeline when the running job is cancelled."""


@dataclass(frozen=True)
class ProgressEvent:
    """One progress update.

    stage   download | transcribe | highlights | rerank | render | pipeline
    status  start | progress | done | warn | error | cancelled | finished
    """

    stage: str
    status: str
    message: str = ""
    current: Optional[float] = None
    total: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    @property
    def fraction(self) -> Optional[float]:
        if self.current is None or not self.total:
            return None
        return max(0.0, min(1.0, self.current / self.total))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["fraction"] = self.fraction
        return d


class JobContext:
    def __init__(self, on_event: Optional[Callable[[ProgressEvent], None]] = None,
                 cancel: Optional[threading.Event] = None):
        self._on_event = on_event
        self.cancel_event = cancel if cancel is not None else threading.Event()

    def emit_event(self, event: ProgressEvent) -> None:
        if self._on_event is not None:
            try:
                self._on_event(event)
            except Exception:  # a broken listener must never break the pipeline
                pass

    def check(self) -> None:
        if self.cancel_event.is_set():
            raise CancelledError()

    def sleep(self, seconds: float) -> None:
        """Sleep, but wake up and raise as soon as the job is cancelled."""
        if self.cancel_event.wait(seconds):
            raise CancelledError()


_current: "contextvars.ContextVar[Optional[JobContext]]" = contextvars.ContextVar("shorts_job", default=None)


def current() -> Optional[JobContext]:
    return _current.get()


@contextlib.contextmanager
def activate(ctx: JobContext) -> Iterator[JobContext]:
    token = _current.set(ctx)
    try:
        yield ctx
    finally:
        _current.reset(token)


def emit(stage: str, status: str, message: str = "", current: Optional[float] = None,
         total: Optional[float] = None, **data: Any) -> None:
    ctx = _current.get()
    if ctx is not None:
        ctx.emit_event(ProgressEvent(stage, status, message, current, total, data))


def checkpoint() -> None:
    """Raise CancelledError if the running job was cancelled. No-op outside a job."""
    ctx = _current.get()
    if ctx is not None:
        ctx.check()


def sleep(seconds: float) -> None:
    ctx = _current.get()
    if ctx is not None:
        ctx.sleep(seconds)
    else:
        time.sleep(seconds)


class Job:
    """Runs `fn(ctx)` on a background thread and exposes events, cancel and the result."""

    def __init__(self, fn: Callable[[JobContext], Any],
                 on_event: Optional[Callable[[ProgressEvent], None]] = None):
        self._fn = fn
        self._listener = on_event
        self._queue: "queue.Queue[Optional[ProgressEvent]]" = queue.Queue()
        self._cancel = threading.Event()
        # Completion is tracked with an explicit Event, not Thread.join()/is_alive(): a Ctrl+C that lands
        # inside join() can make them report "finished" while the thread is still running.
        self._finished = threading.Event()
        self._ctx = JobContext(self._push, self._cancel)
        self._thread = threading.Thread(target=self._run, name="shorts-job", daemon=True)
        self._result: Any = None
        self._error: Optional[BaseException] = None
        self._state = "pending"

    # -- lifecycle
    def start(self) -> "Job":
        self._state = "running"
        self._thread.start()
        return self

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def state(self) -> str:
        """pending | running | done | failed | cancelled"""
        return self._state

    @property
    def cancel_requested(self) -> bool:
        return self._cancel.is_set()

    # -- results
    def events(self) -> Iterator[ProgressEvent]:
        """Yield events as they happen; returns when the job has finished."""
        while True:
            try:
                event = self._queue.get(timeout=0.2)
            except queue.Empty:
                if self._finished.is_set() and self._queue.empty():
                    return
                continue
            if event is None:
                return
            yield event

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until the job has finished. Returns False if `timeout` ran out first."""
        return self._finished.wait(timeout)

    def result(self, timeout: Optional[float] = None) -> Any:
        """The job's return value. Raises its exception, or CancelledError if it was cancelled."""
        if not self.wait(timeout):
            raise TimeoutError("job is still running")
        if self._state == "cancelled":
            raise CancelledError()
        if self._error is not None:
            raise self._error
        return self._result

    # -- internals
    def _push(self, event: ProgressEvent) -> None:
        self._queue.put(event)
        if self._listener is not None:
            try:
                self._listener(event)
            except Exception:
                pass

    def _run(self) -> None:
        try:
            with activate(self._ctx):
                self._result = self._fn(self._ctx)
            self._state = "done"
        except CancelledError:
            self._state = "cancelled"
        except BaseException as exc:  # a worker thread must never die without recording why
            self._error = exc
            self._state = "failed"
        finally:
            self._queue.put(None)
            self._finished.set()  # last, so state/result/error are already recorded
