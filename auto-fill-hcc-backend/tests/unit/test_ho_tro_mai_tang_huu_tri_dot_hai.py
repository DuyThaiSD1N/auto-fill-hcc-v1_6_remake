"""Mai táng hưu trí xã hội: tờ khai Mẫu 02 / 03, lớp soát thứ hai (thanh tra định danh + địa chỉ) và điền đợt 2 Form.io.
Dữ liệu giả."""

import asyncio

from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process import mapper, runner
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.thanh_tra import dia_chi, trang
from app.procedures.registry import PROCEDURES
from app.second_pass.service import capability

_MAU_03 = (
    "Mẫu số 03\nTỜ KHAI ĐỀ NGHỊ HỖ TRỢ CHI PHÍ MAI TÁNG\nKính gửi: UBND phường Mẫu\n"
    "1. Thông tin người đề nghị\nHọ và tên : Trần Văn Bình\nSố căn cước/định danh cá nhân: 012080000222\n"
    "Nơi cư trú: Tổ 5, phường Mẫu, tỉnh Bắc Ninh\n"
    "2. Thông tin người chết được tổ chức mai táng\nHọ và tên: Trần Văn An\nNơi cư trú: Thôn Một, xã Khác, tỉnh Bắc Ninh\n"
    "3. Người, tổ chức nhận hỗ trợ chi phí mai táng\n3.1. Trường hợp cá nhân, thân nhân đứng ra tổ chức mai táng:\n"
    "Họ và tên: Trần Văn Bình\nNơi cư trú: Tổ 5, phường Mẫu\n3.2. Trường hợp cơ quan, tổ chức đứng ra tổ chức mai táng:\n"
    "4. Hình thức nhận chi phí hỗ trợ mai táng: Tiền mặt\n"
)


def test_dang_ky_dot_hai_form_formio():
    entry = next(p for p in PROCEDURES if p["key"] == mapper.PROCEDURE_KEY)
    assert capability(entry) == "secondPassFormio"


def test_dia_chi_cat_dung_dong_nguoi_de_nghi_va_nguoi_chet():
    lines = dia_chi.lines_of([{"text": _MAU_03}], {"NguoiNop_HoTen": "Trần Văn Bình"})
    assert lines["ChuHoSo_NoiCuTru"][0].endswith("tỉnh Bắc Ninh") and "Tổ 5" in lines["ChuHoSo_NoiCuTru"][0]
    assert lines["NguoiNop_NoiCuTru"] == lines["ChuHoSo_NoiCuTru"]
    assert "Thôn Một" in lines["NguoiMat_NoiCuTru"][0]
    # Người nộp không phải người đề nghị (CCCD riêng) → không có dòng trên tờ khai.
    assert "NguoiNop_NoiCuTru" not in dia_chi.lines_of([{"text": _MAU_03}], {"NguoiNop_HoTen": "Người Khác"})


def test_trang_to_khai_mai_tang_la_don():
    assert [page["kind"] for page in trang.pages([{"text": _MAU_03}])] == ["don"]


def test_ten_xa_khong_cat_chu_dau_trung_tien_to():
    assert mapper._area_label("Phương Liễu") == "Phương Liễu"
    assert mapper._area_label("Phường Phương Liễu") == "Phương Liễu"


def test_runner_tra_dot_hai_khi_extension_bao_ho_tro(monkeypatch):
    async def fake_run(files, **kwargs):
        await kwargs["context_builder"]([{"name": "a", "text": _MAU_03}], kwargs["options"])
        return {"fields": [{"name": "ChuHoSo_HoTen", "value": "Trần Văn Bình"}]}

    monkeypatch.setattr(runner.runner, "run", fake_run)
    assert "_second_pass" in asyncio.run(runner.run({}, {"_secondPass": True}))
    assert "_second_pass" not in asyncio.run(runner.run({}, {}))


def test_khop_tai_khoan_gan_khi_ocr_lech_mot_ben():
    person = mapper.Person("ChuHoSo", name="Trần Văn Bính", identity="012080000222")
    anchor = {"applicant_name": "Trần Văn Bình", "applicant_identity": "012080000222"}
    assert mapper._matches_applicant(person, anchor)
    assert mapper._matches_applicant(mapper.Person("ChuHoSo", name="Trần Văn Bình", identity="01208000022"), anchor)
    # Lệch cả tên lẫn số → người khác.
    assert not mapper._matches_applicant(mapper.Person("ChuHoSo", name="Trần Văn Bính", identity="012080000999"), anchor)
    assert not mapper._matches_applicant(mapper.Person("ChuHoSo", name="Trần Thị Hoa", identity="012080000222"), anchor)


def test_khop_gan_thi_khoi_nguoi_nop_lay_ho_ten_so_cua_tai_khoan():
    compact = [{"name": "ChuHoSo_HoTen", "value": "Trần Văn Bính"}, {"name": "ChuHoSo_SoDinhDanh", "value": "012080000223"}]
    fields, _ = mapper.enrich(compact, {"formContext": {"applicantFullname": "TRẦN VĂN BÌNH",
                                                       "applicantIdentityNumber": "012080000222"}})
    by = {f["name"]: f["value"] for f in fields}
    assert by["data[isOwnerDossierCheck]"] is True
    assert by["data[fullname]"] == "Trần Văn Bính" and by["data[identityNumber]"] == "012080000222"


def test_ten_tinh_doc_lech_mot_chu_nan_ve_danh_muc():
    assert mapper._province_label("Quân Ngãi") == "Quảng Ngãi"
    assert mapper._province_label("Tỉnh Quảng Ngãi") == "Quảng Ngãi"
    assert mapper._province_label("Thành phố Đà Nẵng") == "Đà Nẵng"


def test_sdt_bo_dau_cham_va_suy_noi_cap_theo_ngay_cap():
    compact = [{"name": "NguoiMat_HoTen", "value": "Trần Văn An"}, {"name": "NguoiMat_SoDinhDanh", "value": "012040000111"},
               {"name": "NguoiMat_NgayCap", "value": "28/06/2021"},
               {"name": "ChuHoSo_HoTen", "value": "Trần Văn Bình"}, {"name": "ChuHoSo_SoDinhDanh", "value": "012080000222"},
               {"name": "ChuHoSo_DienThoai", "value": "038.649.7941"}, {"name": "ChuHoSo_NgayCap", "value": "02/08/2024"}]
    fields, _ = mapper.enrich(compact, {"submitterMode": "owner_as_submitter"})
    by = {f["name"]: f["value"] for f in fields}
    assert by["data[phoneNumber]"] == "0386497941"
    assert by["data[ownerIdIssuePlace]"] == mapper.default_issuer("28/06/2021")
    assert by["data[idIssuePlace]"] == "Bộ Công an"
    assert mapper._phone("0912 345 67") is None


def test_ngay_cap_uu_tien_giay_in_hon_dong_viet_tay():
    from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.thanh_tra import dinh_danh

    docs = [{"text": "TỜ KHAI ĐỀ NGHỊ HỖ TRỢ CHI PHÍ MAI TÁNG\n1. Thông tin người đề nghị\nHọ và tên: Trần Văn Bình\n"
                     "CCCD số: 012080000222 cấp ngày 10/04/2023...Nơi cấp: Cục cảnh sát"},
            {"text": "HỢP ĐỒNG DỊCH VỤ TANG LỄ\nBên A: Trần Văn Bình\n- Giấy tờ tuỳ thân: 012080000222 Ngày cấp: 04/04/2023"}]
    pages = trang.pages(docs)
    person = dinh_danh.PERSONS[0]
    found = dinh_danh.issue_finding(person, {person.number: "012080000222", person.issued: "10/04/2023"}, pages)
    assert found and found.values == {person.issued: "04/04/2023"}
    assert dinh_danh.issue_finding(person, {person.number: "012080000222", person.issued: "04/04/2023"}, pages) is None


def test_chi_tiet_dia_chi_cat_phan_hanh_chinh_va_so_cung_noi():
    assert dia_chi._admin_tail("Tổ dân phố Mẫu A, phường Mẫu Xã, TP Mẫu") == ("Tổ dân phố Mẫu A", "Mẫu Xã")
    assert dia_chi._admin_tail("Thôn Quan Mẫu 2") == ("Thôn Quan Mẫu 2", "")  # "Quan" không phải "Quận"
    assert not dia_chi._same_place("Thôn Mẫu 2", "TDP Mẫu 4")
    assert dia_chi._same_place("Thôn Lực thanh", "Thôn Lục Thanh")


def test_ngay_cap_tinh_ca_dong_trong_khoi_to_khai_cua_nguoi_do():
    from app.pipelines._shared.thanh_tra.ho_so import Case
    from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.thanh_tra import dinh_danh

    # Số CCCD trên tờ khai bị OCR làm hỏng: hai dòng "ngày cấp" trong khối người đề nghị vẫn là nguồn của người này.
    to_khai = _MAU_03.replace("Số căn cước/định danh cá nhân: 012080000222",
                              "Số căn cước/định danh cá nhân: 0120800 ngày cấp: 12/08/2021")
    to_khai = to_khai.replace("Họ và tên: Trần Văn Bình\nNơi cư trú: Tổ 5, phường Mẫu",
                              "Họ và tên: Trần Văn Bình\nSố căn cước: 01208 ngày cấp: 12/08/2021\nNơi cư trú: Tổ 5, phường Mẫu")
    values = {"ChuHoSo_HoTen": "Trần Văn Bình", "ChuHoSo_SoDinhDanh": "012080000222", "ChuHoSo_NgayCap": "12/09/2021"}
    found = [f for f in dinh_danh.findings_from(Case([{"text": to_khai}], "", values)) if f.unit.key.endswith("ngay_cap")]
    assert found and found[0].values == {"ChuHoSo_NgayCap": "12/08/2021"}


def test_chi_tiet_dinh_ten_xa_khong_dau_phay_thi_cat():
    assert dia_chi._cut_before_ward("Lộc thanh Mẫu Xã quân ngãi", "Mẫu Xã") == "Lộc thanh"
    assert dia_chi._cut_before_ward("Thôn Mẫu Xã", "Mẫu Xã") == ""  # tên thôn trùng tên xã, không có tỉnh phía sau
    assert dia_chi._admin_like("Mẫu Xã Quân ngãi", "Mẫu Xã")
