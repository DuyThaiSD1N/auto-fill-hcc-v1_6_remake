"""Unit test pipeline "Thủ tục báo cáo tổ chức đại hội thành lập, đại hội nhiệm kỳ, đại hội bất thường của hội (cấp
tỉnh)" — mã 1.012942.

Mapper: chủ hồ sơ = nhân sự dự kiến Chủ tịch (Phiếu LLTP / SYLL); nhân thân người nộp chỉ từ CCCD khớp tài khoản,
không có thẻ thì giới tính suy từ số định danh tài khoản; ghi chú = tên đại hội; datagrid mỗi giấy tờ một dòng.
Planner: 18 dòng, chọn dòng theo loại đại hội; Điều lệ vắt qua 2 file ghép một file; không có văn bản dự kiến riêng
thì dòng 6 đính chung văn bản báo cáo. Dữ liệu đều là ví dụ bịa.
"""

from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.attach import planner as P
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.process import mapper
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.process.runner import trim_bulky_pages
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "bao-cao-to-chuc-dai-hoi-hoi-cap-tinh"
NOP_ID = "031085004321"
CTX = {"formContext": {"applicantFullname": "Lê Minh Khoa", "applicantIdentityNumber": NOP_ID}}
HOI = "Hội Cờ tướng tỉnh Bình An"


def _fields(**values):
    return [{"name": k, "value": v} for k, v in values.items()]


def _base(**extra):
    base = dict(
        TenHoi=HOI,
        LoaiDaiHoi="nhiệm kỳ",
        NhiemKy="2026 – 2031",
        TenDaiHoi="Đại hội đại biểu lần thứ V",
        DanhMucHoSo=["Công văn báo cáo tổ chức Đại hội – Số: 12/CV-HCT, ngày 20 tháng 9 năm 2026",
                     "CCCD của ông Lê Minh Khoa", "Đề án nhân sự Đại hội", "Phiếu lý lịch tư pháp số 1"],
        ChuHoSo_HoTen="Phạm Thị An",
        ChuHoSo_NgaySinh="05 tháng 06 năm 1965",
        ChuHoSo_SoDinhDanh="031165009999",
        ChuHoSo_NgayCap="01/07/2024",
        ChuHoSo_NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        ChuHoSo_DiaChi={"quocGia": "Việt Nam", "tinh": "Tỉnh Bình An", "xa": "Phường Minh An",
                        "diaChi": "93 đường Lê Lợi, tổ 5"},
        ChuHoSo_DienThoai="0912.345.678",
        NguoiNop_HoTen="LÊ MINH KHOA",
        NguoiNop_SoDinhDanh=NOP_ID,
        NguoiNop_GioiTinh="Nam",
        NguoiNop_NgayCap="12/12/2022",
        NguoiNop_NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        NguoiNop_DiaChi={"quocGia": "Việt Nam", "tinh": "Tỉnh Bình An", "xa": "Phường Minh An",
                         "diaChi": "Số 7 ngõ 12"},
        NguoiNop_DienThoai="0987654321",
    )
    base.update(extra)
    return base


def _by(out):
    return {f["name"]: f["value"] for f in out}


def test_registry_khop_key_ke_khai_links():
    assert registry.get_procedure(KEY)
    assert registry.get_pipeline(KEY)
    assert registry.get_attach_pipeline(KEY)
    assert any(link["key"] == KEY and link["code"] == "1.012942" for link in KE_KHAI_LINKS)


def test_dien_chu_ho_so_nguoi_nop_ghi_chu_va_danh_muc():
    out, warnings = mapper.enrich(_fields(**_base()), CTX)
    v = _by(out)
    # Chủ hồ sơ = Chủ tịch dự kiến, khác người nộp → bỏ tích; giới tính suy từ số CCCD (chữ số thứ 4 lẻ = Nữ).
    assert v["data[isOwnerDossierCheck]"] is False
    assert v["data[ownerFullname]"] == "Phạm Thị An"
    assert v["data[ownerBirthday]"] == "05/06/1965"
    assert v["data[ownerGender]"] == "Nữ"
    assert v["data[ownerIdentityNumber]"] == "031165009999"
    assert v["data[ownerProvince]"] == "Tỉnh Bình An"
    assert v["data[ownerDistrict]"] == "Phường Minh An"
    assert v["data[ownerAddress]"] == "93 đường Lê Lợi, tổ 5"
    assert v["data[ownerPhoneNumber]"] == "0912345678"
    assert v["data[ownerNation]"] == "Việt Nam"
    assert v["data[ghiChu]"] == f"Báo cáo tổ chức Đại hội {HOI} nhiệm kỳ 2026-2031 (Đại hội đại biểu lần thứ V)"
    # Người nộp: CCCD khớp tài khoản; ô khoá không phát.
    assert v["data[gender]"] == "Nam"
    assert v["data[identityDate]"] == "12/12/2022"
    assert v["data[address]"] == "Số 7 ngõ 12"
    assert v["data[phoneNumber]"] == "0987654321"
    assert not {"data[fullname]", "data[birthday]", "data[identityNumber]", "data[chonDoiTuong]"} & set(v)
    # Datagrid: bỏ CCCD, Loại bản "Bản chính".
    assert v["data[hoSoDinhKem][0][textField1]"].startswith("Công văn báo cáo tổ chức Đại hội")
    assert v["data[hoSoDinhKem][2][textField1]"] == "Phiếu lý lịch tư pháp số 1"
    assert v["data[hoSoDinhKem][2][textField2]"] == "Bản chính"
    assert "data[hoSoDinhKem][3][textField1]" not in v
    assert not warnings


def test_khong_co_cccd_nguoi_nop_gioi_tinh_theo_so_dinh_danh_tai_khoan():
    base = _base()
    for k in [k for k in base if k.startswith("NguoiNop_")]:
        base.pop(k)
    out, warnings = mapper.enrich(_fields(**base), CTX)
    v = _by(out)
    assert v["data[gender]"] == "Nam"  # 031085... chữ số thứ 4 chẵn
    assert not {"data[identityDate]", "data[idIssuePlace]", "data[province]", "data[phoneNumber]"} & set(v)
    assert any("không có CCCD khớp người nộp" in w for w in warnings)
    assert any("SĐT Phần I" in w for w in warnings)


def test_chu_ho_so_tu_nop_thi_tich_va_dung_nhan_than_lltp():
    base = _base(ChuHoSo_HoTen="Lê Minh Khoa", ChuHoSo_SoDinhDanh=NOP_ID)
    for k in [k for k in base if k.startswith("NguoiNop_")]:
        base.pop(k)
    out, _ = mapper.enrich(_fields(**base), CTX)
    v = _by(out)
    assert v["data[isOwnerDossierCheck]"] is True
    assert v["data[identityDate]"] == "01/07/2024"
    assert v["data[address]"] == "93 đường Lê Lợi, tổ 5"
    assert v["data[phoneNumber]"] == "0912345678"


def test_ghi_chu_dai_hoi_bat_thuong():
    out, _ = mapper.enrich(_fields(**_base(LoaiDaiHoi="bất thường", NhiemKy=None, TenDaiHoi=None)), CTX)
    assert _by(out)["data[ghiChu]"] == f"Báo cáo tổ chức Đại hội bất thường của {HOI}"


def test_trim_bulky_pages_bo_du_thao_bao_cao_va_dieu_le():
    text = (
        "Trang 1/5\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM V/v tổ chức Đại hội Kính gửi: Sở Nội vụ. Căn cứ Điều lệ Hội\n"
        "Trang 2/5\nDỰ THẢO BÁO CÁO TỔNG KẾT CÔNG TÁC NHIỆM KỲ\n"
        "Trang 3/5\nbảng số liệu nối tiếp\n"
        "Trang 4/5\nSƠ YẾU LÝ LỊCH Họ và tên khai sinh\n"
        "Trang 5/5\nDỰ THẢO ĐIỀU LỆ HỘI Chương I\n"
    )
    kept = trim_bulky_pages([{"name": "a.pdf", "text": text}])[0]["text"]
    assert "Kính gửi" in kept and "SƠ YẾU LÝ LỊCH" in kept
    assert "TỔNG KẾT" not in kept and "bảng số liệu" not in kept and "ĐIỀU LỆ HỘI" not in kept


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


def test_planner_dai_hoi_nhiem_ky_theo_ho_so_mau():
    pages = {
        0: _pages(["CỘNG HÒA XÃ HỘI CHỦ NGHĨA V/v tổ chức Đại hội nhiệm kỳ Kính gửi Sở Nội vụ thời gian, địa điểm",
                   "Nơi nhận TM. BAN CHẤP HÀNH", "SƠ YẾU LÝ LỊCH", "PHIẾU LÝ LỊCH TƯ PHÁP SỐ 1",
                   "DỰ THẢO BÁO CÁO TỔNG KẾT", "DỰ THẢO NGHỊ QUYẾT ĐẠI HỘI ĐẠI BIỂU", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA "
                   "DỰ THẢO ĐIỀU LỆ HỘI Chương I Điều 1."]),
        1: _pages(["3. Nhiệm vụ của Đại hội", "Điều 20", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA ĐỀ ÁN NHÂN SỰ",
                   "V/v cử cán bộ tham gia BCH", "DỰ THẢO BÁO CÁO KIỂM ĐIỂM", "BÁO CÁO hoạt động Ban kiểm tra",
                   "DỰ THẢO BÁO CÁO CHÍNH TRỊ", "DANH SÁCH DỰ KIẾN BAN CHẤP HÀNH"]),
    }
    segments = [
        _seg(0, 1, 2, "bao_cao_to_chuc_dai_hoi", "Công văn 12/CV báo cáo"), _seg(0, 3, 3, "so_yeu_ly_lich"),
        _seg(0, 4, 4, "ly_lich_tu_phap"), _seg(0, 5, 5, "bao_cao_tong_ket"),
        _seg(0, 6, 6, "du_thao_nghi_quyet_dai_hoi"), _seg(0, 7, 7, "du_thao_dieu_le"),
        # Trang đầu file 2 không có tiêu đề: LLM trả other → nối tiếp Điều lệ cuối file 1.
        _seg(1, 1, 2, "other"), _seg(1, 3, 3, "de_an_nhan_su"), _seg(1, 4, 4, "y_kien_dong_y"),
        _seg(1, 5, 5, "bao_cao_kiem_diem"), _seg(1, 6, 6, "bao_cao_ban_kiem_tra"),
        _seg(1, 7, 7, "bao_cao_tong_ket"), _seg(1, 8, 8, "danh_sach_bch"),
    ]
    attachments, _, warnings, case = _plan(segments, pages, [7, 8])
    assert case == "nhiem_ky"
    assert sorted(a["componentIndex"] for a in attachments) == [1, 3, 6, 11, 14, 15, 16, 17]
    assert all(a["loaiBan"] == "Bản chính" and a["target"] == "attp-row" for a in attachments)
    # Điều lệ: trang 7 file 1 + trang 1-2 file 2 → một file gộp.
    assert _row(attachments, 1)["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [6]},
                                                      {"fileIndex": 1, "pageIndexes": [0, 1]}]
    assert _row(attachments, 3)["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": [2]},
                                                      {"fileIndex": 1, "pageIndexes": [7]}]
    # Dòng 6 + 15 cùng văn bản báo cáo.
    assert _row(attachments, 6)["sourceSegments"] == _row(attachments, 15)["sourceSegments"] == [
        {"fileIndex": 0, "pageIndexes": [0, 1]}]
    assert "/" not in _row(attachments, 15)["documentName"]
    # Dòng 11: tổng kết (2 đoạn) → kiểm điểm BCH → Ban kiểm tra.
    assert _row(attachments, 11)["includedTypes"] == ["bao_cao_tong_ket", "bao_cao_tong_ket", "bao_cao_kiem_diem",
                                                      "bao_cao_ban_kiem_tra"]
    assert _row(attachments, 16)["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2]},
                                                       {"fileIndex": 0, "pageIndexes": [3]}]
    assert any("Nghị quyết của Ban chấp hành về việc tổ chức đại hội nhiệm kỳ (dòng 13)" in w for w in warnings)
    assert any("Báo cáo số lượng hội viên" in w for w in warnings)
    assert any("Báo cáo tài chính riêng" in w for w in warnings)
    assert any("dòng 6 đính chung" in w for w in warnings)
    assert not any("dòng 14" in w for w in warnings)


def test_planner_dai_hoi_bat_thuong_dung_dong_5_7_12():
    pages = {0: _pages(["V/v tổ chức Đại hội bất thường Kính gửi Sở Nội vụ", "NGHỊ QUYẾT QUYẾT NGHỊ Điều 1",
                        "CHƯƠNG TRÌNH ĐẠI HỘI", "ĐƠN ĐỀ NGHỊ ĐỔI TÊN HỘI"])}
    segments = [_seg(0, 1, 1, "bao_cao_to_chuc_dai_hoi"), _seg(0, 2, 2, "nghi_quyet_bch"),
                _seg(0, 3, 3, "du_kien_chuong_trinh"), _seg(0, 4, 4, "don_doi_ten")]
    attachments, _, warnings, case = _plan(segments, pages, [4])
    assert case == "bat_thuong"
    assert sorted(a["componentIndex"] for a in attachments) == [5, 7, 12]
    assert _row(attachments, 5)["includedTypes"] == ["bao_cao_to_chuc_dai_hoi", "don_doi_ten"]
    assert any("đại hội bất thường" in w for w in warnings)


def test_planner_dai_hoi_thanh_lap_gom_ly_lich_vao_dong_2():
    pages = {0: _pages(["BAN VẬN ĐỘNG THÀNH LẬP HỘI báo cáo tổ chức Đại hội thành lập", "ĐỀ ÁN NHÂN SỰ",
                        "SƠ YẾU LÝ LỊCH", "PHIẾU LÝ LỊCH TƯ PHÁP SỐ 1", "V/v cử cán bộ"])}
    segments = [_seg(0, 1, 1, "bao_cao_to_chuc_dai_hoi"), _seg(0, 2, 2, "de_an_nhan_su"),
                _seg(0, 3, 3, "so_yeu_ly_lich"), _seg(0, 4, 4, "ly_lich_tu_phap"), _seg(0, 5, 5, "y_kien_dong_y")]
    attachments, _, warnings, case = _plan(segments, pages, [5])
    assert case == "thanh_lap"
    assert sorted(a["componentIndex"] for a in attachments) == [2, 8, 10]
    assert _row(attachments, 2)["includedTypes"] == ["y_kien_dong_y", "so_yeu_ly_lich", "ly_lich_tu_phap"]
    assert any("(dòng 9)" in w for w in warnings)


def test_planner_rule_fallback_va_cccd_bo_qua():
    pages = {0: _pages(["NGHỊ QUYẾT Về việc tổ chức Đại hội nhiệm kỳ QUYẾT NGHỊ Điều 1", "Nơi nhận",
                        "SƠ YẾU LÝ LỊCH Họ và tên", "CĂN CƯỚC CÔNG DÂN"])}
    segments = [_seg(0, 1, 2, "other"), _seg(0, 3, 3, "other"), _seg(0, 4, 4, "cccd")]
    attachments, classified, _, case = _plan(segments, pages, [4])
    assert case == "nhiem_ky"
    assert {a["componentIndex"] for a in attachments} == {13, 16}
    assert classified[-1]["target"] == "skip"


def test_planner_trang_co_quoc_hieu_khong_noi_tiep():
    pages = {0: _pages(["SƠ YẾU LÝ LỊCH", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM giấy tờ lạ"])}
    attachments, classified, warnings, _ = _plan([_seg(0, 1, 1, "so_yeu_ly_lich"), _seg(0, 2, 2, "other")],
                                                 pages, [2])
    assert _row(attachments, 16)["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert any("Không xác định được loại giấy tờ" in w for w in warnings)
