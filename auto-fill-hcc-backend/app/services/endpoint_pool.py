"""Chọn máy gọi khi nhiều máy cùng làm một việc (LLM, OCR): LB ngoài trước, LB lỗi / không có thì BE tự cân bằng.

Thứ tự thử một lượt:
1. LB ngoài (``kind="lb"``) nếu có cấu hình và không vừa lỗi.
2. Máy chính / phụ do BE tự chia: bốc ngẫu nhiên có trọng số, trọng số giảm theo thời gian xử lý đo được gần đây
   (ms trên một đơn vị việc, bình phương để máy quá tải nhường hẳn phần lớn lượt) và số request đang chạy trên máy đó.
   Máy chậm hẳn vẫn nhận một phần nhỏ để biết khi nào nó hồi lại; máy chưa đo coi nhanh như máy tốt nhất đang biết.
3. Máy vừa lỗi (trong ``down_s`` giây) hoặc bị né (``avoid``) xếp cuối — cả dãy cùng lỗi vẫn thử đủ.

Số liệu giữ trong bộ nhớ từng worker: mỗi worker tự đo, không cần chỗ dùng chung.
"""
import random
import time
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    url: str
    kind: str  # "lb" | "chinh" | "phu" — ghi vào trace (timing.n: llm_lb, ocr_chinh…)
    model: str = ""
    api_key: str = ""


class _Stat:
    __slots__ = ("inflight", "cost", "down_until")

    def __init__(self) -> None:
        self.inflight = 0
        self.cost: float | None = None  # ms trên một đơn vị việc, trung bình trượt
        self.down_until = 0.0


class Pool:
    def __init__(self, down_s: float, alpha: float = 0.3) -> None:
        self.down_s = down_s
        self.alpha = alpha
        # False → giữ thứ tự khai báo (chính trước phụ), chỉ còn xếp máy lỗi xuống cuối — cho test cần thứ tự cố định.
        self.balance = True
        self._stats: dict[str, _Stat] = {}

    def reset(self) -> None:
        self._stats.clear()

    def _stat(self, url: str) -> _Stat:
        return self._stats.setdefault(url, _Stat())

    def order(self, targets: list[Target], *, avoid: set[str] | frozenset[str] = frozenset()) -> list[Target]:
        now = time.monotonic()
        targets = [t for t in targets if t.url]
        ready = [t for t in targets if self._stat(t.url).down_until <= now and t.url not in avoid]
        later = [t for t in targets if t not in ready]
        lb = [t for t in ready if t.kind == "lb"]
        return lb + self._balanced([t for t in ready if t.kind != "lb"]) + later

    def _balanced(self, pool: list[Target]) -> list[Target]:
        if len(pool) < 2 or not self.balance:
            return pool
        known = [self._stat(t.url).cost for t in pool if self._stat(t.url).cost]
        base = min(known) if known else 1.0

        def weight(t: Target) -> float:
            s = self._stat(t.url)
            return 1.0 / ((s.inflight + 1) * (s.cost or base) ** 2)

        first = random.choices(pool, weights=[weight(t) for t in pool])[0]
        return [first] + sorted((t for t in pool if t is not first), key=weight, reverse=True)

    @contextmanager
    def track(self, url: str):
        """Bọc một request tới ``url``: đếm đang chạy, xong thì cập nhật thời gian / lỗi thì xếp máy xuống cuối.
        Nơi gọi ghi ``m["units"]`` (số token, số trang…) để thời gian so được giữa lượt to và lượt nhỏ."""
        s = self._stat(url)
        s.inflight += 1
        t0 = time.monotonic()
        m = {"units": 1}
        try:
            yield m
        except Exception:
            s.down_until = time.monotonic() + self.down_s
            raise
        else:
            s.down_until = 0.0
            ms = (time.monotonic() - t0) * 1000 / max(float(m.get("units") or 1), 1.0)
            s.cost = ms if s.cost is None else s.cost + self.alpha * (ms - s.cost)
        finally:
            s.inflight -= 1
