"""[Sở Xây dựng] Đăng ký lại phương tiện khi chuyển quyền sở hữu, không đổi cơ quan đăng ký (1.004002).

Khoá các điều dễ vỡ: chủ MỚI (bên mua) mới là chủ phương tiện trên form, không lấy chủ cũ; Phần I là người đại diện
của chủ mới; chọn "Tổ chức" trước khi điền panel doanh nghiệp; ô lý do ghép đủ bên chuyển + văn bản + nơi đăng ký cũ;
data[email] dùng chung chỉ phát một lần. Đính kèm: một PDF gộp cả bộ được tách theo trang như ảnh ánh xạ — dòng 3 gộp
Hợp đồng → Hóa đơn → GCN đăng ký cũ (Bản sao), dòng 4 gộp Đơn 07 → Đơn xóa 10, CCCD không đính.
"""

from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.attach import planner
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.process import mapper
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.process.schema import (
    ALLOWED,
    UI_COMP_BY_NAME,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

_KEY = "dang-ky-lai-phuong-tien-chuyen-quyen-so-huu-khong-doi-co-quan"
_TITLE = ("đăng ký lại phương tiện trong trường hợp chuyển quyền sở hữu phương tiện nhưng không thay đổi cơ quan "
          "đăng ký phương tiện")

# Hồ sơ bịa — không dùng dữ liệu thật.
_FACTS = {
    "ChuPT_LoaiDoiTuong": "Tổ chức",
    "ChuPT_Ten": "CÔNG TY TNHH DU LỊCH SÔNG XANH",
    "ChuPT_MaDinhDanhToChuc": "0401 234 567",
    "ChuPT_TruSo": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "12 Nguyễn Văn Linh"},
    "ChuPT_DienThoai": "0912.345.678",
    "ChuPT_Email": "songxanh@example.com",
    "NguoiNop_HoTen": "Bà LÊ THỊ MAI",
    "NguoiNop_SoDinhDanh": "048 190 012 345",
    "NguoiNop_GioiTinh": "Nữ",
    "NguoiNop_NgayCap": "5/6/2024",
    "NguoiNop_NoiCap": "Bộ Công an",
    "PhuongTien_Ten": "TÀU KHÁCH VỎ THÉP 20 HP",
    "PhuongTien_SoDangKy": "ĐNa-0456",
    "PhuongTien_SoGiayChungNhan": "456/ĐK",
    "PhuongTien_NoiDangKyCu": "Sở Giao thông vận tải tỉnh Quảng Nam",
    "PhuongTien_NgayDangKyCu": "20/3/2019",
    "ChuyenQuyen_HinhThuc": "Mua lại",
    "ChuyenQuyen_BenChuyen": "Công ty TNHH MTV Biển Bạc",
    "ChuyenQuyen_BenChuyenDiaChi": "05 Bạch Đằng, phường Hải Châu, thành phố Đà Nẵng",
    "ChuyenQuyen_VanBan": "Hợp đồng mua bán phương tiện thủy nội địa",
    "ChuyenQuyen_SoVanBan": "00012/2026/CCGD",
    "ChuyenQuyen_NgayVanBan": "10/01/2026",
    "Don_KinhGui": "Sở Xây dựng thành phố Đà Nẵng",
    "Don_DiaDanh": "Đà Nẵng",
    "Don_NguoiKy": "Giám đốc Lê Thị Mai",
}


def _facts(**over):
    data = {**_FACTS, **over}
    return [{"name": k, "value": v} for k, v in data.items() if v is not None]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _entry():
    return next(p for p in registry.PROCEDURES if p["key"] == _KEY)


# ---------------- registry / nhận diện ----------------

def test_registry_co_pipeline_process_va_dinh_kem():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert _KEY in registry._PIPELINE
    assert _KEY in registry._ATTACH_PIPELINE


def test_key_trung_ke_khai_links_va_chon_so():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.004002"
    assert link["selectSo"] is True
    public = next(p for p in with_ke_khai_detect_urls(registry.PROCEDURES) if p["key"] == _KEY)
    assert "matthc=1.004002" in public["detect"]["urlIncludes"]


def test_cum_nhan_dien_khop_tieu_de_va_khong_lan_xoa_dang_ky():
    phrase = _entry()["detect"]["textIncludes"][0].lower()
    assert phrase in _TITLE
    assert phrase not in "xóa đăng ký phương tiện thủy nội địa"


# ---------------- process mapper ----------------

def test_chu_moi_to_chuc_dien_phan_i_ii_va_don():
    fields, warnings = mapper.enrich(_facts(), {})
    ui = _values(fields)

    assert fields[0] == {"name": "data[chonDoiTuong]", "comp": "dom-select", "value": "Tổ chức"}
    # Phần I = người đại diện của chủ mới, bỏ danh xưng.
    assert ui["data[fullname]"] == "LÊ THỊ MAI"
    assert ui["data[identityNumber]"] == "048190012345"
    assert ui["data[identityDate]"] == "05/06/2024"
    assert ui["data[gender]"] == "Nữ"
    assert ui["data[phoneNumber]"] == "0912345678"
    # Phần II doanh nghiệp.
    assert ui["data[organization]"] == "CÔNG TY TNHH DU LỊCH SÔNG XANH"
    assert ui["data[taxCode]"] == "0401234567"
    assert ui["data[province1]"] == "Thành phố Đà Nẵng"
    assert ui["data[address1]"] == "12 Nguyễn Văn Linh"
    # Đơn Mẫu 07.
    assert ui["data[kinhgui]"] == "Sở Xây dựng thành phố Đà Nẵng"
    assert ui["data[toChucCaNhan]"] == "CÔNG TY TNHH DU LỊCH SÔNG XANH"
    assert ui["data[maDinhDanhToChuc]"] == "0401234567"
    assert "data[soDinhDanhCCCD]" not in ui
    assert ui["data[trusochinh]"].startswith("12 Nguyễn Văn Linh, ")
    assert ui["data[soDangKy]"] == "ĐNa-0456"
    assert ui["data[soGiayChungNhan]"] == "456/ĐK"
    assert ui["data[tenDiaPhuong]"] == "Thành phố Đà Nẵng"
    assert ui["data[nguoilamdon]"] == "Lê Thị Mai"
    assert ui["data[tenHoSo]"] == "Đăng ký lại phương tiện ĐNa-0456 do chuyển quyền sở hữu"
    # data[email] dùng chung Phần I ↔ Đơn → đúng MỘT lần.
    assert [f["name"] for f in fields].count("data[email]") == 1
    assert any("Ngày sinh" in w for w in warnings), "không có CCCD → nhắc ngày sinh đang là của tài khoản"


def test_ly_do_ghep_ben_chuyen_van_ban_va_noi_dang_ky_cu():
    ui = _values(mapper.enrich(_facts(), {})[0])
    assert ui["data[nayDeNghiCoQuan]"] == (
        "Chuyển quyền sở hữu: mua lại phương tiện từ Công ty TNHH MTV Biển Bạc (địa chỉ: 05 Bạch Đằng, phường Hải "
        "Châu, thành phố Đà Nẵng) theo Hợp đồng mua bán phương tiện thủy nội địa số 00012/2026/CCGD ngày 10/01/2026; "
        "phương tiện đã đăng ký tại Sở Giao thông vận tải tỉnh Quảng Nam ngày 20/03/2019 (Giấy chứng nhận số 456/ĐK)"
    )


def test_khong_co_cccd_nguoi_dai_dien_thi_dung_mst_va_tru_so():
    fields, warnings = mapper.enrich(_facts(NguoiNop_SoDinhDanh=None, NguoiNop_GioiTinh=None), {})
    ui = _values(fields)

    assert ui["data[identityNumber]"] == "0401234567"
    assert ui["data[province]"] == "Thành phố Đà Nẵng"
    assert ui["data[address]"] == "12 Nguyễn Văn Linh"
    assert "data[gender]" not in ui
    assert any("mã số doanh nghiệp" in w for w in warnings)
    assert any("trụ sở chủ phương tiện" in w for w in warnings)


def test_chu_moi_ca_nhan_dien_so_dinh_danh_tren_don():
    fields, _ = mapper.enrich(_facts(
        ChuPT_LoaiDoiTuong="Cá nhân", ChuPT_Ten="TRẦN VĂN BÌNH", ChuPT_MaDinhDanhToChuc=None,
        ChuPT_SoDinhDanh="049095001122", ChuPT_NgaySinh="2/9/1995",
        NguoiNop_HoTen=None, NguoiNop_SoDinhDanh=None, NguoiNop_GioiTinh=None, Don_NguoiKy="Trần Văn Bình",
    ), {})
    ui = _values(fields)

    assert ui["data[chonDoiTuong]"] == "Cá nhân"
    assert ui["data[fullname]"] == "Trần Văn Bình"
    assert ui["data[identityNumber]"] == "049095001122"
    assert ui["data[birthday]"] == "02/09/1995"
    assert ui["data[gender]"] == "Nam"
    assert ui["data[soDinhDanhCCCD]"] == "049095001122"
    assert ui["data[ngayThangNamSinh]"] == "02/09/1995"
    assert "data[organization]" not in ui and "data[maDinhDanhToChuc]" not in ui


def test_canh_bao_khi_ten_chu_moi_trung_chu_cu():
    _, warnings = mapper.enrich(_facts(ChuPT_Ten="Công ty TNHH MTV Biển Bạc"), {})
    assert any("trùng bên chuyển quyền" in w for w in warnings)


def test_moi_o_emit_deu_khai_trong_schema():
    fields, _ = mapper.enrich(_facts(), {})
    assert {f["name"] for f in fields} <= set(UI_COMP_BY_NAME)
    assert set(_FACTS) <= ALLOWED


# ---------------- đính kèm ----------------

# Một PDF 11 trang theo thứ tự của bộ hồ sơ giấy.
_PAGES = {
    1: "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐỀ NGHỊ ĐĂNG KÝ LẠI PHƯƠNG TIỆN THỦY NỘI ĐỊA",
    2: "GIẤY CHỨNG NHẬN ĐĂNG KÝ PHƯƠNG TIỆN THỦY NỘI ĐỊA\nĐã được đăng ký phương tiện có đặc điểm sau",
    3: "GIẤY CHỨNG NHẬN AN TOÀN KỸ THUẬT VÀ BẢO VỆ MÔI TRƯỜNG PHƯƠNG TIỆN THỦY NỘI ĐỊA",
    4: "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐỀ NGHỊ XÓA ĐĂNG KÝ PHƯƠNG TIỆN THỦY NỘI ĐỊA",
    5: "GIẤY NỘP TIỀN VÀO NGÂN SÁCH NHÀ NƯỚC\nLệ phí trước bạ tàu thủy",
    6: "HÓA ĐƠN GIÁ TRỊ GIA TĂNG (VAT INVOICE)",
    7: "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nHỢP ĐỒNG MUA BÁN PHƯƠNG TIỆN THỦY NỘI ĐỊA",
    8: "Công dụng: chở khách. ĐIỀU 2 GIÁ MUA BÁN",
    9: "ĐIỀU 7 ĐIỀU KHOẢN CUỐI CÙNG",
    10: "LỜI CHỨNG CỦA CÔNG CHỨNG VIÊN",
    11: "CHỨNG THỰC BẢN SAO ĐÚNG VỚI BẢN CHÍNH",
}
_FILES = [{"name": "ho-so.pdf", "type": "application/pdf"}]
_META = {0: {"pageCount": 11, "pageBoundariesAvailable": True}}


def _seg(page_from, page_to, doc_type):
    return {"fileIndex": 0, "pageFrom": page_from, "pageTo": page_to, "type": doc_type, "documentName": ""}


def _plan(segments):
    return planner.build_plan_items(_FILES, segments, _META, {0: _PAGES})


def test_pdf_gop_tach_theo_anh_anh_xa():
    segments = [
        _seg(1, 1, "don_dang_ky_lai"), _seg(2, 2, "gcn_dang_ky"), _seg(3, 3, "gcn_an_toan_ky_thuat"),
        _seg(4, 4, "don_xoa_dang_ky"), _seg(5, 5, "bien_lai_le_phi"), _seg(6, 6, "hoa_don"),
        _seg(7, 11, "hop_dong"),
    ]
    attachments, _, warnings = _plan(segments)
    rows = {a["componentIndex"]: a for a in attachments}

    assert sorted(rows) == [1, 2, 3, 4]
    assert rows[1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [4]}]
    assert rows[2]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2]}]
    # Dòng 3: Hợp đồng (tr.7-11) → Hóa đơn (tr.6) → GCN đăng ký cũ (tr.2).
    assert rows[3]["sourceSegments"] == [
        {"fileIndex": 0, "pageIndexes": [6, 7, 8, 9, 10]},
        {"fileIndex": 0, "pageIndexes": [5]},
        {"fileIndex": 0, "pageIndexes": [1]},
    ]
    assert rows[3]["loaiBan"] == "Bản sao"
    # Dòng 4: Đơn 07 (tr.1) → Đơn xóa 10 (tr.4).
    assert rows[4]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}, {"fileIndex": 0, "pageIndexes": [3]}]
    assert rows[4]["loaiBan"] == "Bản chính"
    assert all("untickRows" not in a for a in attachments)
    assert warnings == []


def test_trang_noi_tiep_hop_dong_va_rule_khi_llm_tra_other():
    segments = [_seg(p, p, "other") for p in range(1, 12)]
    attachments, _, _ = _plan(segments)
    rows = {a["componentIndex"]: a for a in attachments}

    assert rows[3]["includedTypes"] == ["hop_dong", "hoa_don", "gcn_dang_ky"]
    assert rows[3]["sourceSegments"][0] == {"fileIndex": 0, "pageIndexes": [6, 7, 8, 9, 10]}
    assert rows[4]["includedTypes"] == ["don_dang_ky_lai", "don_xoa_dang_ky"]


def test_thieu_bien_lai_va_gcn_an_toan_thi_bo_tick_dong_1_2():
    segments = [_seg(1, 1, "don_dang_ky_lai"), _seg(2, 6, "cccd"), _seg(7, 11, "hop_dong")]
    attachments, classified, warnings = _plan(segments)

    assert [a["componentIndex"] for a in attachments] == [3, 4]
    assert attachments[0]["untickRows"] == [planner._ROWS[1]["componentName"], planner._ROWS[2]["componentName"]]
    assert any(c.get("target") == "skip" and c["type"] == "cccd" for c in classified)
    assert any("dòng 1" in w for w in warnings) and any("dòng 2" in w for w in warnings)
    assert any("Giấy chứng nhận đăng ký phương tiện cũ" in w for w in warnings)


def test_validated_segments_giu_loai_cua_thu_tuc():
    errors: list[str] = []
    raw = [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_dang_ky_lai"},
        {"fileIndex": 0, "pageFrom": 2, "pageTo": 6, "type": "hoa_don"},
        {"fileIndex": 0, "pageFrom": 7, "pageTo": 11, "type": "hop_dong"},
    ]
    segments = planner._validated_segments(raw, _FILES, _META, errors)
    assert [s["type"] for s in segments] == ["don_dang_ky_lai", "hoa_don", "hop_dong"]
    assert errors == []
