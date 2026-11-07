"""Chấm kết quả chạy lại — thuần tất định, không gọi agent.

Trọng tài chỉ được đề ra tiêu chí; đạt hay không là do mã ở đây quyết định từ output thật của backend.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Iterable

OPS = ("equals", "contains", "not_contains", "empty", "not_empty", "regex")


def field_key(field: dict) -> str:
    occurrence = field.get("occurrence")
    return f"{field.get('name')}#{occurrence}" if occurrence else str(field.get("name"))


def _canonical(value: Any) -> Any:
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    if isinstance(value, dict):
        return {k: _canonical(value[k]) for k in sorted(value)}
    return value


def value_text(value: Any) -> str:
    """Giá trị để so: bỏ khoảng trắng thừa, object xếp khoá, rỗng/null coi như nhau (khớp valueText bên web)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        if all(v is None or v == "" for v in value.values()):
            return ""
        return json.dumps(_canonical(value), ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return json.dumps(_canonical(value), ensure_ascii=False, separators=(",", ":"))
    return str(value)


def run_values(fields: Iterable[dict] | None) -> dict[str, str]:
    return {field_key(f): value_text(f.get("value")) for f in (fields or []) if isinstance(f, dict) and "name" in f}


def actual_values(run: dict) -> dict[str, str]:
    """Giá trị để chấm: chạy trên cổng thì lấy cái thật sự hiện trên form, không thì lấy cái backend trả."""
    form = run.get("form")
    if form is not None:
        return {key: value_text(value) for key, value in form.items()}
    return run_values((run.get("response") or {}).get("fields"))


def check_passes(check: dict, actual: str) -> bool:
    op = check.get("op")
    expected = value_text(check.get("expected"))
    if op == "equals":
        return actual == expected
    if op == "contains":
        return bool(expected) and expected in actual
    if op == "not_contains":
        return bool(expected) and expected not in actual
    if op == "empty":
        return actual == ""
    if op == "not_empty":
        return actual != ""
    if op == "regex":
        try:
            return re.search(str(check.get("expected") or ""), actual) is not None
        except re.error:
            return False
    return False


def run_ok(run: dict) -> bool:
    return run.get("status") in ("ok", "partial")


def evaluate(checks: list[dict], runs: list[dict]) -> dict:
    """Bảng tiêu chí × lần. Lượt lỗi tính là trượt: không có output thì không thể kết luận đã hết lỗi."""
    rows = []
    for check in checks:
        cells = []
        for run in runs:
            if not run_ok(run):
                cells.append({"value": None, "ok": False})
                continue
            actual = actual_values(run).get(str(check.get("field")), "")
            cells.append({"value": actual, "ok": check_passes(check, actual)})
        rows.append({"check": check, "cells": cells})
    passed = sum(1 for i in range(len(runs)) if rows and all(row["cells"][i]["ok"] for row in rows))
    return {
        "rows": rows,
        "passed": passed,
        "total": len(runs),
        "allPass": bool(rows) and bool(runs) and passed == len(runs),
    }


def unknown_fields(checks: list[dict], known: set[str]) -> list[str]:
    """Tiêu chí trỏ tới field mà form không có → tiêu chí sai, chấm cũng vô nghĩa."""
    needs_value = {"equals", "contains", "not_empty", "regex"}
    return [str(c.get("field")) for c in checks if c.get("op") in needs_value and str(c.get("field")) not in known]


def known_fields(original: list[dict] | None, runs: list[dict]) -> set[str]:
    keys = set(run_values(original))
    for run in runs:
        keys |= set(run_values((run.get("response") or {}).get("fields"))) | set(actual_values(run))
    return keys


def field_table(original: list[dict] | None, runs: list[dict]) -> list[dict]:
    """Field × lần cho agent đọc: giá trị lượt gốc, từng lần chạy lại, có ổn định không.

    Chạy trên cổng thì ``runs`` là giá trị trên form, ``beRuns`` là giá trị backend trả.
    """
    base = run_values(original)
    per_run = [actual_values(r) if run_ok(r) else None for r in runs]
    per_be = [run_values((r.get("response") or {}).get("fields")) if run_ok(r) else None for r in runs]
    on_portal = any(r.get("form") is not None for r in runs)
    keys: list[str] = list(base)
    for values in (*per_run, *per_be):
        keys.extend(k for k in (values or {}) if k not in keys)
    table = []
    for key in keys:
        values = [None if v is None else v.get(key, "") for v in per_run]
        seen = {v for v in values if v is not None}
        row = {"field": key, "original": base.get(key, ""), "runs": values, "stable": len(seen) <= 1}
        if on_portal:
            row["beRuns"] = [None if v is None else v.get(key, "") for v in per_be]
        table.append(row)
    return table


def form_gaps(runs: list[dict]) -> list[dict]:
    """Field backend có giá trị mà form không nhận: dấu hiệu lỗi ở extension hoặc tên ô, không phải ở pipeline."""
    gaps: dict[str, dict] = {}
    for run in runs:
        form = run.get("form")
        if form is None or not run_ok(run):
            continue
        for key, value in run_values((run.get("response") or {}).get("fields")).items():
            if value in ("", "false"):
                continue
            if key not in form or form[key] is None:
                reason = "notFound"
            elif value_text(form[key]) == "":
                reason = "empty"
            else:
                continue
            gap = gaps.setdefault(key, {"field": key, "be": value, "notFound": 0, "empty": 0})
            gap[reason] += 1
    return list(gaps.values())


def find_regressions(baseline_values: list[dict[str, str]], after_runs: list[dict], targets: set[str]) -> list[dict]:
    """Field ngoài phạm vi sửa mà giá trị sau sửa không trùng bất kỳ giá trị nào trước sửa.

    So theo tập giá trị chứ không so từng lần, vì LLM vốn dao động: field vốn không ổn định thì
    chỉ tính là hỏng khi nhảy ra giá trị chưa từng thấy.
    """
    after = [actual_values(r) for r in after_runs if run_ok(r)]
    if not after or not baseline_values:
        return []
    keys: set[str] = set()
    for values in (*baseline_values, *after):
        keys |= set(values)
    regressions = []
    for key in sorted(keys - targets):
        before = {values.get(key, "") for values in baseline_values}
        now = {values.get(key, "") for values in after}
        if not (before & now):
            regressions.append({"field": key, "before": sorted(before), "after": sorted(now)})
    return regressions


def replay_coverage(original: list[dict] | None, runs: list[dict]) -> dict:
    """Lượt chạy lại giống lượt gốc tới đâu: số field có giá trị ở lượt gốc mà chạy lại cũng ra được.

    Lấy lần tốt nhất: một lần lỗi không có nghĩa là cả phép chạy lại sai ngữ cảnh.
    """
    wanted = {key for key, value in run_values(original).items() if value}
    if not wanted:
        return {"original": 0, "matched": 0, "ratio": 1.0}
    matched = 0
    for run in runs:
        if run_ok(run):
            filled = {k for k, v in run_values((run.get("response") or {}).get("fields")).items() if v}
            matched = max(matched, len(wanted & filled))
    return {"original": len(wanted), "matched": matched, "ratio": round(matched / len(wanted), 3)}


def ocr_fresh_count(runs: list[dict]) -> int:
    return sum(1 for r in runs if r.get("ocrFresh") is True)
