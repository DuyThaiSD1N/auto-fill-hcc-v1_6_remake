"""Bộ công cụ Auto test trong web Monitor (12007): tái hiện một lượt, nội dung trợ lý điền, bộ ca test từ lượt thật,
lần chạy bộ ca.

Đọc lượt giống Agent tự sửa: Mongo nguồn (local hoặc trolysoao qua SSH) → kho lưu trữ (lượt production đã dọn sau
~30 phút) → Mongo của backend local. Chỉ đọc, không ghi gì vào nguồn hay kho.

Dữ liệu đang có (đợt 1, 22/11/2026): công đoạn backend (trace_steps: span, OCR từng tệp, từng lần gọi LLM), giá trị
trường backend trả, mốc ảnh chụp form của extension (fill / edit / step) và bảng từng ô be → fill → final do kho
dựng (formReview), lịch sử hội thoại handfree (conversations.history, Mongo giữ 24 giờ, kho giữ lâu hơn), lượt nộp
trên cổng (dossiers.submit_events). CHƯA có: HTML eform từng bản, nhật ký thao tác extension, độ tin cậy từng ô.

Ca test dựng từ lượt thật: OCR + câu trả lời LLM đã ghi của lượt, đáp án = giá trị người dân để lại trên form lúc
nộp (formReview.final), ẩn danh bằng regression_case.Anonymizer rồi quét lại bằng codeguard. Ca để trong
``runs/_lab`` (gitignore): khác ca hồi quy của Agent tự sửa (regression/cases, phải luôn đạt, chạy trong CI), ca
ở đây có thể đang trượt — đó là chỗ trợ lý từng sai.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import archive
import codeguard
import evidence
import regression_case
import replay
import scoring
import verify
from config import BE, MAIN_BE, REGRESSION, REGRESSION_CASES, RUNS, SERVER_MODE, SOURCE_SSH, USE_WORKSPACE

LAB = RUNS / "_lab"
SUITES = LAB / "suites"
SUITE_RUNS = LAB / "suite-runs"
INDEX = LAB / "cases.json"
ACCESS = LAB / "access.jsonl"

EDITED = ("llm", "ocr", "other", "cleared")
VERDICT_TEXT = {
    "same": "Giữ nguyên",
    "llm": "Người dân sửa — giấy tờ có giá trị đúng, trợ lý trích sai",
    "ocr": "Người dân sửa — OCR đọc sai chữ / số",
    "other": "Người dân sửa — giá trị không có trên giấy tờ",
    "cleared": "Người dân xoá giá trị trợ lý điền",
    "missing": "Trợ lý bỏ trống, người dân tự điền",
    "nodata": "Backend có giá trị nhưng form không nhận",
}
STEPS = ("Nhận giấy tờ", "Đọc giấy tờ (OCR)", "Trích xuất và điền", "Người dân rà soát", "Nộp hồ sơ")
_SUBMIT = re.compile(r"n[ộo]p|submit|g[ửu]i h[ồo] s[ơo]", re.I)
_VN = timezone(timedelta(hours=7))


class LabError(Exception):
    """Không làm được việc được yêu cầu, có câu giải thích cho người xem."""


# ---- tiện ích -------------------------------------------------------------------------------------------------------

def _dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _ms(value: Any) -> int | None:
    found = _dt(value)
    return int(found.timestamp() * 1000) if found else None


def _iso(ms: int | None) -> str | None:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat() if ms is not None else None


def _text(value: Any) -> str:
    return scoring.value_text(value)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    partial.write_text(json.dumps(evidence._plain(data), ensure_ascii=False, indent=2), encoding="utf-8")
    for attempt in range(5):  # Windows: Defender / VS Code giữ file → Access denied một lúc
        try:
            partial.replace(path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.2)


def audit(user: dict | None, action: str, request_id: str | None = None, **extra: Any) -> None:
    """Nhật ký mỗi lần mở / tái hiện / tải gói / tạo ca: ai, lúc nào, lượt nào (đọc lại ở màn Cấu hình ghi)."""
    LAB.mkdir(parents=True, exist_ok=True)
    entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "user": (user or {}).get("username"),
             "action": action, "requestId": request_id, **extra}
    with ACCESS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recent_access(limit: int = 40) -> list[dict]:
    try:
        lines = ACCESS.read_text(encoding="utf-8").splitlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


# ---- đọc một lượt ---------------------------------------------------------------------------------------------------

def _steps_doc(db, request_id: str, kind: str | None) -> dict | None:
    if kind:
        found = db.trace_steps.find_one({"_id": f"{request_id}:{kind}"})
        if found:
            return found
    return db.trace_steps.find_one({"request_id": request_id})


def _from_db(db, request_id: str) -> tuple[dict | None, dict | None, dict | None]:
    request = db.process_requests.find_one({"request_id": request_id})
    trace = db.traces.find_one({"request_id": request_id})
    return request, trace, _steps_doc(db, request_id, (trace or {}).get("kind") or "autofill")


def load(request_id: str) -> dict:
    """Mọi thứ đang có về một lượt. Ném LabError nếu không tìm thấy ở đâu."""
    try:
        request, trace, steps, stored = evidence._records(request_id)
        db = evidence.database()
    except evidence.CaseError as reason:
        raise LabError(str(reason)) from reason
    source = "archive" if stored else "mongo"
    if not request and not trace and evidence.SOURCE_MONGO_URI:
        # Nguồn là production (trolysoao): lượt chạy trên máy này nằm ở Mongo của backend local.
        local = evidence._local_db()
        found = _from_db(local, request_id)
        if found[0] or found[1]:
            request, trace, steps = found
            db, source = local, "local"
    bundle = None
    if archive.enabled() and (not request or not (stored or {}).get("formReview")):
        try:
            bundle = archive.get_run(request_id)
        except archive.ArchiveError:
            bundle = None
    if not request and not trace and bundle:
        # Mongo nguồn đã không còn bản ghi (quá hạn giữ): dựng lại từ gói của kho.
        runs = bundle.get("runs") or {}
        kind = next((k for k in ("autofill", "attach", *runs) if runs.get(k)), None)
        if kind:
            stored = {"ocrTexts": bundle.get("ocrTexts") or {}, "bundleId": bundle.get("bundleId"),
                      "formReview": bundle.get("formReview")}
            request = (bundle.get("processRequests") or [None])[0]
            trace = {"kind": kind, **(runs[kind].get("trace") or {})}
            steps = runs[kind].get("steps") or {}
            source = "archive"
    if not request and not trace:
        where = "Mongo nguồn, kho lưu trữ và Mongo local" if archive.enabled() else "Mongo nguồn và Mongo local"
        raise LabError(f"Không thấy {request_id} trong {where}.")
    review = (stored or {}).get("formReview") or (bundle or {}).get("formReview")
    return {"request": request or {}, "trace": trace or {}, "steps": steps or {}, "stored": stored, "review": review,
            "db": db, "source": source, "requestId": request_id}


def _conversation(data: dict) -> dict | None:
    request, steps = data["request"], data["steps"]
    conversation_id = (request.get("options") or {}).get("conversation_id") or (steps.get("meta") or {}).get("conversation_id")
    if not conversation_id:
        return None
    try:
        doc = data["db"].conversations.find_one({"_id": conversation_id},
                                                 {"history": 1, "form_context": 1, "eform_running": 1})
    except Exception:  # noqa: BLE001 — hội thoại là phần phụ, không được làm hỏng màn tái hiện
        doc = None
    if doc and doc.get("history"):
        return {"source": "mongo", **doc}
    if archive.enabled():
        created = _dt(request.get("created_at"))
        day = created.astimezone(_VN).strftime("%Y-%m-%d") if created else None
        try:
            doc = archive.find_conversation(conversation_id, str(request.get("user_id") or "") or None, day)
        except archive.ArchiveError:
            doc = None
        if doc:
            return {"source": "archive", **doc}
    return None


def _unit(data: dict) -> dict:
    request, trace = data["request"], data["trace"]
    user_id = request.get("user_id") or trace.get("user_id")
    user = None
    try:
        user = data["db"].users.find_one({"_id": evidence._object_id(user_id)}, {"username": 1, "name": 1, "xa": 1, "tinh": 1,
                                                                                   "role": 1})
    except Exception:  # noqa: BLE001
        user = None
    user = user or {}
    return {"id": str(user_id or ""), "username": user.get("username") or trace.get("username"),
            "name": user.get("name") or trace.get("name"), "xa": user.get("xa"), "tinh": user.get("tinh"),
            "role": user.get("role")}


def _be_fields(data: dict) -> list[dict]:
    fields = data["request"].get("fields")
    if not fields:
        fields = ((data["steps"].get("outputs") or {}).get("response") or {}).get("fields")
    return [f for f in fields or [] if isinstance(f, dict) and f.get("name")]


def _llm_calls(steps: dict) -> list[dict]:
    try:
        return regression_case._steps_llm(steps)
    except regression_case.Skip:
        return []


def _parsed(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return value


def _llm_names(steps: dict) -> set[str]:
    """Trường LLM trích thẳng từ giấy (lần gọi extract cuối). Trường backend trả mà không có ở đây là mapper / luật suy ra."""
    extract = [c for c in _llm_calls(steps) if c.get("purpose") == "extract"]
    if not extract:
        return set()
    parsed = _parsed(extract[-1].get("parsed"))
    fields = parsed.get("fields") if isinstance(parsed, dict) else None
    if isinstance(fields, dict):
        return {str(k) for k in fields}
    if isinstance(fields, list):
        return {str(f.get("name")) for f in fields if isinstance(f, dict) and f.get("name")}
    return set()


def _ocr_texts(data: dict) -> dict[str, str]:
    stored = data["stored"] or {}
    out: dict[str, str] = {}
    for ref in data["steps"].get("ocr") or []:
        sha = ref.get("sha256")
        text = (stored.get("ocrTexts") or {}).get(sha) if stored else None
        if text is None and sha:
            try:
                doc = data["db"].ocr_texts.find_one({"_id": sha}, {"text": 1})
            except Exception:  # noqa: BLE001
                doc = None
            text = (doc or {}).get("text")
        out[str(ref.get("name"))] = text or ref.get("text") or ""
    return out


def _files(data: dict) -> list[dict]:
    refs = {str(r.get("name")): r for r in data["steps"].get("ocr") or []}
    texts = _ocr_texts(data)
    out = []
    for i, item in enumerate(data["request"].get("files") or data["trace"].get("attachments") or []):
        name = str(item.get("name") or f"tệp {i + 1}")
        ref = refs.get(name, {})
        out.append({
            "idx": i, "name": name, "type": item.get("type") or ref.get("type"), "role": item.get("role"),
            "size": item.get("size") or ref.get("bytes"), "pages": ref.get("pages"), "chars": ref.get("chars"),
            "cache": ref.get("cache"), "provider": ref.get("provider"), "error": ref.get("error"),
            "ocr": texts.get(name, ""),
        })
    return out


_SUFFIX = re.compile(r"__\d{8,}(?=#|$)")


def base_key(key: str) -> str:
    """Tên ô SurveyJS trên form có hậu tố mã câu hỏi (citizenHotenMe__1761724625529); backend trả tên gốc."""
    return _SUFFIX.sub("", key or "")


def _rows(data: dict) -> list[dict]:
    """Từng ô: backend trả gì, form nhận gì (fill), người dân để lại gì khi nộp (final), kho chấm ra sao."""
    be_fields = _be_fields(data)
    be_map = scoring.run_values(be_fields)
    llm = _llm_names(data["steps"])
    # Model trích theo khoá riêng rồi mapper đổi sang tên ô: không trùng tên nào thì không biết ô nào là "từ giấy tờ".
    named = bool(llm & {base_key(k).split("#")[0] for k in be_map})
    review = data["review"] or {}
    rows = []
    for row in review.get("rows") or []:
        key = scoring.field_key(row)
        base = base_key(key)
        be = _text(row.get("be")) if row.get("be") is not None else be_map.get(key) or be_map.get(base, "")
        in_be = bool(row.get("inBe")) or bool(be_map.get(base))
        name = base.split("#")[0]
        rows.append({
            "key": key, "beKey": base, "name": row.get("name"), "label": row.get("label") or row.get("name"),
            "section": row.get("section"), "comp": row.get("comp"), "pos": row.get("pos"), "inBe": in_be, "be": be,
            "fill": _text(row.get("fill")), "final": _text(row.get("final")), "verdict": row.get("verdict") or "",
            "verdictText": VERDICT_TEXT.get(row.get("verdict") or "", row.get("verdict") or ""),
            "onDocs": len(row.get("files") or []),
            "source": ("llm" if name in llm else "rule") if in_be and named else "be" if in_be else "none",
        })
    if rows:
        return rows
    # Chưa có ảnh chụp form (lượt cũ, hoặc kho chưa nhận): chỉ biết backend trả gì.
    return [{"key": key, "beKey": key, "name": key.split("#")[0], "label": key, "section": None, "comp": None, "pos": None,
             "inBe": True, "be": value, "fill": None, "final": None, "verdict": "", "verdictText": "Chưa có ảnh chụp form",
             "onDocs": 0, "source": ("llm" if key.split("#")[0] in llm else "rule") if named else "be"}
            for key, value in be_map.items()]


def _summary(rows: list[dict]) -> dict:
    verdicts = Counter(r["verdict"] for r in rows)
    be_filled = [r for r in rows if r["inBe"] and r["be"]]
    return {
        "total": len(rows),
        "beFilled": len(be_filled),
        "same": sum(1 for r in be_filled if r["verdict"] == "same"),
        "edited": sum(verdicts[v] for v in EDITED),
        "missing": sum(1 for r in rows if r["verdict"] == "missing" and r["final"]),
        "missingOnDocs": sum(1 for r in rows if r["verdict"] == "missing" and r["final"] and r["onDocs"]),
        "nodata": verdicts["nodata"],
        "byVerdict": dict(verdicts),
    }


def _wait_ms(data: dict) -> int:
    """Thời gian backend xử lý lượt (người dùng chờ)."""
    for timing in (data["steps"].get("timing"), data["trace"].get("timing")):
        if isinstance(timing, dict) and timing.get("wait"):
            return int(timing["wait"])
    stats = data["trace"].get("stats") or data["request"].get("stats") or {}
    return int(stats.get("total_latency_ms") or 0)


def backend_origin(data: dict) -> tuple[int, bool]:
    """Mốc backend bắt đầu xử lý (ms epoch) và có phải ước lượng không.

    created_at / finished_at của process_requests là lúc GHI bản ghi; bản ghi có thể được ghi lại sau (điền đợt 2 chạy
    sau khi người dân nộp), nên có lượt mà giờ backend muộn hơn cả lúc extension điền xong. Khi đó dời công đoạn
    backend về ngay trước ảnh chụp form đầu tiên (extension chỉ điền được sau khi backend trả)."""
    request, trace, steps = data["request"], data["trace"], data["steps"]
    wait = _wait_ms(data)
    end = _ms(request.get("finished_at"))
    start = _ms(request.get("created_at")) or _ms(trace.get("created_at")) or _ms(steps.get("created_at"))
    if end is None:
        end = (start + wait) if start is not None else None
    snaps = [_ms(s.get("at")) for s in (data["review"] or {}).get("snapshots") or []]
    first = min((s for s in snaps if s is not None), default=None)
    if first is not None and (end is None or end > first):
        return first - 1000 - wait, True
    if end is None:
        return 0, True
    # created_at = finished_at (ghi một lần lúc xong) → lùi đúng thời gian xử lý.
    return (start if start is not None and start < end - wait / 2 else end - wait), False


def _snapshot_label(snap: dict) -> str:
    kind = snap.get("kind")
    if kind == "fill":
        return "Extension điền xong, đọc lại form"
    if kind == "edit":
        return "Người dân sửa ô trên form"
    trigger = (snap.get("trigger") or "").strip()
    return f"Bấm “{trigger}”" if trigger else "Rời bước kê khai"


def _events(data: dict, chat: list[dict], dossier: dict | None) -> tuple[list[dict], list[dict], int]:
    """Dòng thời gian của lượt: công đoạn backend, các lần gọi mô hình, ảnh chụp form, hội thoại, lượt nộp."""
    request, trace, steps = data["request"], data["trace"], data["steps"]
    origin, _estimated = backend_origin(data)
    events: list[dict] = []

    def add(at: int | None, src: str, kind: str, label: str, text: str = "", *, ms: int | None = None,
            warn: bool = False, step: int | None = None, data_: Any = None, snap: str | None = None) -> None:
        if at is None:
            return
        events.append({"at": at, "src": src, "type": kind, "label": label, "text": text, "ms": ms, "warn": warn,
                       "step": step, "data": data_, "snap": snap})

    files = request.get("files") or []
    add(origin, "backend", "request", "Backend nhận giấy tờ",
        f"{len(files)} tệp · thủ tục {request.get('procedure') or trace.get('procedure') or '?'}", step=0)
    calls = _llm_calls(steps)
    spans = [s for s in steps.get("spans") or [] if isinstance(s, dict) and s.get("n") != "pre.request"]
    for span in sorted(spans, key=lambda s: s.get("t0") or 0):
        name = str(span.get("n") or "")
        group = name.split(".", 1)[0]
        if group == "llm" and calls:
            continue  # từng lần gọi mô hình có dòng riêng, đủ thông tin hơn span
        if (span.get("ms") or 0) < 30 and span.get("st") != "error":
            continue
        add(origin + int(span.get("t0") or 0), "backend", group if group in ("pre", "ocr", "llm", "post", "persist") else "other",
            name, "", ms=span.get("ms"), warn=span.get("st") == "error",
            step=0 if group == "pre" else 1 if group == "ocr" else 2, data_={"attrs": span.get("a") or {}})
    ocr_at = min((origin + int(s.get("t0") or 0) for s in spans if str(s.get("n") or "").startswith("ocr")), default=origin)
    for ref in steps.get("ocr") or []:
        bits = [f"{ref.get('pages')} trang" if ref.get("pages") else "", f"{ref.get('chars')} ký tự" if ref.get("chars") else "",
                f"cache {ref.get('cache')}" if ref.get("cache") else ""]
        add(ocr_at, "backend", "ocr", f"Đọc tệp {ref.get('name') or ref.get('idx')}", " · ".join(b for b in bits if b),
            warn=bool(ref.get("error")), step=1,
            data_={k: ref.get(k) for k in ("idx", "name", "type", "pages", "chars", "cache", "reason", "provider", "error")})
    for call in calls:
        bits = [call.get("model") or call.get("target") or "",
                f"{call.get('tokens_in')}→{call.get('tokens_out')} token" if call.get("tokens_out") is not None else ""]
        problem = call.get("error") or call.get("parse_error") or (
            "bị cắt do max_tokens" if call.get("finish_reason") == "length" else "")
        add(origin + int(call.get("t0") or 0), "backend", "llm", f"Gọi mô hình · {call.get('purpose') or '?'}",
            " · ".join(b for b in bits if b) + (f" · {problem}" if problem else ""), ms=call.get("ms"), warn=bool(problem),
            step=2, data_={k: call.get(k) for k in ("n", "purpose", "model", "target", "ms", "tokens_in", "tokens_out",
                                                      "finish_reason", "max_tokens", "error", "parse_error", "tries")})
    finished = origin + _wait_ms(data)
    errors = steps.get("errors") or trace.get("errors") or []
    add(finished, "backend", "response", "Trả kết quả cho extension",
        f"{len(_be_fields(data))} trường" + (f" · {len(errors)} lỗi: {errors[0]}" if errors else ""),
        warn=bool(errors), step=2, data_={"errors": errors} if errors else None)

    snapshots = []
    for i, snap in enumerate((data["review"] or {}).get("snapshots") or []):
        sid = f"S{i + 1}"
        at = _ms(snap.get("at"))
        kind = snap.get("kind")
        step = 2 if kind == "fill" else 4 if kind == "step" and _SUBMIT.search(snap.get("trigger") or "") else 3
        label = _snapshot_label(snap)
        text = f"{snap.get('fields') or 0} ô" + (" · form trống" if snap.get("empty") else "") + (
            f" · extension {snap['extVersion']}" if snap.get("extVersion") else "")
        add(at, "form", f"snapshot.{kind}", label, text, warn=bool(snap.get("empty")), step=step, snap=sid,
            data_={k: snap.get(k) for k in ("kind", "trigger", "host", "path", "fields", "empty", "extVersion")})
        snapshots.append({"id": sid, "at": at, "kind": kind, "trigger": snap.get("trigger") or "", "label": label,
                          "fields": snap.get("fields"), "empty": bool(snap.get("empty")), "extVersion": snap.get("extVersion"),
                          "host": snap.get("host"), "path": snap.get("path")})
    for message in chat:
        add(message["at"], "chat", f"chat.{message['role']}", "Người dân" if message["role"] == "user" else "Trợ lý",
            message["text"], data_={k: message.get(k) for k in ("source", "state")})
    for submit in (dossier or {}).get("submit_events") or []:
        add(_ms(submit.get("at")), "extension", "submit", "Bấm nộp hồ sơ trên cổng", submit.get("host") or "", step=4)

    events.sort(key=lambda e: (e["at"], 0 if e["src"] == "backend" else 1))
    start = events[0]["at"] if events else origin
    last_step = 0
    for no, event in enumerate(events, 1):
        event["no"] = no
        event["t"] = event["at"] - start
        if event["step"] is None:
            event["step"] = last_step
        last_step = max(last_step, event["step"]) if event["src"] != "chat" else last_step
        event["at"] = _iso(event["at"])
    for snap in snapshots:
        snap["t"] = snap["at"] - start if snap["at"] is not None else None
        snap["at"] = _iso(snap["at"])
    return events, snapshots, start


def _chat(conversation: dict | None) -> list[dict]:
    out = []
    for message in (conversation or {}).get("history") or []:
        if not isinstance(message, dict) or not message.get("text"):
            continue
        at = _ms(message.get("ts"))
        if at is None:
            continue
        role = "user" if message.get("role") in ("user", "citizen", "nguoi_dan") else "bot"
        out.append({"at": at, "role": role, "text": str(message.get("text"))[:2000], "source": message.get("source"),
                    "state": message.get("state")})
    return out


def _dossier(data: dict) -> dict | None:
    dossier_id = data["trace"].get("dossier_id") or (data["steps"].get("meta") or {}).get("dossier_id")
    if not dossier_id:
        return None
    try:
        return data["db"].dossiers.find_one({"_id": dossier_id}, {"submit_events": 1, "submitted_at": 1, "events": 1})
    except Exception:  # noqa: BLE001
        return None


def run_view(request_id: str) -> dict:
    data = load(request_id)
    request, trace, steps = data["request"], data["trace"], data["steps"]
    conversation = _conversation(data)
    chat = _chat(conversation)
    events, snapshots, start = _events(data, chat, _dossier(data))
    rows = _rows(data)
    duration = max((e["t"] for e in events), default=0)
    ranges = []
    for index, name in enumerate(STEPS):
        times = [e["t"] for e in events if e["step"] == index and e["src"] != "chat"]
        ranges.append({"no": index + 1, "name": name, "from": min(times) if times else None, "to": max(times) if times else None})
    ext = next((s["extVersion"] for s in snapshots if s.get("extVersion")), None)
    return {
        "requestId": request_id,
        "kind": trace.get("kind") or steps.get("kind") or "autofill",
        "source": data["source"],
        "procedure": request.get("procedure") or trace.get("procedure"),
        "label": trace.get("procedure_label") or request.get("procedure"),
        "experience": request.get("experience") or trace.get("experience") or steps.get("experience"),
        "outcome": steps.get("outcome") or trace.get("outcome"),
        "unit": {k: v for k, v in _unit(data).items() if k in ("id", "username", "name", "xa", "tinh")},
        "dossierId": trace.get("dossier_id") or (steps.get("meta") or {}).get("dossier_id"),
        "startAt": _iso(start),
        "durationMs": duration,
        "backendEstimated": backend_origin(data)[1],
        "waitMs": _wait_ms(data),
        "extVersion": ext,
        "files": _files(data),
        "steps": ranges,
        "events": events,
        "chat": [{**m, "t": m["at"] - start, "at": _iso(m["at"])} for m in chat],
        "chatSource": (conversation or {}).get("source"),
        "conversationId": (request.get("options") or {}).get("conversation_id"),
        "snapshots": snapshots,
        "trust": (data["review"] or {}).get("trust"),
        "hasReview": bool((data["review"] or {}).get("rows")),
        "rows": rows,
        "summary": _summary(rows),
        "beFields": [{"name": f.get("name"), "comp": f.get("comp"), "occurrence": f.get("occurrence"), "value": f.get("value")}
                     for f in _be_fields(data)],
        "caseId": case_for_request(request_id),
    }


def raw_bundle(request_id: str) -> dict:
    """Gói ghi thô của lượt (để tải về / xem JSON): đủ bản ghi gốc, kể cả OCR và câu trả lời LLM."""
    data = load(request_id)
    conversation = _conversation(data)
    return evidence._plain({
        "requestId": request_id, "source": data["source"], "processRequest": data["request"], "trace": data["trace"],
        "steps": data["steps"], "formReview": data["review"], "ocrTexts": _ocr_texts(data),
        "conversation": {"source": conversation.get("source"), "history": conversation.get("history"),
                         "form_context": conversation.get("form_context")} if conversation else None,
    })


def recent(edited_only: bool = True, limit: int = 40) -> dict:
    """Lượt gần đây để chọn tái hiện. Kho lưu trữ có số ô người dân sửa (edited); không có kho thì đọc Mongo nguồn."""
    if archive.enabled():
        items: list[dict] = []
        for page in (1, 2, 3, 4, 5):
            try:
                res = archive.list_records(type="request", pageSize=100, page=page)
            except archive.ArchiveError as reason:
                raise LabError(str(reason)) from reason
            rows = res.get("items") or []
            for row in rows:
                if edited_only and not row.get("edited"):
                    continue
                items.append({"requestId": row.get("requestId"), "procedure": row.get("procedure"),
                              "label": row.get("procedureLabel") or row.get("procedure"), "unit": row.get("unitName") or row.get("username"),
                              "experience": row.get("experience"), "kinds": row.get("kinds") or [], "createdAt": row.get("createdAt"),
                              "edited": row.get("edited") or 0, "files": row.get("files")})
            if len(items) >= limit or len(rows) < 100:
                break
        return {"source": "archive", "items": items[:limit]}
    try:
        db = evidence.database()
        docs = list(db.process_requests.find({}, {"request_id": 1, "procedure": 1, "experience": 1, "created_at": 1, "files": 1})
                    .sort("created_at", -1).limit(limit))
    except Exception as reason:  # noqa: BLE001 — CaseError (đường hầm) hoặc lỗi Mongo
        raise LabError(f"Không đọc được Mongo nguồn: {reason}") from reason
    return {"source": "mongo", "items": [{"requestId": d.get("request_id"), "procedure": d.get("procedure"), "label": d.get("procedure"),
                                          "experience": d.get("experience"), "createdAt": evidence._plain(d.get("created_at")),
                                          "edited": None, "files": len(d.get("files") or [])} for d in docs]}


# ---- ca test từ lượt thật ---------------------------------------------------------------------------------------------

def _index() -> dict:
    return _read_json(INDEX, {})


def case_for_request(request_id: str) -> str | None:
    for case_id, meta in _index().items():
        if meta.get("requestId") == request_id and _case_path(case_id, meta.get("procedure")).is_file():
            return case_id
    return None


def _case_path(case_id: str, procedure: str | None) -> Path:
    return SUITES / re.sub(r"[^\w.-]", "_", str(procedure or "khac")) / f"{case_id}.json"


def _prefix(procedure: str) -> str:
    words = [w for w in re.split(r"[-_]", procedure or "") if w]
    return ("".join(w[0] for w in words)[:4] or "CA").upper()


def _new_id(procedure: str) -> str:
    prefix = _prefix(procedure)
    taken = [int(m.group(1)) for cid in _index() if (m := re.match(rf"^{prefix}-(\d+)$", cid))]
    folder = SUITES / re.sub(r"[^\w.-]", "_", procedure or "khac")
    taken += [int(m.group(1)) for p in folder.glob("*.json") if (m := re.match(rf"^{prefix}-(\d+)$", p.stem))]
    return f"{prefix}-{max(taken, default=0) + 1:04d}"


def answer_checks(rows: list[dict], be_fields: list[dict]) -> list[dict]:
    """Đáp án của ca: ô người dân giữ nguyên → giá trị backend trả (kho đã chấm là khớp form); ô người dân sửa → giá trị
    khi nộp; ô bị xoá → phải trống; ô trợ lý bỏ trống mà giấy tờ có → giá trị khi nộp. Ô form không nhận giá trị
    backend (nodata) là lỗi phía extension, backend không chấm được nên bỏ."""
    be_map = scoring.run_values(be_fields)
    checks = []
    for row in rows:
        verdict = row.get("verdict") or ""
        key = row.get("beKey") or base_key(row.get("key") or scoring.field_key(row))
        meta = {"field": key, "label": row.get("label"), "verdict": verdict, "be": row.get("be") or ""}
        final = row.get("final") or ""
        if verdict == "same":
            expected = be_map.get(key, row.get("be") or "")
            if expected:
                checks.append({**meta, "op": "equals", "expected": expected})
        elif verdict in ("llm", "ocr", "other"):
            if final:
                checks.append({**meta, "op": "equals", "expected": final, "edited": True})
        elif verdict == "cleared":
            checks.append({**meta, "op": "empty", "expected": "", "edited": True})
        elif verdict == "missing" and final and row.get("onDocs"):
            checks.append({**meta, "op": "equals", "expected": final, "edited": True, "missed": True})
        elif not verdict and row.get("be"):
            # Lượt chưa có ảnh chụp form: đáp án là chính kết quả lúc ghi (ca hồi quy thuần).
            checks.append({**meta, "op": "equals", "expected": row["be"], "verdict": "recorded"})
    return checks


def build_case(data: dict, case_id: str) -> dict:
    """Ca ẩn danh từ một lượt đã ghi. Ném regression_case.Skip nếu thiếu dữ liệu hoặc còn dữ liệu thật sau khi thay."""
    request, trace, steps = data["request"], data["trace"], data["steps"]
    kind = trace.get("kind") or steps.get("kind") or "autofill"
    if kind != "autofill":
        raise regression_case.Skip("Chỉ tạo ca test từ lượt điền: lượt đính kèm phát lại cần tệp thật để chia trang.")
    if not steps:
        raise regression_case.Skip("Lượt không có trace_steps (ghi trước khi bật bộ ghi công đoạn), không có câu trả lời "
                                   "LLM để phát lại.")
    calls = regression_case._steps_llm(steps)
    if not calls:
        raise regression_case.Skip("Lượt không gọi mô hình, không có gì để phát lại.")
    if any(c.get("raw") is None for c in calls):
        raise regression_case.Skip("Câu trả lời LLM của lượt bị cắt khi ghi trace, phát lại sẽ khác lượt thật.")
    texts = _ocr_texts(data)
    files = []
    for item in request.get("files") or []:
        name = str(item.get("name") or "")
        files.append({"name": name, "role": item.get("role") or "doc", "ocr": texts.get(name, "")})
    if not files:
        raise regression_case.Skip("Lượt không có tệp nào.")
    rows = _rows(data)
    be_fields = _be_fields(data)
    checks = answer_checks(rows, be_fields)
    if not checks:
        raise regression_case.Skip("Không có ô nào làm được đáp án (backend không trả trường nào, form cũng không có).")
    options = replay.replay_options(request.get("options") or {}, "lab")
    if not options.get("formContext"):
        context = {}
        try:
            context = evidence._form_context(data["db"], request)
        except Exception:  # noqa: BLE001
            context = {}
        if not context:
            conversation = _conversation(data) or {}
            context = dict(conversation.get("form_context") or {})
            if isinstance(conversation.get("eform_running"), dict):
                context.update(conversation["eform_running"])
        if context:
            options["formContext"] = context
    raws = [regression_case._clean_raw(c["raw"]) for c in calls]

    anon = regression_case.Anonymizer()
    answers = [{"name": r.get("name"), "value": v} for r in rows for v in (r.get("be"), r.get("fill"), r.get("final")) if v]
    anon.collect(be_fields)
    anon.collect(answers)
    anon.collect(options)
    for raw in raws:
        for block in regression_case._json_blocks(raw):
            anon.collect(block)
    for item in files:
        anon.collect_text(item["ocr"])

    unit = _unit(data)
    edited = sum(1 for c in checks if c.get("edited"))
    out = {
        "version": 1,
        "id": case_id,
        "origin": "lab",
        "procedure": request.get("procedure") or trace.get("procedure"),
        "label": trace.get("procedure_label") or request.get("procedure"),
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Ca test dựng từ một lượt thật (Monitor › Auto test). Đáp án = giá trị người dân để lại trên form khi nộp. "
                "Dữ liệu cá nhân đã thay bằng dữ liệu giả.",
        "answer": "form" if data["review"] and (data["review"] or {}).get("rows") else "backend",
        "experience": request.get("experience") or trace.get("experience"),
        "account": {k: unit.get(k) for k in ("username", "xa", "tinh", "role") if unit.get(k)},
        "options": anon.deep(options),
        "files": [{"name": anon.text(f["name"]), "role": f["role"], "ocr": anon.text(f["ocr"])} for f in files],
        "llm": [{"purpose": c.get("purpose"), "raw": anon.text(raw)} for c, raw in zip(calls, raws)],
        "checks": [{**c, "expected": anon.text(c["expected"]) if isinstance(c.get("expected"), str) else c.get("expected"),
                    "be": anon.text(c.get("be") or "")} for c in checks],
        "stats": {"files": len(files), "llm": len(calls), "checks": len(checks), "edited": edited,
                  "fields": len(rows)},
    }
    terms = codeguard.private_terms([*be_fields, *answers], data["requestId"])
    terms |= {codeguard._norm(name) for name in anon.names} | {codeguard._norm(s) for s in anon.segments if len(s) >= 8}
    dumped = json.dumps(out, ensure_ascii=False)
    leaks = codeguard.leaked_terms("\n".join("+" + line for line in dumped.splitlines()), terms)
    if leaks:
        raise regression_case.Skip(f"Sau khi thay dữ liệu cá nhân vẫn còn {len(leaks)} chuỗi dữ liệu thật, không lưu ca.")
    return out


_case_lock = threading.Lock()


def create_case(request_id: str, user: dict | None) -> dict:
    existing = case_for_request(request_id)
    if existing:
        return {"caseId": existing, "existing": True}
    data = load(request_id)
    with _case_lock:
        procedure = data["request"].get("procedure") or data["trace"].get("procedure") or "khac"
        case_id = _new_id(procedure)
        try:
            case = build_case(data, case_id)
        except regression_case.Skip as reason:
            raise LabError(str(reason)) from reason
        _write_json(_case_path(case_id, procedure), case)
        index = _index()
        index[case_id] = {"requestId": request_id, "procedure": procedure, "createdAt": case["createdAt"],
                          "createdBy": (user or {}).get("username"), "unit": (case.get("account") or {}).get("username")}
        _write_json(INDEX, index)
    audit(user, "tạo ca test", request_id, caseId=case_id)
    return {"caseId": case_id, "existing": False, "stats": case["stats"]}


def delete_case(case_id: str, user: dict | None) -> None:
    index = _index()
    meta = index.get(case_id)
    if not meta:
        raise LabError("Không có ca này.")
    _case_path(case_id, meta.get("procedure")).unlink(missing_ok=True)
    with _case_lock:
        index = _index()
        index.pop(case_id, None)
        _write_json(INDEX, index)
    audit(user, "xoá ca test", meta.get("requestId"), caseId=case_id)


# ---- bộ ca + lần chạy ------------------------------------------------------------------------------------------------

def _case_files(suite: str) -> list[Path]:
    if suite == "agent":
        return sorted(REGRESSION_CASES.rglob("*.json")) if REGRESSION_CASES.is_dir() else []
    if suite.startswith("lab:"):
        folder = SUITES / suite[4:]
        return sorted(folder.glob("*.json")) if folder.is_dir() else []
    raise LabError("Bộ ca không hợp lệ.")


def _case_summary(path: Path, index: dict) -> dict:
    case = _read_json(path, {})
    checks = case.get("checks") or []
    meta = index.get(case.get("id") or path.stem, {})
    return {
        "id": case.get("id") or path.stem, "procedure": case.get("procedure"), "label": case.get("label"),
        "origin": case.get("origin") or "agent", "createdAt": case.get("createdAt"), "requestId": meta.get("requestId"),
        "unit": (case.get("account") or {}).get("username"), "xa": (case.get("account") or {}).get("xa"),
        "experience": case.get("experience"), "answer": case.get("answer"),
        "files": len(case.get("files") or []), "llm": len(case.get("llm") or []), "checks": len(checks),
        "edited": sum(1 for c in checks if c.get("edited")),
    }


def _run_list() -> list[dict]:
    out = []
    for path in SUITE_RUNS.glob("*.json") if SUITE_RUNS.is_dir() else []:
        data = _read_json(path, None)
        if isinstance(data, dict) and data.get("no"):
            out.append(data)
    return sorted(out, key=lambda r: r["no"], reverse=True)


def suites() -> dict:
    index = _index()
    runs = _run_list()
    out = []
    folders = sorted(p for p in SUITES.iterdir() if p.is_dir()) if SUITES.is_dir() else []
    keys = [f"lab:{p.name}" for p in folders] + (["agent"] if _case_files("agent") else [])
    for key in keys:
        cases = [_case_summary(p, index) for p in _case_files(key)]
        if not cases:
            continue
        mine = [r for r in runs if r.get("suite") == key and r.get("status") == "done"]
        history = {}
        for run in mine[:2]:
            for result in run.get("results") or []:
                history.setdefault(result["id"], []).append({"no": run["no"], "status": result.get("status"),
                                                             "failed": result.get("failedFields", 0)})
        for case in cases:
            case["history"] = history.get(case["id"], [])
        label = cases[0].get("label") if key != "agent" else "Ca hồi quy của Agent tự sửa"
        out.append({
            "key": key, "kind": "agent" if key == "agent" else "lab", "label": label, "procedure": key[4:] if key != "agent" else None,
            "cases": cases, "edited": sum(1 for c in cases if c["edited"]),
            "lastRun": _run_brief(mine[0]) if mine else None,
            "running": any(r.get("suite") == key and r.get("status") == "running" for r in runs),
        })
    return {"suites": out, "targets": targets()}


def targets() -> list[dict]:
    out = [{"key": "dev", "label": "Bản đang phát triển (máy này)", "ok": (MAIN_BE / "app").is_dir(), **_tree_info(MAIN_BE)}]
    if USE_WORKSPACE:
        out.append({"key": "release", "label": "Bản production (tag release)", "ok": (BE / "app").is_dir(), **_tree_info(BE)})
    return out


def _tree_info(be: Path) -> dict:
    if not (be / "app").is_dir():
        return {"commit": None, "dirty": False}
    try:
        commit = subprocess.run(["git", "-C", str(be), "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                                timeout=15).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(be), "status", "--porcelain", "--", "app"], capture_output=True,
                                    text=True, timeout=30).stdout.strip())
        tag = subprocess.run(["git", "-C", str(be), "describe", "--tags", "--exact-match"], capture_output=True, text=True,
                             timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": False}
    return {"commit": commit or None, "dirty": dirty, "tag": tag or None}


def _run_brief(run: dict) -> dict:
    return {k: run.get(k) for k in ("no", "suite", "suiteLabel", "target", "targetLabel", "commit", "dirty", "tag", "status",
                                    "startedAt", "finishedAt", "durationMs", "by", "counts", "fields", "error", "total",
                                    "previous")}


def list_runs() -> list[dict]:
    return [_run_brief(r) for r in _run_list()]


def get_run(no: int) -> dict:
    run = _read_json(SUITE_RUNS / f"{no}.json", None)
    if not run:
        raise LabError("Không có lần chạy này.")
    previous = _read_json(SUITE_RUNS / f"{run['previous']}.json", None) if run.get("previous") else None
    if previous:
        run["previousResults"] = {r["id"]: {"status": r.get("status"), "failed": r.get("failedFields", 0),
                                            "rows": {x["field"]: x.get("actual") for x in r.get("rows") or []}}
                                  for r in previous.get("results") or []}
    return run


def _status(result: dict) -> str:
    if result.get("status") not in (200, None) or (result.get("error") and not result.get("rows")):
        return "error"
    if not result.get("ok"):
        return "fail"
    if result.get("extraFields"):
        return "review"
    return "pass"


class SuiteRunner:
    """Một lần chạy một bộ ca tại một thời điểm (phát lại OCR/LLM đã ghi, không gọi mạng, không cần Docker)."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.current: int | None = None
        for run in _run_list():  # dịch vụ tắt giữa chừng: lần chạy dở không bao giờ xong
            if run.get("status") == "running":
                run.update(status="error", error="Dịch vụ agent khởi động lại giữa lúc chạy.")
                _write_json(SUITE_RUNS / f"{run['no']}.json", run)

    def start(self, suite: str, target: str, case_ids: list[str] | None, user: dict | None, busy: str | None) -> dict:
        paths = _case_files(suite)
        if case_ids:
            wanted = set(case_ids)
            paths = [p for p in paths if p.stem in wanted]
        if not paths:
            raise LabError("Bộ ca không có ca nào để chạy.")
        tree = next((t for t in targets() if t["key"] == target), None)
        if not tree or not tree["ok"]:
            raise LabError("Không có cây backend này trên máy dịch vụ agent.")
        if target == "release" and busy:
            raise LabError("Agent tự sửa đang chạy một ca trong khu làm việc, chờ ca đó xong rồi chạy trên bản production.")
        with self.lock:
            if self.current is not None:
                raise LabError(f"Lần chạy #{self.current} chưa xong.")
            runs = _run_list()
            no = (runs[0]["no"] if runs else 0) + 1
            previous = next((r["no"] for r in runs if r.get("suite") == suite and r.get("status") == "done"), None)
            index = _index()
            first = _case_summary(paths[0], index)
            run = {
                "no": no, "suite": suite, "suiteLabel": first.get("label") if suite != "agent" else "Ca hồi quy của Agent tự sửa",
                "target": target, "targetLabel": tree["label"], "commit": tree.get("commit"), "dirty": tree.get("dirty"),
                "tag": tree.get("tag"), "status": "running", "startedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "by": (user or {}).get("username"), "total": len(paths), "caseIds": [p.stem for p in paths], "previous": previous,
            }
            _write_json(SUITE_RUNS / f"{no}.json", run)
            self.current = no
        threading.Thread(target=self._execute, args=(run, paths, MAIN_BE if target == "dev" else BE), daemon=True).start()
        audit(user, "chạy bộ ca test", None, suite=suite, run=no)
        return _run_brief(run)

    def _execute(self, run: dict, paths: list[Path], be: Path) -> None:
        out = SUITE_RUNS / f"{run['no']}.out.json"
        started = time.monotonic()
        try:
            cmd = [sys.executable, str(REGRESSION / "run.py"), "--be", str(be), "--json", str(out), *map(str, paths)]
            _code, output = verify.run(cmd, be, 900, threading.Event(), verify._pytest_env())
            data = _read_json(out, None)
            if not data:
                raise LabError("Bộ chạy ca không ghi được kết quả: " + output[-800:])
            run["results"] = [self._result(item, path) for item, path in zip(self._ordered(data, paths), paths)]
            counts = Counter(r["status"] for r in run["results"])
            run["counts"] = {k: counts.get(k, 0) for k in ("pass", "fail", "review", "error")}
            fields_ok = sum(r["okFields"] for r in run["results"])
            fields_total = sum(r["totalFields"] for r in run["results"])
            run["fields"] = {"ok": fields_ok, "total": fields_total}
            run["status"] = "done"
        except Exception as reason:  # noqa: BLE001 — lần chạy hỏng phải hiện lỗi trên web, không làm chết luồng
            run.update(status="error", error=f"{type(reason).__name__}: {reason}"[:1500])
        finally:
            run["finishedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            run["durationMs"] = int((time.monotonic() - started) * 1000)
            _write_json(SUITE_RUNS / f"{run['no']}.json", run)
            out.unlink(missing_ok=True)
            with self.lock:
                self.current = None

    @staticmethod
    def _ordered(data: dict, paths: list[Path]) -> list[dict]:
        by_file = {r.get("file"): r for r in data.get("results") or []}
        return [by_file.get(p.name) or {"id": p.stem, "ok": False, "error": "không có kết quả"} for p in paths]

    @staticmethod
    def _result(item: dict, path: Path) -> dict:
        case = _read_json(path, {})
        checks = {str(c.get("field")): c for c in case.get("checks") or []}
        rows = []
        for row in item.get("rows") or []:
            check = checks.get(str(row.get("field")), {})
            rows.append({**row, "label": check.get("label") or row.get("field"), "verdict": check.get("verdict"),
                         "edited": bool(check.get("edited")), "be": check.get("be")})
        result = {
            "id": item.get("id") or path.stem, "ok": bool(item.get("ok")), "error": item.get("error"),
            "rows": rows, "extraFields": item.get("extraFields") or [], "ms": item.get("ms"),
            "skippedHooks": item.get("skippedHooks") or [], "status": None,
            "okFields": sum(1 for r in rows if r.get("ok")), "totalFields": len(rows),
            "failedFields": sum(1 for r in rows if not r.get("ok")),
        }
        result["status"] = _status({**item, "rows": rows})
        return result


runner = SuiteRunner()


def config_view() -> dict:
    index = _index()
    return {
        "source": {
            "mongo": "trolysoao (production, đọc qua SSH)" if SOURCE_SSH else "production (máy server)" if SERVER_MODE else "Mongo local",
            "archive": archive.enabled(),
        },
        "lab": {"cases": len(index), "suites": len([p for p in SUITES.iterdir() if p.is_dir()]) if SUITES.is_dir() else 0,
                "runs": len(_run_list()), "dir": "auto-test-hcc/runs/_lab (gitignore, không commit)"},
        "targets": targets(),
        "access": recent_access(),
    }
