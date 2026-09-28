"""Unit test pipeline "Cấp mới chứng chỉ hành nghề môi giới bất động sản" — mã 1.012906.

Mapper: Đơn đăng ký dự thi = người đề nghị (data[birthday] trùng key Phần I → gắn scope); Phần I chỉ điền khi người
đề nghị chính là tài khoản hoặc từ CCCD khớp tài khoản; panel doanh nghiệp chỉ khi có giấy tờ của tổ chức; nơi sinh
= tỉnh/TP hiện hành lấy từ quê quán trên CCCD; đơn xin cấp lại → cảnh báo lệch thủ tục.
Planner: 6 dòng; một PDF Đơn + CCCD tách về dòng 3 / dòng 2; không có ảnh rời thì dòng 6 đính chung trang đơn; không
có chứng chỉ nước ngoài thì bỏ tick dòng 4. Dữ liệu đều là ví dụ bịa.
"""

from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach import planner as P
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.process import mapper
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.process.schema import DON_SCOPE
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "cap-moi-chung-chi-hanh-nghe-moi-gioi-bat-dong-san"
DE_NGHI_ID = "045090001234"
NOP_ID = "031185004321"
CTX_TU_NOP = {"formContext": {"applicantFullname": "Trần Văn Bình", "applicantIdentityNumber": DE_NGHI_ID}}
CTX_NOP_THAY = {"formContext": {"applicantFullname": "Lê Thị Hoa", "applicantIdentityNumber": NOP_ID}}
CUC_CS = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def _fields(**values):
    return [{"name": k, "value": v} for k, v in values.items()]


def _base(**extra):
    base = dict(
        NguoiDeNghi_HoTen="TRẦN VĂN BÌNH",
        NguoiDeNghi_NgaySinh="15 Tháng 03 Năm 1990",
        NguoiDeNghi_GioiTinh="Nam",
        NguoiDeNghi_QuocTich="Việt Nam",
        NguoiDeNghi_LoaiGiayTo="CCCD",
        NguoiDeNghi_SoGiayTo="0450 9000 1234",
        NguoiDeNghi_NgayCap="10/05/2021",
        NguoiDeNghi_NoiCap="CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
        NguoiDeNghi_DiaChiThuongTru="Tổ 3 An Hòa, Cẩm Lệ, Đà Nẵng",
        NguoiDeNghi_ThuongTru={"quocGia": "Việt Nam", "tinh": "TP Đà nẵng", "xa": "Phường Cẩm Lệ",
                               "diaChi": "Tổ 3 An Hòa"},
        NguoiDeNghi_DienThoai="0905.123.456",
        NguoiDeNghi_DonViCongTac="Công ty TNHH Nhà Đất An Phú",
        Don_Loai="dang_ky_du_thi",
        Don_KinhGui="Sở Xây dựng thành phố Đà Nẵng",
        Don_DiaDanh="Đà nẵng",
        Don_NguoiLamDon="TRẦN VĂN BÌNH",
        Don_CamKet="Có",
    )
    base.update(extra)
    return base


def _by(out):
    return {f["name"]: f["value"] for f in out}


def test_registry_khop_key_ke_khai_links():
    assert registry.get_procedure(KEY)
    assert registry.get_pipeline(KEY)
    assert registry.get_attach_pipeline(KEY)
    assert any(link["key"] == KEY and link["code"] == "1.012906" for link in KE_KHAI_LINKS)


def test_tu_nop_dien_phan_i_va_don():
    out, warnings = mapper.enrich(_fields(**_base()), CTX_TU_NOP)
    v = _by(out)
    # Phần I: cổng đổ họ tên / ngày sinh / số định danh → không phát; phần còn lại theo người đề nghị.
    for locked in ("data[fullname]", "data[identityNumber]", "data[chonDoiTuong]"):
        assert locked not in v
    assert v["data[gender]"] == "Nam"
    assert v["data[identityDate]"] == "10/05/2021"
    assert v["data[identityAgency]"] == CUC_CS
    assert v["data[phoneNumber]"] == "0905123456"
    assert v["data[nation]"] == "Việt Nam"
    assert v["data[province]"] == "Thành phố Đà Nẵng"
    assert v["data[district]"] == "Phường Cẩm Lệ"
    assert v["data[address]"] == "Tổ 3 An Hòa"
    # Đơn đăng ký dự thi.
    assert v["data[TinTTTe1]"] == "Thành phố Đà Nẵng"
    assert v["data[recipient]"] == "Sở Xây dựng thành phố Đà Nẵng"
    assert v["data[fullName]"] == "TRẦN VĂN BÌNH"
    assert v["data[birthday]"] == "15/03/1990"
    assert v["data[nationality]"] == "Việt Nam"
    assert v["data[idType]"] == "CCCD (Căn cước công dân)"
    assert v["data[idNumber]"] == DE_NGHI_ID
    assert v["data[CapNGay]"] == "10/05/2021"
    assert v["data[idIssuePlace]"] == CUC_CS
    assert v["data[permanentAddress]"] == "Tổ 3 An Hòa, Cẩm Lệ, Đà Nẵng"
    assert v["data[contactPhone]"] == "0905123456"
    assert v["data[commitment]"] is True
    assert v["data[KyGhiRoHoTen]"] == "TRẦN VĂN BÌNH"
    # Ngày sinh của đơn trùng key Phần I → chỉ được điền trong panel đơn.
    birthday = next(f for f in out if f["name"] == "data[birthday]")
    assert birthday["scope"] == DON_SCOPE
    assert birthday["scopeNear"] == "data[provincenoisinh]"
    assert "data[chonDoiTuong]" in birthday["scopeAway"]
    assert all("scope" not in f for f in out if f["name"] != "data[birthday]")
    # Thiếu nơi sinh (bắt buộc) + văn bằng → cảnh báo; không lấy đơn vị công tác làm doanh nghiệp.
    assert "data[provincenoisinh]" not in v
    assert "data[organization]" not in v
    assert any("Nơi sinh" in w for w in warnings)
    assert any("văn bằng" in w for w in warnings)
    assert not any("CẤP LẠI" in w for w in warnings)


def test_noi_sinh_van_bang_va_loai_giay_to():
    out, _ = mapper.enrich(_fields(**_base(
        NguoiDeNghi_NoiSinh="Xã Hòa Tiến, huyện Hòa Vang, Đà Nẵng",
        NguoiDeNghi_VanBang=["1. Bằng tốt nghiệp THPT – Trường THPT Lê Lợi, 2008", "Căn cước công dân",
                             "Giấy chứng nhận hoàn thành khóa học môi giới BĐS – 2026"],
        NguoiDeNghi_LoaiGiayTo="Thẻ căn cước",
    )), CTX_TU_NOP)
    v = _by(out)
    assert v["data[provincenoisinh]"] == "Thành phố Đà Nẵng"
    # Quê quán ghi tỉnh CŨ trước sáp nhập → tỉnh hiện hành trong danh mục 34 tỉnh.
    assert mapper._noi_sinh_province("Tân Phú, Phú Ninh, Quảng Nam") == "Thành phố Đà Nẵng"
    assert mapper._noi_sinh_province("Xã Thanh Hải, huyện Thanh Hà, tỉnh Hải Dương") == "Thành phố Hải Phòng"
    assert mapper._noi_sinh_province("Sơn Tây, Hà Tây") == "Thành phố Hà Nội"
    assert mapper._noi_sinh_province("Nghi Hoa, Nghi Lộc, Nghệ An") == "Tỉnh Nghệ An"
    assert v["data[educationCertificates]"] == ("Bằng tốt nghiệp THPT – Trường THPT Lê Lợi, 2008\n"
                                               "Giấy chứng nhận hoàn thành khóa học môi giới BĐS – 2026")
    assert v["data[idType]"] == "Thẻ căn cước"
    assert mapper._id_type("Thẻ Căn cước công dân", None) == "CCCD (Căn cước công dân)"
    assert mapper._id_type("", "123456789") == "CMND (Chứng minh nhân dân)"
    assert mapper._id_type("Hộ chiếu", "C1234567") == "Hộ chiếu"


def test_nop_thay_khong_co_cccd_nguoi_nop_khong_dien_phan_i():
    out, warnings = mapper.enrich(_fields(**_base()), CTX_NOP_THAY)
    v = _by(out)
    # Không lấy nhân thân người đề nghị cho Phần I; giới tính suy từ số định danh tài khoản (chữ số thứ 4 lẻ = Nữ).
    assert v["data[gender]"] == "Nữ"
    for key in ("data[identityDate]", "data[identityAgency]", "data[phoneNumber]", "data[province]",
                "data[address]"):
        assert key not in v
    # Đơn vẫn là người đề nghị.
    assert v["data[fullName]"] == "TRẦN VĂN BÌNH"
    assert v["data[contactPhone]"] == "0905123456"
    assert any("khác người đề nghị" in w for w in warnings)
    assert any("Số điện thoại Phần I" in w for w in warnings)


def test_nop_thay_co_cccd_nguoi_nop():
    out, _ = mapper.enrich(_fields(**_base(
        NguoiNop_HoTen="LÊ THỊ HOA", NguoiNop_SoDinhDanh=NOP_ID, NguoiNop_GioiTinh="Nữ",
        NguoiNop_NgayCap="02/02/2023", NguoiNop_NoiCap="Bộ Công an",
        NguoiNop_DiaChi={"quocGia": "Việt Nam", "tinh": "Tỉnh Bình An", "xa": "Phường Minh An",
                         "diaChi": "Số 7 ngõ 12"},
        NguoiNop_DienThoai="0987654321",
    )), CTX_NOP_THAY)
    v = _by(out)
    assert v["data[gender]"] == "Nữ"
    assert v["data[identityDate]"] == "02/02/2023"
    assert v["data[identityAgency]"] == "Bộ Công an"
    assert v["data[province]"] == "Tỉnh Bình An"
    assert v["data[address]"] == "Số 7 ngõ 12"
    assert v["data[phoneNumber]"] == "0987654321"


def test_to_chuc_chon_doi_tuong_va_dien_doanh_nghiep():
    out, warnings = mapper.enrich(_fields(**_base(
        ToChuc_Ten="Công ty Cổ phần Bất động sản Sông Hàn",
        ToChuc_MaSoThue="0401234567",
        ToChuc_DienThoai="02363 888 999",
        ToChuc_DiaChi={"quocGia": "Việt Nam", "tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu",
                       "diaChi": "12 Bạch Đằng"},
    )), CTX_TU_NOP)
    v = _by(out)
    assert out[0]["name"] == "data[chonDoiTuong]" and out[0]["value"] == "Tổ chức"
    assert v["data[organization]"] == "Công ty Cổ phần Bất động sản Sông Hàn"
    assert v["data[taxCode]"] == "0401234567"
    assert v["data[organizationPhoneNumber]"] == "02363888999"
    assert v["data[nation1]"] == "Việt Nam"
    assert v["data[province1]"] == "Thành phố Đà Nẵng"
    assert v["data[district1]"] == "Phường Hải Châu"
    assert v["data[address1]"] == "12 Bạch Đằng"
    assert any("Tổ chức" in w for w in warnings)


def test_don_cap_lai_canh_bao_va_khong_co_tai_khoan():
    out, warnings = mapper.enrich(_fields(**_base(Don_Loai="cap_lai", Don_DiaDanh=None)), {})
    v = _by(out)
    # Không có địa danh → lấy tỉnh trong "Kính gửi".
    assert v["data[TinTTTe1]"] == "Thành phố Đà Nẵng"
    assert "data[gender]" not in v and "data[identityDate]" not in v
    assert any("ĐƠN XIN CẤP LẠI" in w for w in warnings)
    assert any("tài khoản đang đăng nhập" in w for w in warnings)


# ---------------- Planner ----------------

def _pages(texts):
    return {i + 1: t for i, t in enumerate(texts)}


def _seg(file_index, page_from, page_to, doc_type, name=""):
    return {"fileIndex": file_index, "pageFrom": page_from, "pageTo": page_to, "type": doc_type,
            "documentName": name}


def _plan(segments, pages_by_file, page_counts, types=None):
    raw_files = [{"name": f"hoso{i + 1}.pdf", "type": (types or {}).get(i, "application/pdf")}
                 for i in range(len(page_counts))]
    meta = {i: {"pageCount": n, "pageBoundariesAvailable": True} for i, n in enumerate(page_counts)}
    return P.build_plan_items(raw_files, segments, meta, pages_by_file)


def _row(attachments, idx):
    return next(a for a in attachments if a["componentIndex"] == idx)


def test_planner_mot_pdf_don_cap_lai_va_cccd():
    pages = {0: _pages(["ĐƠN XIN CẤP LẠI CHỨNG CHỈ HÀNH NGHỀ MÔI GIỚI BẤT ĐỘNG SẢN Kính gửi Sở Xây dựng",
                        "CĂN CƯỚC CÔNG DÂN IDVNM0000000000"])}
    attachments, classified, warnings = _plan([_seg(0, 1, 1, "don_dang_ky", "Đơn xin cấp lại CCHN"),
                                               _seg(0, 2, 2, "cccd")], pages, [2])
    assert sorted(a["componentIndex"] for a in attachments) == [2, 3, 6]
    assert _row(attachments, 3)["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert _row(attachments, 2)["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1]}]
    # Ảnh 4x6 dán trên đơn → dòng 6 đính chung trang đơn.
    assert _row(attachments, 6)["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert _row(attachments, 6)["documentName"] == "Ảnh 4x6 dán trên đơn"
    assert _row(attachments, 2)["loaiBan"] == "Bản sao"
    assert _row(attachments, 3)["loaiBan"] == _row(attachments, 6)["loaiBan"] == "Bản chính"
    assert all(a["target"] == "attp-row" for a in attachments)
    # Không có chứng chỉ nước ngoài → bỏ tick dòng 4.
    assert attachments[0]["untickRows"] == [P._ROWS[4]["componentName"]]
    assert any(c.get("shared") and c["componentIndex"] == 6 for c in classified)
    assert any("(dòng 1)" in w for w in warnings)
    assert any("(dòng 5)" in w for w in warnings)
    assert any("ĐƠN XIN CẤP LẠI" in w for w in warnings)
    assert any("phong bì" in w for w in warnings)
    assert any("chứng thực" in w for w in warnings)


def test_planner_du_bo_anh_roi_va_rule_fallback():
    pages = {
        0: _pages(["ĐƠN ĐĂNG KÝ DỰ THI SÁT HẠCH CẤP CHỨNG CHỈ HÀNH NGHỀ MÔI GIỚI BẤT ĐỘNG SẢN Số CCCD", "Người làm đơn"]),
        1: _pages(["CĂN CƯỚC CÔNG DÂN chứng thực bản sao đúng với bản chính", "IDVNM mặt sau"]),
        2: _pages(["BẰNG TỐT NGHIỆP TRUNG HỌC PHỔ THÔNG"]),
        3: _pages(["GIẤY CHỨNG NHẬN đã hoàn thành khóa học đào tạo bồi dưỡng kiến thức hành nghề môi giới bất động "
                   "sản"]),
        4: _pages([""]),
    }
    segments = [_seg(0, 1, 1, "other"), _seg(0, 2, 2, "other"), _seg(1, 1, 1, "cccd"), _seg(1, 2, 2, "other"),
                _seg(2, 1, 1, "other"), _seg(3, 1, 1, "gcn_khoa_hoc"), _seg(4, 1, 1, "other")]
    attachments, _, warnings = _plan(segments, pages, [2, 2, 1, 1, 1], types={4: "image/jpeg"})
    assert sorted(a["componentIndex"] for a in attachments) == [1, 2, 3, 5, 6]
    # Trang 2 của đơn / mặt sau CCCD không tiêu đề → nối tiếp.
    assert _row(attachments, 3)["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": None}]
    assert _row(attachments, 2)["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": None}]
    # Ảnh chụp rời (OCR rỗng) → dòng 6, không đính chung đơn.
    assert _row(attachments, 6)["sourceSegments"] == [{"fileIndex": 4, "pageIndexes": None}]
    assert not any("(dòng" in w for w in warnings)
    assert not any("chứng thực" in w for w in warnings)


def test_planner_chung_chi_nuoc_ngoai_khong_bo_tick_va_bo_qua_giay_to_khac():
    pages = {0: _pages(["REAL ESTATE BROKER LICENSE", "CHỨNG CHỈ HÀNH NGHỀ MÔI GIỚI BẤT ĐỘNG SẢN số 01/2020",
                        "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP"])}
    segments = [_seg(0, 1, 1, "chung_chi_nuoc_ngoai"), _seg(0, 2, 2, "chung_chi_cu"),
                _seg(0, 3, 3, "giay_to_to_chuc")]
    attachments, classified, warnings = _plan(segments, pages, [3])
    assert [a["componentIndex"] for a in attachments] == [4]
    assert "untickRows" not in attachments[0]
    assert [c["target"] for c in classified if c.get("target")] == ["skip", "skip"]
    assert any("Thêm giấy tờ" in w for w in warnings)
    assert not any("Không xác định được loại" in w for w in warnings)
