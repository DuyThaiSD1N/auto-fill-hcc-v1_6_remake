"""Đính giấy lấy từ Ví cá nhân của cổng Bộ Tư pháp bằng nút "Chọn" của ví (dùng chung handfree + Auto Fill).

Cổng chỉ tính "dùng lại giấy tờ" khi cán bộ chọn tệp có sẵn trong ví; tải lên lại là tạo tệp mới. Tệp ví vẫn được tải về
để planner đọc nội dung đặt tên thành phần, rồi ở đây gắn ``walletPick`` cho mục kế hoạch dùng NGUYÊN một tệp ví →
extension mở ví của dòng và bấm "Chọn" thay vì tải lên.
"""

TABS = ("uploaded", "issued")


def _sources(item: dict) -> list[dict]:
    segments = item.get("sourceSegments")
    if isinstance(segments, list) and segments:
        return [s for s in segments if isinstance(s, dict)]
    # Gộp nguyên tệp (vd hai mặt căn cước chụp rời ở planner cấp bản sao từ sổ gốc): mỗi tệp một nguồn, không thì tệp
    # ví đứng đầu bị coi là cả mục và các tệp gộp cùng bị rơi.
    merged = item.get("sourceFileIndexes")
    if isinstance(merged, list) and len(merged) > 1:
        return [{"fileIndex": index, "pageIndexes": None} for index in dict.fromkeys(merged)]
    return [{"fileIndex": item.get("fileIndex"), "pageIndexes": None}]


def from_options(options: dict | None, files_count: int) -> dict[int, dict]:
    """``options.walletFiles`` của Auto Fill: ``[{index, id, name, tab}]`` — index là vị trí tệp trong lượt gửi."""
    out: dict[int, dict] = {}
    raw = (options or {}).get("walletFiles")
    for row in raw if isinstance(raw, list) else []:
        if not isinstance(row, dict):
            continue
        index = row.get("index")
        wid = str(row.get("id") or "").strip()[:120]
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < files_count or not wid:
            continue
        out[index] = {"id": wid, "name": str(row.get("name") or "").strip()[:200],
                      "tab": row.get("tab") if row.get("tab") in TABS else TABS[0]}
    return out


def apply_wallet_picks(attachments: list[dict], wallet_of: dict[int, dict]) -> list[dict]:
    """Gắn ``walletPick`` cho mục kế hoạch dùng NGUYÊN một tệp ví (``wallet_of[fileIndex]``).

    Nút "Chọn" đính nguyên tệp trong ví, không gộp / cắt trang được, nên:
    - mục gộp tệp ví với phần khác → tách: mỗi tệp ví một dòng riêng ("<tên> phần k"), phần còn lại giữ dòng cũ;
    - tệp ví bị planner cắt ra nhiều giấy (dùng ở nhiều mục) → giữ đường tải lên như cũ cho các mục đó.
    """
    if not wallet_of or not attachments:
        return attachments
    uses: dict[int, int] = {}
    for item in attachments:
        if item.get("target") == "skipped":
            continue
        for index in {s.get("fileIndex") for s in _sources(item)}:
            uses[index] = uses.get(index, 0) + 1

    def pickable(source: dict) -> bool:
        return source.get("fileIndex") in wallet_of and uses.get(source.get("fileIndex")) == 1

    def picked(item: dict, index: int) -> dict:
        out = {k: v for k, v in item.items() if k not in ("sourceSegments", "sourceFileIndexes")}
        out["fileIndex"] = index
        out["fileName"] = str(wallet_of[index].get("fileName") or out.get("fileName") or "")
        out["walletPick"] = {k: wallet_of[index][k] for k in ("id", "name", "tab") if k in wallet_of[index]}
        return out

    result: list[dict] = []
    for item in attachments:
        sources = _sources(item)
        if item.get("target") == "skipped" or not any(pickable(s) for s in sources):
            result.append(item)
            continue
        if len(sources) == 1:
            result.append(picked(item, sources[0]["fileIndex"]))
            continue
        picks = list(dict.fromkeys(s["fileIndex"] for s in sources if pickable(s)))
        rest = [s for s in sources if not pickable(s)]
        parts: list[dict] = []
        if rest:
            kept = {k: v for k, v in item.items() if k != "sourceFileIndexes"}
            if len(rest) == 1 and rest[0].get("pageIndexes") is None:
                kept.pop("sourceSegments", None)
                kept["fileIndex"] = rest[0]["fileIndex"]
            elif all(r.get("pageIndexes") is None for r in rest) and not item.get("sourceSegments"):
                kept["sourceFileIndexes"] = [r["fileIndex"] for r in rest]
                kept["fileIndex"] = rest[0]["fileIndex"]
            else:
                kept["sourceSegments"] = rest
                kept["fileIndex"] = rest[0]["fileIndex"]
            parts.append(kept)
        parts.extend(picked(item, index) for index in picks)
        name = str(item.get("documentName") or "").strip()
        stem = name[:42].rstrip()
        for k, part in enumerate(parts):
            if k == 0:
                continue
            part_name = f"{stem} phần {k + 1}".strip()
            part.update({"documentName": part_name, "componentName": part_name, "target": "new",
                         "componentIndex": None, "needsAddComponent": True})
        if len(parts) > 1 and name:
            parts[0]["documentName"] = f"{stem} phần 1".strip()
            if parts[0].get("target") == "new":
                parts[0]["componentName"] = parts[0]["documentName"]
        result.extend(parts)
    return result
