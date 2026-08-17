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


def test_map_full_case():
    out = _by_name(mapper.enrich(_fields(_VO, _CHONG, _HOSO)))

    # Bên nữ (vợ)
    assert out["HoTenBenNu"]["value"] == "MÁ THỊ SỐ"
    assert out["SoDinhDanh_BenNu"]["value"] == "012189003303"
    assert out["SoGiayToDinhDanh_BenNu"]["value"] == "012189003303"
    # Nhãn option eForm cổng mới: nơi cấp Bộ Công an → "Thẻ Căn cước" (thẻ mẫu mới).
    assert out["LoaiGiayToDinhDanh_BenNu"]["value"] == "Thẻ Căn cước"
    assert out["NgaySinhBenNu"]["value"] == "01/01/1989"
    assert out["NgayCapDD_BenNu"]["value"] == "16/03/2026"
    assert out["NoiCapDD_BenNu"]["value"] == "Bộ Công an"        # bỏ đuôi tiếng Anh
    assert out["DanTocBenNu"]["value"] == "Mông (Hmông)"          # H'Mông -> option đúng
    assert out["QuocTichBenNu"]["value"] == "Việt Nam"
    assert out["LoaiCuTru_BenNu"]["value"] == "Thường trú"
    assert out["NoiCuTru_BenNu"]["value"] == "1"
    # Sáp nhập ĐVHC: "Đoàn Kết" (Lai Châu) đổi tên chuẩn thành "Phường Đoàn Kết" (remap data
    # _shared/data/remap_lai_chau.json) — khớp option trên cổng.
    assert out["NoiCuTru_BenNu_TrongNuoc"]["value"]["xa"] == "Phường Đoàn Kết"
    assert out["NoiCuTru_BenNu_TrongNuoc"]["value"]["diaChi"] == "Tổ dân phố Cư Nhà La"

    # Bên nam (chồng)
    assert out["HoTenBenNam"]["value"] == "SÙNG A CỦ"
    assert out["SoDinhDanh_BenNam"]["value"] == "012086005221"
    assert out["NoiCapDD_BenNam"]["value"] == "Bộ Công an"
    assert out["LoaiGiayToDinhDanh_BenNam"]["value"] == "Thẻ Căn cước"

    # Mặc định vàng: tình trạng hôn nhân + số lần kết hôn
    for side in ("BenNu", "BenNam"):
        assert out[f"SoLanKetHon_{side}"]["value"] == "1"
        assert out[f"SoLanKetHon_{side}"].get("default") is True
        assert out[f"SoLanKetHon_{side}"]["comp"] == "x-input-number"
        assert out[f"LoaiTinhTrangHonNhan_{side}"]["value"] == "Hiện tại đang có vợ/chồng"
        assert out[f"LoaiTinhTrangHonNhan_{side}"].get("default") is True

    # Hồ sơ gốc (đăng ký lại)
    assert out["loaiDangKy"]["value"] == "Đăng ký lại"
    assert out["loaiDangKy"].get("default") is True
    assert out["soDangKyTruocDay"]["value"] == "40/2026"
    assert out["quyenDangKyTruocDay"]["value"] == "01/2026"       # 40//200+1 = 1
    assert out["quyenDangKyTruocDay"].get("default") is True
    assert out["ngayDangKyTruocDay"]["value"] == "01/04/2026"
    assert out["noiDangKyTruocDay_filter"]["value"] == "Lai Châu"       # tỉnh (lọc)
    assert out["noiDangKyTruocDay"]["value"] == "Phường Đoàn Kết"        # xã/phường chuẩn

    # Đề nghị cấp bản sao mặc định Có + 1 bản (vàng)
    assert out["CapBanSao"]["value"] == "Có"
    assert out["CapBanSao"].get("default") is True
    assert out["SoLuong"]["value"] == "1"
    assert out["SoLuong"]["comp"] == "raw"
    assert out["SoLuong"].get("default") is True


def test_missing_wife_cccd_falls_back_to_marriage_cert():
    """Thiếu CCCD vợ → LLM đã lấy CccdNu_* từ giấy CN kết hôn; mapper vẫn map đủ bên nữ."""
    out = _by_name(mapper.enrich(_fields(_CHONG, _HOSO,
                                         {"CccdNu_HoTen": "MÁ THỊ SỐ", "CccdNu_NgaySinh": "01/01/1989"})))
    assert out["HoTenBenNu"]["value"] == "MÁ THỊ SỐ"
    assert out["NgaySinhBenNu"]["value"] == "01/01/1989"
    assert out["HoTenBenNam"]["value"] == "SÙNG A CỦ"


def test_registry_dang_ky_lai_ket_hon_entry():
    from app.pipelines.ket_hon_lai import process as agent
    from app.procedures.registry import get_pipeline, get_procedure
    from app.upload_session.classify import classify_text, route_to_slot

    proc = get_procedure("dang-ky-lai-ket-hon")
    assert get_pipeline("dang-ky-lai-ket-hon") is agent.run
    assert not proc.get("hiddenFromList")          # đã đẩy lên card chọn thủ tục (2026-08-13)
    assert proc["needsAgencySelect"] is True
    assert proc["keKhaiUrl"].endswith("019d2bfd-6711-733d-b674-f82cb6606242")
    docs = {r["key"]: r for r in proc["requiredDocs"]}
    assert set(docs) == {"cccd_nam", "cccd_nu", "ho_tich", "to_khai"}
    assert not docs["ho_tich"].get("optional")     # GCN kết hôn cũ BẮT BUỘC

    # GCN kết hôn cũ: classify hiện tại nhận "chứng nhận kết hôn" → key ho_tich route thẳng vào ô.
    info = classify_text("GIẤY CHỨNG NHẬN KẾT HÔN Số: 40/2026")
    key, _side, _note = route_to_slot(info, proc["requiredDocs"], [], None)
    assert key == "ho_tich"
