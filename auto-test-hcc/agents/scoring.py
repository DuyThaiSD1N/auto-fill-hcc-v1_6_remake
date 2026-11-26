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
    """Giá trị để chấm: các trường backend trả (lượt đính kèm: ô ảo dựng từ kế hoạch)."""
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


def merge_patch(fields: list[dict] | None, patch: list[dict] | None) -> list[dict]:
    """Giá trị cuối cùng lên form của thủ tục có thanh tra: ô lượt điền đầu, ô nào bản vá đợt 2 ghi lại thì lấy giá trị
    bản vá (extension ghi đè đúng các ô đó). Ô bản vá có mà lượt đầu chưa có thì thêm vào cuối. Bản vá không xoá ô nào."""
    out = [dict(f) for f in fields or [] if isinstance(f, dict)]
    index = {field_key(f): i for i, f in enumerate(out)}
    for item in patch or []:
        if not isinstance(item, dict) or "name" not in item:
            continue
        field = {k: v for k, v in item.items() if k not in ("from", "by")}
        key = field_key(field)
        if key in index:
            out[index[key]] = {**out[index[key]], **field}
        else:
            index[key] = len(out)
            out.append(field)
    return out


def _first_pass_values(run: dict) -> dict[str, str] | None:
    """Giá trị lượt điền đầu của một lần chạy có thanh tra ghi lại ô (None = lần đó không có bản vá)."""
    first = (run.get("response") or {}).get("firstPassFields")
    return run_values(first) if isinstance(first, list) else None


def field_table(original: list[dict] | None, runs: list[dict], original_first: list[dict] | None = None) -> list[dict]:
    """Field × lần cho agent đọc: giá trị lượt gốc, từng lần chạy lại, có ổn định không.

    Thủ tục có thanh tra: giá trị là giá trị CUỐI (sau bản vá đợt 2). Ô nào thanh tra đã ghi lại ở ít nhất một lần thì
    thêm ``dot1`` (giá trị lượt điền đầu từng lần, None = lần đó thanh tra không đổi ô này) và ``originalDot1``."""
    base = run_values(original)
    base_first = run_values(original_first) if original_first is not None else None
    per_run = [actual_values(r) if run_ok(r) else None for r in runs]
    first_runs = [_first_pass_values(r) if run_ok(r) else None for r in runs]
    keys: list[str] = list(base)
    for values in per_run:
        keys.extend(k for k in (values or {}) if k not in keys)
    table = []
    for key in keys:
        values = [None if v is None else v.get(key, "") for v in per_run]
        seen = {v for v in values if v is not None}
        row = {"field": key, "original": base.get(key, ""), "runs": values, "stable": len(seen) <= 1}
        dot1 = [None if f is None or v is None or f.get(key, "") == v.get(key, "") else f.get(key, "")
                for f, v in zip(first_runs, per_run)]
        original_dot1 = None if base_first is None or base_first.get(key, "") == base.get(key, "") else base_first.get(key, "")
        if any(d is not None for d in dot1) or original_dot1 is not None:
            row["dot1"] = dot1
            row["originalDot1"] = original_dot1
        table.append(row)
    return table


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


# ---- Đính kèm ----------------------------------------------------------------------------------------------------
# Lượt đính kèm không có field. Kế hoạch đính kèm được quy thành "ô ảo" để mọi thứ ở trên (bảng ô × lần, tiêu chí của
# trọng tài, hồi quy, độ giống lượt gốc) dùng nguyên. Khoá của ô ảo:
#   dòng: <tên dòng>       giấy nào vào dòng đó, kèm trang: "Giấy khai sinh [#1:1-2] | Căn cước [#2]"
#   loại: <detectedType>   dòng mà loại giấy đó được xếp vào
#   tệp #<n>               từng trang của tệp thứ n (đếm từ 1) vào dòng nào: "1→Tờ khai; 2→Căn cước; 3→(không đính)"
#   tổng: số mục | tổng: trang thiếu | tổng: trang trùng | tổng: lỗi

def _clip(text: Any, limit: int = 90) -> str:
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(text or ""))).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def fold(text: Any) -> str:
    """Bỏ dấu, chữ thường, chỉ còn chữ số và khoảng trắng."""
    text = unicodedata.normalize("NFD", str(text or "")).replace("đ", "d").replace("Đ", "D")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def attach_row_name(item: dict) -> str:
    """Tên dòng đích trong bảng thành phần hồ sơ, chưa có tiền tố."""
    if item.get("target") == "supplementary":
        return "Đính kèm bổ sung"
    keywords = " / ".join(str(k) for k in item.get("slotKeywords") or [])
    name = item.get("componentName") or item.get("slotName") or keywords or item.get("documentName") or "?"
    if item.get("sectionHeader"):
        name = f"{item['sectionHeader']} › {name}"
    return _clip(name)


def attach_row(item: dict) -> str:
    """Khoá dòng của ô ảo. Dòng extension tự thêm thường mang chính tên giấy LLM đặt, tên đó đổi giữa các lần chạy, nên gom chung
    một khoá "Thêm mới"; chỉ giữ tên khi planner đặt tên dòng riêng khác tên giấy (vd "Giấy tờ khác")."""
    if item.get("target") == "new" or item.get("needsAddComponent"):
        component = item.get("componentName")
        if component and fold(component) != fold(item.get("documentName")):
            return _clip(f"Thêm mới: {component}")
        return "Thêm mới"
    return attach_row_name(item)


def attach_refs(item: dict) -> list[tuple[int, int | None]]:
    """(chỉ số tệp, chỉ số trang 0-based) mục này lấy. Trang None = cả tệp. Ưu tiên sourceSegments > sourceFileIndexes > fileIndex."""
    refs: list[tuple[int, int | None]] = []
    for segment in item.get("sourceSegments") or []:
        if not isinstance(segment, dict) or not isinstance(segment.get("fileIndex"), int):
            continue
        pages = segment.get("pageIndexes")
        if pages is None:
            refs.append((segment["fileIndex"], None))
        else:
            refs.extend((segment["fileIndex"], p) for p in pages if isinstance(p, int))
    if refs:
        return refs
    sources = [i for i in item.get("sourceFileIndexes") or [] if isinstance(i, int)]
    if sources:
        return [(i, None) for i in sources]
    return [(item["fileIndex"], None)] if isinstance(item.get("fileIndex"), int) else []


def _ranges(pages: list[int]) -> str:
    spans: list[list[int]] = []
    for page in sorted(set(pages)):
        if spans and page == spans[-1][1] + 1:
            spans[-1][1] = page
        else:
            spans.append([page, page])
    return ",".join(f"{a + 1}" if a == b else f"{a + 1}-{b + 1}" for a, b in spans)


def _refs_text(refs: list[tuple[int, int | None]]) -> str:
    by_file: dict[int, list[int] | None] = {}
    for index, page in refs:
        if page is None:
            by_file[index] = None
        elif by_file.get(index, []) is not None:
            by_file.setdefault(index, []).append(page)
    return " + ".join(f"#{i + 1}" if pages is None else f"#{i + 1}:{_ranges(pages)}" for i, pages in sorted(by_file.items()))


def _covered(refs: list[tuple[int, int | None]], counts: list[int | None]) -> list[tuple[int, int | None]]:
    """Cả tệp mà biết số trang thì bung ra từng trang, để so được với mục chỉ lấy vài trang của cùng tệp."""
    out: list[tuple[int, int | None]] = []
    for index, page in refs:
        count = counts[index] if 0 <= index < len(counts) else None
        out.extend(((index, p) for p in range(count)) if page is None and count else [(index, page)])
    return out


def _entry(item: dict) -> str:
    doc = _clip(item.get("documentName") or item.get("fileName") or "?", 80)
    return f"{doc} [{_refs_text(attach_refs(item)) or '?'}]"


def attach_fields(plan: list[dict] | None, page_counts: list[int | None] | None, errors: list | None = None) -> list[dict]:
    """Ô ảo của một kế hoạch đính kèm, dạng [{name, value}] như field backend trả."""
    counts = list(page_counts or [])
    items = [item for item in plan or [] if isinstance(item, dict)]
    rows: dict[str, list[str]] = {}
    kinds: dict[str, set[str]] = {}
    owners: dict[tuple[int, int | None], list[str]] = {}
    for item in items:
        row = attach_row(item)
        rows.setdefault(row, []).append(_entry(item))
        if item.get("detectedType"):
            kinds.setdefault(_clip(item["detectedType"], 60), set()).add(row)
        for ref in dict.fromkeys(_covered(attach_refs(item), counts)):
            owners.setdefault(ref, []).append(row)
    fields = [{"name": f"dòng: {row}", "value": " | ".join(sorted(entries))} for row, entries in sorted(rows.items())]
    fields += [{"name": f"loại: {kind}", "value": " | ".join(sorted(where))} for kind, where in sorted(kinds.items())]
    missing: list[str] = []
    for index, count in enumerate(counts):
        if count:
            parts = []
            for page in range(count):
                where = owners.get((index, page))
                parts.append(f"{page + 1}→{' + '.join(sorted(set(where))) if where else '(không đính)'}")
                if not where:
                    missing.append(f"#{index + 1}:{page + 1}")
            value = "; ".join(parts)
        else:
            whole = owners.get((index, None))
            pages = sorted(p for (i, p) in owners if i == index and p is not None)
            parts = [f"cả tệp→{' + '.join(sorted(set(whole)))}"] if whole else []
            parts += [f"{p + 1}→{' + '.join(sorted(set(owners[(index, p)])))}" for p in pages]
            value = "; ".join(parts) or "(không đính)"
            if not parts:
                missing.append(f"#{index + 1}")
            elif not whole:
                missing.append(f"#{index + 1}:?")  # không biết số trang nên không biết có sót trang nào không
        fields.append({"name": f"tệp #{index + 1}", "value": value})
    duplicate = sorted((ref for ref, where in owners.items() if len(where) > 1), key=lambda r: (r[0], -1 if r[1] is None else r[1]))
    fields += [
        {"name": "tổng: số mục", "value": str(len(items))},
        {"name": "tổng: trang thiếu", "value": ", ".join(missing)},
        {"name": "tổng: trang trùng", "value": ", ".join(f"#{i + 1}" if p is None else f"#{i + 1}:{p + 1}" for i, p in duplicate)},
        {"name": "tổng: lỗi", "value": "; ".join(_clip(e, 200) for e in errors or [] if e)},
    ]
    return fields
