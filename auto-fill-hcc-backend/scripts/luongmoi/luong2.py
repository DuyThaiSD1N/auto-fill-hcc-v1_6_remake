"""Luồng mới 2: Qwen chạy NGUYÊN bộ trích xuất trên ẢNH (song song v1) → code so từng ô + bằng chứng → cờ.

(1) v1: dùng lại v1 đã lưu của luồng cũ (cùng đầu vào đã chấm) hoặc chạy lại pipeline.
(2) Bản đọc thứ hai: trich_qwen.trich_nguyen_con — cùng prompt/schema với v1, đọc ảnh, có độ chắc từng ô.
(3) Code so từng ô v1 ↔ bản thứ hai, cộng bằng chứng chắc: MRZ mặt sau CCCD (chữ số kiểm tra), cấu trúc số
    CCCD, cùng một người ghi ở hai chỗ (khối "bản thân", tờ khai ↔ thẻ).
      bằng chứng MRZ nói v1 sai     → SỬA (ô thẻ) / ĐỎ kèm giá trị MRZ (ô tờ khai, giấy ủy quyền)
      khác, bản thứ hai chắc ≥ P_DO → ĐỎ; ô giấy hộ tịch mà giá trị mới có trên văn bản in → SỬA
      khác, chưa chắc               → CAM
      giống v1 → không cờ (kể cả bản thứ hai không chắc)
      số định danh lệch năm sinh → CAM cả hai ô (không biết ô nào sai)
      v1 trống, bản thứ hai chắc ≥ P_DIEN và giá trị có trên giấy → SỬA (điền)
(4) Một agent rà soát duy nhất (chuan_hoa): chuẩn hoá mục đích. Địa chỉ hiện KHÔNG rà (giữ v1).
(6) Chỉ giữ cờ làm ô form thay đổi; v2 = v1 + chỗ sửa → mapper.
"""
from __future__ import annotations

import asyncio
import difflib
import hashlib
import re
import time
import unicodedata

from scripts.luongmoi import chuan_hoa, kiem_tra, luong, trich_qwen
from scripts.luongmoi.thu_do_chac import _check_digit, _dates, _digits, _fold, _text_key, kind, same as _same_loose

P_DO = 0.8
P_DIEN = 0.9

_PERSONS = {  # khối người → (ô họ tên, ô số định danh, ô ngày sinh)
    "NguoiDuocCap_": ("NguoiDuocCap_HoTen", "NguoiDuocCap_SoDinhDanh", "NguoiDuocCap_NgaySinh"),
    "NguoiYeuCau_": ("NguoiYeuCau_HoTen", "NguoiYeuCau_SoDinhDanh", "NguoiYeuCau_NgaySinh"),
    "ToKhai_": ("ToKhai_HoTen", "ToKhai_SoDinhDanh", "ToKhai_NgaySinh"),
    "ToKhaiYeuCau_": ("ToKhaiYeuCau_HoTen", "ToKhaiYeuCau_SoDinhDanh", "ToKhaiYeuCau_NgaySinh"),
    "PoA_Subject": ("PoA_SubjectName", "PoA_SubjectIdNumber", "PoA_SubjectDoB"),
}
_CARD_BLOCKS = ("NguoiDuocCap_", "NguoiYeuCau_")
# Ô tờ khai ↔ ô cùng người trên thẻ in.
_FORM_CARD = {"HoTen": "HoTen", "NgaySinh": "NgaySinh", "SoDinhDanh": "SoDinhDanh", "NgayCapGiayTo": "NgayCap"}


def _kind(field: str) -> str | None:
    base = re.sub(r"_\d$", "", field)
    if base.startswith("Period_"):
        return "ngay"
    if field in kiem_tra.NO_WARN_FIELDS or field in kiem_tra.ADDRESS_FIELDS:
        return None
    return kind(base)


def same(k: str, a, b) -> bool:
    """Như so sánh của phép thử, riêng chữ (cơ quan, dân tộc...) siết lại: "xã Tân Vực" ≠ "xã Tân Việt"."""
    if k != "chu":
        return _same_loose(k, a, b)
    ka, kb = (re.sub(r"\bTT\b", "THI TRAN", _text_key(x)).replace(" ", "") for x in (a, b))
    return bool(ka and kb) and (ka == kb or ka in kb or kb in ka or difflib.SequenceMatcher(None, ka, kb).ratio() >= 0.95)


def _has_marks(text: str) -> bool:
    return any(unicodedata.category(c) == "Mn" for c in unicodedata.normalize("NFD", str(text))) or "đ" in str(text).lower()


def _lost_marks(old: str, new: str) -> bool:
    """Bản đọc thứ hai đọc TRƠN (không dấu) một chữ mà v1 có dấu — Qwen hay làm vậy với tên in (bị dòng MRZ kéo)."""
    pairs = list(zip(str(old).split(), str(new).split()))
    return any(_has_marks(o) and not _has_marks(n) for o, n in pairs)


def _b_fields(res: dict) -> dict:
    """Ô của bản đọc thứ hai → (giá trị, p thấp nhất trong ô, chữ yếu)."""
    data = ((res or {}).get("data") or {}).get("fields") or {}
    conf: dict[str, tuple[float, list]] = {}
    for v in (res or {}).get("values") or []:
        path = v["path"]
        if len(path) >= 2 and path[0] == "fields":
            p, weak = conf.get(path[1], (1.0, []))
            conf[path[1]] = (min(p, v["p"]), weak + v["weak"])
    return {n: (val, *conf.get(n, (1.0, []))) for n, val in data.items()
            if n in kiem_tra.FIELD_NAMES and not kiem_tra._empty(val)}


# ------------------------------------------------------------------ bằng chứng chắc của code

_MRZ1 = re.compile(r"I[DO]VNM(\d{9})(\d)(\d{12})")
_MRZ2 = re.compile(r"(\d{6})(\d)[MF<](\d{6})(\d)VNM")


def mrz_facts(text: str) -> list[dict]:
    """MRZ mặt sau CCCD trong OCR Vintern, chỉ giữ phần qua chữ số kiểm tra → [{so, ngay_sinh?}]."""
    flat = re.sub(r"[ \t]", "", text or "")
    out = []
    for m in _MRZ1.finditer(flat):
        so9, chk, so12 = m.groups()
        if _check_digit(so9) != chk or so12[-9:] != so9:
            continue
        fact = {"so": so12}
        m2 = _MRZ2.search(flat, m.end(), m.end() + 120)
        if m2 and _check_digit(m2.group(1)) == m2.group(2):
            yy, mm, dd = int(m2.group(1)[:2]), int(m2.group(1)[2:4]), int(m2.group(1)[4:6])
            century = {"0": 1900, "1": 1900, "2": 2000, "3": 2000}.get(so12[3], 1900)
            fact["ngay_sinh"] = f"{dd:02d}/{mm:02d}/{century + yy}"
        out.append(fact)
    return out


def _near(a: str, b: str) -> bool:
    return len(a) == len(b) == 12 and sum(x == y for x, y in zip(a, b)) >= 9


def bang_chung(v1: dict, vintern_text: str) -> dict:
    """→ {ô: ("dung", nguồn) | ("sai", giá trị đúng, nguồn) | ("nghi", lý do, giá trị gợi ý|None)}."""
    ev: dict = {}
    facts = mrz_facts(vintern_text)
    for prefix, (f_name, f_id, f_dob) in _PERSONS.items():
        num = _digits(v1.get(f_id))
        if len(num) != 12:
            continue
        fact = next((f for f in facts if f["so"] == num), None) or next((f for f in facts if _near(f["so"], num)), None)
        if not fact:
            continue
        ev[f_id] = ("dung", "MRZ") if fact["so"] == num else ("sai", fact["so"], "MRZ mặt sau CCCD")
        if fact.get("ngay_sinh") and v1.get(f_dob):
            ev[f_dob] = ("dung", "MRZ") if _dates(v1[f_dob])[:1] == _dates(fact["ngay_sinh"]) \
                else ("sai", fact["ngay_sinh"], "MRZ mặt sau CCCD")

    def nghi(field: str, reason: str, value=None, twin: str | None = None):
        if field not in ev and not kiem_tra._empty(v1.get(field)):
            ev[field] = ("nghi", reason, value, twin)

    # Cùng một người ghi ở hai khối tờ khai (tự khai cho bản thân) → hai khối phải giống hệt.
    ban_than = str(v1.get("ToKhai_LaBanThan")).lower() in ("true", "1") or \
        "bản thân" in str(v1.get("ToKhaiYeuCau_QuanHe") or "").lower()
    if ban_than:
        for tail in ("HoTen", "NgaySinh", "SoDinhDanh", "NgayCapGiayTo"):
            a, b = v1.get("ToKhaiYeuCau_" + tail), v1.get("ToKhai_" + tail)
            k = _kind("ToKhai_" + tail)
            if a and b and not same(k, a, b):
                nghi("ToKhaiYeuCau_" + tail, f"cùng một người mà hai khối tờ khai ghi khác: {a} ≠ {b}", None, "ToKhai_" + tail)
                nghi("ToKhai_" + tail, f"cùng một người mà hai khối tờ khai ghi khác: {a} ≠ {b}", None, "ToKhaiYeuCau_" + tail)
    # Tờ khai ↔ thẻ IN của cùng người: lệch thì nghi ô tờ khai, gợi ý theo thẻ.
    pairs = [("ToKhai_", "NguoiDuocCap_"), ("ToKhaiYeuCau_", "NguoiYeuCau_")]
    if ban_than:
        pairs.append(("ToKhaiYeuCau_", "NguoiDuocCap_"))
    for form, card in pairs:
        f_num, c_num = _digits(v1.get(form + "SoDinhDanh")), _digits(v1.get(card + "SoDinhDanh"))
        one = (f_num and (f_num == c_num or _near(f_num, c_num))) or \
            (_fold(v1.get(form + "HoTen")) and _fold(v1.get(form + "HoTen")) == _fold(v1.get(card + "HoTen")))
        if not one or (f_num and c_num and len(f_num) != len(c_num)):
            continue  # người khác, hoặc tờ khai ghi giấy tờ khác (CMND 9 số) → không so
        for f_tail, c_tail in _FORM_CARD.items():
            a, b = v1.get(form + f_tail), v1.get(card + c_tail)
            k = _kind(form + f_tail)
            if not a or not b:
                continue
            differ = _fold(a) != _fold(b) if k == "ten" else not same(k, a, b)
            if differ:
                nghi(form + f_tail, f"tờ khai ghi {a}, thẻ in ghi {b}", b)
    # Cấu trúc số CCCD (mã tỉnh, thế kỷ, năm sinh) — dạng lỗi code kiểm chắc.
    for fields, msg in kiem_tra.loi_dang(v1):
        if all(f in kiem_tra.ID_FIELDS or f.endswith(("NgaySinh", "DoB")) for f in fields):
            for f in fields:
                if len(fields) == 2 and f not in ev and not kiem_tra._empty(v1.get(f)):
                    # Số lệch năm sinh: biết chắc MỘT trong hai ô sai nhưng không biết ô nào → cảnh báo cả cặp.
                    ev[f] = ("cap", "số định danh và ngày sinh không khớp nhau — một trong hai ô bị sai")
                else:
                    nghi(f, msg)
    return ev


# ------------------------------------------------------------------ quyết định cờ

def _row(name, flag, old, value=None, muc=None, ly_do="", goi_y=None, p=None, weak=None, nguon=None) -> dict:
    return {"name": name, "flag": flag, "muc": muc, "old": old, "value": value, "goi_y": goi_y, "p": p,
            "weak": (weak or [])[:4], "ly_do": ly_do, "nguon": nguon}


def _block_has(v1: dict, field: str) -> bool:
    prefix = field.split("_", 1)[0] + "_"
    return any(k.startswith(prefix) and k != field and not kiem_tra._empty(v) for k, v in v1.items())


def quyet_dinh(v1: dict, b: dict, ev: dict, vintern_text: str, vdocs: list[dict]) -> tuple[list[dict], dict]:
    flags, stats = [], {"v1_co_b_trong": 0}
    for name in sorted(set(v1) | set(b)):
        k = _kind(name)
        if k is None:
            continue
        a, q = v1.get(name), b.get(name)
        if kiem_tra._empty(a):
            if not q:
                continue
            val, p, weak = q
            has_form = any(n.startswith("ToKhai") and not kiem_tra._empty(v) for n, v in v1.items())
            allowed = (_block_has(v1, name) or name in kiem_tra.CIVIL_FIELDS or name.endswith("DanToc")) and \
                not (name.startswith("ToKhai") and not has_form)
            if p >= P_DIEN and allowed and kiem_tra._co_tren_giay(val, vintern_text):
                flags.append(_row(name, "sua", a, val, ly_do="v1 trống, bản đọc thứ hai có trên giấy", p=p, weak=weak))
            continue
        e = ev.get(name)
        if e and e[0] == "dung":
            continue
        if name.startswith("DivorceDecision_Number") and re.search(r"HN\s*G\s*D(?![A-Za-zĐđ])", str(a)):
            fixed = re.sub(r"HN\s*G\s*D(?![A-Za-zĐđ])", "HNGĐ", str(a))
            flags.append(_row(name, "sua", a, fixed, ly_do="ký hiệu bản án/quyết định ly hôn là HNGĐ (OCR mất chữ Đ)"))
            continue
        if e and e[0] == "sai":
            if name.startswith(_CARD_BLOCKS):
                flags.append(_row(name, "sua", a, e[1], ly_do=f"{e[2]} ghi {e[1]}", nguon=e[2]))
            else:
                flags.append(_row(name, "canh_bao", a, muc="do", goi_y=e[1], ly_do=f"{e[2]} ghi {e[1]}", nguon=e[2]))
            continue
        muc, goi_y, reasons, p, weak = None, None, [], None, []
        if q is None:
            stats["v1_co_b_trong"] += 1
        else:
            val, p, weak = q
            if not same(k, a, val):
                if k == "ten" and _fold(a) == _fold(val):
                    if not _lost_marks(a, val):
                        muc, goi_y = "cam", val
                        reasons.append(f"chỉ khác dấu: bản đọc thứ hai đọc {val}")
                else:
                    muc, goi_y = ("do" if p >= P_DO else "cam"), val
                    reasons.append(f"bản đọc thứ hai đọc {val} (chắc {p:.2f})")
        if e and e[0] == "nghi":
            # Hai khối "bản thân" lệch nhau: bản đọc thứ hai chắc chắn khớp ô NÀY mà lệch ô kia → lỗi nằm ở ô kia.
            twin = e[3] if len(e) > 3 else None
            resolved = False
            if twin and q and same(k, a, q[0]) and q[1] >= P_DO:
                q_twin = b.get(twin)
                resolved = bool(q_twin) and not same(k, v1.get(twin), q_twin[0])
            if not resolved:
                muc = "do"
                reasons.append(e[1])
                goi_y = goi_y or e[2]
        if e and e[0] == "cap":
            muc = muc or "cam"
            reasons.append(e[1])
        if not muc:
            continue
        if muc == "do" and name in kiem_tra.CIVIL_FIELDS and q and \
                kiem_tra._civil_source_ok(None, q[0], vdocs, name) and not kiem_tra._civil_source_ok(None, a, vdocs, name):
            flags.append(_row(name, "sua", a, q[0], ly_do="giá trị mới có trên văn bản in, v1 thì không",
                              p=p, weak=weak, nguon="văn bản in (OCR Vintern)"))
            continue
        flags.append(_row(name, "canh_bao", a, muc=muc, goi_y=goi_y, ly_do="; ".join(reasons), p=p, weak=weak))
    return flags, stats


def sua_manh(old, new) -> bool:
    """Câu mục đích bị đổi NHIỀU (bỏ mất chữ có nghĩa, bỏ/thêm từ 2 chữ) → vẫn sửa nhưng gắn cam để cán bộ liếc lại.
    Sửa chính tả từng chữ (Bổng → Bổ sung, kí → ký) hay bỏ hư từ ("để") là sửa nhẹ."""
    if kiem_tra._empty(old) or kiem_tra._empty(new):
        return False
    a, b = _fold(old).lower().split(), _fold(new).lower().split()

    def unmatched(xs, ys):
        return [x for x in xs if not any(x == y or difflib.SequenceMatcher(None, x, y).ratio() >= 0.6 for y in ys)]

    removed, added = unmatched(a, b), unmatched(b, a)
    return len(removed) >= 2 or len(added) >= 2 or any(len(w) >= 3 for w in removed)


# ------------------------------------------------------------------ chạy một hồ sơ

async def chay(case: dict, v1: dict | None = None, output1_s: float | None = None, refresh_b: bool = False) -> dict:
    t0 = time.monotonic()
    if v1 is None:
        (res1, v1_s), b_res = await asyncio.gather(luong._timed(luong._pipeline(case)),
                                                   trich_qwen.trich_nguyen_con(case, refresh=refresh_b))
        v1 = dict(((res1.get("llm_output") or {}).get("fields")) or {})
        output1_s = round(case["vintern_prod_s"] + v1_s, 1)
    else:
        res1, b_res = await asyncio.gather(luong._pipeline(case, {"fields": v1}),
                                           trich_qwen.trich_nguyen_con(case, refresh=refresh_b))
    ui1 = luong._ui(res1)
    b = _b_fields(b_res)
    vdocs = [{"text": case["vintern_by_sha"].get(hashlib.sha256(d["dataUrl"].encode()).hexdigest(), "")}
             for d in case["docs"]]

    t_code = time.monotonic()
    ev = bang_chung(v1, case["vintern_text"])
    flags, stats = quyet_dinh(v1, b, ev, case["vintern_text"], vdocs)
    code_s = round(time.monotonic() - t_code, 2)

    # Một agent rà soát duy nhất: chuẩn hoá mục đích.
    ra = await chuan_hoa.ra_soat(case, v1, b) or {}
    md = ra.get("muc_dich")
    md_row = kiem_tra.chot_muc_dich(md, v1)
    if md_row:
        muc = "cam" if md_row["flag"] == "canh_bao" or sua_manh(md_row["old"], md_row["value"]) else None
        flags.append({**md_row, "muc": muc})

    flags = await luong._gan_o_ui(case, v1, ui1, flags)
    v2 = {**v1, **{r["name"]: r["value"] for r in flags if r["flag"] == "sua"}}
    res2 = await luong._pipeline(case, {"fields": v2})
    ui2 = luong._ui(res2)
    ui_changes = {key: [ui1.get(key), ui2.get(key)] for key in luong._changed(ui1, ui2)}

    b_s = round((b_res.get("ms") or 0) / 1000, 1)
    md_s = round((ra.get("ms") or 0) / 1000, 1)
    return {
        "rid": case["rid"],
        "output1": {"llm": v1, "ui": ui1},
        "ban_doc_2": {"fields": {n: {"value": q[0], "p": q[1]} for n, q in b.items()}, "ms": b_res.get("ms"),
                      "in_tokens": b_res.get("in_tokens"), "out_tokens": b_res.get("out_tokens"),
                      "cached": b_res.get("cached")},
        "bang_chung": {n: list(e) for n, e in ev.items()},
        "output2": {"review": flags, "ui_changes": ui_changes},
        "muc_dich": md,
        "thong_ke": stats,
        "thoi_gian": {"output1_s": output1_s, "ban_doc_2_s": b_s, "code_s": code_s, "muc_dich_s": md_s,
                      "uoc_output2_s": round(max(output1_s or 0, b_s) + md_s + code_s, 1),
                      "chay_s": round(time.monotonic() - t0, 1)},
    }
