"""Mai táng đối tượng bảo trợ xã hội 1.116910: tờ khai Mẫu 02 / 03, lớp soát thứ hai (thanh tra định danh + địa chỉ),
điền đợt 2 Form.io và các chuẩn hoá mapper. Dữ liệu giả."""

import asyncio

from app.pipelines.ho_tro_mai_tang.process import mapper, runner
from app.pipelines.ho_tro_mai_tang.thanh_tra import dia_chi, trang
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
    entry = next(p for p in PROCEDURES if p["key"] == mapper.PROCEDURE_KEYS[0])
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
    compact = [{"name": "NguoiMat_HoTen", "value": "Trần Văn An"},
               {"name": "ChuHoSo_HoTen", "value": "Trần Văn Bính"}, {"name": "ChuHoSo_SoDinhDanh", "value": "012080000223"}]
    anchor = {"formContext": {"applicantFullname": "TRẦN VĂN BÌNH", "applicantIdentityNumber": "012080000222"}}
    by = {f["name"]: f["value"] for f in mapper.enrich(compact, anchor)[0]}
    assert by["data[isOwnerDossierCheck]"] is False and by["data[ownerFullname]"] == "Trần Văn An"
    assert by["data[identityNumber]"] == "012080000222"
    # Đơn vị khai người đề nghị làm chủ hồ sơ: khớp gần tài khoản → tích tự nộp.
    by = {f["name"]: f["value"] for f in mapper.enrich(compact, {**anchor, mapper.REQUESTER_AS_OWNER_OPTION: True})[0]}
    assert by["data[isOwnerDossierCheck]"] is True and by["data[identityNumber]"] == "012080000222"


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
    from app.pipelines.ho_tro_mai_tang.thanh_tra import dinh_danh

    docs = [{"text": "TỜ KHAI ĐỀ NGHỊ HỖ TRỢ CHI PHÍ MAI TÁNG\n1. Thông tin người đề nghị\nHọ và tên: Trần Văn Bình\n"
                     "CCCD số: 012080000222 cấp ngày 10/04/2023...Nơi cấp: Cục cảnh sát"},
            {"text": "HỢP ĐỒNG DỊCH VỤ TANG LỄ\nBên A: Trần Văn Bình\n- Giấy tờ tuỳ thân: 012080000222 Ngày cấp: 04/04/2023"}]
    pages = trang.pages(docs)
    person = dinh_danh.PERSONS[0]
    found = dinh_danh.issue_finding(person, {person.number: "012080000222", person.issued: "10/04/2023"}, pages)
    assert found and found.values == {person.issued: "04/04/2023"}
    assert dinh_danh.issue_finding(person, {person.number: "012080000222", person.issued: "04/04/2023"}, pages) is None


def test_tich_tu_nop_ghi_ca_ngay_sinh_gioi_tinh_chu_ho_so():
    org = [{"name": "ChuHoSo_HoTen", "value": "Trần Văn Bình"}, {"name": "ChuHoSo_SoDinhDanh", "value": "012080000222"},
           {"name": "ChuHoSo_NgaySinh", "value": "05/06/1980"}, {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
           {"name": "NguoiMat_HoTen", "value": "Trần Thị An"}, {"name": "NguoiMat_GioiTinh", "value": "Nữ"}]
    opts = {"formContext": {"applicantFullname": "TRẦN VĂN BÌNH", "applicantIdentityNumber": "012080000222"},
            mapper.REQUESTER_AS_OWNER_OPTION: True}
    by = {f["name"]: f["value"] for f in mapper.enrich(org, opts)[0]}
    assert by["data[isOwnerDossierCheck]"] is True
    assert by["data[ownerBirthday]"] == "05/06/1980" and by["data[ownerGender]"] == "Nam"
