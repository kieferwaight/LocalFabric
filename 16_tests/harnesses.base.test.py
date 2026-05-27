"""Contract tests for harnesses.base — Protocol/ABC surface, lifecycle ordering,
error surfaces, and default-implementation behaviour.

No real providers, no network, no subprocess. Every test completes in well under
a second.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from harnesses.base import Harness, HarnessError, HarnessStatus

# ---------------------------------------------------------------------------
# Minimal concrete subclass (test double)
# ---------------------------------------------------------------------------


class FakeHarness(Harness):
    """Minimal concrete implementation of Harness for contract testing."""

    name = "fake"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.start_calls: int = 0
        self.stop_calls: int = 0
        self.invoke_calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []

    def start(self) -> HarnessStatus:
        self.start_calls += 1
        return self._set_state("running")

    def stop(self) -> HarnessStatus:
        self.stop_calls += 1
        return self._set_state("stopped")

    def status(self) -> HarnessStatus:
        return HarnessStatus(name=self.name, state=self._state)

    def invoke(self, request: dict[str, Any]) -> dict[str, Any]:
        self.invoke_calls.append(dict(request))
        return {"result": "ok"}

    def stream(self, request: dict[str, Any]) -> Iterator[dict[str, Any]]:
        self.stream_calls.append(dict(request))
        yield {"chunk": "a"}
        yield {"chunk": "b"}

    def logs(self, tail: int = 50) -> list[str]:
        return list(self._logs)[-tail:]

    def health(self) -> HarnessStatus:
        return HarnessStatus(name=self.name, state=self._state)


# ---------------------------------------------------------------------------
# Protocol shape — required abstract methods exist with expected signatures
# ---------------------------------------------------------------------------

ABSTRACT_METHODS = [
    "start",
    "stop",
    "status",
    "invoke",
    "stream",
    "logs",
    "health",
]


@pytest.mark.parametrize("method_name", ABSTRACT_METHODS)
def test_abstract_method_is_declared_on_harness(method_name: str) -> None:
    assert hasattr(Harness, method_name), f"Harness.{method_name} not found"
    method = getattr(Harness, method_name)
    assert callable(method)


def test_harness_cannot_be_instantiated_directly() -> None:
    """Harness is abstract — direct instantiation must raise TypeError."""
    with pytest.raises(TypeError):
        Harness()  # type: ignore[abstract]


def test_harness_is_abstract_class() -> None:
    assert inspect.isabstract(Harness)


def test_start_signature() -> None:
    sig = inspect.signature(Harness.start)
    params = list(sig.parameters)
    assert params == ["self"]


def test_stop_signature() -> None:
    sig = inspect.signature(Harness.stop)
    params = list(sig.parameters)
    assert params == ["self"]


def test_status_signature() -> None:
    sig = inspect.signature(Harness.status)
    params = list(sig.parameters)
    assert params == ["self"]


def test_invoke_signature() -> None:
    sig = inspect.signature(Harness.invoke)
    params = list(sig.parameters)
    assert "self" in params
    assert "request" in params


def test_stream_signature() -> None:
    sig = inspect.signature(Harness.stream)
    params = list(sig.parameters)
    assert "self" in params
    assert "request" in params


def test_logs_has_tail_parameter_with_default_50() -> None:
    sig = inspect.signature(Harness.logs)
    assert "tail" in sig.parameters
    assert sig.parameters["tail"].default == 50


def test_health_signature() -> None:
    sig = inspect.signature(Harness.health)
    params = list(sig.parameters)
    assert params == ["self"]


# ---------------------------------------------------------------------------
# HarnessError is a subclass of RuntimeError
# ---------------------------------------------------------------------------


def test_harness_error_is_runtime_error() -> None:
    assert issubclass(HarnessError, RuntimeError)


def test_harness_error_can_be_raised_and_caught() -> None:
    with pytest.raises(HarnessError, match="boom"):
        raise HarnessError("boom")


def test_harness_error_caught_as_runtime_error() -> None:
    with pytest.raises(RuntimeError):
        raise HarnessError("also a runtime error")


# ---------------------------------------------------------------------------
# HarnessStatus dataclass
# ---------------------------------------------------------------------------


def test_harness_status_ok_returns_true_for_running() -> None:
    s = HarnessStatus(name="x", state="running")
    assert s.ok() is True


def test_harness_status_ok_returns_true_for_ready() -> None:
    s = HarnessStatus(name="x", state="ready")
    assert s.ok() is True


def test_harness_status_ok_returns_false_for_stopped() -> None:
    s = HarnessStatus(name="x", state="stopped")
    assert s.ok() is False


def test_harness_status_ok_returns_false_for_error() -> None:
    s = HarnessStatus(name="x", state="error")
    assert s.ok() is False


def test_harness_status_to_dict_roundtrip() -> None:
    s = HarnessStatus(name="my-harness", state="running", detail="all good", metadata={"k": 1})
    d = s.to_dict()
    assert d == {
        "name": "my-harness",
        "state": "running",
        "detail": "all good",
        "metadata": {"k": 1},
    }


def test_harness_status_to_dict_metadata_is_copy() -> None:
    """Mutations to the returned dict's metadata must not affect the original."""
    original_meta = {"k": 1}
    s = HarnessStatus(name="x", state="running", metadata=original_meta)
    d = s.to_dict()
    d["metadata"]["k"] = 999
    assert s.metadata["k"] == 1


def test_harness_status_default_detail_is_empty_string() -> None:
    s = HarnessStatus(name="x", state="stopped")
    assert s.detail == ""


def test_harness_status_default_metadata_is_empty_dict() -> None:
    s = HarnessStatus(name="x", state="stopped")
    assert s.metadata == {}


# ---------------------------------------------------------------------------
# Harness.__init__ — config and initial state
# ---------------------------------------------------------------------------


def test_init_default_config_is_empty_dict() -> None:
    h = FakeHarness()
    assert h.config == {}


def test_init_accepts_config_mapping() -> None:
    h = FakeHarness(config={"key": "value"})
    assert h.config["key"] == "value"


def test_init_config_is_a_copy() -> None:
    original = {"key": "value"}
    h = FakeHarness(config=original)
    h.config["key"] = "mutated"
    assert original["key"] == "value"


def test_init_state_is_stopped() -> None:
    h = FakeHarness()
    assert h._state == "stopped"


def test_init_logs_deque_is_empty() -> None:
    h = FakeHarness()
    assert len(h._logs) == 0


def test_init_logger_named_after_harness() -> None:
    h = FakeHarness()
    assert h._logger.name == "harness.fake"


# ---------------------------------------------------------------------------
# Lifecycle ordering: init → start → invoke → stop
# ---------------------------------------------------------------------------


def test_start_transitions_state_to_running() -> None:
    h = FakeHarness()
    result = h.start()
    assert h._state == "running"
    assert isinstance(result, HarnessStatus)
    assert result.state == "running"


def test_stop_transitions_state_to_stopped() -> None:
    h = FakeHarness()
    h.start()
    result = h.stop()
    assert h._state == "stopped"
    assert isinstance(result, HarnessStatus)
    assert result.state == "stopped"


def test_invoke_returns_dict() -> None:
    h = FakeHarness()
    h.start()
    result = h.invoke({"prompt": "hello"})
    assert isinstance(result, dict)
    assert result == {"result": "ok"}


def test_invoke_records_request() -> None:
    h = FakeHarness()
    h.start()
    h.invoke({"prompt": "test"})
    assert h.invoke_calls == [{"prompt": "test"}]


def test_stream_yields_events() -> None:
    h = FakeHarness()
    h.start()
    events = list(h.stream({"prompt": "stream me"}))
    assert events == [{"chunk": "a"}, {"chunk": "b"}]


def test_stream_records_request() -> None:
    h = FakeHarness()
    h.start()
    list(h.stream({"prompt": "x"}))
    assert h.stream_calls == [{"prompt": "x"}]


def test_full_lifecycle_start_invoke_stop() -> None:
    h = FakeHarness()
    assert h._state == "stopped"
    h.start()
    assert h._state == "running"
    h.invoke({"q": 1})
    assert h._state == "running"
    h.stop()
    assert h._state == "stopped"


# ---------------------------------------------------------------------------
# _set_state and _record — default implementations on the base
# ---------------------------------------------------------------------------


def test_set_state_updates_internal_state() -> None:
    h = FakeHarness()
    snap = h._set_state("starting", "warming up")
    assert h._state == "starting"
    assert snap.state == "starting"
    assert snap.detail == "warming up"
    assert snap.name == "fake"


def test_set_state_without_detail() -> None:
    h = FakeHarness()
    snap = h._set_state("running")
    assert snap.detail == ""


def test_set_state_appends_to_logs() -> None:
    h = FakeHarness()
    h._set_state("running")
    assert any("running" in line for line in h._logs)


def test_record_appends_line_to_logs() -> None:
    h = FakeHarness()
    h._record("hello from test")
    assert "hello from test" in h._logs


def test_logs_respects_tail_parameter() -> None:
    h = FakeHarness()
    for i in range(10):
        h._record(f"line {i}")
    last3 = h.logs(tail=3)
    assert len(last3) == 3
    assert last3[-1] == "line 9"


def test_logs_returns_all_when_tail_exceeds_buffer() -> None:
    h = FakeHarness()
    for i in range(5):
        h._record(f"line {i}")
    all_logs = h.logs(tail=100)
    assert len(all_logs) == 5


def test_log_buffer_size_caps_deque() -> None:
    """Records beyond log_buffer_size silently evict the oldest."""

    class SmallBufferHarness(FakeHarness):
        log_buffer_size = 4

    h = SmallBufferHarness()
    for i in range(10):
        h._record(f"line {i}")
    assert len(h._logs) == 4
    assert "line 9" in h._logs
    assert "line 0" not in h._logs


def test_set_state_with_detail_includes_detail_in_log() -> None:
    h = FakeHarness()
    h._set_state("error", "connection refused")
    assert any("connection refused" in line for line in h._logs)


# ---------------------------------------------------------------------------
# Context-manager protocol (__enter__ / __exit__)
# ---------------------------------------------------------------------------


def test_context_manager_calls_start_and_stop() -> None:
    h = FakeHarness()
    with h as entered:
        assert entered is h
        assert h.start_calls == 1
        assert h._state == "running"
    assert h.stop_calls == 1
    assert h._state == "stopped"


def test_context_manager_calls_stop_on_exception() -> None:
    h = FakeHarness()
    with pytest.raises(ValueError):
        with h:
            raise ValueError("oops")
    assert h.stop_calls == 1


# ---------------------------------------------------------------------------
# Class-level attribute defaults
# ---------------------------------------------------------------------------


def test_default_name_attribute_is_harness_string() -> None:
    """Harness.name class attribute defaults to 'harness'."""
    assert Harness.name == "harness"


def test_default_log_buffer_size_is_256() -> None:
    assert Harness.log_buffer_size == 256


def test_subclass_can_override_name() -> None:
    assert FakeHarness.name == "fake"


def test_subclass_name_used_in_logger() -> None:
    h = FakeHarness()
    assert "fake" in h._logger.name


# ---------------------------------------------------------------------------
# _record emits to the logging subsystem
# ---------------------------------------------------------------------------


def test_record_emits_debug_log(caplog: pytest.LogCaptureFixture) -> None:
    h = FakeHarness()
    with caplog.at_level(logging.DEBUG, logger="harness.fake"):
        h._record("debug message")
    assert any("debug message" in rec.message for rec in caplog.records)
