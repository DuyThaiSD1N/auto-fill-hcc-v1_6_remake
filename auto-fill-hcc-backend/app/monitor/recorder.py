"""Bộ ghi thời gian + output từng công đoạn của MỘT lượt xử lý (điền / đính kèm / phân loại).

Đường chính chỉ được phép làm việc rẻ: ``time.perf_counter`` + append vào list + giữ THAM CHIẾU
tới output đã có sẵn trong bộ nhớ. Không copy, không serialize, không I/O — mọi việc nặng dồn
sang ``app.monitor.persist`` chạy nền sau khi đã trả kết quả cho người dùng.

Recorder nằm trong ``contextvars`` nên code ở tầng sâu (dịch vụ OCR, LLM client) tự gắn span vào
đúng lượt đang chạy mà không phải truyền tham số qua 148 runner + 176 planner. Không có recorder
(test, script, batch) → mọi hàm ở đây là no-op.

Nhóm thời gian lấy theo TIỀN TỐ tên span (``pre.`` / ``ocr.`` / ``llm.`` / ``post.`` /
``persist.``), không theo chỗ gọi: decode base64 nằm trong hàm OCR vẫn tính vào PRE. Thời gian
một nhóm = hợp các khoảng thời gian (không cộng dồn) để lượt gọi LLM song song không bị đếm lặp.
"""
from __future__ import annotations

import time
from contextvars import ContextVar
from typing import Any

from app.config import settings

GROUPS = ("pre", "ocr", "llm", "post", "persist")
# Nhóm tính vào thời gian người dùng chờ; persist tách riêng vì ở Auto Fill chạy sau response.
WAIT_GROUPS = ("pre", "ocr", "llm", "post")

_current: ContextVar["TraceRecorder | None"] = ContextVar("monitor_recorder", default=None)
_parent: ContextVar[int | None] = ContextVar("monitor_parent_span", default=None)
# Mốc perf_counter lúc middleware nhận request → recorder tính được cả phần nhận/parse body.
_origin: ContextVar[float | None] = ContextVar("monitor_origin", default=None)


def group_of(name: str) -> str | None:
    head = name.split(".", 1)[0]
    return head if head in GROUPS else None


class Span:
    __slots__ = ("id", "parent", "name", "t0", "t1", "status", "attrs")

    def __init__(self, sid: int, parent: int | None, name: str, t0: float, attrs: dict):
        self.id = sid
        self.parent = parent
        self.name = name
        self.t0 = t0
        self.t1: float | None = None
        self.status = "ok"
        self.attrs = attrs


class TraceRecorder:
    """Dữ liệu thô của một lượt; chỉ persist mới đọc lại để dựng document."""

    def __init__(
        self,
        kind: str,
        experience: str,
        *,
        origin: float | None = None,
        detail: str = "full",
        **meta: Any,
    ):
        # origin = mốc perf_counter lúc request bắt đầu (middleware) để tính cả phần nhận request.
        self.origin = origin if origin is not None else time.perf_counter()
        self.kind = kind
        self.experience = experience
        self.detail = detail
        self.meta: dict[str, Any] = dict(meta)
        self.spans: list[Span] = []
        self.outputs: dict[str, Any] = {}
        self.llm_calls: list[dict] = []
        self.ocr_files: list[dict] = []
        self.counters: dict[str, float] = {}
        self.flags: dict[str, bool] = {}
        self.errors: list[str] = []
        self.outcome = "ok"  # ok | partial (có errors[]) | error (lượt hỏng)
        self.marks: dict[str, float] = {}
        self.wait_end: float | None = None
        self._next_id = 0

    # --- ghi -------------------------------------------------------------------------------
    def open_span(self, name: str, attrs: dict) -> Span:
        self._next_id += 1
        span = Span(self._next_id, _parent.get(), name, time.perf_counter(), attrs)
        self.spans.append(span)
        return span

    def add_span(self, name: str, t0: float, t1: float, **attrs: Any) -> None:
        """Span đo bằng khoảng trống giữa hai mốc (vd hậu xử lý của package quanh runner chung)."""
        self._next_id += 1
        span = Span(self._next_id, _parent.get(), name, t0, attrs)
        span.t1 = max(t1, t0)
        self.spans.append(span)

    def new_llm_call(self, **fields: Any) -> dict:
        call = {"n": len(self.llm_calls) + 1, "t0": self.ms(time.perf_counter()), **fields}
        self.llm_calls.append(call)
        return call

    def find_llm_call(self, raw: str) -> dict | None:
        """Lần gọi LLM sinh ra đúng chuỗi ``raw`` (so định danh trước, rồi so nội dung)."""
        for call in reversed(self.llm_calls):
            if call.get("raw") is raw:
                return call
        for call in reversed(self.llm_calls):
            if call.get("raw") == raw:
                return call
        return None

    def output(self, key: str, value: Any) -> None:
        """Giữ THAM CHIẾU; ``value`` là hàm không tham số → chỉ gọi lúc ghi nền (vd dựng
        response qua Pydantic) để không tốn CPU trên đường chính."""
        if self.detail == "full":
            self.outputs[key] = value

    def count(self, key: str, value: float = 1) -> None:
        self.counters[key] = self.counters.get(key, 0) + value

    def flag(self, key: str, value: bool = True) -> None:
        self.flags[key] = self.flags.get(key, False) or value

    def error(self, message: str) -> None:
        if len(self.errors) < 50:
            self.errors.append(str(message)[:500])

    def mark(self, name: str) -> None:
        self.marks[name] = time.perf_counter()

    def close_gap(self, mark: str, name: str) -> None:
        """Span ``name`` từ mốc ``mark`` tới bây giờ (vd runner chung xong → pipeline package trả
        = hậu xử lý/mapper của package), không phải sửa từng package."""
        t0 = self.marks.pop(mark, None)
        if t0 is not None:
            self.add_span(name, t0, time.perf_counter())

    def set_outcome(self, outcome: str) -> None:
        # error > partial > ok: không hạ mức đã ghi.
        rank = {"ok": 0, "partial": 1, "error": 2}
        if rank.get(outcome, 0) > rank.get(self.outcome, 0):
            self.outcome = outcome

    def mark_wait_end(self) -> None:
        """Mốc kết quả sẵn sàng cho người dùng; lớp ngoài (vd v2 bọc v1) gọi sau thì ghi đè."""
        self.wait_end = time.perf_counter()

    # --- tóm tắt (chạy trong persist, KHÔNG gọi trên đường chính) --------------------------
    def ms(self, t: float) -> int:
        return int(round((t - self.origin) * 1000))

    def summary(self) -> dict:
        now = time.perf_counter()
        wait_end = self.wait_end or now
        closed = [s for s in self.spans if s.t1 is not None]
        by_id = {s.id: s for s in closed}
        children: dict[int, list[Span]] = {}
        for s in closed:
            if s.parent is not None and s.parent in by_id:
                children.setdefault(s.parent, []).append(s)

        own: dict[str, list[tuple[float, float]]] = {g: [] for g in GROUPS}
        for s in closed:
            g = group_of(s.name)
            if g is None:
                continue
            cut = [(c.t0, c.t1) for c in children.get(s.id, []) if group_of(c.name) not in (g, None)]
            own[g].extend(_subtract([(s.t0, s.t1)], _union(cut)))

        groups = {g: _length(_union(own[g])) for g in GROUPS}
        wait_window = [(self.origin, wait_end)]
        busy = _union([iv for g in GROUPS for iv in own[g]])
        wait_ms = (wait_end - self.origin) * 1000
        other_ms = _length(_subtract(wait_window, busy))
        # Ghi DB nằm TRONG thời gian chờ (đính kèm, handfree ghi trước khi trả) — Auto Fill điền
        # ghi sau response nên phần này = 0.
        after_wait = [(wait_end, float("inf"))]
        persist_wait_ms = _length(_subtract(_union(own["persist"]), after_wait))

        # Bảng bước = thời gian RIÊNG của từng bước (trừ bước con) → span bọc ngoài (vd planner
        # đính kèm bọc cả OCR/LLM) chỉ còn đúng phần logic của chính nó; cộng lại ≈ tổng thời gian.
        steps: dict[str, float] = {}
        by_name: dict[str, list[tuple[float, float]]] = {}
        for s in closed:
            cut = _union([(c.t0, c.t1) for c in children.get(s.id, [])])
            by_name.setdefault(s.name, []).extend(_subtract([(s.t0, s.t1)], cut))
        for name, ivs in by_name.items():
            steps[name] = _length(_union(ivs))

        llm_sum = sum(c.get("ms", 0) for c in self.llm_calls)
        counters = {
            **self.counters,
            "llm_calls": len(self.llm_calls),
            "llm_sum": llm_sum,
            "tok_in": sum(c.get("tokens_in") or 0 for c in self.llm_calls),
            "tok_out": sum(c.get("tokens_out") or 0 for c in self.llm_calls),
        }
        return {
            "v": 1,
            "wait": int(round(wait_ms)),
            "wall": int(round((max([wait_end] + [s.t1 for s in closed]) - self.origin) * 1000)),
            "g": {g: int(round(groups[g])) for g in WAIT_GROUPS},
            "other": int(round(other_ms)),
            "persist": int(round(groups["persist"])),
            "persist_wait": int(round(persist_wait_ms)),
            "s": {k: int(round(v)) for k, v in sorted(steps.items())},
            "n": {k: int(round(v)) for k, v in counters.items()},
            "f": dict(self.flags),
        }


# --- interval helpers (đơn vị giây perf_counter; _length trả ms) ------------------------------
def _union(ivs: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for a, b in sorted(ivs):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _subtract(ivs: list[tuple[float, float]], cuts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for a, b in ivs:
        pieces = [(a, b)]
        for c, d in cuts:
            nxt = []
            for x, y in pieces:
                if d <= x or c >= y:
                    nxt.append((x, y))
                    continue
                if c > x:
                    nxt.append((x, c))
                if d < y:
                    nxt.append((d, y))
            pieces = nxt
        out.extend(pieces)
    return out


def _length(ivs: list[tuple[float, float]]) -> float:
    return sum(b - a for a, b in ivs) * 1000


# --- API dùng ở mọi nơi ------------------------------------------------------------------------
class _SpanCtx:
    """Context manager dùng được cả ``with`` lẫn ``async with``."""

    __slots__ = ("_rec", "_name", "_attrs", "_span", "_token")

    def __init__(self, rec: TraceRecorder, name: str, attrs: dict):
        self._rec = rec
        self._name = name
        self._attrs = attrs
        self._span: Span | None = None
        self._token = None

    def __enter__(self) -> Span:
        self._span = self._rec.open_span(self._name, self._attrs)
        self._token = _parent.set(self._span.id)
        return self._span

    def __exit__(self, exc_type, exc, tb) -> bool:
        span = self._span
        if span is not None:
            span.t1 = time.perf_counter()
            if exc is not None:
                span.status = "error"
                span.attrs["error"] = f"{type(exc).__name__}: {exc}"[:300]
        if self._token is not None:
            _parent.reset(self._token)
        return False

    async def __aenter__(self) -> Span:
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return self.__exit__(exc_type, exc, tb)


class _NoopSpan:
    __slots__ = ()

    def __enter__(self):
        return _NOOP_TARGET

    def __exit__(self, *_):
        return False

    async def __aenter__(self):
        return _NOOP_TARGET

    async def __aexit__(self, *_):
        return False


class _NoopTarget:
    """Thay cho Span khi không ghi: gán ``attrs[...]`` vào đây là mất, không lỗi."""

    __slots__ = ()

    @property
    def attrs(self) -> dict:
        return {}


_NOOP = _NoopSpan()
_NOOP_TARGET = _NoopTarget()


def start(kind: str, experience: str, *, origin: float | None = None, fresh: bool = False,
          **meta: Any) -> TraceRecorder | None:
    """Tạo recorder cho lượt hiện tại và gắn vào context; ``TRACE_DETAIL=off`` → None.

    Đã có recorder cùng ``kind`` trong context (v2 bọc v1) → dùng lại, chỉ bổ sung meta;
    ``fresh=True`` (tác vụ nền handfree) → luôn tạo mới.
    """
    detail = settings.trace_detail
    if detail == "off":
        return None
    existing = _current.get()
    if existing is not None and existing.kind == kind and not fresh:
        existing.meta.update(meta)
        return existing
    if origin is None:
        origin = _origin.get()
    rec = TraceRecorder(kind, experience, origin=origin, detail=detail, **meta)
    _current.set(rec)
    return rec


def set_origin(t: float) -> None:
    _origin.set(t)


def bind(rec: TraceRecorder | None) -> None:
    """Gắn recorder vào context hiện tại (tác vụ nền nhận recorder qua tham số)."""
    if rec is not None:
        _current.set(rec)


def mark(name: str) -> None:
    rec = _current.get()
    if rec is not None:
        rec.mark(name)


def current() -> TraceRecorder | None:
    return _current.get()


def span(name: str, **attrs: Any):
    rec = _current.get()
    if rec is None:
        return _NOOP
    return _SpanCtx(rec, name, attrs)


def output(key: str, value: Any) -> None:
    rec = _current.get()
    if rec is not None:
        rec.output(key, value)


def count(key: str, value: float = 1) -> None:
    rec = _current.get()
    if rec is not None:
        rec.count(key, value)


def flag(key: str, value: bool = True) -> None:
    rec = _current.get()
    if rec is not None:
        rec.flag(key, value)
