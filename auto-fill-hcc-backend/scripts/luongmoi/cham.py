"""Đối chiếu kết quả luồng mới với bản chấm tay (<mã>/phan_tich_claude.json — chữ trên giấy, xem bằng ảnh gốc)."""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from pathlib import Path

from app.pipelines._shared.area_remap import canonical_province
from scripts.luongmoi.kiem_tra import FIX_FIELDS, NAME_FIELDS, NO_WARN_FIELDS

# Bản chấm làm trước khi đổi tên field: thẻ "Cccd_*" nay là NguoiDuocCap_* HOẶC NguoiYeuCau_* (thẻ người đi nộp).
_CARD_OLD, _CARD_NEW = "Cccd_", ("NguoiDuocCap_", "NguoiYeuCau_")
# Không chấm: ô do mapper chuẩn hoá (nơi cấp) hoặc bản chấm ghi câu diễn giải (tình trạng hôn nhân).
_SKIP = NO_WARN_FIELDS | {"TinhTrangHonNhanC1", "ToKhai_LaBanThan"}
_ABBR = {"ubnd": "ủy ban nhân dân", "tand": "tòa án nhân dân", "uỷ": "ủy", "tp": "thành phố", "t": "tổ", "k": "kiệt"}
_ADMIN_PREFIX = re.compile(r"^(tỉnh|t\.|thành phố|tp\.?|phường|p\.|xã|x\.|thị trấn)\s*", re.I)
_DATE_RE = re.compile(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{4}")


def _norm(value) -> str:
    """Bỏ định dạng; dấu thanh tách riêng và sắp lại để "Thuỳ" = "Thùy" (khác vị trí bỏ dấu, cùng chữ)."""
    text = unicodedata.normalize("NFC", str(value or "")).strip().lower()
    text = _ADMIN_PREFIX.sub("", text)
    if _DATE_RE.fullmatch(text):
        return "/".join(str(int(x)) for x in re.findall(r"\d+", text))
    text = re.sub(r"[\W_]+", "", " ".join(_ABBR.get(w, w) for w in re.findall(r"\w+", text)))
    decomposed = unicodedata.normalize("NFD", text)
    marks = sorted(ch for ch in decomposed if unicodedata.combining(ch))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)) + "|" + "".join(marks)


def _base(value) -> str:
    return _norm(value).split("|")[0]


def _clean_truth(text) -> str | None:
    """Bản chấm có ghi chú trong ngoặc "(chữ mờ…)" → bỏ; cả ô là ghi chú "(không có…)" → coi như trống."""
    text = str(text or "").strip()
    if not text or text.startswith("("):
        return ""
    text = re.split(r"\s+—\s+|;", text)[0]  # phần sau "—"/";" là ghi chú người chấm
    text = re.sub(r"\s*\((?=[^)]*[^\W\d_]{2})[^)]*\)", "", text)  # ngoặc chứa chữ = ghi chú người chấm
    words = re.search(r"ngày\s*(\d{1,2})\s*(?:tháng|[-–/.])\s*(\d{1,2})\s*(?:năm|[-–/.])\s*(\d{4})", text, re.I)
    if words:
        text = f"{words.group(1)}/{words.group(2)}/{words.group(3)}"
    return text.replace("[", "").replace("]", "").replace("?", "").strip()


def load(case_dir: Path) -> dict | None:
    path = case_dir / "phan_tich_claude.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    truth: dict[str, dict] = {}
    for row in data.get("truong") or []:
        name = row.get("field") or ""
        names = [p + name[len(_CARD_OLD):] for p in _CARD_NEW] if name.startswith(_CARD_OLD) else [name]
        for n in names:
            if n.partition(".")[0] not in _SKIP:
                truth[n] = {"giay": _clean_truth(row.get("tren_giay")), "chac": row.get("do_chac") == "chac",
                            "the_cu": len(names) > 1}
    md = data.get("muc_dich") or {}
    truth["Purpose"] = {"giay": _clean_truth(md.get("tren_giay")), "chac": md.get("do_chac") == "chac", "the_cu": False}
    return truth


def _value(values: dict, key: str):
    name, _, sub = key.partition(".")
    value = values.get(name)
    return (value or {}).get(sub) if sub and isinstance(value, dict) else value


def _match(key: str, value, giay: str) -> bool:
    if key.endswith(".tinh"):
        value, giay = canonical_province(value) or value, canonical_province(giay) or giay
    a, b = _norm(value), _norm(giay)
    if key == "Purpose":
        return difflib.SequenceMatcher(None, a, b).ratio() >= 0.9
    if key.endswith("_Agency") and a.split("|")[0] and a.split("|")[0] in b.split("|")[0]:
        return True  # cơ quan ghi gọn (bỏ cấp huyện/tỉnh) vẫn là cùng cơ quan
    return a == b


def _field_ok(values: dict, field: str, truth: dict) -> bool | None:
    # Phần giấy không ghi (vd khối II bỏ trống tỉnh) thì không chấm phần đó.
    keys = [k for k in truth if (k == field or k.startswith(field + ".")) and (truth[k]["giay"] or "." not in k)]
    if not keys:
        return None
    return all(_match(k, _value(values, k), truth[k]["giay"]) for k in keys)


def _empty_field(values: dict, name: str) -> bool:
    return values.get(name) in (None, "", {})


def nhom(name: str) -> str:
    """Nhóm ô để thống kê cờ theo loại thông tin."""
    if name == "Purpose":
        return "mục đích"
    if name.endswith(("NoiCuTru", "Address")):
        return "địa chỉ"
    if name.endswith(("HoTen", "Name")):
        return "tên"
    if name.endswith(("SoDinhDanh", "IdNumber", "Number")):
        return "số"
    if re.search(r"NgaySinh|NgayCap|Date|DoB|IdDate", name):
        return "ngày"
    if re.search(r"Agency|NoiCap|Issuer", name):
        return "cơ quan"
    return "khác"


def danh_gia(result: dict, truth: dict | None) -> dict:
    """Từng cờ: sửa đúng / sửa hỏng / sửa chưa tới / sửa vô hại; cảnh báo trúng / nhầm; field v1 sai mà lọt cờ."""
    if not truth:
        return {}
    v1, v2 = result["output1"]["llm"], result["v2_llm"]
    flagged = {r["name"]: r for r in result["output2"]["review"]}
    verdict = {}
    for name, row in flagged.items():
        ok1, ok2 = _field_ok(v1, name, truth), _field_ok(v2, name, truth)
        if ok1 is None:
            kq = "chưa chấm"
        elif row["flag"] == "sua":
            kq = {(False, True): "sửa đúng", (True, False): "sửa HỎNG", (False, False): "sửa chưa tới",
                  (True, True): "sửa vô hại"}[(ok1, ok2)]
        else:
            kq = "cảnh báo trúng" if not ok1 else "cảnh báo nhầm"
        if ok1 is not None and not all(truth[k]["chac"] for k in truth if k == name or k.startswith(name + ".")):
            kq += " (giấy khó đọc)"
        verdict[name] = kq
    fields = {k.partition(".")[0] for k in truth}
    lot = []
    for name in sorted(fields - set(flagged)):
        keys = [k for k in truth if k == name or k.startswith(name + ".")]
        if not all(truth[k]["chac"] for k in keys):
            continue
        if any(truth[k]["the_cu"] for k in keys):
            twin = name.replace("NguoiDuocCap_", "NguoiYeuCau_") if name.startswith("NguoiDuocCap_") \
                else name.replace("NguoiYeuCau_", "NguoiDuocCap_")
            if _empty_field(v1, name) or _field_ok(v1, twin, {k.replace(name, twin): v for k, v in truth.items()
                                                              if k == name or k.startswith(name + ".")}):
                continue  # thẻ chấm theo tên cũ (Cccd_*): khớp khối kia hoặc ô trống → không tính lọt
        if name in NAME_FIELDS and _base(v1.get(name)) == _base(truth[name]["giay"]):
            continue  # chỉ khác dấu: luật không cảnh báo
        if _field_ok(v1, name, truth) is False and any(truth[k]["giay"] or _value(v1, k) for k in keys):
            no_form = name.startswith("ToKhai") and not any(k.startswith("ToKhai") and not _empty_field(v1, k) for k in v1)
            lot.append({"name": name, "v1": v1.get(name), "giay": {k: truth[k]["giay"] for k in keys},
                        "nhom": "sửa" if name in FIX_FIELDS else "cảnh báo",
                        "loai": "v1 không nhận ra tờ khai" if no_form else "lọt"})
    return {"co": verdict, "lot": lot}
