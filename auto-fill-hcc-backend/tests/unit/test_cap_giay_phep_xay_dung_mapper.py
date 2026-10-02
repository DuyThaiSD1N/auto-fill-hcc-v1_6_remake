"""Mapper tests for construction permit process."""

import base64
import io
import zipfile

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines._shared.compact_agent.runner import _extract_docx_images
from app.pipelines.cap_giay_phep_xay_dung import process as agent
from app.pipelines.cap_giay_phep_xay_dung.process import mapper
from app.pipelines.cap_giay_phep_xay_dung.process.prompt import EXTRA_RULES
from app.pipelines.cap_giay_phep_xay_dung.process.schema import FIELDS
from app.procedures.registry import get_pipeline, get_procedure


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _values(mapped: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in mapped}


def test_cap_giay_phep_xay_dung_registered():
    key = "cap-giay-phep-xay-dung-moi-nha-o-rieng-le"
    proc = get_procedure(key)

    assert proc
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert "Cấp giấy phép xây dựng mới" in proc["label"]
    assert get_pipeline(key) is agent.run


def test_cap_giay_phep_xay_dung_maps_private_house_sample():
    fields = [
        _field("Applicant_HoTen", "NGUYỄN TRUNG CHÍNH"),
        _field("Applicant_NgaySinh", "08/03/1977"),
        _field("Applicant_GioiTinh", "Nam"),
        _field("Applicant_SoDinhDanh", "027077015515"),
        _field("Applicant_NgayCap", "18/12/2021"),
        _field("Applicant_NoiCap", "Cục cảnh sát quản lý hành chính về trật tự xã hội"),
        _field("Applicant_DienThoai", "0985986500"),
        _field(
            "Applicant_NoiCuTru",
            {"quocGia": "Việt Nam", "tinh": "Tỉnh Bắc Ninh", "xa": "Phường Song Liễu", "diaChi": "TDP Ngọc Tỉnh"},
        ),
        _field("Don_KinhGui", "UBND phường Song Liễu"),
        _field("ChuDauTu_Loai", "Chủ hộ"),
        _field("ChuHo_HoTen", "NGUYỄN TRUNG CHÍNH"),
        _field("ChuHo_SoDinhDanh", "027077015515"),
        _field("ChuHo_DienThoai", "0985986500"),
        _field(
            "Dat_DiaDiemXayDung",
            {"quocGia": "Việt Nam", "tinh": "Tỉnh Bắc Ninh", "xa": "Phường Song Liễu", "diaChi": "TDP Ngọc Tỉnh"},
        ),
        _field("Dat_ThuaDatSo", "604"),
        _field("Dat_ToBanDoSo", "3"),
        _field("Dat_DienTich", "228 m2"),
        _field("LapThietKe_Loai", "Tổ chức"),
        _field("ThietKe_ToChuc_Ten", "CÔNG TY CỔ PHẦN TƯ VẤN ĐẦU TƯ XÂY DỰNG ARECO"),
        _field("ThietKe_ToChuc_MaSo", "2301199858"),
        _field("ThietKe_ChuNhiem_HoTen", "Nguyễn Văn Lục"),
        _field("ThietKe_ChuNhiem_ChungChi", "BAN-00000047"),
        _field("ThietKe_ChuTri_DanhSach", [
            {"boMon": "Kiến trúc", "hoTen": "Nguyễn Văn Lục", "chungChi": "BAN-00000047"},
            {"boMon": "Kết cấu", "hoTen": "Cao Đình Chính", "chungChi": "BAN-00127083"},
            {"boMon": "Điện", "hoTen": "Nguyễn Văn Thắng", "chungChi": "BXD-00028135"},
            {"boMon": "Nước", "hoTen": "Nguyễn Văn An", "chungChi": "BAN-00109462"},
        ]),
        _field("CongTrinh_Ten", "NHÀ Ở GIA ĐÌNH"),
        _field("CongTrinh_Loai", "Nhà ở riêng lẻ"),
        _field("CongTrinh_Cap", "Cấp III"),
        _field("CongTrinh_DienTichXayDung", "106,0 m2"),
        _field("CongTrinh_CotXayDung", "+ 0,45 m"),
        _field("CongTrinh_TongDienTichSan", "214,1 m2"),
        _field("CongTrinh_ChiTietDienTichSan", "Tầng 1: 106 m2; tầng 2: 101,7 m2; mái: 112,4 m2"),
        _field("CongTrinh_ChieuCao", "9,6 m"),
        _field("CongTrinh_ChiTietChieuCao", "Tầng 1: 3,9m; tầng 2: 3,6m; mái: 2,1m"),
        _field("CongTrinh_SoTang", "02 tầng"),
        _field("CongTrinh_ChiTietSoTang", "02 tầng + mái"),
        _field("CongTrinh_ThoiGianDuKienHoanThanh", "06 tháng"),
    ]

    out, warnings = mapper.enrich(fields, {})
    d = _values(out)

    assert warnings == []
    assert d["data[chonDoiTuong]"] == "Cá nhân"
    assert d["data[fullname]"] == "NGUYỄN TRUNG CHÍNH"
    assert d["data[birthday]"] == "08/03/1977"
    assert d["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["data[province]"] == "Tỉnh Bắc Ninh"
    assert d["data[district]"] == "Phường Song Liễu"
    assert d["data[address]"] == "TDP Ngọc Tỉnh"
    assert d["data[kinhGui]"] == "UBND phường Song Liễu"
    assert d["data[loaiHinhChuDauTu]"] == "chuHo"
    assert d["data[tenChuHo]"] == "NGUYỄN TRUNG CHÍNH"
    assert d["data[loDatSo]"] == "604 (tờ bản đồ số 3)"
    assert d["data[dienTichLoDat]"] == "228"
    assert d["data[duongPho]"] == "TDP Ngọc Tỉnh"
    assert d["data[thoiGianDuKienHoanThanh]"] == "6"
    assert d["data[toChucCaNhanLapThietKe]"] == "toChuc"
    assert d["data[maSoDoanhNghiepLapThietKe]"] == "2301199858"
    assert d["data[thietKeXayDung][0][boMonChuTriThietKe]"] == "Kiến trúc"
    assert d["data[thietKeXayDung][0][hoVaTenChuTriThietKe]"] == "Nguyễn Văn Lục"
    assert d["data[thietKeXayDung][0][maSoChungChiHanhNgheChuTriThietKe]"] == "BAN-00000047"
    assert d["data[thietKeXayDung][1][boMonChuTriThietKe]"] == "Kết cấu"
    assert d["data[thietKeXayDung][1][hoVaTenChuTriThietKe]"] == "Cao Đình Chính"
    assert d["data[thietKeXayDung][1][maSoChungChiHanhNgheChuTriThietKe]"] == "BAN-00127083"
    assert d["data[thietKeXayDung][2][boMonChuTriThietKe]"] == "Điện"
    assert d["data[thietKeXayDung][2][hoVaTenChuTriThietKe]"] == "Nguyễn Văn Thắng"
    assert d["data[thietKeXayDung][2][maSoChungChiHanhNgheChuTriThietKe]"] == "BXD-00028135"
    assert d["data[thietKeXayDung][3][boMonChuTriThietKe]"] == "Nước"
    assert d["data[thietKeXayDung][3][hoVaTenChuTriThietKe]"] == "Nguyễn Văn An"
    assert d["data[thietKeXayDung][3][maSoChungChiHanhNgheChuTriThietKe]"] == "BAN-00109462"
    assert d["data[loaiCongTrinh]"] == "Nhà ở riêng lẻ"
    assert d["data[tenCongTrinhNhaO]"] == "NHÀ Ở GIA ĐÌNH"
    assert d["data[capCongTrinhNhaO]"] == "III"
    assert d["data[dienTichXayDungTang1NhaO]"] == "106"
    assert d["data[cotXayDungNhaO]"] == "0.45"
    assert d["data[tongDienTichSanNhaO]"] == "214.1"
    assert d["data[chieuCaoCongTrinhNhaO]"] == "9.6"
    assert d["data[soTangNhaO]"] == "02 tầng"
    assert "data[capCongTrinhKhongTheoTuyen]" not in d
    assert d["data[toChucCaNhanThamTraThietKe]"] == "caNhan"


def test_cap_giay_phep_xay_dung_fills_applicant_only_when_ui_context_matches():
    fields = [
        _field("Applicant_HoTen", "NGUYỄN TRUNG CHÍNH"),
        _field("Applicant_NgaySinh", "08/03/1977"),
        _field("Applicant_SoDinhDanh", "027077015515"),
        _field("Applicant_NgayCap", "18/12/2021"),
        _field("Applicant_DienThoai", "0985986500"),
        _field("ChuDauTu_Loai", "Chủ hộ"),
        _field("ChuHo_HoTen", "NGUYỄN TRUNG CHÍNH"),
        _field("ChuHo_SoDinhDanh", "027077015515"),
        _field("ChuHo_DienThoai", "0985986500"),
    ]

    matched, _ = mapper.enrich(
        fields,
        {"formContext": {"applicantFullname": "Nguyễn Trung Chính", "applicantIdentityNumber": "027077015515"}},
    )
    matched_values = _values(matched)

    assert matched_values["data[fullname]"] == "NGUYỄN TRUNG CHÍNH"
    assert matched_values["data[identityNumber]"] == "027077015515"
    assert matched_values["data[phoneNumber]"] == "0985986500"
    assert matched_values["data[tenChuHo]"] == "NGUYỄN TRUNG CHÍNH"

    mismatched, _ = mapper.enrich(
        fields,
        {"formContext": {"applicantFullname": "TRẦN VĂN KHÁC", "applicantIdentityNumber": "012345678901"}},
    )
    mismatch_values = _values(mismatched)

    assert "data[fullname]" not in mismatch_values
    assert "data[identityNumber]" not in mismatch_values
    assert "data[phoneNumber]" not in mismatch_values
    assert "data[chonDoiTuong]" not in mismatch_values
    assert mismatch_values["data[tenChuHo]"] == "NGUYỄN TRUNG CHÍNH"
    assert mismatch_values["data[soDinhDanhChuHo]"] == "027077015515"


def test_cap_giay_phep_xay_dung_prompt_locks_private_house_rules():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Đơn đề nghị cấp phép xây dựng là nguồn chính" in system_prompt
    assert "Công trình không theo tuyến, tín ngưỡng, tôn giáo" in system_prompt
    assert "không trả bất kỳ field ThamTra_* nào" in system_prompt
    assert "ThietKe_ChuTri_DanhSach" in system_prompt
    assert "TẤT CẢ các dòng" in system_prompt
    assert "ưu tiên bộ môn Kiến trúc" not in system_prompt
    assert "ƯU TIÊN TUYỆT ĐỐI \"Nơi cư" in system_prompt
    assert "CHỈ khi Giấy ủy quyền không ghi hoặc không đọc được địa chỉ" in system_prompt
    assert "ƯU TIÊN \"Địa chỉ liên hệ\"" not in system_prompt


def test_cap_giay_phep_xay_dung_deduplicates_design_leads_and_keeps_one_row_shape():
    out, _ = mapper.enrich([
        _field("LapThietKe_Loai", "Tổ chức"),
        _field("ThietKe_ToChuc_Ten", "CÔNG TY THIẾT KẾ MINH AN"),
        _field("ThietKe_ChuTri_DanhSach", [
            {"boMon": "Kết cấu", "hoTen": "Lê Minh Anh", "chungChi": ""},
            {"boMon": "KẾT CẤU", "hoTen": "LÊ MINH ANH", "chungChi": "HCM-01234567"},
        ]),
    ], {})
    d = _values(out)

    assert d["data[thietKeXayDung][0][boMonChuTriThietKe]"] == "Kết cấu"
    assert d["data[thietKeXayDung][0][hoVaTenChuTriThietKe]"] == "Lê Minh Anh"
    assert d["data[thietKeXayDung][0][maSoChungChiHanhNgheChuTriThietKe]"] == "HCM-01234567"
    assert not any(name.startswith("data[thietKeXayDung][1]") for name in d)


def test_cap_giay_phep_xay_dung_does_not_promote_chief_designer_to_discipline_lead():
    out, _ = mapper.enrich([
        _field("LapThietKe_Loai", "Tổ chức"),
        _field("ThietKe_ToChuc_Ten", "CÔNG TY THIẾT KẾ MINH AN"),
        _field("ThietKe_ChuNhiem_HoTen", "Trần Văn Bình"),
        _field("ThietKe_ChuNhiem_ChungChi", "HAN-07654321"),
    ], {})
    d = _values(out)

    assert d["data[tenChuNhiemThietKe]"] == "Trần Văn Bình"
    assert not any(name.startswith("data[thietKeXayDung]") for name in d)


def test_cap_giay_phep_xay_dung_maps_explicit_dan_dung_subtype():
    out, warnings = mapper.enrich([
        _field("Applicant_HoTen", "NGUYỄN TRUNG CHÍNH"),
        _field("Applicant_SoDinhDanh", "027077015515"),
        _field("CongTrinh_Ten", "NHÀ Ở GIA ĐÌNH"),
        _field("CongTrinh_Loai", "Dân dụng"),
    ], {})
    d = _values(out)

    assert warnings == ["Chưa đọc được thông số xây dựng chính từ đơn/bản vẽ."]
    assert d["data[loaiCongTrinh]"] == "Công trình không theo tuyến, tín ngưỡng, tôn giáo"
    assert d["data[loaiCongTrinhKhongTheoTuyen]"] == "Công trình dân dụng"


def test_cap_giay_phep_xay_dung_detects_house_from_shared_form_section():
    out, warnings = mapper.enrich([
        _field("CongTrinh_Ten", "NHÀ Ở GIA ĐÌNH"),
        _field("CongTrinh_Cap", "Cấp III"),
        _field("CongTrinh_DienTichXayDung", "106 m2"),
    ], {
        "_ocr_text": "Mẫu số 01 ... 4.4. Đối với công trình nhà ở riêng lẻ: Cấp công trình III ...",
    })
    d = _values(out)

    assert not any("nhánh loại hình công trình" in warning for warning in warnings)
    assert d["data[loaiCongTrinh]"] == "Nhà ở riêng lẻ"
    assert d["data[tenCongTrinhNhaO]"] == "NHÀ Ở GIA ĐÌNH"
    assert d["data[capCongTrinhNhaO]"] == "III"
    assert "data[tenCongTrinhKhongTheoTuyen]" not in d


def test_cap_giay_phep_xay_dung_does_not_default_unknown_construction_branch():
    out, warnings = mapper.enrich([
        _field("CongTrinh_Ten", "Công trình chưa rõ loại"),
    ], {})
    d = _values(out)

    assert "data[loaiCongTrinh]" not in d
    assert any("nhánh loại hình công trình" in warning for warning in warnings)


def test_compact_runner_extracts_docx_embedded_images():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", "<w:document/>")
        zf.writestr("word/media/image1.jpeg", b"fake-jpeg")
        zf.writestr("word/media/image2.png", b"fake-png")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    files = _extract_docx_images({
        "name": "cccd.docx",
        "type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "dataUrl": "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64," + b64,
    })

    assert [f["name"] for f in files] == ["cccd.docx::image1.jpeg", "cccd.docx::image2.png"]
    assert files[0]["type"] == "image/jpeg"
    assert files[1]["type"] == "image/png"
    assert files[0]["_sourceDocxName"] == "cccd.docx"


# ---------------------------------------------------------------------------
# Hồ sơ thật req_c7ff7df997f2 (Ninh Bình, bà V.T.N — CCCD 12 số, đơn không ghi ngày sinh)
# ---------------------------------------------------------------------------
def _comps(mapped: list[dict]) -> dict:
    return {f["name"]: f["comp"] for f in mapped}


def test_chi_biet_nam_sinh_thi_khong_bia_ngay_thang():
    """CCCD 12 số mã hoá NĂM sinh + giới tính, nhưng KHÔNG có ngày/tháng. Trước đây mapper ghép
    '01/01/<năm>' → form hiện ngày sinh BỊA. Giờ phải bỏ trống và tô đỏ cho cán bộ tự nhập."""
    mapped, _ = mapper.enrich(
        [_field("Applicant_HoTen", "Nguyễn Thị A"), _field("Applicant_SoDinhDanh", "037160002966")],
        {},
    )

    assert _values(mapped)["data[birthday]"] == ""
    assert _comps(mapped)["data[birthday]"] == "dom-expect"
    # Giới tính thì VẪN điền được: chữ số thứ 4 của CCCD mã hoá giới tính, đây là suy ra tất định.
    assert _values(mapped)["data[gender]"] == "Nữ"


def test_chi_co_nam_sinh_roi_cung_khong_dung_de_ghep_ngay():
    mapped, _ = mapper.enrich(
        [_field("Applicant_HoTen", "Nguyễn Thị A"), _field("Applicant_NamSinh", "1960")],
        {},
    )

    assert _values(mapped)["data[birthday]"] == ""
    assert _comps(mapped)["data[birthday]"] == "dom-expect"


def test_ngay_sinh_day_du_van_duoc_dien_va_van_chuan_nam_theo_cccd():
    """Có ngày/tháng thật thì vẫn điền; năm lệch với CCCD thì chỉ sửa NĂM, giữ nguyên ngày/tháng."""
    mapped, _ = mapper.enrich(
        [
            _field("Applicant_HoTen", "Nguyễn Thị A"),
            _field("Applicant_SoDinhDanh", "037160002966"),
            _field("Applicant_NgaySinh", "23/05/1968"),
        ],
        {},
    )

    assert _values(mapped)["data[birthday]"] == "23/05/1960"


def _design_fields(chu_nhiem_name, chu_nhiem_chung_chi):
    return [
        _field("Applicant_HoTen", "Nguyễn Thị A"),
        _field("LapThietKe_Loai", "Tổ chức"),
        _field("ThietKe_ToChuc_Ten", "Công ty TNHH Tư vấn Xây dựng M"),
        _field("ThietKe_ChuNhiem_HoTen", chu_nhiem_name),
        _field("ThietKe_ChuNhiem_ChungChi", chu_nhiem_chung_chi),
        _field("ThietKe_ChuTri_DanhSach", [
            {"boMon": "Kết Cấu", "hoTen": "Trần Văn B", "chungChi": "NIB-00169422"},
            {"boMon": "Kiến Trúc", "hoTen": "Lê Văn C", "chungChi": "NIB-00000033"},
        ]),
    ]


def test_chung_chi_chu_nhiem_khop_theo_ten_khong_ghep_cheo_dong():
    """Đơn kê mỗi người một dòng '<tên>, Mã số: <mã> — <vai trò>' nên LLM hay ghép tên dòng này với mã
    dòng kia. Mapper khớp TẤT ĐỊNH theo họ tên trong danh sách chủ trì để lấy đúng mã."""
    mapped, _ = mapper.enrich(_design_fields("Trần Văn B", "NIB-00000033"), {})

    values = _values(mapped)
    assert values["data[tenChuNhiemThietKe]"] == "Trần Văn B"
    assert values["data[maSoChungChiChuNhiemThietKe]"] == "NIB-00169422"


def test_chu_nhiem_khong_co_trong_danh_sach_chu_tri_thi_giu_gia_tri_llm():
    mapped, _ = mapper.enrich(_design_fields("Phạm Văn D", "NIB-00123456"), {})

    assert _values(mapped)["data[maSoChungChiChuNhiemThietKe]"] == "NIB-00123456"


def test_thu_tu_chu_tri_giu_dung_thu_tu_ke_khai():
    mapped, _ = mapper.enrich(_design_fields("Trần Văn B", "NIB-00169422"), {})

    values = _values(mapped)
    assert values["data[thietKeXayDung][0][boMonChuTriThietKe]"] == "Kết Cấu"
    assert values["data[thietKeXayDung][0][hoVaTenChuTriThietKe]"] == "Trần Văn B"
    assert values["data[thietKeXayDung][1][boMonChuTriThietKe]"] == "Kiến Trúc"


def test_prompt_day_du_quy_tac_vai_tro_cuoi_dong():
    assert "VAI TRÒ NẰM Ở CUỐI DÒNG" in EXTRA_RULES
    assert 'Người chỉ ghi "Chủ trì: ..." KHÔNG phải chủ nhiệm' in EXTRA_RULES
    assert "Cấm ghép tên người này với mã số người kia." in EXTRA_RULES
    chu_nhiem = next(f for f in FIELDS if f["name"] == "ThietKe_ChuNhiem_HoTen")
    assert "BỎ TRỐNG" in chu_nhiem["desc"]


def test_desc_dien_tich_xay_dung_chot_la_tang_1_va_cam_lay_o_dong_chieu_cao():
    """Hồ sơ mẫu: đơn ghi 'Diện tích xây dựng tầng 1: 30m²' nhưng form bị điền 116.4 — con số đó nằm ở
    dòng 'Chiều cao công trình (tầng 1: 116.4m...)'. Desc phải chặn đúng cái nhầm này."""
    desc = next(f for f in FIELDS if f["name"] == "CongTrinh_DienTichXayDung")["desc"]

    assert "TẦNG 1" in desc
    assert "Chiều cao công trình" in desc
    assert "Tổng diện tích sàn" in desc


def test_ba_o_trong_do_van_duoc_map_khi_llm_tra_chi_tiet():
    """3 ô 'Trong đó' của nhà ở riêng lẻ phải ra đủ khi LLM đọc được phần liệt kê theo tầng."""
    mapped, _ = mapper.enrich(
        [
            _field("Applicant_HoTen", "Nguyễn Thị A"),
            _field("CongTrinh_Nhanh", "nha_o_rieng_le"),
            _field("CongTrinh_TongDienTichSan", "393"),
            _field("CongTrinh_ChiTietDienTichSan", "tầng 1: 30m², tầng 2: 43,2 m², tầng 3: 43,2 m²"),
            _field("CongTrinh_ChieuCao", "11,9"),
            _field("CongTrinh_ChiTietChieuCao", "tầng 1: 3,4m, tầng 2: 3m, tầng tum: 2,5m"),
            _field("CongTrinh_SoTang", "3"),
            _field("CongTrinh_ChiTietSoTang", "3 tầng"),
        ],
        {},
    )

    values = _values(mapped)
    assert values["data[chiTietDienTichSanNhaO]"].startswith("tầng 1: 30m²")
    assert values["data[chiTietChieuCaoNhaO]"].startswith("tầng 1: 3,4m")
    assert values["data[chiTietSoTangNhaO]"] == "3 tầng"


def test_desc_chi_tiet_nhan_ca_3_kieu_trinh_bay_va_bat_buoc_tra():
    """Đơn thật viết phần liệt kê theo 3 kiểu (sau 'Trong đó:', trong ngoặc, nối tiếp cùng dòng).
    Prompt/desc phải phủ cả ba, và phải nói rõ ĐÃ trả field số thì VẪN trả field chi tiết —
    nếu không LLM hay bỏ trống 3 ô 'Trong đó'."""
    by_name = {f["name"]: f["desc"] for f in FIELDS}

    for name in ("CongTrinh_ChiTietDienTichSan", "CongTrinh_ChiTietChieuCao", "CongTrinh_ChiTietSoTang"):
        assert "BẮT BUỘC trả" in by_name[name], name

    assert "MỖI THÔNG SỐ CÓ HAI FIELD" in EXTRA_RULES
    assert "trong NGOẶC ĐƠN cùng dòng" in EXTRA_RULES
    # Cảnh báo "không lấy số ở dòng chiều cao" phải được giới hạn cho field SỐ, không chặn field chi tiết.
    assert "chỉ áp cho field SỐ" in EXTRA_RULES
