"""Đăng ký lại khai sinh: có giấy ủy quyền thì người yêu cầu là bên được ủy quyền, kể cả khi có tờ khai."""
from app.pipelines.khai_sinh_dang_ky_lai.process import mapper

_FIELDS = {
    "Requester_SourceDocumentTitle": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH",
    "Requester_RelationToSubject": "Bản thân",
    "Requester_FullName": "TRẦN VĂN AN",
    "Requester_IdNumber": "001071000001",
    "Authorized_SourceDocumentTitle": "GIẤY ỦY QUYỀN",
    "Authorized_FullName": "Lê Văn Bình",
    "Authorized_IdNumber": "001056000002",
    "Subject_FullName": "TRẦN VĂN AN",
    "Subject_IdNumber": "001071000001",
}
_CONTEXT = ("<nguoi_duoc_uy_quyen>\nHọ tên: {ten}\nSố CCCD/CMND: {so}\n</nguoi_duoc_uy_quyen>\n"
            "<to_khai_dang_ky_lai>\nCó tờ khai đăng ký lại khai sinh: {co}\n</to_khai_dang_ky_lai>")


def _run(fields, has_declaration, authorized=("Lê Văn Bình", "001056000002")):
    context = _CONTEXT.format(ten=authorized[0], so=authorized[1], co="Có" if has_declaration else "Không")
    out = mapper.enrich([{"name": k, "value": v} for k, v in fields.items()], {"_reasoning_context": context})
    return {f["name"]: f["value"] for f in out}


def test_co_to_khai_va_giay_uy_quyen_nguoi_yeu_cau_la_ben_duoc_uy_quyen():
    v = _run(_FIELDS, True)
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("Khac", "LÊ VĂN BÌNH", "001056000002")


def test_co_to_khai_ben_duoc_uy_quyen_la_me_thi_tich_me_de():
    fields = {
        **_FIELDS,
        "Authorized_FullName": "Nguyễn Thị Hoa",
        "Authorized_IdNumber": "001160000003",
        "Mother_FullName": "Nguyễn Thị Hoa",
        "Mother_IdNumber": "001160000003",
    }
    v = _run(fields, True, ("Nguyễn Thị Hoa", "001160000003"))
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("MeDe", "NGUYỄN THỊ HOA", "001160000003")


def test_co_to_khai_khong_co_giay_uy_quyen_nguoi_yeu_cau_theo_to_khai():
    fields = {k: v for k, v in _FIELDS.items() if not k.startswith("Authorized_")}
    out = mapper.enrich(
        [{"name": k, "value": v} for k, v in fields.items()],
        {"_reasoning_context": "<to_khai_dang_ky_lai>\nCó tờ khai đăng ký lại khai sinh: Có\n</to_khai_dang_ky_lai>"},
    )
    v = {f["name"]: f["value"] for f in out}
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("BanThan", "TRẦN VĂN AN", "001071000001")


def test_khong_co_to_khai_thi_nguoi_yeu_cau_la_ben_duoc_uy_quyen():
    fields = {k: v for k, v in _FIELDS.items() if not k.startswith("Requester_")}
    v = _run(fields, False)
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("Khac", "LÊ VĂN BÌNH", "001056000002")


# Tờ khai viết tay: người yêu cầu đọc từ tờ khai, so với tài khoản đăng nhập theo "1 trong 3" (tên/số/ngày sinh).
_TAI_KHOAN = {"applicantFullname": "TRẦN VĂN HĨ", "applicantIdentityNumber": "001071000001",
              "applicantBirthday": "05/06/1971", "applicantIdDate": "03/04/2022", "applicantGender": "Nam"}
_GIAY_TO = ("SoDinhDanhC", "SoGiayToDinhDanhC", "LoaiGiayToDinhDanhC")


def _run_tai_khoan(ten="Trần Văn Hũ", so="00207100001", ngay_sinh="05 / 6 / 1971", quan_he="Khác",
                   con=("Trần Văn Bảo", "01/01/2000"), account=None):
    fields = {
        "Requester_SourceDocumentTitle": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH",
        "Requester_RelationToSubject": quan_he,
        "Requester_FullName": ten,
        "Requester_IdNumber": so,
        "Requester_IdIssueDate": "01/02/2021",
        "Requester_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "Subject_FullName": con[0],
        "Subject_BirthDate": con[1],
        "Subject_Gender": "Nam",
    }
    context = (f"<nguoi_yeu_cau>\nHọ tên: {ten}\nNgày sinh: {ngay_sinh}\n"
               "Vai trò đồng thời: không xác định\n</nguoi_yeu_cau>\n"
               "<to_khai_dang_ky_lai>\nCó tờ khai đăng ký lại khai sinh: Có\n</to_khai_dang_ky_lai>")
    out = mapper.enrich([{"name": k, "value": v} for k, v in fields.items()],
                        {"formContext": {**_TAI_KHOAN, **(account or {})}, "_reasoning_context": context})
    return {f["name"]: f for f in out}


def _la_chu_tai_khoan(v):
    return (v["HoVaTenC"]["value"], v["SoDinhDanhC"]["value"], v["NgayCapDDC"]["value"]) == (
        "TRẦN VĂN HĨ", "001071000001", "03/04/2022")


def test_ten_lech_mot_ky_tu_la_du_dien_muc_i_theo_tai_khoan():
    v = _run_tai_khoan(ngay_sinh="", account={"applicantBirthday": ""})
    assert _la_chu_tai_khoan(v)
    assert v["SoGiayToDinhDanhC"]["value"] == "001071000001"
    assert not any(v[name].get("clear") for name in mapper._REQUESTER_IDENTITY_FIELDS)


def test_chi_trung_ngay_sinh_la_du():
    assert _la_chu_tai_khoan(_run_tai_khoan(ten="Trần Văn Bình"))


def test_chi_so_roi_mot_chu_so_la_du():
    assert _la_chu_tai_khoan(_run_tai_khoan(ten="Trần Văn Bình", so="00107100001", ngay_sinh=""))


def test_khac_ho_thi_khac_nguoi_du_trung_ngay_sinh():
    v = _run_tai_khoan(ten="Lê Văn Hĩ")
    assert v["HoVaTenC"]["value"] == "LÊ VĂN HĨ"
    assert all(v[name].get("clear") for name in (*_GIAY_TO, "NgayCapDDC", "NoiCapDDC"))


def test_hai_so_du_12_chu_so_lech_nhieu_thi_khac_nguoi_du_trung_ten():
    v = _run_tai_khoan(ten="Trần Văn Hĩ", so="001071999991")
    assert (v["HoVaTenC"]["value"], v["SoDinhDanhC"]["value"]) == ("TRẦN VĂN HĨ", "001071999991")


def test_khong_khop_tieu_chi_nao_thi_xoa_ca_cum_giay_to():
    v = _run_tai_khoan(ten="Trần Văn Bình", ngay_sinh="05 / 6 / 1980")
    assert v["HoVaTenC"]["value"] == "TRẦN VĂN BÌNH"
    assert all(v[name].get("clear") for name in (*_GIAY_TO, "NgayCapDDC", "NoiCapDDC"))


def test_ban_than_khop_tai_khoan_thi_muc_ii_theo_tai_khoan():
    v = _run_tai_khoan(quan_he="Bản thân", con=("Trần Văn Lê", "05/06/1971"))
    assert (v["HoTenKS"]["value"], v["NgaySinhChon"]["value"]) == ("TRẦN VĂN HĨ", "05/06/1971")


def test_ban_than_nhung_nguoi_con_khong_khop_tai_khoan_thi_giu_muc_ii():
    v = _run_tai_khoan(quan_he="Bản thân", con=("Trần Văn Bảo", "01/01/2000"))
    assert v["HoTenKS"]["value"] == "TRẦN VĂN BẢO"


def test_ngay_sinh_khac_thi_ten_lech_mot_ky_tu_khong_du():
    v = _run_tai_khoan(ngay_sinh="05 / 6 / 1975")
    assert v["HoVaTenC"]["value"] == "TRẦN VĂN HŨ"
    assert all(v[name].get("clear") for name in _GIAY_TO)


def test_ngay_sinh_khac_nhung_so_roi_mot_chu_so_van_la_chu_tai_khoan():
    assert _la_chu_tai_khoan(_run_tai_khoan(so="00107100001", ngay_sinh="05 / 6 / 1975"))


# Phường Hiệp Hòa (cờ grantorAsRequester do server đặt theo tài khoản): người yêu cầu là BÊN ỦY QUYỀN.
from app.pipelines.khai_sinh_dang_ky_lai.process import reason

_HIEP_HOA = {"tinh": "Tỉnh Bắc Ninh", "xa": "Phường Hiệp Hòa"}
_GIAY_UY_QUYEN = """GIẤY ỦY QUYỀN
I. BÊN ỦY QUYỀN:
Họ và tên: Nguyễn Thị Hoa
Số CCCD: 001160000003 cấp ngày 10/05/2021
Nơi cư trú: Thôn Đông, Phường Hiệp Hòa, Tỉnh Bắc Ninh
II. BÊN ĐƯỢC ỦY QUYỀN:
Họ và tên: Lê Văn Bình
Số CCCD: 001056000002
III. NỘI DUNG ỦY QUYỀN:
Bên ủy quyền và bên được ủy quyền cam kết thực hiện đúng nội dung trên.
BÊN ỦY QUYỀN          BÊN ĐƯỢC ỦY QUYỀN
"""


def _run_hiep_hoa(fields, grantor=("Nguyễn Thị Hoa", "001160000003"), user=_HIEP_HOA):
    context = _CONTEXT.format(ten="Lê Văn Bình", so="001056000002", co="Có")
    if grantor:
        context += f"<nguoi_uy_quyen>\nHọ tên: {grantor[0]}\nSố CCCD/CMND: {grantor[1]}\n</nguoi_uy_quyen>\n"
    options = mapper.with_account_process_options(
        {"_reasoning_context": context}, user, "khai-sinh-dang-ky-lai")
    out = mapper.enrich([{"name": k, "value": v} for k, v in fields.items()], options)
    return {f["name"]: f["value"] for f in out}


def test_co_hiep_hoa_chi_bat_cho_dung_phuong_va_dung_thu_tuc():
    on = mapper.with_account_process_options({}, _HIEP_HOA, "khai-sinh-dang-ky-lai")
    assert on[reason.GRANTOR_AS_REQUESTER_OPTION] is True
    assert mapper.with_account_process_options(
        {}, {"tinh": "Thành phố Bắc Ninh", "xa": "Xã Hiệp Hòa"}, "khai-sinh-dang-ky-lai")["grantorAsRequester"]
    assert "grantorAsRequester" not in mapper.with_account_process_options(
        {"grantorAsRequester": True}, {"tinh": "Tỉnh Bắc Ninh", "xa": "Phường Kinh Bắc"}, "khai-sinh-dang-ky-lai")
    assert "grantorAsRequester" not in mapper.with_account_process_options(
        {}, _HIEP_HOA, "xac-nhan-tinh-trang-hon-nhan")


def test_hiep_hoa_ben_uy_quyen_la_me_thi_tich_me_de_va_lay_the_cua_me():
    fields = {**_FIELDS, "Mother_FullName": "Nguyễn Thị Hoa", "Mother_IdNumber": "001160000003",
              "Mother_IdIssueDate": "10/05/2021"}
    v = _run_hiep_hoa(fields)
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"], v["NgayCapDDC"]) == (
        "MeDe", "NGUYỄN THỊ HOA", "001160000003", "10/05/2021")


def test_hiep_hoa_ben_uy_quyen_khong_trung_vai_nao_thi_tich_khac():
    v = _run_hiep_hoa(_FIELDS, grantor=("Phạm Văn Cường", "001060000004"))
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("Khac", "PHẠM VĂN CƯỜNG", "001060000004")


def test_hiep_hoa_khong_doc_duoc_ben_uy_quyen_thi_theo_to_khai_khong_lay_ben_duoc_uy_quyen():
    v = _run_hiep_hoa(_FIELDS, grantor=None)
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("BanThan", "TRẦN VĂN AN", "001071000001")


def test_phuong_khac_van_lay_ben_duoc_uy_quyen_du_context_co_ben_uy_quyen():
    v = _run_hiep_hoa(_FIELDS, user={"tinh": "Tỉnh Bắc Ninh", "xa": "Phường Kinh Bắc"})
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("Khac", "LÊ VĂN BÌNH", "001056000002")


def test_reason_doc_muc_ben_uy_quyen_chi_khi_bat_co():
    docs = [{"name": "giay_uy_quyen.pdf", "text": _GIAY_UY_QUYEN}]
    assert reason._render_grantor(docs, {}) == ""
    block = reason._render_grantor(docs, {"grantorAsRequester": True})
    assert reason._labeled_value(block, "Họ tên") == "Nguyễn Thị Hoa"
    assert reason._labeled_value(block, "Số CCCD/CMND") == "001160000003"
    assert reason._labeled_value(block, "Ngày cấp") == "10/05/2021"
    assert reason._authorized_person(docs)["name"] == "Lê Văn Bình"


_XUAN_HUONG = {"tinh": "Tỉnh Lâm Đồng", "xa": "Phường Xuân Hương - Đà Lạt"}
_DECEASED = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": "Đã chết"}


def _run_deceased_parents(user):
    fields = {**_FIELDS, "Mother_FullName": "Nguyễn Thị Hoa", "Mother_ResidenceDomestic": _DECEASED,
              "Father_FullName": "Trần Văn Cường", "Father_ResidenceDomestic": _DECEASED}
    context = _CONTEXT.format(ten="Lê Văn Bình", so="001056000002", co="Có")
    options = mapper.with_account_process_options({"_reasoning_context": context}, user, "khai-sinh-dang-ky-lai")
    out = mapper.enrich([{"name": k, "value": v} for k, v in fields.items()], options)
    return {f["name"]: f["value"] for f in out}


def test_xuan_huong_cha_me_da_chet_chon_khong_co_thong_tin_va_viet_nam():
    v = _run_deceased_parents(_XUAN_HUONG)
    for prefix in ("Cha", "Me"):
        assert v[f"{prefix}LoaiCuTru"] == "Không có thông tin"
        assert v[f"{prefix}NoiCuTru"] == "Khác"
        assert v[f"{prefix}NoiCuTru_NuocNgoai"] == {"quocGia": "Việt Nam", "diaChi": "Đã chết"}


def test_noi_khac_cha_me_da_chet_giu_nhu_cu():
    v = _run_deceased_parents({"tinh": "Tỉnh Lâm Đồng", "xa": "Xã Đơn Dương"})
    for prefix in ("Cha", "Me"):
        assert f"{prefix}LoaiCuTru" not in v
        assert v[f"{prefix}NoiCuTru_NuocNgoai"] == "Đã chết"


def test_co_xuan_huong_chi_bat_cho_dung_phuong_va_dung_thu_tuc():
    assert mapper.with_account_process_options({}, _XUAN_HUONG, "khai-sinh-dang-ky-lai")["deceasedParentNoInfo"]
    assert "deceasedParentNoInfo" not in mapper.with_account_process_options(
        {"deceasedParentNoInfo": True}, _HIEP_HOA, "khai-sinh-dang-ky-lai")
    assert "deceasedParentNoInfo" not in mapper.with_account_process_options(
        {}, _XUAN_HUONG, "thay-doi-cai-chinh-ho-tich")


def _the(so, ten, ngay, gioi):
    return (f"CĂN CƯỚC CÔNG DÂN\nSố / No.: {so}\nHọ và tên / Full name: {ten}\nNgày sinh / Date of birth: {ngay}\n"
            f"Giới tính / Sex: {gioi} Quốc tịch / Nationality: Việt Nam\n")


_HO_SO_KEM_KHAI_SINH_CUA_CON = "\n".join(f"───── Trang {i}/6 ─────\n{body}" for i, body in enumerate([
    _the("001180000011", "TRẦN THỊ MAI", "01/01/1980", "Nữ"),
    _the("001156000012", "LÊ THỊ HOA", "01/05/1956", "Nữ"),
    _the("001055000013", "TRẦN VĂN NAM", "10/01/1955", "Nam"),
    "GIẤY KHAI SINH\n(BẢN SAO)\nHọ, chữ đệm, tên: PHẠM VĂN AN\nNgày, tháng, năm sinh: 02/01/2000\n"
    "Họ, chữ đệm, tên người mẹ: TRẦN THỊ MAI\nNơi đăng ký khai sinh: Ủy ban nhân dân xã A\n",
    "KẾT QUẢ KIỂM TRA THÔNG TIN CÔNG DÂN\nHọ và tên công dân: TRẦN THỊ MAI\n"
    "1. Số định danh cá nhân của công dân: 001180000011\n5. Dân tộc của công dân: Tày\n",
    "13. Địa chỉ thường trú của công dân: Xã A",
], start=1))


def test_giay_khai_sinh_cua_con_khong_tinh_dang_ky_truoc_day_va_dan_toc_theo_phieu_dan_cu():
    from app.pipelines.khai_sinh_dang_ky_lai.process import reason

    docs = [{"name": "ho_so.pdf", "text": _HO_SO_KEM_KHAI_SINH_CUA_CON}]
    context = reason._render_context("", {}, docs)
    assert "TRẦN THỊ MAI" in reason._section(context, "con")
    assert "Có tài liệu khai sinh hợp lệ: Không" in context
    fields = reason.sanitize_extracted_fields([
        {"name": "Subject_FullName", "comp": "x-input", "value": "TRẦN THỊ MAI"},
        {"name": "PreviousRegistration_Number", "comp": "x-input", "value": "09/2000"},
    ], context)
    v = {f["name"]: f["value"] for f in fields}
    assert v.get("Subject_Ethnicity") == "Tày" and "PreviousRegistration_Number" not in v
    # Giấy khai sinh đúng tên người được đăng ký lại vẫn là nguồn hợp lệ.
    own = _HO_SO_KEM_KHAI_SINH_CUA_CON.replace("PHẠM VĂN AN", "TRẦN THỊ MAI").replace("02/01/2000", "01/01/1980")
    assert "Có tài liệu khai sinh hợp lệ: Có" in reason._render_context("", {}, [{"name": "ho_so.pdf", "text": own}])


def test_dan_toc_cha_me_khong_giay_nao_ghi_thi_giu_agent_hoac_suy_theo_con_va_to_vang():
    from app.pipelines.khai_sinh_dang_ky_lai.process import reason

    context = reason._render_context("", {}, [{"name": "ho_so.pdf", "text": _HO_SO_KEM_KHAI_SINH_CUA_CON}])
    fields = reason.sanitize_extracted_fields([
        {"name": "Subject_FullName", "comp": "x-input", "value": "TRẦN THỊ MAI"},
        {"name": "Mother_FullName", "comp": "x-input", "value": "LÊ THỊ HOA"},
        {"name": "Mother_Ethnicity", "comp": "x-select", "value": "Kinh"},
        {"name": "Father_FullName", "comp": "x-input", "value": "TRẦN VĂN NAM"},
    ], context)
    v = {f["name"]: (f["value"], f.get("default")) for f in fields}
    assert v["Mother_Ethnicity"] == ("Kinh", True)
    assert v["Father_Ethnicity"] == ("Tày", True) and v["Subject_Ethnicity"][0] == "Tày"
    # Con không rõ dân tộc mà cha mẹ cùng dân tộc → con theo cha mẹ.
    v = {f["name"]: f["value"] for f in reason._infer_family_ethnicity([
        {"name": "Subject_FullName", "value": "A"}, {"name": "Father_Ethnicity", "value": "Kinh"},
        {"name": "Mother_Ethnicity", "value": "Kinh"}])}
    assert v["Subject_Ethnicity"] == "Kinh"


def test_quoc_tich_viet_tat_cua_viet_nam_deu_ra_viet_nam():
    for raw in ("VN", "VNM", "vn", "V.N", "V.N.M", "(2) VNM", "Việt", "Viet Nam", "VIỆT NAM", "Vietnam",
                "Vietnamese", "Việt Nam (VN)", "VN/VNM", "Người Việt Nam", "CHXHCN Việt Nam",
                "Cộng hòa xã hội chủ nghĩa Việt Nam", "Quốc tịch: Việt Nam", "", None):
        assert mapper._nationality(raw) == "Việt Nam", raw
    for raw in ("Lào", "Trung Quốc", "Hàn Quốc"):
        assert mapper._nationality(raw) == raw


def test_quoc_tich_viet_tat_tren_giay_dien_viet_nam_cho_ca_con_cha_me():
    fields = {**_FIELDS, "Subject_Nationality": "VN", "Mother_FullName": "Nguyễn Thị Hoa",
              "Mother_Nationality": "VNM", "Father_FullName": "Trần Văn Cường", "Father_Nationality": "V.N"}
    v = _run(fields, True)
    assert (v["QuocTichKS"], v["QuocTichMeKS"], v["QuocTichChaKS"]) == ("Việt Nam", "Việt Nam", "Việt Nam")


def _loai_khai_sinh(fields):
    out = mapper.enrich([{"name": k, "value": v} for k, v in fields.items()], {})
    return {f["name"]: f for f in out}


def test_khong_co_cha_thi_loai_khai_sinh_chua_xac_dinh_duoc_cha():
    v = _loai_khai_sinh({"Subject_FullName": "Trần Văn An", "Mother_FullName": "Trần Thị Hoa",
                         "Mother_IdNumber": "001160000003"})
    assert v["nksLoaiKhaiSinh"]["value"] == "Chưa xác định được cha"
    assert all(v[name].get("clear") for name in mapper._FATHER_CLEARABLE_FIELDS)


def test_khong_co_me_thi_loai_khai_sinh_chua_xac_dinh_duoc_me():
    v = _loai_khai_sinh({"Subject_FullName": "Trần Văn An", "Father_FullName": "Trần Văn Cường"})
    assert v["nksLoaiKhaiSinh"]["value"] == "Chưa xác định được mẹ"


def test_du_cha_me_hoac_thieu_ca_hai_giu_mac_dinh():
    du = _loai_khai_sinh({"Subject_FullName": "Trần Văn An", "Father_FullName": "Trần Văn Cường",
                          "Mother_FullName": "Trần Thị Hoa"})
    thieu = _loai_khai_sinh({"Subject_FullName": "Trần Văn An", "Father_Nationality": "Việt Nam"})
    assert du["nksLoaiKhaiSinh"]["value"] == thieu["nksLoaiKhaiSinh"]["value"] == "Đã xác định được cả cha lẫn mẹ"


_TO_KHAI_CHEP_TEN_CHA = """TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH
Họ, chữ đệm, tên người yêu cầu: Lê Thị Hoa
Ngày, tháng, năm sinh: 01/05/1966
Giấy tờ tùy thân: CCCD số 001166000021
Quan hệ với người được khai sinh: mẹ đẻ
Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:
Họ, chữ đệm, tên: Trần Văn Nam
Ngày, tháng, năm sinh: 02/03/1991
Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam
Họ, chữ đệm, tên người mẹ: Lê Thị Hoa
Năm sinh: 01/05/1966 Dân tộc: Kinh Quốc tịch: Việt Nam
Giấy tờ tùy thân: CCCD 001166000021
Họ, chữ đệm, tên người cha: Trần Văn Nam
Năm sinh: 10/01/1960 Dân tộc: Kinh Quốc tịch: Việt Nam
Giấy tờ tùy thân: CCCD 001060000022
"""
_GIAY_UY_QUYEN_NGOI_THU_NHAT = """GIẤY ỦY QUYỀN
Tôi tên là: Trần Văn Hải
Sinh ngày: 2/3/1991
CCCD số 001091000023 cấp ngày 10/8/2021
Hộ khẩu thường trú: Thôn Đông, Phường Hiệp Hòa, Tỉnh Bắc Ninh
Bằng giấy này, tôi ủy quyền cho mẹ tôi:
Họ và tên: Lê Thị Hoa
CCCD số 001166000021
Người ủy quyền
ngón trỏ phải của ông
Trần Văn Hải
"""


def _ho_so_chep_ten_cha():
    return [
        {"name": "the.pdf", "text": "\n".join(f"───── Trang {i}/3 ─────\n{body}" for i, body in enumerate([
            _the("001166000021", "LÊ THỊ HOA", "01/05/1966", "Nữ"),
            _the("001060000022", "TRẦN VĂN NAM", "10/01/1960", "Nam"),
            _the("001091000023", "TRẦN VĂN HẢI", "02/03/1991", "Nam"),
        ], start=1))},
        {"name": "uy_quyen.pdf", "text": _GIAY_UY_QUYEN_NGOI_THU_NHAT},
        {"name": "to_khai.pdf", "text": _TO_KHAI_CHEP_TEN_CHA},
    ]


def test_to_khai_chep_ten_cha_vao_dong_con_thi_ho_ten_con_theo_cccd_dung_ngay_sinh():
    context = reason._render_context("", {}, _ho_so_chep_ten_cha())
    con = reason._section(context, "con")
    assert reason._role_name(con) == "TRẦN VĂN HẢI" and reason._role_id(con) == "001091000023"
    assert reason._labeled_value(con, reason._GENERATION_CARD_LABEL)
    assert reason._role_name(reason._section(context, "cha")) == "TRẦN VĂN NAM"
    fields = reason.sanitize_extracted_fields(
        [{"name": "Subject_FullName", "comp": "x-input", "value": "Trần Văn Nam"}], context)
    v = {f["name"]: (f["value"], f.get("default")) for f in fields}
    assert v["Subject_FullName"] == ("TRẦN VĂN HẢI", True)


def test_giay_uy_quyen_ngoi_thu_nhat_doc_ben_uy_quyen_bo_dong_diem_chi():
    person = reason._grantor_person([{"name": "uy_quyen.pdf", "text": _GIAY_UY_QUYEN_NGOI_THU_NHAT}])
    assert (person["name"], person["id"], person["issue_date"]) == ("Trần Văn Hải", "001091000023", "10/8/2021")
    # Chỉ có dòng ký/điểm chỉ dưới chữ "Người ủy quyền" thì không đọc ra ai.
    chi_ky = "GIẤY ỦY QUYỀN\nNgười ủy quyền\nngón trỏ phải của ông\n"
    assert reason._grantor_person([{"name": "uy_quyen.pdf", "text": chi_ky}]) is None
