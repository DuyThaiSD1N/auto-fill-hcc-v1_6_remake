"""OCR fallback extractors for water-contract name transfer."""

from app.pipelines.dang_ky_dat_dai.process.fallback import extract_gcn_serial


def _as_dict(raw_fields):
    if isinstance(raw_fields, dict):
        return dict(raw_fields)
    if isinstance(raw_fields, list):
        return {
            f.get("name"): f.get("value")
            for f in raw_fields
            if isinstance(f, dict) and f.get("name") and f.get("value") not in (None, "", {}, [])
        }
    return {}


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    if fields.get("DonDoiTen_TenCoQuanToChuc") or fields.get("DonDoiTen_MaSoThue"):
        return fields
    if not fields.get("Gcn_SoPhatHanh"):
        text = "\n".join(d.get("text") or "" for d in documents)
        serial = extract_gcn_serial(text)
        if serial:
            fields["Gcn_SoPhatHanh"] = serial
    return fields
