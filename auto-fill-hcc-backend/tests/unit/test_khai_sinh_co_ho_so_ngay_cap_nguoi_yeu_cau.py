from app.pipelines.khai_sinh_co_ho_so.process.mapper import _issue_date_not_birth

_ACCOUNT = {"formContext": {"applicantIdentityNumber": "001190000001", "applicantBirthday": "02/03/1990"}}


def test_ngay_cap_trung_ngay_sinh_khi_tu_dang_ky_thi_bo():
    values = {"Requester_RelationToSubject": "Bản thân", "Requester_IdNumber": "001190000001",
              "Subject_BirthDate": "2/3/1990"}
    assert _issue_date_not_birth("02/03/1990", values, None) == ""


def test_ngay_cap_trung_ngay_sinh_tai_khoan_cung_so_thi_bo():
    values = {"Requester_RelationToSubject": "Mẹ", "Requester_IdNumber": "001190000001",
              "Subject_BirthDate": "05/06/2020"}
    assert _issue_date_not_birth("02/03/1990", values, _ACCOUNT) == ""


def test_ngay_cap_cua_nguoi_khac_trung_ngay_sinh_con_van_giu():
    values = {"Requester_RelationToSubject": "Mẹ", "Requester_IdNumber": "001190000009",
              "Subject_BirthDate": "05/06/2020"}
    assert _issue_date_not_birth("05/06/2020", values, _ACCOUNT) == "05/06/2020"


def test_ngay_cap_khac_ngay_sinh_giu_nguyen():
    values = {"Requester_RelationToSubject": "Bản thân", "Subject_BirthDate": "02/03/1990"}
    assert _issue_date_not_birth("14/08/2021", values, _ACCOUNT) == "14/08/2021"
