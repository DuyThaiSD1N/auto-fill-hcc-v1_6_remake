"""Compact agent pipeline cho "[Bắc Ninh] Xác nhận tiếp tục sử dụng đất nông nghiệp" (1.115462).

TÁCH theo purpose (chọn TRƯỚC khi gọi LLM để mỗi lần trích gọn, không lẫn người):
- "registration_form" (mặc định): Đơn Mẫu 09 + phần xác nhận UBND xã + người nhận kết quả.
- "authorized_person": nhân thân MỘT người = chủ hồ sơ (bên ủy quyền) → khối doiTuongKhac*; trả kèm
  ``authorizedSubject`` = "Người cao tuổi" khi chủ hồ sơ từ đủ 60 tuổi.

OCR fallback (``apply_ocr_fallback``): LLM bỏ sót dòng thửa / số phát hành / số vào sổ / điện thoại của Đơn thì đọc lại
theo nhãn in sẵn của Mẫu 09.
"""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_bac_ninh.process import mapper
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_bac_ninh.process.prompt import (
    EXTRA_RULES,
    RULES_UYQUYEN,
)
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_bac_ninh.process.schema import (
    ALIASES,
    ALLOWED,
    ALLOWED_UYQUYEN,
    COMPACT_COMP_BY_NAME,
    COMPACT_COMP_UYQUYEN,
    FIELDS,
    FIELDS_UYQUYEN,
)

# Một dòng thửa của mục 3.1 Mẫu 09: "Thửa đất số: 59  Tờ bản đồ số: XV  Diện tích (m2): 312".
_THUA_RE = re.compile(
    r"Th[ửu]a\s*đ[ấa]t\s*s[ốo]\s*:?\s*(\d+[a-zA-Z]?)\s*[,;]?\s*"
    r"T[ờo]\s*b[ảa]n\s*đ[ồo]\s*s[ốo]\s*:?\s*([IVXLC]+|\d+)\s*[,;]?\s*"
    r"Di[ệe]n\s*t[íi]ch\s*(?:\(\s*m\s*[2²]?\s*\))?\s*:?\s*(\d[\d.,]*)",
    re.IGNORECASE,
)
_SO_PHAT_HANH_RE = re.compile(r"S[ốo]\s*ph[áa]t\s*h[àa]nh\s*:?\s*([A-ZĐ]{1,2}\s?\d{6,8})", re.IGNORECASE)
_SO_VAO_SO_RE = re.compile(r"S[ốo]\s*v[àa]o\s*s[ổo]\s*:?\s*([^;\n]+?)\s*(?:,|;|\n|Ng[àa]y\s*c[ấa]p)", re.IGNORECASE)
# Số vào sổ GCN mẫu cũ ĐỦ hai vế: "00704-QSDĐ/344-QĐCT", "00704 QSDD/344QĐCT" (GCN, Giấy ủy quyền).
_SO_VAO_SO_DU_RE = re.compile(r"\b(\d{3,6})[\s.\-]*(QSD[ĐD])\s*/\s*(\d{1,5})[\s.\-]*(Q[ĐD][A-ZĐ]{1,4})\b", re.IGNORECASE)
_DIEN_THOAI_RE =re.compile(r"đi[ệe]n\s*tho[ạa]i\s*:?\s*((?:\+?84|0)[\d.\s-]{8,14}\d)", re.IGNORECASE)


def _as_dict(raw_fields) -> dict:
    if isinstance(raw_fields, dict):
        return dict(raw_fields)
    if isinstance(raw_fields, list):
        return {
            f.get("name"): f.get("value")
            for f in raw_fields
            if isinstance(f, dict) and f.get("name") and f.get("value") not in (None, "", {}, [])
        }
    return {}


def _count(value) -> int:
    return len([p for p in re.split(r"\s*[;\n]\s*|,\s+", str(value or "")) if p.strip()])


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(d.get("text") or "" for d in documents)

    # Dòng thửa: OCR đọc được NHIỀU dòng hơn LLM trả → thay cả ba danh sách (giữ đúng cặp thửa / tờ / diện tích).
    rows, seen = [], set()
    for m in _THUA_RE.finditer(text):
        row = (m.group(1), m.group(2).upper(), m.group(3).strip(".,"))
        if row not in seen:
            seen.add(row)
            rows.append(row)
    if rows and len(rows) > _count(fields.get("Don_ThuaSo")):
        fields["Don_ThuaSo"] = ", ".join(r[0] for r in rows)
        fields["Don_ToBanDo"] = ", ".join(r[1] for r in rows)
        fields["Don_DienTich"] = ", ".join(r[2] for r in rows)

    for name, pattern in (("Gcn_SoPhatHanh", _SO_PHAT_HANH_RE), ("Gcn_SoVaoSo", _SO_VAO_SO_RE),
                          ("Don_DienThoai", _DIEN_THOAI_RE)):
        if str(fields.get(name) or "").strip():
            continue
        m = pattern.search(text)
        if m:
            value = " ".join(m.group(1).split()).strip(" .,;")
            if value:
                fields[name] = value

    # OCR dòng 3.8 của Đơn có khi rớt vế sau dấu "/" ("00704 QSDĐ" thay "00704 QSDĐ/344 QĐCT"); GCN / Giấy ủy quyền in
    # đủ số cùng phần đầu → lấy số đủ, viết theo kiểu Đơn ("00704 QSDĐ/344 QĐCT").
    so_vao_so = str(fields.get("Gcn_SoVaoSo") or "").strip()
    head = re.match(r"\d{3,6}", so_vao_so)
    if head and "/" not in so_vao_so:
        for m in _SO_VAO_SO_DU_RE.finditer(text):
            if m.group(1) == head.group(0):
                qsd = "QSDĐ" if m.group(2).upper() in ("QSDD", "QSDĐ") else m.group(2)
                fields["Gcn_SoVaoSo"] = f"{m.group(1)} {qsd}/{m.group(3)} {m.group(4).upper().replace('QD', 'QĐ', 1)}"
                break
    return fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    if str((options or {}).get("purpose") or "registration_form") == "authorized_person":
        res = await runner.run(
            files_by_role,
            fields=FIELDS_UYQUYEN,
            allowed=ALLOWED_UYQUYEN,
            comp_by_name=COMPACT_COMP_UYQUYEN,
            aliases=ALIASES,
            extra_rules=RULES_UYQUYEN,
        )
        raw = res["fields"]
        res["fields"], warnings = mapper.enrich_authorized(raw)
        subject = mapper.authorized_subject(raw)
        if subject and res["fields"]:
            res["authorizedSubject"] = subject
        if warnings:
            res.setdefault("errors", []).extend(warnings)
        return res

    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=apply_ocr_fallback,
    )
    res["fields"] = mapper.enrich(res["fields"])
    return res
