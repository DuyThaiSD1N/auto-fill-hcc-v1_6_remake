"""Map compact facts của đăng ký lại kết hôn → field UI (dữ liệu mẫu từ spec)."""

from app.pipelines.ket_hon_lai.process import mapper

_VO = {  # bên nữ
    "CccdNu_HoTen": "MÁ THỊ SỐ",
    "CccdNu_SoDinhDanh": "012189003303",
    "CccdNu_NgaySinh": "01/01/1989",
    "CccdNu_NgayCap": "16/03/2026",
    "CccdNu_NoiCap": "BỘ CÔNG AN / MINISTRY OF PUBLIC SECURITY",
    "CccdNu_DanToc": "H'Mông",
    "CccdNu_NoiCuTru_TrongNuoc": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Đoàn Kết",
                                  "diaChi": "Tổ dân phố Cư Nhà La"},
}
_CHONG = {  # bên nam
    "CccdNam_HoTen": "SÙNG A CỦ",
    "CccdNam_SoDinhDanh": "012086005221",
    "CccdNam_NgaySinh": "01/01/1986",
    "CccdNam_NgayCap": "06/01/2026",
    "CccdNam_NoiCap": "Bộ Công an",
    "CccdNam_DanToc": "H'Mông",
    "CccdNam_NoiCuTru_TrongNuoc": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Đoàn Kết",
                                   "diaChi": "Tổ dân phố Cư Nhà La"},
}
_HOSO = {
    "HoTich_So": "40/2026",
    "HoTich_NgayDangKy": "01/04/2026",
    "HoTich_TinhDangKy": "Lai Châu",
    "HoTich_XaDangKy": "Phường Đoàn Kết",
}


def _fields(*dicts):
    merged = {}
    for d in dicts:
        merged.update(d)
    return [{"name": k, "value": v} for k, v in merged.items()]


def _by_name(out):
    return {f["name"]: f for f in out}


def test_missing_wife_cccd_falls_back_to_marriage_cert():
    """Thiếu CCCD vợ → LLM đã lấy CccdNu_* từ giấy CN kết hôn; mapper vẫn map đủ bên nữ."""
    out = _by_name(mapper.enrich(_fields(_CHONG, _HOSO,
                                         {"CccdNu_HoTen": "MÁ THỊ SỐ", "CccdNu_NgaySinh": "01/01/1989"})))
    assert out["HoTenBenNu"]["value"] == "MÁ THỊ SỐ"
    assert out["NgaySinhBenNu"]["value"] == "01/01/1989"
    assert out["HoTenBenNam"]["value"] == "SÙNG A CỦ"


def test_registry_dang_ky_lai_ket_hon_entry():
    from app.pipelines.ket_hon_lai import process as agent
    from app.channels.handfree.procedure_registry import get_pipeline, get_procedure
    from app.upload_session.classify import classify_text, route_to_slot

    proc = get_procedure("dang-ky-lai-ket-hon")
    assert get_pipeline("dang-ky-lai-ket-hon") is agent.run
    assert not proc.get("hiddenFromList")          # đã đẩy lên card chọn thủ tục (2026-08-13)
    assert proc["needsAgencySelect"] is True
    assert proc["keKhaiUrl"].endswith("019d2bfd-6711-733d-b674-f82cb6606242")
    docs = {r["key"]: r for r in proc["requiredDocs"]}
    assert set(docs) == {"cccd_nam", "cccd_nu", "ho_tich", "to_khai", "khac"}
    assert not docs["ho_tich"].get("optional")     # GCN kết hôn cũ BẮT BUỘC

    # GCN kết hôn cũ: classify hiện tại nhận "chứng nhận kết hôn" → key ho_tich route thẳng vào ô.
    info = classify_text("GIẤY CHỨNG NHẬN KẾT HÔN Số: 40/2026")
    key, _side, _note = route_to_slot(info, proc["requiredDocs"], [], None)
    assert key == "ho_tich"
