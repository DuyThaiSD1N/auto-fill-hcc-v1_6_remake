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
