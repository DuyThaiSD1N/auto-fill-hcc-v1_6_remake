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
