"""Unit test pipeline "Thủ tục chia, tách; sáp nhập; hợp nhất hội (cấp tỉnh)" — mã 1.012945.

Mapper: "Chọn mẫu đơn" mở đúng fieldset và tên hội vào đúng cặp ô; hồ sơ ghi gộp "sáp nhập, hợp nhất" → mẫu hợp nhất;
mẫu tách gắn scope vì trùng field-key Phần I; chủ hồ sơ = chủ tịch dự kiến (Phiếu LLTP); nhân thân người nộp chỉ từ
CCCD khớp tài khoản. Planner: 7 dòng, thiếu văn bản trụ sở thì tạm đính trang Đề án về trụ sở, danh sách BCH thiếu
Ban kiểm tra thì đính thêm trang Đề án có bảng Ban kiểm tra. Dữ liệu đều là ví dụ bịa.
"""

from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach import planner as P
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process import mapper
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process.schema import TACH_SCOPE
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "chia-tach-sap-nhap-hop-nhat-hoi-cap-tinh"
NOP_ID = "031085004321"
CTX = {"formContext": {"applicantFullname": "Lê Minh Khoa", "applicantIdentityNumber": NOP_ID}}
HOI_A = "Hội Cờ tướng Thành phố Hải Phòng"
HOI_B = "Hội Cờ tướng tỉnh Bình An"


def _fields(**values):
    return [{"name": k, "value": v} for k, v in values.items()]


def _base(**extra):
    base = dict(
        LoaiThuTuc="hợp nhất",
        HoiThamGia=[HOI_A, HOI_B],
        HoiMoi=[f"{HOI_A} (mới)"],
        KinhGui_Tinh="Thành phố Hải Phòng",
        NghiDinhSo="126/2024/NĐ-CP",
        LyDo="Đoạn lý do thứ nhất.\n\nĐoạn   lý do thứ hai.",
        DanhMucHoSo=["Đơn đề nghị hợp nhất – Số: 01/ĐĐN, ngày 02 tháng 3 năm 2026", "CCCD của ông Lê Minh Khoa",
                     "Nghị quyết – Số: 02/NQ, ngày 03 tháng 3 năm 2026", "Dự thảo Điều lệ (dự thảo)"],
        TruSo_DiaChi={"quocGia": "Việt Nam", "tinh": "Thành phố Hải Phòng", "xa": "Phường Minh An",
                      "diaChi": "Nhà văn hóa Số 5, đường Lê Lợi"},
        NguoiKy_TMBCH="Lê Minh Khoa",
        NguoiLienHe_HoTen="Lê Minh Khoa",
        NguoiLienHe_DienThoai="0912 345 678",
        ChuHoSo_HoTen="PHẠM VĂN AN",
        ChuHoSo_NgaySinh="05/06/1970",
        ChuHoSo_GioiTinh="Nam",
        ChuHoSo_SoDinhDanh="031070009999",
        ChuHoSo_NgayCap="01/07/2024",
        ChuHoSo_NoiCap="Bộ Công An",
        ChuHoSo_DiaChi={"quocGia": "Việt Nam", "tinh": "Thành phố Hải Phòng", "xa": "Phường Minh An",
                        "diaChi": "Tổ dân phố 3"},
        NguoiNop_HoTen="LÊ MINH KHOA",
        NguoiNop_SoDinhDanh=NOP_ID,
        NguoiNop_GioiTinh="Nam",
        NguoiNop_NgayCap="12/12/2022",
        NguoiNop_NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        NguoiNop_DiaChi={"quocGia": "Việt Nam", "tinh": "Thành phố Hải Phòng", "xa": "Phường Minh An",
                         "diaChi": "Số 7 ngõ 12"},
    )
    base.update(extra)
    return base


def _by(out):
    return {(f["name"], bool(f.get("scope"))): f["value"] for f in out}


def test_registry_khop_key_ke_khai_links():
    assert registry.get_procedure(KEY)
    assert registry.get_pipeline(KEY)
    assert registry.get_attach_pipeline(KEY)
    assert any(link["key"] == KEY and link["code"] == "1.012945" for link in KE_KHAI_LINKS)


def test_hop_nhat_dien_dung_fieldset_va_chu_ho_so():
    out, warnings = mapper.enrich(_fields(**_base()), CTX)
    v = _by(out)
    names = [f["name"] for f in out]
    assert v[("data[ChonTruongHop]", False)] == "Đơn đề nghị hợp nhất hội"
    # Chọn mẫu đơn phát TRƯỚC các ô của fieldset.
    assert names.index("data[ChonTruongHop]") < names.index("data[HopNhatHoi]")
    assert v[("data[HopNhatHoi]", False)] == HOI_A
    assert v[("data[VaHoi7]", False)] == HOI_B
    assert v[("data[ThanhHoi9]", False)] == HOI_A  # bỏ chú thích "(mới)"
    assert v[("data[NghiDinhSo3]", False)] == "126/2024/NĐ-CP"
    assert v[("data[NgayNd3]", False)] == "08/10/2024"  # Nghị định 126 thiếu ngày → ngày ban hành
    assert v[("data[LyDoHopNhat]", False)] == "Đoạn lý do thứ nhất.\nĐoạn lý do thứ hai."
    assert v[("data[HoSoHopNhat]", False)].startswith("1) Đơn đề nghị hợp nhất")
    assert "CCCD" not in v[("data[HoSoHopNhat]", False)]
    assert v[("data[hoSoDinhKem][2][textField1]", False)] == "Dự thảo Điều lệ (dự thảo)"
    assert v[("data[hoSoDinhKem][2][textField2]", False)] == "Bản chính"
    assert ("data[hoSoDinhKem][3][textField1]", False) not in v
    assert v[("data[fullname3]", False)] == "Lê Minh Khoa"
    assert v[("data[phoneNumber3]", False)] == "0912345678"
    assert v[("data[province3]", False)] == "Thành phố Hải Phòng"
    assert v[("data[district3]", False)] == "Phường Minh An"
    assert v[("data[address3]", False)] == "Nhà văn hóa Số 5, đường Lê Lợi"
    assert v[("data[TM.BCH4]", False)] == "Lê Minh Khoa"
    assert v[("data[TM.BCH5]", False)] == "Lê Minh Khoa"
    assert v[("data[noiGui]", False)] == "Thành phố Hải Phòng"
    # Chủ hồ sơ = chủ tịch dự kiến, khác người nộp → bỏ tích.
    assert v[("data[isOwnerDossierCheck]", False)] is False
    assert v[("data[ownerFullname]", False)] == "PHẠM VĂN AN"
    assert v[("data[ownerIdentityNumber]", False)] == "031070009999"
    assert v[("data[ownerNation]", False)] == "Việt Nam"
    # Người nộp: CCCD khớp tài khoản; ô khoá không phát.
    assert v[("data[gender]", False)] == "Nam"
    assert v[("data[identityDate]", False)] == "12/12/2022"
    assert v[("data[address]", False)] == "Số 7 ngõ 12"
    assert v[("data[phoneNumber]", False)] == "0912345678"
    assert not {"data[fullname]", "data[birthday]", "data[identityNumber]", "data[chonDoiTuong]"} & set(names)
    assert not any("không ghi rõ" in w for w in warnings)


def test_ghi_gop_sap_nhap_hop_nhat_chon_mau_hop_nhat_va_canh_bao():
    out, warnings = mapper.enrich(_fields(**_base(LoaiThuTuc="sáp nhập, hợp nhất")), CTX)
    assert _by(out)[("data[ChonTruongHop]", False)] == "Đơn đề nghị hợp nhất hội"
    assert any("không ghi rõ" in w for w in warnings)


def test_sap_nhap_hoi_nhan_la_hoi_tiep_tuc_ton_tai():
    out, _ = mapper.enrich(_fields(**_base(LoaiThuTuc="sáp nhập", HoiMoi=[HOI_A],
                                           NguoiKy_HoiKhac="Trần Thị Bích")), CTX)
    v = _by(out)
    assert v[("data[ChonTruongHop]", False)] == "Đơn đề nghị sáp nhập hội"
    assert v[("data[SapNhapHoi]", False)] == HOI_B
    assert v[("data[VaoHoi4]", False)] == HOI_A
    assert v[("data[TM.BCH2]", False)] == "Trần Thị Bích"
    assert v[("data[TM.BCH3]", False)] == "Lê Minh Khoa"
    assert v[("data[NghiDinhSo2]", False)] == "126/2024/NĐ-CP"
    assert ("data[HopNhatHoi]", False) not in v


def test_tach_gan_scope_cho_o_trung_phan_i():
    out, _ = mapper.enrich(_fields(**_base(LoaiThuTuc="tách", HoiThamGia=[HOI_A],
                                           HoiMoi=[HOI_A, "Hội Cờ tướng trẻ Hải Phòng"])), CTX)
    v = _by(out)
    assert v[("data[TachHoi]", False)] == HOI_A
    assert v[("data[VaHoi2]", False)] == "Hội Cờ tướng trẻ Hải Phòng"
    # Cùng key data[address]: Phần I (không scope) = địa chỉ người nộp, fieldset tách (scope) = trụ sở.
    assert v[("data[address]", False)] == "Số 7 ngõ 12"
    assert v[("data[address]", True)] == "Nhà văn hóa Số 5, đường Lê Lợi"
    assert v[("data[fullname]", True)] == "Lê Minh Khoa"
    scoped = [f for f in out if f.get("scope")]
    assert scoped and all(f["scope"] == TACH_SCOPE and f["scopeAway"] for f in scoped)
    assert ("data[fullname]", False) not in v


def test_cccd_khong_khop_tai_khoan_khong_dien_phan_i():
    out, warnings = mapper.enrich(_fields(**_base(NguoiNop_SoDinhDanh="031085000000")), CTX)
    names = {f["name"] for f in out if not f.get("scope")}
    assert not {"data[gender]", "data[identityDate]", "data[idIssuePlace]", "data[province]"} & names
    assert any("không có CCCD khớp người nộp" in w for w in warnings)


def test_chu_ho_so_chinh_la_nguoi_nop_thi_tich():
    out, _ = mapper.enrich(_fields(**_base(ChuHoSo_HoTen="LÊ MINH KHOA", ChuHoSo_SoDinhDanh=NOP_ID)), CTX)
    assert _by(out)[("data[isOwnerDossierCheck]", False)] is True


# ---------------- Planner ----------------
def _pages(texts: list[str]) -> dict[int, str]:
    return {i: t for i, t in enumerate(texts, start=1)}


def _seg(file_index, page_from, page_to, doc_type, name=""):
    return {"fileIndex": file_index, "pageFrom": page_from, "pageTo": page_to, "type": doc_type,
            "documentName": name}


def _plan(segments, pages_by_file, page_counts):
    raw_files = [{"name": f"file{i}.pdf"} for i in range(len(page_counts))]
    meta = {i: {"pageCount": n, "pageBoundariesAvailable": True} for i, n in enumerate(page_counts)}
    return P.build_plan_items(raw_files, segments, meta, pages_by_file)


def _row(attachments, idx):
    return next(a for a in attachments if a["componentIndex"] == idx)


def test_planner_bay_dong_dinh_kem_chung_trang_de_an():
    pages = {
        0: _pages(["ĐƠN XIN HỢP NHẤT HỘI Kính gửi", "BIÊN BẢN HỌP Thành phần tham dự",
                   "NGHỊ QUYẾT QUYẾT NGHỊ Điều 1", "Nơi nhận", "DANH SÁCH BAN CHẤP HÀNH TT HỌ VÀ TÊN"]),
        1: _pages(["ĐỀ ÁN HỢP NHẤT Căn cứ", "Tên gọi ... Địa chỉ đặt trụ sở Văn phòng",
                   "Ban chấp hành ... Ban kiểm tra TT HỌ VÀ TÊN CHỨC DANH Trưởng ban", "Về trụ sở làm việc"]),
        2: _pages(["ĐIỀU LỆ Chương I", "Điều 2"]),
        3: _pages(["PHIẾU LÝ LỊCH TƯ PHÁP SỐ 1 Tình trạng án tích"]),
    }
    segments = [
        _seg(0, 1, 1, "don_de_nghi"), _seg(0, 2, 2, "bien_ban_hop"), _seg(0, 3, 4, "nghi_quyet"),
        _seg(0, 5, 5, "danh_sach_bch"), _seg(1, 1, 4, "de_an"), _seg(2, 1, 2, "du_thao_dieu_le"),
        _seg(3, 1, 1, "ly_lich_tu_phap"),
    ]
    attachments, _, warnings = _plan(segments, pages, [5, 4, 2, 1])
    assert sorted(a["componentIndex"] for a in attachments) == [1, 2, 3, 4, 5, 6, 7]
    assert all(a["loaiBan"] == "Bản chính" and a["target"] == "attp-row" for a in attachments)
    # Dòng 1: thiếu văn bản trụ sở → tạm trang 2 và 4 của Đề án.
    assert _row(attachments, 1)["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": [1, 3]}]
    assert _row(attachments, 3)["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": None}]
    # Dòng 4: Nghị quyết trước, Biên bản họp sau.
    assert _row(attachments, 4)["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2, 3]},
                                                      {"fileIndex": 0, "pageIndexes": [1]}]
    # Dòng 5: danh sách BCH riêng không có Ban kiểm tra → thêm trang 3 Đề án.
    assert _row(attachments, 5)["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [4]},
                                                      {"fileIndex": 1, "pageIndexes": [2]}]
    assert _row(attachments, 6)["sourceSegments"] == [{"fileIndex": 3, "pageIndexes": None}]
    assert any("TẠM đính" in w for w in warnings)
    assert any("Sơ yếu lý lịch" in w for w in warnings)
    assert any("đã đính kèm trang Đề án có danh sách Ban kiểm tra" in w for w in warnings)


def test_planner_co_van_ban_tru_so_khong_dinh_trang_de_an():
    pages = {
        0: _pages(["GIẤY XÁC NHẬN cho mượn địa điểm làm trụ sở"]),
        1: _pages(["ĐỀ ÁN Địa chỉ đặt trụ sở"]),
    }
    attachments, _, warnings = _plan([_seg(0, 1, 1, "van_ban_tru_so"), _seg(1, 1, 1, "de_an")], pages, [1, 1])
    assert _row(attachments, 1)["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": None}]
    assert not any("TẠM đính" in w for w in warnings)


def test_planner_rule_fallback_khi_llm_tra_other():
    pages = {0: _pages(["NGHỊ QUYẾT Về việc hợp nhất QUYẾT NGHỊ Điều 1", "Nơi nhận",
                        "SƠ YẾU LÝ LỊCH Họ và tên"])}
    segments = [_seg(0, 1, 2, "other"), _seg(0, 3, 3, "other")]
    attachments, classified, _ = _plan(segments, pages, [3])
    assert {a["componentIndex"] for a in attachments} == {4, 6}
    assert _row(attachments, 4)["includedTypes"] == ["nghi_quyet"]


def test_planner_cccd_bo_qua():
    pages = {0: _pages(["CĂN CƯỚC CÔNG DÂN"])}
    attachments, classified, _ = _plan([_seg(0, 1, 1, "cccd")], pages, [1])
    assert attachments == []
    assert classified[0]["target"] == "skip"


def test_split_ocr_pages_giu_van_ban_du():
    text = "Trang 1/2\n" + "a" * 1500 + " trụ sở\nTrang 2/2\nb"
    pages, boundaries = P._split_ocr_pages(text, 2)
    assert boundaries and set(pages) == {1, 2}
    assert pages[1].endswith("trụ sở")
