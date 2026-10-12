"""Unit test "Gia hạn giấy phép xây dựng" (mã 1.013227, cổng Bộ Xây dựng): registry, mapper, đính kèm."""

from app.pipelines.gia_han_giay_phep_xay_dung.attach import planner
from app.pipelines.gia_han_giay_phep_xay_dung.process import mapper
from app.pipelines.gia_han_giay_phep_xay_dung.process.prompt import EXTRA_RULES
from app.pipelines.gia_han_giay_phep_xay_dung.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "gia-han-giay-phep-xay-dung"

_HAI_VO_CHONG = {
    "Applicant_HoTen": "Trần Văn Bình",
    "Applicant_NgaySinh": "12/04/1975",
    "Applicant_SoDinhDanh": "068075000111",
    "Applicant_NgayCap": "10/10/2022",
    "Applicant_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "Applicant_DienThoai": "0900111222",
    "Applicant_NoiCuTru": {"tinh": "Lâm Đồng", "xa": "Phường Xuân Hương - Đà Lạt", "diaChi": "12 Đường Mẫu"},
    "Don_KinhGui": "UBND phường Lâm Viên - Đà Lạt",
    "ChuDauTu_Loai": "Chủ hộ",
    "ChuHo_HoTen": "Trần Văn Bình - Lê Thị Hoa",
    "ChuHo_SoDinhDanh": "068075000111 - 068176000222",
    "ChuHo_DienThoai": "0900111222",
    "Dat_DiaDiemXayDung": {"tinh": "Lâm Đồng", "xa": "Phường Lâm Viên - Đà Lạt"},
    "Dat_LoDatSo": "AB 123456",
    "Dat_ThuaDatSo": "120 (gốc 45)",
    "Dat_ToBanDoSo": "7 (12b)",
    "Dat_DienTich": "150,5",
    "GPXD_So": "15/GPXD",
    "GPXD_NgayCap": "01/02/2026",
    "GPXD_CoQuanCap": "UBND phường Lâm Viên - Đà Lạt",
    "GPXD_NoiDung": "Nhà cấp III, diện tích XD tầng trệt: 80 m²; tổng diện tích sàn: 320 m²",
    "GiaHan_LyDo": "Gia hạn giấy phép",
    "CongTrinh_ThoiGianDuKienHoanThanh": "12 tháng",
    "Don_NguoiKy": "Lê Thị Hoa - Trần Văn Bình",
}


def _run(values: dict, options: dict | None = None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options or {})
    by: dict = {}
    for f in fields:
        by[(f["name"], f.get("occurrence"))] = f
    return by, fields, warnings


def _val(by: dict, name: str, occurrence: int | None = None):
    return by[(name, occurrence)]["value"]


def test_registry_wires_key_from_ke_khai_links_va_nhan_dien_bang_h2():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.013227"
    proc = registry.get_procedure(KEY)
    assert proc["label"] == link["label"]
    # Nhận diện bằng h2 tên thủ tục: heading = nguyên văn h2 trên cổng, không dùng urlScope.
    assert proc["detect"]["heading"] == link["label"]
    assert proc["detect"]["heading"].startswith("Gia hạn giấy phép xây dựng đối với công trình cấp III, cấp IV")
    assert "urlScope" not in proc["detect"] and not proc["detect"].get("headingDisabled")
    assert proc["hasAttachmentStep"] is True
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    public = next(p for p in with_ke_khai_detect_urls([proc]))
    assert "matthc=1.013227" in public["detect"]["urlIncludes"]
    # Tên package trùng key trong ke_khai_links.
    assert planner.__name__.split(".")[2] == KEY.replace("-", "_")


def test_ca_nhan_hai_vo_chong_dien_du_to_don_gia_han():
    by, _, warnings = _run(_HAI_VO_CHONG)
    # Người nộp = MỘT người (người đứng đầu), chủ hộ = cả hai.
    assert _val(by, "data[chonDoiTuong]") == "Cá nhân"
    assert _val(by, "data[fullname]") == "Trần Văn Bình"
    assert _val(by, "data[identityNumber]") == "068075000111"
    assert _val(by, "data[birthday]") == "12/04/1975"
    assert _val(by, "data[gender]") == "Nam"
    assert _val(by, "data[province]", 0) == "Tỉnh Lâm Đồng"
    assert _val(by, "data[district]", 0) == "Phường Xuân Hương - Đà Lạt"
    assert _val(by, "data[recipient]") == "UBND phường Lâm Viên - Đà Lạt"
    assert _val(by, "data[loaiHinhChuDauTu]") == "chuHo"
    assert _val(by, "data[tenChuHo]") == "Trần Văn Bình - Lê Thị Hoa"
    assert _val(by, "data[soDinhDanhChuHo]") == "068075000111 - 068176000222"
    # Địa điểm xây dựng: ô 'đường' nhận tờ bản đồ khi thửa đất không có tên đường.
    assert _val(by, "data[lotNumber]") == "AB 123456"
    assert _val(by, "data[landArea]") == "150.5"
    assert _val(by, "data[locationAt]") == "Thửa đất số 120 (gốc 45)"
    assert _val(by, "data[street]") == "Tờ bản đồ số 7 (12b)"
    assert _val(by, "data[province]", 1) == "Tỉnh Lâm Đồng"
    assert _val(by, "data[phuongxaaa]") == "Phường Lâm Viên - Đà Lạt"
    # GPXD đã cấp + loại đề nghị.
    assert _val(by, "data[existingPermitNumber]") == "15/GPXD"
    assert _val(by, "data[NgayCap]") == "01/02/2026"
    assert _val(by, "data[existingPermitAuthority]") == "UBND phường Lâm Viên - Đà Lạt"
    assert _val(by, "data[existingPermitContent]").startswith("Nhà cấp III")
    assert _val(by, "data[requestType]") == "Gia hạn Giấy phép xây dựng"
    assert _val(by, "data[estimatedCompletionMonths]") == "12"
    assert by[("data[commitment]", None)] == {"name": "data[commitment]", "comp": "dom-checkbox", "value": True}
    assert _val(by, "data[tinhthanhqwaasa]") == "Tỉnh Lâm Đồng"
    assert _val(by, "data[KyGhiRoHoTen]") == "Lê Thị Hoa - Trần Văn Bình"
    assert _val(by, "data[tenHoSo]") == "Gia hạn Giấy phép xây dựng số 15/GPXD"
    assert not warnings


def test_ly_do_cut_thi_ghep_gpxd_tham_chieu_ly_do_cu_the_giu_nguyen():
    by, _, _ = _run(_HAI_VO_CHONG)
    assert _val(by, "data[extensionReason]") == (
        "Đề nghị gia hạn Giấy phép xây dựng số 15/GPXD ngày 01/02/2026 của UBND phường Lâm Viên - Đà Lạt."
    )
    ly_do = "Chưa khởi công do thời tiết mưa kéo dài, đề nghị gia hạn giấy phép."
    by, _, _ = _run({**_HAI_VO_CHONG, "GiaHan_LyDo": ly_do})
    assert _val(by, "data[extensionReason]") == ly_do


def test_loai_de_nghi_dung_truoc_ly_do_va_radio_truoc_o_chu_ho():
    _, fields, _ = _run(_HAI_VO_CHONG)
    names = [f["name"] for f in fields]
    assert names.index("data[requestType]") < names.index("data[extensionReason]")
    assert names.index("data[loaiHinhChuDauTu]") < names.index("data[tenChuHo]")


def test_thieu_applicant_lay_nguoi_dung_dau_cua_chu_ho():
    values = {k: v for k, v in _HAI_VO_CHONG.items() if not k.startswith("Applicant_")}
    by, _, _ = _run(values)
    assert _val(by, "data[fullname]") == "Trần Văn Bình"
    assert _val(by, "data[identityNumber]") == "068075000111"
    # Không có ngày sinh/ngày cấp → tô đỏ, không bịa.
    assert by[("data[birthday]", None)]["comp"] == "dom-expect"
    assert by[("data[identityDate]", None)]["comp"] == "dom-expect"
    # Không có nơi cư trú người nộp → không phát data[province] lần 0, tỉnh lô đất vẫn ở lần 1.
    assert ("data[province]", 0) not in by
    assert _val(by, "data[province]", 1) == "Tỉnh Lâm Đồng"


def test_thua_dat_co_ten_duong_thi_to_ban_do_ghep_vao_o_tai():
    by, _, _ = _run({**_HAI_VO_CHONG, "Dat_DuongPho": "Đường Mẫu"})
    assert _val(by, "data[locationAt]") == "Thửa đất số 120 (gốc 45), tờ bản đồ số 7 (12b)"
    assert _val(by, "data[street]") == "Đường Mẫu"


def test_khac_tai_khoan_dang_nhap_thi_khong_ghi_khoi_nguoi_nop():
    options = {"formContext": {"applicantFullname": "Người Khác", "applicantIdentityNumber": "001090000009"}}
    by, _, _ = _run(_HAI_VO_CHONG, options)
    assert ("data[fullname]", None) not in by
    assert _val(by, "data[tenChuHo]") == "Trần Văn Bình - Lê Thị Hoa"
    assert _val(by, "data[existingPermitNumber]") == "15/GPXD"


def test_canh_bao_thieu_gpxd_va_noi_dung():
    values = {k: v for k, v in _HAI_VO_CHONG.items() if not k.startswith("GPXD_")}
    by, _, warnings = _run(values)
    assert ("data[existingPermitNumber]", None) not in by
    # Kính gửi thay cho cơ quan cấp khi GPXD không đọc được.
    assert _val(by, "data[existingPermitAuthority]") == "UBND phường Lâm Viên - Đà Lạt"
    assert _val(by, "data[extensionReason]") == "Gia hạn giấy phép"
    assert any("số Giấy phép xây dựng" in w for w in warnings)
    assert any("Nội dung Giấy phép" in w for w in warnings)


def test_moi_field_mapper_phat_deu_co_trong_ui_va_prompt_dung_field_hop_le():
    _, fields, _ = _run(_HAI_VO_CHONG)
    assert all(f["name"] in UI_COMP_BY_NAME for f in fields)
    for name in ("GPXD_NoiDung", "GiaHan_LyDo", "Dat_LoDatSo", "Don_NguoiKy"):
        assert name in ALLOWED and name in EXTRA_RULES


def test_dinh_kem_ba_muc_don_cccd_gop_dong_1_gcn_qua_them_giay_to():
    files = [{"name": n} for n in ("cccd.jpg", "don.pdf", "gpxd.pdf", "gcn.pdf", "la.pdf")]
    llm = {0: "cccd", 1: "don_gia_han", 2: "gpxd_da_cap", 3: "giay_to_dat_dai", 4: "other"}
    items, warnings, classified = planner.build_plan_items(files, {}, llm)
    by_file = {item["fileName"]: item for item in items}
    assert set(by_file) == {"cccd.jpg", "don.pdf", "gpxd.pdf", "gcn.pdf"}

    don_row = "Đơn đề nghị gia hạn giấy phép xây dựng theo Mẫu số 2"
    # Dòng 1 đính chung, Đơn đứng TRƯỚC CCCD.
    assert [i["fileName"] for i in items if i["componentName"] == don_row] == ["don.pdf", "cccd.jpg"]
    assert by_file["cccd.jpg"]["target"] == "attp-row" and by_file["cccd.jpg"]["loaiBan"] == "Bản chính"
    assert by_file["gpxd.pdf"]["componentName"] == "Bản chính giấy phép xây dựng đã được cấp"
    gcn = by_file["gcn.pdf"]
    assert gcn["target"] == "add-document-dialog" and gcn["needsAddComponent"] is True
    assert gcn["componentName"] == "Giấy chứng nhận quyền sử dụng đất" and gcn["loaiBan"] == "Bản sao"
    assert gcn["fallbackComponentName"] == don_row
    assert all(item["untickUnplannedRows"] for item in items)
    assert all(len(item["documentName"]) <= 50 for item in items)
    assert {c["fileName"] for c in classified if c.get("skipped")} == {"la.pdf"}
    assert any("la.pdf" in w for w in warnings)
    assert not any("bắt buộc" in w for w in warnings)


def test_dinh_kem_rule_du_phong_khi_khong_co_llm():
    files = [{"name": n} for n in ("a.pdf", "b.pdf", "c.pdf", "d.jpg", "e.pdf", "f.jpg")]
    texts = {
        0: "Phụ lục II - Mẫu số 02 ĐƠN ĐỀ NGHỊ ĐIỀU CHỈNH/GIA HẠN/CẤP LẠI GIẤY PHÉP XÂY DỰNG Kính gửi",
        1: "ỦY BAN NHÂN DÂN PHƯỜNG MẪU GIẤY PHÉP XÂY DỰNG Số: 15/GPXD Cấp cho: ông Trần Văn Bình "
           "Giấy chứng nhận quyền sử dụng đất số AB 123456",
        2: "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN KHÁC GẮN LIỀN VỚI ĐẤT",
        3: "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số / No.",
        4: "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM GIẤY ỦY QUYỀN Căn cước công dân số",
        5: "",
    }
    items, warnings, _ = planner.build_plan_items(files, texts)
    types = {item["fileName"]: item["detectedType"] for item in items}
    assert types == {
        "a.pdf": "don_gia_han", "b.pdf": "gpxd_da_cap", "c.pdf": "giay_to_dat_dai",
        "d.jpg": "cccd", "e.pdf": "giay_uy_quyen",
    }
    assert any("f.jpg" in w for w in warnings)


def test_dinh_kem_canh_bao_thieu_giay_bat_buoc_va_danh_so_tep_trung_loai():
    files = [{"name": "cccd1.jpg"}, {"name": "cccd2.jpg"}]
    items, warnings, _ = planner.build_plan_items(files, {}, {0: "cccd", 1: "cccd"})
    assert [item["documentName"] for item in items] == ["Căn cước công dân", "Căn cước công dân 2"]
    assert any("Đơn đề nghị gia hạn" in w for w in warnings)
    assert any("Giấy phép xây dựng đã được cấp" in w for w in warnings)
