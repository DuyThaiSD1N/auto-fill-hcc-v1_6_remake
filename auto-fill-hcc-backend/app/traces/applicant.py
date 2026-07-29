"""Suy ra "người làm thủ tục" để lưu trace.

Ưu tiên: (1) tên từ UI/VNeID cổng đã điền (options.formContext.applicantFullname);
(2) nếu không có → lấy từ kết quả parse: ô người yêu cầu trong fields UI, rồi tới
llm_output thô (ưu tiên người yêu cầu, cuối cùng lấy bất kỳ tên người hợp lý).
"""

# Ô "người yêu cầu" trong fields UI (kết quả cuối, đã được mapper ưu tiên gán).
_REQUESTER_UI_FIELDS = ("HoVaTenC", "CongDan_tenCongDan")

# Khoá tên người yêu cầu trong llm_output thô, theo thứ tự ưu tiên.
_REQUESTER_RAW_KEYS = (
    "Requester_FullName",
    "Cccd_HoTen",
    "CccdNam_HoTen",
    "ToKhai_HoTenNguoiYeuCau",
)

# Dấu hiệu một khoá "tên người" bất kỳ (fallback cuối) — vd Gbt_HoTenNguoiMat, Mother_FullName.
_NAME_MARKERS = ("HoTen", "HoVaTen", "FullName")


def _clean(value) -> str:
    return str(value or "").strip()


def _from_fields(result: dict) -> str:
    fields = result.get("fields") or []
    by_name = {f.get("name"): f.get("value") for f in fields if isinstance(f, dict)}
    for name in _REQUESTER_UI_FIELDS:
        val = _clean(by_name.get(name))
        if val:
            return val
    return ""


def _from_raw(result: dict) -> str:
    raw = result.get("llm_output")
    if not isinstance(raw, dict):
        return ""
    for key in _REQUESTER_RAW_KEYS:
        val = _clean(raw.get(key))
        if val:
            return val
    # Bất kỳ tên người nào hợp lý.
    for key, value in raw.items():
        if isinstance(key, str) and any(m in key for m in _NAME_MARKERS):
            val = _clean(value)
            if val:
                return val
    return ""


def resolve_applicant_name(options: dict | None, result: dict | None) -> str | None:
    ctx = (options or {}).get("formContext") or {}
    name = _clean(ctx.get("applicantFullname"))
    if name:
        return name
    result = result or {}
    return _from_fields(result) or _from_raw(result) or None
