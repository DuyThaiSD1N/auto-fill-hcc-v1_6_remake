"""Unit test "Đề nghị miễn, giảm học phí trong cơ sở GDNN, GDĐH tư thục…" (mã 1.014335, cổng Bộ GD&ĐT): registry,
mapper, đính kèm."""

from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.attach import planner
from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.process import mapper
from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.process.prompt import EXTRA_RULES
from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "mien-giam-hoc-phi-gdnn-dai-hoc-tu-thuc"

_DOI_TUONG = ("Học sinh, sinh viên học một số nghề nặng nhọc, độc hại, nguy hiểm đối với giáo dục nghề nghiệp theo "
              "danh mục các nghề học nặng nhọc, độc hại, nguy hiểm do cơ quan quản lý nhà nước về giáo dục nghề nghiệp "
              "ở trung ương quy định.")

# Hồ sơ bịa: sinh viên ở Đà Lạt, mẹ đăng nhập nộp thay; CCCD ghi địa danh cũ, Đơn ghi địa danh hiện hành.
_HO_SO = {
    "SinhVien_HoTen": "Lê Thị An",
    "SinhVien_NgaySinh": "15/03/2006",
    "SinhVien_GioiTinh": "Nữ",
    "SinhVien_SoDinhDanh": "06.8306.01.2345",
    "SinhVien_NgayCap": "12/08/2021",
    "SinhVien_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "SinhVien_ThuongTru": {"tinh": "Tỉnh Lâm Đồng", "xa": "Phường Lang Biang - Đà Lạt",
                           "diaChi": "12 Đường Mẫu, TDP 3"},
    "SinhVien_ThuongTruCCCD": {"tinh": "Lâm Đồng", "huyen": "Thành phố Đà Lạt", "xa": "Phường 7",
                               "diaChi": "12 Đường Mẫu"},
    "SinhVien_NoiSinh": {"tinh": "tỉnh Lâm Đồng", "diaChi": "Bệnh viện Đa khoa",
                         "fullText": "Bệnh viện Đa khoa, tỉnh Lâm Đồng"},
    "Don_KinhGui": "Trường Cao đẳng Mẫu",
    "Don_Lop": "Dược 2K1",
    "Don_NienKhoa": "2024 - 2027",
    "Don_Khoa": "Dược",
    "Don_HoTenChaMe": "Lê Văn Bình",
    "Don_DoiTuong": _DOI_TUONG,
    "Don_NgayLam": "05/10/2026",
    "KhaiSinh_HoTenCha": "LÊ VĂN BÌNH",
    "KhaiSinh_HoTenMe": "TRẦN THỊ HOA",
}
_ME_DANG_NHAP = {"formContext": {"applicantFullname": "TRẦN THỊ HOA", "applicantIdentityNumber": "042181000999"}}


def _run(values: dict, options: dict | None = None, ocr_text: str = ""):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options or {}, ocr_text)
    return {f["name"]: f for f in fields}, fields, warnings


def _val(by: dict, name: str):
    return by[name]["value"]


def test_registry_wires_key_from_ke_khai_links_va_nhan_dien_theo_panel_don_pl4():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.014335"
    proc = registry.get_procedure(KEY)
    assert proc["label"] == link["label"]
    assert proc["detect"]["textPriority"] is True
    assert "urlScope" not in proc["detect"]
    assert proc["hasAttachmentStep"] is True
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    public = next(p for p in with_ke_khai_detect_urls([proc]))
    assert "matthc=1.014335" in public["detect"]["urlIncludes"]
    # Tên package trùng key trong ke_khai_links.
    assert planner.__name__.split(".")[2] == KEY.replace("-", "_")


_PHAN_I = ("data[fullname]", "data[identityNumber]", "data[birthday]", "data[chonDoiTuong]", "data[gender]",
           "data[identityDate]", "data[idIssuePlace]", "data[email]", "data[province]", "data[district]",
           "data[address]", "data[phoneNumber]")


def test_me_nop_thay_dien_chu_ho_so_sinh_vien_va_don_pl4():
    by, _, warnings = _run(_HO_SO, _ME_DANG_NHAP)
    # Phần I là người đăng nhập (mẹ) nhưng hồ sơ không có giấy tờ của mẹ → bỏ qua cả phần, không tô đỏ.
    for name in _PHAN_I:
        assert name not in by
    # Phần II: chủ hồ sơ = sinh viên.
    assert _val(by, "data[ChuHS]") == "Cá nhân"
    assert _val(by, "data[ownerFullname]") == "LÊ THỊ AN"
    assert _val(by, "data[ownerIdentityNumber]") == "068306012345"
    assert _val(by, "data[ownerGender]") == "Nữ"
    assert _val(by, "data[ownerBirthday]") == "15/03/2006"
    assert _val(by, "data[ownerIdentityDate]") == "12/08/2021"
    assert _val(by, "data[ownerIdentityAgency22]") == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert _val(by, "data[ownerNation]") == "Việt Nam"
    assert _val(by, "data[ownerProvince]") == "Tỉnh Lâm Đồng"
    assert _val(by, "data[ownerDistrict]") == "Phường Lang Biang - Đà Lạt"
    # Số nhà theo Đơn (địa danh hiện hành, đủ tổ dân phố) chứ không theo CCCD.
    assert _val(by, "data[ownerAddress]") == "12 Đường Mẫu, TDP 3"
    # Panel Đơn PL IV.
    assert _val(by, "data[province2]") == "Lâm Đồng"
    assert _val(by, "data[d]") == "05/10/2026"
    assert _val(by, "data[KinhGui]") == "Trường Cao đẳng Mẫu"
    assert _val(by, "data[TenChaMe]") == "Lê Văn Bình"
    assert _val(by, "data[Lop]") == "Dược 2K1"
    assert _val(by, "data[Khoa1]") == "2024 - 2027"
    assert _val(by, "data[Khoa2]") == "Dược"
    assert _val(by, "data[DoiTuong]") == _DOI_TUONG
    # Nơi sinh: Giấy khai sinh chỉ ghi bệnh viện + tỉnh → ô Phường/Xã tô đỏ, có cảnh báo.
    assert _val(by, "data[TinhThanhPho]") == "Tỉnh Lâm Đồng"
    assert _val(by, "data[SoNhaDuong]") == "Bệnh viện Đa khoa"
    assert by["data[QuanHuyen]"]["comp"] == "dom-expect"
    assert any("Nơi sinh chưa có phường/xã" in w for w in warnings)
    assert _val(by, "data[TinhThanhPho1]") == "Tỉnh Lâm Đồng"
    assert _val(by, "data[QuanHuyen1]") == "Phường Lang Biang - Đà Lạt"
    assert _val(by, "data[SoNhaDuong1]") == "12 Đường Mẫu, TDP 3"


def test_sinh_vien_tu_nop_dien_phan_i_tu_cccd_sinh_vien():
    options = {"formContext": {"applicantFullname": "LÊ THỊ AN", "applicantIdentityNumber": "068306012345"}}
    by, _, warnings = _run({**_HO_SO, "SinhVien_DienThoai": "0900 111 222"}, options)
    assert _val(by, "data[gender]") == "Nữ"
    assert _val(by, "data[identityDate]") == "12/08/2021"
    assert _val(by, "data[idIssuePlace]") == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert _val(by, "data[province]") == "Tỉnh Lâm Đồng" and "default" not in by["data[province]"]
    assert _val(by, "data[phoneNumber]") == "0900111222"
    assert _val(by, "data[ownerPhoneNumber]") == "0900111222" and "default" not in by["data[ownerPhoneNumber]"]
    assert not any("Tài khoản nộp không trùng" in w for w in warnings)


def test_cha_nop_thay_co_cccd_dien_phan_i_theo_cccd_cha():
    values = {
        **_HO_SO,
        "NguoiNop_HoTen": "LÊ VĂN BÌNH",
        "NguoiNop_SoDinhDanh": "068077000111",
        "NguoiNop_NgayCap": "20/04/2022",
        "NguoiNop_ThuongTru": {"tinh": "Lâm Đồng", "xa": "Phường Lang Biang - Đà Lạt", "diaChi": "12 Đường Mẫu"},
        "NguoiNop_DienThoai": "0912345678",
    }
    options = {"formContext": {"applicantFullname": "LÊ VĂN BÌNH", "applicantIdentityNumber": "068077000111"}}
    by, _, _ = _run(values, options)
    assert _val(by, "data[gender]") == "Nam"
    assert _val(by, "data[identityDate]") == "20/04/2022"
    assert _val(by, "data[address]") == "12 Đường Mẫu" and "default" not in by["data[address]"]
    assert _val(by, "data[phoneNumber]") == "0912345678"
    # SĐT sinh viên không có → dùng SĐT người nộp, tô vàng.
    assert _val(by, "data[ownerPhoneNumber]") == "0912345678" and by["data[ownerPhoneNumber]"]["default"] is True
    # Người nộp không lẫn sang chủ hồ sơ.
    assert _val(by, "data[ownerIdentityNumber]") == "068306012345"


def test_giay_tiep_nhan_ghi_nguoi_khac_tai_khoan_thi_khong_dien_phan_i():
    """Giấy tiếp nhận ghi mẹ sinh viên là người nộp, nhưng người đăng nhập VNeID là cán bộ (hoặc extension không gửi
    formContext) → không được đổ giới tính/SĐT/địa chỉ của mẹ vào Phần I."""
    values = {
        **_HO_SO,
        "NguoiNop_HoTen": "Trần Thị Hoa",
        "NguoiNop_SoDinhDanh": "042181000999",
        "NguoiNop_GioiTinh": "Nữ",
        "NguoiNop_ThuongTru": {"tinh": "Lâm Đồng", "xa": "Phường Lang Biang - Đà Lạt", "diaChi": "12 Đường Mẫu"},
        "NguoiNop_DienThoai": "0912345678",
    }
    can_bo = {"formContext": {"applicantFullname": "NGUYỄN VĂN CÁN", "applicantIdentityNumber": "001090000009"}}
    for options in (can_bo, {}):
        by, _, _ = _run(values, options)
        for name in _PHAN_I:
            assert name not in by
        # SĐT liên hệ của hồ sơ vẫn dùng dự phòng cho chủ hồ sơ (tô vàng).
        assert _val(by, "data[ownerPhoneNumber]") == "0912345678" and by["data[ownerPhoneNumber]"]["default"] is True
    # Đúng mẹ đăng nhập → điền Phần I theo giấy tờ của mẹ.
    by, _, _ = _run(values, _ME_DANG_NHAP)
    assert _val(by, "data[gender]") == "Nữ"
    assert _val(by, "data[phoneNumber]") == "0912345678"
    assert _val(by, "data[address]") == "12 Đường Mẫu"


_OCR_CCCD_CAN_BO = """===== giay_tiep_nhan.jpg (tiengnoi) =====
GIẤY TIẾP NHẬN HỒ SƠ VÀ HẸN TRẢ KẾT QUẢ
Cá nhân/Tổ chức/Doanh nghiệp: Trần Thị Hoa
Số định danh cá nhân/tổ chức: 042181000999
===== cccd_can_bo.jpg (tiengnoi) =====
CĂN CƯỚC CÔNG DÂN
Citizen Identity Card
Số / No: 001090000009
Họ và tên / Full name:
NGUYỄN VĂN CÁN
Ngày sinh / Date of birth: 01/02/1990
Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam
Nơi thường trú / Place of residence: 12 Đường Mẫu
Phường 7, Thành phố Đà Lạt, Lâm Đồng
Có giá trị đến: 01/02/2030
"""


def test_co_cccd_nguoi_dang_nhap_thi_dien_phan_i_theo_the_khong_theo_giay_tiep_nhan():
    """LLM lấy người nộp từ Giấy tiếp nhận (mẹ sinh viên), nhưng hồ sơ có thẻ CCCD mang số tài khoản đăng nhập →
    Phần I đọc thẳng từ thẻ đó; SĐT trên Giấy tiếp nhận là của người khác nên không dùng."""
    values = {
        **_HO_SO,
        "NguoiNop_HoTen": "Trần Thị Hoa",
        "NguoiNop_SoDinhDanh": "042181000999",
        "NguoiNop_GioiTinh": "Nữ",
        "NguoiNop_DienThoai": "0912345678",
    }
    can_bo = {"formContext": {"applicantFullname": "Nguyễn Văn Cán", "applicantIdentityNumber": "001090000009"}}
    by, _, _ = _run(values, can_bo, _OCR_CCCD_CAN_BO)
    assert _val(by, "data[gender]") == "Nam"
    assert _val(by, "data[province]") == "Tỉnh Lâm Đồng"
    assert _val(by, "data[district]") == "Phường Lang Biang - Đà Lạt"
    assert _val(by, "data[address]") == "12 Đường Mẫu"
    assert by["data[phoneNumber]"]["comp"] == "dom-expect"
    assert "data[fullname]" not in by and "data[identityNumber]" not in by
    # Thẻ mang số KHÁC tài khoản → không phải người đăng nhập dù OCR không đọc được tên.
    other = {"formContext": {"applicantFullname": "Người Khác", "applicantIdentityNumber": "001090000777"}}
    by, _, _ = _run(values, other, _OCR_CCCD_CAN_BO)
    assert "data[gender]" not in by and "data[province]" not in by


def _await(coro):
    """Chạy coroutine không có await bên trong (không cần event loop — conftest chặn socketpair trên Windows)."""
    try:
        coro.send(None)
    except StopIteration as stop:
        return stop.value
    raise AssertionError("coroutine bất ngờ chờ I/O")


def test_neo_nguoi_nop_cho_llm_theo_so_dinh_danh_tai_khoan():
    from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.process.runner import _submitter_context

    docs = [{"text": seg} for seg in _OCR_CCCD_CAN_BO.split("=====")[2::2]]
    # Tên trên thẻ OCR rơi xuống dòng/thiếu vẫn khớp được bằng số định danh.
    ctx = {"formContext": {"applicantFullname": "NGUYỄN VĂN CÁN", "applicantIdentityNumber": "001090000009"}}
    text = _await(_submitter_context(docs, ctx))
    assert 'result="co_giay_to"' in text and "Tài liệu #2" in text
    other = {"formContext": {"applicantFullname": "Người Khác", "applicantIdentityNumber": "001090000777"}}
    assert 'result="khong_co_giay_to"' in _await(_submitter_context(docs, other))
    assert _await(_submitter_context(docs, {})) == ""


def test_thieu_don_lay_du_phong_giay_xac_nhan_va_khai_sinh():
    values = {k: v for k, v in _HO_SO.items() if k not in ("Don_KinhGui", "Don_HoTenChaMe", "Don_DoiTuong")}
    values.update({"Truong_Ten": "Trường Cao đẳng Mẫu", "GiayXacNhan_DoiTuong": "Sinh viên học ngành nghề nặng nhọc"})
    by, _, _ = _run(values, _ME_DANG_NHAP)
    assert _val(by, "data[KinhGui]") == "Trường Cao đẳng Mẫu"
    assert _val(by, "data[TenChaMe]") == "LÊ VĂN BÌNH"
    assert _val(by, "data[DoiTuong]") == "Sinh viên học ngành nghề nặng nhọc"


def test_noi_sinh_dia_danh_cu_quy_doi_sang_tinh_xa_hien_hanh():
    values = {**_HO_SO, "SinhVien_NoiSinh": {"tinh": "Bắc Giang", "huyen": "Lục Nam", "xa": "Tam Dị"}}
    by, _, warnings = _run(values, _ME_DANG_NHAP)
    assert _val(by, "data[TinhThanhPho]") == "Thành phố Bắc Ninh"
    assert by["data[QuanHuyen]"]["comp"] == "dom-select"
    assert not any("Nơi sinh chưa có phường/xã" in w for w in warnings)


def test_chi_co_cccd_dia_danh_cu_van_quy_doi_phuong_hien_hanh():
    values = {k: v for k, v in _HO_SO.items() if k != "SinhVien_ThuongTru"}
    by, _, _ = _run(values, _ME_DANG_NHAP)
    assert _val(by, "data[ownerDistrict]") == "Phường Lang Biang - Đà Lạt"
    assert _val(by, "data[ownerAddress]") == "12 Đường Mẫu"


def test_moi_field_mapper_phat_deu_co_trong_ui_va_prompt_dung_field_hop_le():
    _, fields, _ = _run(_HO_SO, _ME_DANG_NHAP)
    assert all(f["name"] in UI_COMP_BY_NAME for f in fields)
    for name in ("SinhVien_NoiSinh", "SinhVien_ThuongTruCCCD", "Don_NienKhoa", "Don_DoiTuong", "Don_KinhGui"):
        assert name in ALLOWED and name in EXTRA_RULES


def test_dinh_kem_gop_moi_dong_thanh_mot_pdf_dung_thu_tu_bo_phieu_tiep_nhan():
    names = ("don.jpg", "cccd.jpg", "gxn_pl5.jpg", "phieu_tn.jpg", "gxn_truong.jpg", "khai_sinh.jpg",
             "bang_bia.jpg", "du_toan.jpg", "bang_trong.jpg")
    files = [{"name": n} for n in names]
    llm = {0: "don_pl4", 1: "cccd", 2: "gxn_pl5", 3: "phieu_tiep_nhan", 4: "gxn_truong", 5: "giay_khai_sinh",
           7: "du_toan_pl6", 8: "bang_tot_nghiep"}
    items, warnings, classified = planner.build_plan_items(files, {}, llm)
    assert len(items) == 2
    row1, row2 = items
    assert row1["componentName"] == "giấy tờ chứng minh thuộc đối tượng miễn, giảm học phí"
    # GXN trường → GXN PL V → CCCD → Giấy KS → Bằng (bìa ảnh không chữ + trang trong).
    assert [names[i] for i in row1["sourceFileIndexes"]] == [
        "gxn_truong.jpg", "gxn_pl5.jpg", "cccd.jpg", "khai_sinh.jpg", "bang_bia.jpg", "bang_trong.jpg",
    ]
    assert row1["fileIndex"] == row1["sourceFileIndexes"][0]
    assert row2["componentName"] == "Đơn đề nghị chi trả tiền miễn giảm học phí theo mẫu tại Phụ lục IV"
    assert [names[i] for i in row2["sourceFileIndexes"]] == ["don.jpg", "du_toan.jpg"]
    for item in items:
        assert item["target"] == "attp-row" and item["loaiBan"] == "Bản chính"
        assert item["untickUnplannedRows"] is True
        assert len(item["documentName"]) <= 50
    assert {c["fileName"] for c in classified if c.get("skipped")} == {"phieu_tn.jpg"}
    assert any("phieu_tn.jpg" in w for w in warnings)
    assert not any("bắt buộc" in w for w in warnings)


def test_dinh_kem_rule_du_phong_khi_khong_co_llm():
    files = [{"name": f"{i}.pdf"} for i in range(7)]
    texts = {
        0: "Phụ lục IV ĐƠN ĐỀ NGHỊ CHI TRẢ TIỀN MIỄN, GIẢM HỌC PHÍ Kính gửi Người làm đơn",
        1: "PHỤ LỤC VI DỰ TOÁN KINH PHÍ CẤP BÙ TIỀN MIỄN, GIẢM HỌC PHÍ Tổng dự toán",
        2: "PHỤ LỤC V GIẤY XÁC NHẬN (Dùng cho các cơ sở giáo dục nghề nghiệp) Mức thu học phí",
        3: "TRƯỜNG CAO ĐẲNG MẪU GIẤY XÁC NHẬN Trường xác nhận sinh viên Thuộc đối tượng",
        4: "GIẤY KHAI SINH (BẢN SAO) Họ, chữ đệm, tên người mẹ",
        5: "GIẤY TIẾP NHẬN HỒ SƠ VÀ HẸN TRẢ KẾT QUẢ Mã hồ sơ Đơn đề nghị chi trả tiền miễn giảm học phí theo mẫu tại "
           "Phụ lục IV",
        6: "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số / No.",
    }
    items, _, classified = planner.build_plan_items(files, texts)
    types = {c["fileName"]: c["docType"] for c in classified}
    assert types == {
        "0.pdf": "don_pl4", "1.pdf": "du_toan_pl6", "2.pdf": "gxn_pl5", "3.pdf": "gxn_truong",
        "4.pdf": "giay_khai_sinh", "5.pdf": "phieu_tiep_nhan", "6.pdf": "cccd",
    }
    assert [i["sourceFileIndexes"] for i in items] == [[3, 2, 6, 4], [0, 1]]


def test_dinh_kem_canh_bao_thieu_don_va_giay_chung_minh():
    items, warnings, _ = planner.build_plan_items([{"name": "cccd.jpg"}], {}, {0: "cccd"})
    assert [i["sourceFileIndexes"] for i in items] == [[0]]
    assert any("Phụ lục IV" in w and "bắt buộc" in w for w in warnings)
    assert any("giấy tờ chứng minh" in w and "bắt buộc" in w for w in warnings)
