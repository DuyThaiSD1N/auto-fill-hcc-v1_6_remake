"""Unit test mapper "Giao đất, cho thuê đất, chuyển mục đích SDĐ..." (Đà Nẵng).

Kiểm: HAI vai (tự nộp / ủy quyền / thiếu chủ hồ sơ), panel THỬA ĐẤT (Số thửa/Số tờ/địa chỉ thửa), nội
dung yêu cầu đa dòng + fallback, không lẫn địa chỉ người ↔ thửa đất."""

from app.pipelines.giao_thue_chuyen_muc_dich_dat_da_nang.process.mapper import enrich


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _map(vals: dict) -> dict:
    fields, _ = enrich(_flds(vals), {})
    return {f["name"]: f["value"] for f in fields}


_PARCEL = {
    "ThuaDat_SoThua": "thửa đất số 308",
    "ThuaDat_SoTo": "tờ bản đồ số 103",
    "ThuaDat_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "50A Nguyễn Chí Thanh"},
}


def test_tu_nop_tick_va_dien_1_vai():
    vals = {
        "ChuHoSo_LoaiChuThe": "Cá nhân",
        "ChuHoSo_HoTen": "LÊ THỊ THÚY KIỀU",
        "NguoiNop_HoTen": "LÊ THỊ THÚY KIỀU",
        "NguoiNop_SoDinhDanh": "048149001928",
        "NguoiNop_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "88 Quang Trung"},
        **_PARCEL,
    }
    out = _map(vals)
    assert out["data[ownerFullname]"] == "LÊ THỊ THÚY KIỀU"
    assert out["data[isOwnerDossier]"] is True
    assert out["data[fullname]"] == "LÊ THỊ THÚY KIỀU"
    assert out["data[chonDoiTuong]"] == "Cá nhân"
    # địa chỉ NGƯỜI (không phải thửa đất)
    assert out["data[province]"] == "Thành phố Đà Nẵng"
    assert out["data[district]"] == "Phường Hải Châu"
    assert out["data[address]"] == "88 Quang Trung"


def test_uy_quyen_bo_tich_dien_2_vai_khong_lan():
    vals = {
        "ChuHoSo_HoTen": "LÊ THỊ THÚY KIỀU",
        "NguoiNop_HoTen": "VÕ HOÀI SƠN",
        "NguoiNop_NgaySinh": "12/11/1984",
        "NguoiNop_GioiTinh": "Nam",
        "NguoiNop_SoDinhDanh": "048084007873",
        "NguoiNop_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "12 Lê Lợi"},
        **_PARCEL,
    }
    out = _map(vals)
    assert out["data[ownerFullname]"] == "LÊ THỊ THÚY KIỀU"
    assert out["data[isOwnerDossier]"] is False
    assert out["data[fullname]"] == "VÕ HOÀI SƠN"
    assert out["data[identityNumber]"] == "048084007873"
    assert out["data[gender]"] == "Nam"


def test_panel_thua_dat():
    out = _map({"ChuHoSo_HoTen": "NGUYỄN VĂN A", "NguoiNop_HoTen": "NGUYỄN VĂN A", **_PARCEL})
    # Số thửa/Số tờ đã bỏ chữ dẫn.
    assert out["data[SoThuaDat]"] == "308"
    assert out["data[SoToBanDo]"] == "103"
    assert out["data[province2]"] == "Thành phố Đà Nẵng"
    assert out["data[district2]"] == "Phường Hải Châu"
    assert out["data[diaChiThuaDat]"] == "50A Nguyễn Chí Thanh"
    assert out["data[nation2]"] == "Việt Nam"


def test_thua_dat_chi_phuong_tinh_van_dien():
    # Thửa đất chỉ ghi tới cấp phường + tỉnh (không số nhà) → KHÔNG bị drop như địa chỉ người.
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN VĂN A", "NguoiNop_HoTen": "NGUYỄN VĂN A",
        "ThuaDat_DiaChi": {"tinh": "Tỉnh Bắc Ninh", "xa": "Phường Song Liễu", "diaChi": ""},
    })
    assert out["data[province2]"] == "Thành phố Bắc Ninh"
    assert out["data[district2]"] == "Phường Song Liễu"
    assert "data[diaChiThuaDat]" not in out  # không có chi tiết → bỏ trống, không bịa


def test_noi_dung_yeu_cau_da_dong():
    noi_dung = "Chuyển 41,3 m² đất trồng cây lâu năm (CLN) sang đất ở\n- Thửa số 308, tờ bản đồ 103"
    out = _map({"ChuHoSo_HoTen": "LÊ THỊ THÚY KIỀU", "NguoiNop_HoTen": "LÊ THỊ THÚY KIỀU",
                "NoiDungYeuCau": noi_dung})
    assert out["data[noidungyeucaugiaiquyet]"] == noi_dung  # giữ nguyên xuống dòng


def test_noi_dung_trong_thi_fallback_cau_khung():
    out = _map({"ChuHoSo_HoTen": "LÊ THỊ THÚY KIỀU", "NguoiNop_HoTen": "LÊ THỊ THÚY KIỀU"})
    assert out["data[noidungyeucaugiaiquyet]"].startswith("LÊ THỊ THÚY KIỀU ĐỀ NGHỊ GIẢI QUYẾT")


def test_tu_nop_dia_chi_lay_tu_chu_ho_so_khi_nguoi_nop_thieu():
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN VĂN A", "NguoiNop_HoTen": "NGUYỄN VĂN A",
        "ChuHoSo_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hòa Cường", "diaChi": "5 Núi Thành"},
    })
    assert out["data[province]"] == "Thành phố Đà Nẵng"
    assert out["data[district]"] == "Phường Hòa Cường"
    assert out["data[address]"] == "5 Núi Thành"


def test_chu_ho_so_to_chuc():
    out = _map({
        "ChuHoSo_LoaiChuThe": "Tổ chức",
        "ChuHoSo_HoTen": "Công ty TNHH ABC",
        "NguoiNop_HoTen": "TRẦN VĂN B",
        "NguoiNop_SoDinhDanh": "049084001234",
        "NguoiNop_MaSoThue": "0401234567",
    })
    assert out["data[ownerFullname]"] == "Công ty TNHH ABC"
    assert out["data[organization]"] == "Công ty TNHH ABC"
    # ủy quyền (người nộp cá nhân khác chủ tổ chức)
    assert out["data[isOwnerDossier]"] is False
    assert out["data[chonDoiTuong]"] == "Cá nhân"


def test_thieu_chu_ho_so_van_giu_nguoi_nop():
    fields, warnings = enrich(_flds({"NguoiNop_HoTen": "VÕ HOÀI SƠN", "NguoiNop_SoDinhDanh": "048084007873"}), {})
    names = {f["name"] for f in fields}
    assert "data[fullname]" in names
    assert any("chủ hồ sơ" in w.lower() for w in warnings)


# ===== Planner đính kèm (bảng 12 dòng, crawl 29/10/2026) =====

from app.pipelines.giao_thue_chuyen_muc_dich_dat_da_nang.attach import planner as _planner

_COMPONENTS = [{"index": i + 1, "componentName": n} for i, n in enumerate(_planner._DEFAULT_ROWS)]
_DON_CMD = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐỀ NGHỊ CHUYỂN MỤC ĐÍCH\nKính gửi: UBND phường\nMẫu số 01"
_DON_GIAO = "ĐƠN XIN GIAO ĐẤT, CHO THUÊ ĐẤT, CHO PHÉP CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT\nKính gửi: UBND phường"
_DON_GIA_HAN = "ĐƠN ĐỀ NGHỊ GIA HẠN SỬ DỤNG ĐẤT\nKính gửi: UBND phường"


def _plan(docs: list[tuple[str, str, str | None]], components=_COMPONENTS):
    """docs = [(tên file, OCR, loại LLM trả — None nếu LLM không trả)]."""
    files = [{"name": n} for n, _, _ in docs]
    ocr = [{"name": n, "text": t} for n, t, _ in docs]
    llm = {i: d for i, (_, _, d) in enumerate(docs) if d is not None}
    return _planner.build_plan_items(files, ocr, llm, components)


def _rows(items):
    return {it["fileName"]: it["componentIndex"] for it in items}


def test_dinh_kem_llm_other_khong_bi_rule_ghi_de_va_khong_bo_tep():
    # Giấy ủy quyền nhắc tới "giấy chứng nhận quyền sử dụng đất" → rule cũ ép thành GCN; LLM nói other thì giữ other.
    # Tệp không có dòng riêng (other, CCCD) đính chung vào dòng Đơn, giữ tên thật — đủ 5/5 tệp.
    items, warnings, classified = _plan([
        ("don.pdf", _DON_CMD, "don_m01"),
        ("gcn.pdf", "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT", "gcn"),
        ("giấy ủy quyền_0001.pdf", "GIẤY ỦY QUYỀN ... theo giấy chứng nhận quyền sử dụng đất số AB 000001", "other"),
        ("to_khai.pdf", "TỜ KHAI LỆ PHÍ TRƯỚC BẠ Số CMND/CCCD", "other"),
        ("cccd.pdf", "CĂN CƯỚC CÔNG DÂN", "cccd"),
    ])
    assert _rows(items) == {"don.pdf": 1, "gcn.pdf": 8, "giấy ủy quyền_0001.pdf": 1, "to_khai.pdf": 1, "cccd.pdf": 1}
    assert {it["fileName"]: it["documentName"] for it in items if it["componentIndex"] == 1} == {
        "don.pdf": "Đơn đề nghị theo Mẫu số 01",
        "giấy ủy quyền_0001.pdf": "giấy ủy quyền 0001",
        "to_khai.pdf": "to khai",
        "cccd.pdf": "Căn cước công dân",
    }
    assert all(it["loaiBan"] == "Bản chính" for it in items if it["componentIndex"] == 1)
    assert len(warnings) == 1 and "giấy ủy quyền_0001.pdf" in warnings[0] and "cccd.pdf" in warnings[0]
    assert all(it["componentName"] == _planner._DEFAULT_ROWS[it["componentIndex"] - 1] for it in items)


def test_dinh_kem_chu_truong_dau_tu_theo_nhanh():
    vb = ("qd.pdf", "QUYẾT ĐỊNH chấp thuận chủ trương đầu tư", "chu_truong_dau_tu")
    items, _, _ = _plan([("don.pdf", _DON_CMD, "don_m01"), vb])
    assert _rows(items)["qd.pdf"] == 7
    items, _, _ = _plan([("don.pdf", _DON_GIAO, "don_m01"), vb])
    assert _rows(items)["qd.pdf"] == 5


def test_dinh_kem_gia_han_gcn_vao_dong_12():
    items, _, _ = _plan([
        ("don.pdf", _DON_GIA_HAN, "don_m01"),
        ("gcn.pdf", "GIẤY CHỨNG NHẬN", "gcn"),
        ("vb.pdf", "cho phép gia hạn thời hạn hoạt động của dự án", "van_ban_gia_han_du_an"),
    ])
    assert _rows(items) == {"don.pdf": 1, "gcn.pdf": 12, "vb.pdf": 12}


def test_dinh_kem_cac_dong_con_lai():
    items, _, _ = _plan([
        ("lcndt.pdf", "phê duyệt kết quả lựa chọn nhà đầu tư", "lua_chon_nha_dau_tu"),
        ("dg.pdf", "kết quả đấu giá quyền sử dụng đất không thành", "van_ban_giao_thue"),
        ("pa1.pdf", "PHƯƠNG ÁN SỬ DỤNG ĐẤT của tổ chức kinh tế", "phuong_an_sdd"),
        ("pa2.pdf", "PHƯƠNG ÁN SỬ DỤNG ĐẤT Công ty nông, lâm nghiệp", "phuong_an_sdd"),
        ("pa3.pdf", "PHƯƠNG ÁN SỬ DỤNG ĐẤT thu hồi của công ty nông, lâm nghiệp", "phuong_an_sdd"),
        ("lua.pdf", "Phương án sử dụng tầng đất mặt", "phuong_an_dat_mat"),
        ("rung.pdf", "báo cáo hiện trạng rừng", "du_an_giao_rung"),
        ("dgr.pdf", "biên bản đấu giá cho thuê rừng", "dau_gia_thue_rung"),
    ])
    assert _rows(items) == {
        "lcndt.pdf": 6, "dg.pdf": 5, "pa1.pdf": 9, "pa2.pdf": 10, "pa3.pdf": 11,
        "lua.pdf": 2, "rung.pdf": 3, "dgr.pdf": 4,
    }


def test_dinh_kem_rule_chi_khi_llm_khong_tra_va_ten_khong_trung():
    items, _, classified = _plan([
        ("a.pdf", "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT", None),
        ("b.pdf", "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT", "gcn"),
    ])
    assert [c["source"] for c in classified] == ["rule", "llm"]
    names = [it["documentName"] for it in items]
    assert len(set(names)) == 2 and names[0].endswith("(1)")


def test_dinh_kem_khong_co_attachment_context_dung_bang_mac_dinh():
    items, _, _ = _plan([("gcn.pdf", "GIẤY CHỨNG NHẬN", "gcn")], components=None)
    assert _rows(items) == {"gcn.pdf": 8}
    # Trang thiếu dòng GCN → không bỏ tệp, đính vào dòng Đơn.
    items, warnings, _ = _plan([("gcn.pdf", "GIẤY CHỨNG NHẬN", "gcn")], components=_COMPONENTS[:3])
    assert _rows(items) == {"gcn.pdf": 1} and "gcn.pdf" in warnings[0]
