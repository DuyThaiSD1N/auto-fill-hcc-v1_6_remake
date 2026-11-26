from app.pipelines.trich_luc.process.mapper import enrich


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


def test_trich_luc_maps_declaration_relationship_to_radio_label():
    result = _by_name(enrich([
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "TRẦN VĂN TRUNG"},
        {"name": "CopyRequest_QuanHe", "value": "Con đẻ"},
    ]))

    assert result["NYC_QuanHe"]["comp"] == "x-radio"
    assert result["NYC_QuanHe"]["value"] == "Con Đẻ"


def test_trich_luc_ambiguous_ba_relationship_ticks_khac_with_default():
    result = _by_name(enrich([
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "TRẦN VĂN TRUNG"},
        {"name": "CopyRequest_QuanHe", "value": "Ba"},
    ]))

    # "Ba" nhập nhằng (bố Nam bộ vs Bà) → không đoán vai, chỉ tick "Khác" kèm viền vàng.
    assert result["NYC_QuanHe"]["value"] == "Khác"
    assert result["NYC_QuanHe"].get("default") is True


# --- Form cũ eForm Bộ Tư pháp (key trich-luc-ks-eform) -------------------------------------------------------------

_EFORM_KEY = "trich-luc-ks-eform"


def _popup_detect_key(url: str) -> str | None:
    """Mô phỏng bước khớp URL của popup: urlScope chặn host trước, rồi mới xét urlIncludes (đã lower-case)."""
    from app.procedures.ke_khai_links import with_ke_khai_detect_urls
    from app.procedures.registry import public_list

    url = url.lower()
    for proc in with_ke_khai_detect_urls(public_list()):
        detect = proc.get("detect") or {}
        scope = detect.get("urlScope") or []
        if scope and not any(s and str(s).lower() in url for s in scope):
            continue
        if any(u and str(u).lower() in url for u in detect.get("urlIncludes") or []):
            return proc["key"]
    return None


def test_eform_cu_noi_ve_pipeline_trich_luc():
    from app.pipelines.trich_luc.attach import plan as old_attach
    from app.pipelines.trich_luc.process import run as old_run
    from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

    entry = get_procedure(_EFORM_KEY)
    assert entry["formVariantOf"] == "trich-luc-ks"
    assert entry["hasAttachmentStep"] is True and entry["supportsSplitDocuments"] is True
    assert entry["collectFormContext"] is True
    assert get_pipeline(_EFORM_KEY) is old_run
    assert get_attach_pipeline(_EFORM_KEY) is old_attach
    # Key gốc vẫn chạy Cổng DVC quốc gia mới.
    assert get_pipeline("trich-luc-ks") is not old_run


def test_eform_cu_nhan_dien_theo_url_moj_khong_tranh_voi_dvc_moi():
    moj = "https://dichvucongnganhtuphap.moj.gov.vn/nop-ho-so/100002?tinhThanhId=1&maThuTuc=2.000635&MaDVC=2.000635.01"
    assert _popup_detect_key(moj) == _EFORM_KEY
    dvc_moi = "https://dichvucong.gov.vn/nop-ho-so?formalityId=019d2bfd-867c-72db-b6a7-dcbd8c763807"
    assert _popup_detect_key(dvc_moi) == "trich-luc-ks"


def test_eform_cu_chi_cho_auto_fill_khong_len_tro_ly():
    from app.channels.handfree.procedure_registry import PROCEDURES as HANDFREE_PROCEDURES

    assert all(p.get("key") != _EFORM_KEY for p in HANDFREE_PROCEDURES)
