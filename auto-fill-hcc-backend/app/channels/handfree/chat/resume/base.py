"""Luồng khôi phục chung cho mọi họ cổng; mỗi họ cổng một lớp con khai các bước của mình.

Mỗi bước gắn với một tác vụ nền của pipeline_runner. Lưu: sau mỗi lượt, `capture_<bước>` sao kết quả của tác vụ
(cùng phần cán bộ đã sửa) vào bản ghi. Khôi phục: công dân vẫn đi tuần tự trên cổng; tới bước nào flow bật tác vụ
của bước đó thì tác vụ bị chặn (replay.py) và `apply_<bước>` nạp kết quả đã lưu, đúng như tác vụ vừa chạy xong.
"""
from dataclasses import dataclass

from app.channels.handfree.chat.resume import replay


@dataclass(frozen=True)
class Step:
    key: str        # khoá dữ liệu trong bản ghi: steps[key]
    pipeline: str   # tác vụ nền được thay: pipeline_runner owner | process | attach
    state: str      # state hội thoại trong lúc tác vụ đó chạy
    event: str      # sự kiện flow nhận khi tác vụ xong


class ResumeAdapter:
    family = ""
    steps: tuple[Step, ...] = ()

    # ── Lưu ──
    def decorate(self, conv: dict, reply) -> None:
        """Nhờ extension đọc thêm dữ liệu trên trang ở lệnh của lượt này (vd ô form trước khi rời bước)."""

    def observe(self, conv: dict, intent) -> None:
        """Ghi lại dữ liệu extension gửi kèm lượt này để `capture_*` lưu."""

    def capture(self, conv: dict, saved: dict, fids: list[str]) -> dict:
        """Dữ liệu mới nhất từng bước; bước chưa làm lại ở phiên này giữ bản đã lưu."""
        out = dict(saved)
        for step in self.steps:
            data = getattr(self, f"capture_{step.key}")(conv, saved.get(step.key) or {}, fids)
            if data:
                out[step.key] = data
        return out

    def progress(self, steps: dict) -> list[str]:
        return [step.key for step in self.steps if steps.get(step.key)]

    # ── Khôi phục ──
    def replayable(self, resume: dict, fids: list[str]) -> set[str]:
        """Tác vụ nền được thay trong lượt này: bước có dữ liệu, chưa nạp lại, dữ liệu còn dùng được."""
        done = set(resume.get("replayed") or [])
        steps = resume.get("steps") or {}
        return {step.pipeline for step in self.steps
                if step.key not in done and steps.get(step.key) and self.usable(step, steps[step.key], fids)}

    def usable(self, step: Step, data: dict, fids: list[str]) -> bool:
        return True

    def due_step(self, conv: dict) -> Step | None:
        """Bước mà flow vừa bật tác vụ trong lượt này (tác vụ đã bị chặn) → chờ nạp dữ liệu đã lưu."""
        if conv.get("pipeline_status") != "running":
            return None
        return next((step for step in self.steps
                     if replay.skip_pipeline(step.pipeline) and conv.get("state") == step.state
                     and step.key not in conv["resume"]["replayed"]), None)

    def apply(self, step: Step, conv: dict) -> None:
        resume = conv["resume"]
        getattr(self, f"apply_{step.key}")(conv, resume["steps"][step.key], resume)
        resume["replayed"].append(step.key)


def merge_fields(fields: list[dict], answers: list[dict], snapshot: list[dict]) -> list[dict]:
    """Lệnh điền tờ khai: bản trợ lý điền ← câu trả lời vòng bổ sung ô ← ảnh chụp form cán bộ đã sửa (mới nhất thắng).

    Ảnh chụp đọc ô bằng chính engine đã điền nên giá trị điền lại được nguyên dạng. Ô trống trong ảnh chụp không
    xoá giá trị đã có; ô cán bộ tự thêm (không có trong bản trợ lý) được điền thêm.
    """
    out = [dict(f) for f in fields if isinstance(f, dict) and f.get("name")]

    def slot(name: str, occurrence) -> dict | None:
        return next((f for f in out if f["name"] == name and f.get("occurrence") == occurrence), None)

    for answer in answers:
        found = slot(str(answer.get("key") or ""), None)
        if found is not None and answer.get("value") not in (None, ""):
            found["value"] = answer["value"]
    for item in snapshot:
        value = item.get("value")
        if not item.get("name") or value in (None, "", {}, []):
            continue
        found = slot(item["name"], item.get("occurrence"))
        if found is not None:
            found["value"] = value
        else:
            extra = {"name": item["name"], "comp": item.get("comp") or "", "value": value}
            if item.get("occurrence") is not None:
                extra["occurrence"] = item["occurrence"]
            out.append(extra)
    return out
