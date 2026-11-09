"""Pipeline "Tiếp nhận đối tượng cần bảo vệ khẩn cấp vào cơ sở trợ giúp xã hội" (1.116908, NĐ 335/2026/NĐ-CP):
người giám hộ là người nộp, đối tượng là chủ hồ sơ; đính kèm 2 dòng (Tờ khai Mẫu số 04, Biên bản tiếp nhận).
Dữ liệu trong test là ví dụ bịa."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.attach import planner as ap
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process import mapper
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process import runner as process_runner
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process.prompt import EXTRA_RULES
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process.schema import FIELDS
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "tiep-nhan-doi-tuong-can-bao-ve-khan-cap-vao-co-so-tro-giup-xa-hoi"
_DECLARATION_MODE = {"submitterMode": "owner_as_submitter"}


def _result(fields, options=None):
    return mapper.enrich([{"name": name, "value": value} for name, value in fields.items()], options)


def _mapped(fields, options=None):
    result, warnings = _result(fields, options)
    return {f["name"]: f["value"] for f in result if not f.get("clear")}, warnings


def _cleared(fields, options=None):
    result, _ = _result(fields, options)
    return {f["name"] for f in result if f.get("clear")}


def _subject():
    # Trẻ khuyết tật cần bảo vệ khẩn cấp: tờ khai mục I.4 ghi không có số điện thoại.
    return {
        "DoiTuong_HoTen": "ĐỖ THU TRANG",
        "DoiTuong_NgaySinh": "09/06/2014",
        "DoiTuong_GioiTinh": "Nữ",
        "DoiTuong_SoDinhDanh": "075314007788",
        "DoiTuong_NgayCap": "10/02/2025",
        "DoiTuong_NoiCap": "BỘ CÔNG AN",
        "DoiTuong_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "thành phố Đồng Nai", "xa": "phường Biên Hòa",
                              "diaChi": "Tổ 8, khu phố Tân Mai 3"},
        "DoiTuong_NoiOHienNay": "Đang tạm lánh tại nhà dì ruột – Số 45, khu phố Long Bình, phường Biên Hòa",
        "DoiTuong_DienThoai": "Không có (liên hệ qua người giám hộ)",
        "DoiTuong_NhomDoiTuong": "Người khuyết tật nặng, đặc biệt nặng; Đối tượng cần bảo vệ khẩn cấp",
        "DoiTuong_MucDoKhuyetTat": "Nặng",
    }


def _guardian():
    return {
        **_subject(),
        "NguoiNop_HoTen": "PHAN THỊ HẠNH",
        "NguoiNop_NgaySinh": "15/05/1970",
        "NguoiNop_GioiTinh": "Nữ",
        "NguoiNop_SoDinhDanh": "075170009911",
        "NguoiNop_NgayCap": "05/09/2024",
        "NguoiNop_NoiCap": "Bộ Công an",
        "NguoiNop_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "", "xa": "Phường Biên Hòa",
                              "diaChi": "Số 45, khu phố Long Bình"},
        "NguoiNop_DienThoai": "0903 123 456",
    }


def test_nguoi_giam_ho_la_nguoi_nop_doi_tuong_la_chu_ho_so():
    ui, warnings = _mapped(_guardian(), _DECLARATION_MODE)

    assert not warnings
    assert ui["data[chonDoiTuong]"] == "Cá nhân"
    assert ui["data[fullname]"] == "PHAN THỊ HẠNH"
    assert ui["data[identityNumber]"] == "075170009911"
    assert ui["data[birthday]"] == "15/05/1970"
    assert ui["data[idIssuePlace]"] == "Bộ Công an"
    # Tỉnh của người giám hộ suy từ cùng phường của đối tượng; nhãn đúng danh mục (Đồng Nai là thành phố).
    assert ui["data[province]"] == "Thành phố Đồng Nai"
    assert ui["data[address]"] == "Số 45, khu phố Long Bình"
    assert ui["data[phoneNumber]"] == "0903123456"
    assert ui["data[isOwnerDossierCheck]"] is False
    assert ui["data[ownerFullname]"] == "ĐỖ THU TRANG"
    assert ui["data[ownerIdentityNumber]"] == "075314007788"
    assert ui["data[ownerIdIssuePlace]"] == "Bộ Công an"
    assert ui["data[ownerProvince]"] == "Thành phố Đồng Nai"
    assert ui["data[ownerDistrict]"] == "Phường Biên Hòa"
    assert ui["data[ownerAddress]"] == "Tổ 8, khu phố Tân Mai 3"
    assert ui["data[ownerNation]"] == "Việt Nam"


def test_doi_tuong_khong_co_sdt_thi_dung_sdt_nguoi_giam_ho():
    ui, _ = _mapped(_guardian(), _DECLARATION_MODE)
    assert ui["data[ownerPhoneNumber]"] == "0903123456"


def test_ghi_chu_nhom_doi_tuong_va_noi_o_hien_nay():
    ui, _ = _mapped(_guardian(), _DECLARATION_MODE)
    assert ui["data[ghiChu]"] == (
        "Đối tượng cần bảo vệ khẩn cấp; người khuyết tật nặng (Tờ khai Mẫu số 04 mục I.7). "
        "Nơi ở hiện nay: Đang tạm lánh tại nhà dì ruột – Số 45, khu phố Long Bình, phường Biên Hòa."
    )


def test_noi_o_hien_nay_trung_noi_cu_tru_thi_khong_ghi_lai():
    ui, _ = _mapped({**_guardian(), "DoiTuong_NoiOHienNay": "Tổ 8, khu phố Tân Mai 3, phường Biên Hòa"},
                    _DECLARATION_MODE)
    assert "Nơi ở hiện nay" not in ui["data[ghiChu]"]


def test_khong_doc_duoc_nhom_doi_tuong_chi_ghi_dieu_kien_thu_tuc():
    fields = {k: v for k, v in _guardian().items()
              if k not in ("DoiTuong_NhomDoiTuong", "DoiTuong_MucDoKhuyetTat", "DoiTuong_NoiOHienNay")}
    ui, _ = _mapped(fields, _DECLARATION_MODE)
    assert ui["data[ghiChu]"] == "Đối tượng cần bảo vệ khẩn cấp."


def test_nhom_tre_em_va_nguoi_tu_du_16_tuoi_khong_lan():
    assert mapper._groups_note("Trẻ em dưới 16 tuổi không có nguồn nuôi dưỡng", None) == (
        "Đối tượng cần bảo vệ khẩn cấp; trẻ em dưới 16 tuổi không có nguồn nuôi dưỡng")
    assert mapper._groups_note("Người từ đủ 16 tuổi không có nguồn nuôi dưỡng đang đi học", None) == (
        "Đối tượng cần bảo vệ khẩn cấp; người từ đủ 16 tuổi không có nguồn nuôi dưỡng đang đi học")
    assert mapper._groups_note(["Người khuyết tật nặng, đặc biệt nặng"], "Đặc biệt nặng") == (
        "Đối tượng cần bảo vệ khẩn cấp; người khuyết tật đặc biệt nặng")


def test_bien_ban_chi_ghi_nam_sinh_thi_khong_tu_dien_ngay():
    fields = {**_guardian(), "DoiTuong_NgaySinh": "2014"}
    ui, warnings = _mapped(fields, _DECLARATION_MODE)

    assert "data[ownerBirthday]" not in ui
    # Ô ngày sinh chủ hồ sơ còn giữ ngày sinh người nộp do cổng chép sang → phải xoá trống.
    assert "data[ownerBirthday]" in _cleared(fields, _DECLARATION_MODE)
    assert any("2014" in w and "xác minh" in w for w in warnings)


def test_doi_tuong_chua_co_the_thi_xoa_o_dinh_danh_chu_ho_so():
    fields = {k: v for k, v in _guardian().items()
              if k not in ("DoiTuong_SoDinhDanh", "DoiTuong_NgayCap", "DoiTuong_NoiCap")}
    ui, _ = _mapped(fields, _DECLARATION_MODE)

    assert "data[ownerIdentityNumber]" not in ui
    assert {"data[ownerIdentityNumber]", "data[ownerIdentityDate]", "data[ownerIdIssuePlace]"} <= _cleared(
        fields, _DECLARATION_MODE)


def test_khong_co_email_thi_xoa_o_email():
    assert {"data[email]", "data[ownerEmail]"} <= _cleared(_guardian(), _DECLARATION_MODE)


def test_tai_khoan_khop_nguoi_giam_ho_lay_ten_va_so_theo_tai_khoan():
    options = {"formContext": {"applicantFullname": "Phan Thị Hạnh", "applicantIdentityNumber": "075170009911"}}
    ui, warnings = _mapped(_guardian(), options)

    assert not warnings
    assert ui["data[fullname]"] == "Phan Thị Hạnh"
    assert ui["data[identityDate]"] == "05/09/2024"
    assert ui["data[ownerFullname]"] == "ĐỖ THU TRANG"
    # Chế độ theo tài khoản không xoá ô Phần I cổng đổ sẵn.
    assert "data[birthday]" not in _cleared({k: v for k, v in _guardian().items() if k != "NguoiNop_NgaySinh"},
                                            options)


def test_tai_khoan_khong_co_trong_ho_so_chi_dien_ten_va_so():
    ui, warnings = _mapped(_guardian(), {
        "formContext": {"applicantFullname": "Vũ Minh Khoa", "applicantIdentityNumber": "075088012345"}
    })

    assert ui["data[fullname]"] == "Vũ Minh Khoa"
    assert ui["data[identityNumber]"] == "075088012345"
    for leaked in ("data[birthday]", "data[identityDate]", "data[address]"):
        assert leaked not in ui
    assert warnings and "075088012345" in warnings[0]


def test_cai_dat_nguoi_nop_theo_to_khai_bo_moc_tai_khoan_va_xoa_o_tai_khoan_do_san():
    # Bật "Lấy người nộp theo tờ khai": FE vẫn gửi mốc tài khoản nhưng BE lấy người giám hộ ở mục II.
    options = {**_DECLARATION_MODE,
               "formContext": {"applicantFullname": "Vũ Minh Khoa", "applicantIdentityNumber": "075088012345"}}
    fields = {k: v for k, v in _guardian().items() if k not in ("NguoiNop_NgaySinh", "NguoiNop_NgayCap")}
    ui, warnings = _mapped(fields, options)

    assert not warnings
    assert ui["data[fullname]"] == "PHAN THỊ HẠNH"
    assert ui["data[identityNumber]"] == "075170009911"
    assert {"data[birthday]", "data[identityDate]"} <= _cleared(fields, options)
    assert "data[idIssuePlace]" not in _cleared(fields, options)


def test_cai_dat_nguoi_nop_theo_to_khai_thieu_so_dinh_danh_thi_canh_bao():
    _, warnings = _mapped({**_guardian(), "NguoiNop_SoDinhDanh": "07517000991"}, _DECLARATION_MODE)
    assert any("PHAN THỊ HẠNH" in w and "CC/CCCD" in w for w in warnings)


def test_khong_co_nguoi_giam_ho_thi_doi_tuong_tu_nop():
    ui, warnings = _mapped({**_subject(), "DoiTuong_DienThoai": "0987000111"}, _DECLARATION_MODE)

    assert not warnings
    assert ui["data[fullname]"] == "ĐỖ THU TRANG"
    assert ui["data[phoneNumber]"] == "0987000111"
    assert ui["data[ownerFullname]"] == "ĐỖ THU TRANG"


async def test_runner_mo_khoa_o_ho_ten_va_cccd_khi_theo_to_khai(monkeypatch):
    async def fake_run(files_by_role, **kwargs):
        return {"fields": [{"name": k, "value": v} for k, v in _guardian().items()], "errors": []}

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    res = await process_runner.run({}, _DECLARATION_MODE)

    unlocked = {f["name"] for f in res["fields"] if f.get("enableInput")}
    assert unlocked == {"data[fullname]", "data[identityNumber]"}
    res = await process_runner.run({}, {})
    assert not any(f.get("enableInput") for f in res["fields"])


def test_prompt_noi_ro_muc_ii_nguoi_giam_ho_va_nguoi_tiep_nhan():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    assert "Nghị định" in system_prompt and "335/2026/NĐ-CP" in system_prompt
    assert "Thông tin người giám hộ" in system_prompt
    assert "NGƯỜI TIẾP NHẬN TỜ KHAI" in system_prompt
    assert "đúng 9 hoặc 12 chữ số" in system_prompt


# ── Đính kèm: dòng 1 Tờ khai Mẫu số 04, dòng 2 Biên bản tiếp nhận; CCCD không có dòng → không đính. ──

_TK04_TEXT = (
    "Mẫu số 04 TỜ KHAI ĐỀ NGHỊ CHĂM SÓC, NUÔI DƯỠNG TẠI CƠ SỞ TRỢ GIÚP XÃ HỘI I. Thông tin của người đề nghị "
    "được chăm sóc, nuôi dưỡng Số căn cước Giấy xác nhận khuyết tật số 0123 NGƯỜI TIẾP NHẬN TỜ KHAI"
)
_BB_TEXT = (
    "BIÊN BẢN TIẾP NHẬN ĐỐI TƯỢNG CẦN BẢO VỆ KHẨN CẤP Đại diện Công an xã, đại diện cơ sở trợ giúp xã hội; "
    "đối tượng đã ký tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội"
)
_CCCD_TEXT = "CĂN CƯỚC CÔNG DÂN Số định danh cá nhân Họ, chữ đệm và tên khai sinh"
_GXN_TEXT = "GIẤY XÁC NHẬN KHUYẾT TẬT Dạng khuyết tật Mức độ khuyết tật: Nặng"


def _files(*names):
    return [{"name": n, "type": "application/pdf", "dataUrl": ""} for n in names]


def test_to_khai_dong_1_bien_ban_dong_2_cccd_khong_dinh():
    files = _files("cccd_tre.pdf", "bien_ban.pdf", "to_khai.pdf", "cccd_di.pdf", "gxn.pdf")
    ocr = [
        {"name": "cccd_tre.pdf", "text": _CCCD_TEXT},
        {"name": "bien_ban.pdf", "text": _BB_TEXT},
        {"name": "to_khai.pdf", "text": _TK04_TEXT},
        {"name": "cccd_di.pdf", "text": _CCCD_TEXT},
        {"name": "gxn.pdf", "text": _GXN_TEXT},
    ]
    items, warnings, classified = ap.build_plan_items(files, ocr, {})

    assert not warnings
    assert [(i["fileName"], i["componentName"], i["documentName"]) for i in items] == [
        ("to_khai.pdf", "Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội",
         "Tờ khai đề nghị chăm sóc, nuôi dưỡng (Mẫu số 04)"),
        ("bien_ban.pdf", "Biên bản tiếp nhận có chữ ký", "Biên bản tiếp nhận"),
    ]
    assert all(i["target"] == "attp-row" and i["loaiBan"] == "Scan tệp tin" for i in items)
    assert {c["fileName"]: c["docType"] for c in classified}["gxn.pdf"] == "giay_to_khac"


def test_rule_to_khai_nhac_tiep_nhan_van_la_to_khai_bien_ban_nhac_ten_to_khai_van_la_bien_ban():
    assert ap._rule_doc_type(_TK04_TEXT) == "to_khai_mau_04"
    assert ap._rule_doc_type(_BB_TEXT) == "bien_ban_tiep_nhan"
    assert ap._rule_doc_type(_CCCD_TEXT) == "can_cuoc"
    assert ap._rule_doc_type(_TK04_TEXT + " " + _BB_TEXT) == "to_khai_kem_bien_ban"


def test_tep_chung_to_khai_va_bien_ban_dinh_ca_hai_dong():
    files = _files("ho_so.pdf")
    items, warnings, _ = ap.build_plan_items(files, [{"name": "ho_so.pdf", "text": "noi dung"}],
                                             {0: "to_khai_kem_bien_ban"})

    assert [(i["fileIndex"], i["componentName"]) for i in items] == [
        (0, "Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội"),
        (0, "Biên bản tiếp nhận có chữ ký"),
    ]
    assert len(warnings) == 1 and "cả hai dòng" in warnings[0]


def test_llm_goi_mot_loai_nhung_ocr_co_ca_hai_tieu_de_thi_la_tep_chung():
    files = _files("ho_so.pdf")
    items, _, classified = ap.build_plan_items(files, [{"name": "ho_so.pdf", "text": _TK04_TEXT + " " + _BB_TEXT}],
                                               {0: "to_khai_mau_04"})
    assert len(items) == 2
    assert classified[0]["docType"] == "to_khai_kem_bien_ban"


def test_thieu_bien_ban_thi_canh_bao_scan_bo_sung():
    files = _files("to_khai.pdf", "cccd.pdf")
    ocr = [{"name": "to_khai.pdf", "text": _TK04_TEXT}, {"name": "cccd.pdf", "text": _CCCD_TEXT}]
    items, warnings, _ = ap.build_plan_items(files, ocr, {})

    assert [i["fileName"] for i in items] == ["to_khai.pdf"]
    assert len(warnings) == 1 and "chưa có Biên bản tiếp nhận" in warnings[0]


def test_nhieu_trang_to_khai_cung_dong_va_tep_la_khong_dinh():
    files = _files("tk_1.jpg", "tk_2.jpg", "mo.pdf", "bb.pdf")
    ocr = [{"name": "mo.pdf", "text": "khong ro"}]
    items, warnings, classified = ap.build_plan_items(
        files, ocr, {0: "to_khai_mau_04", 1: "to_khai_mau_04", 2: "other", 3: "bien_ban_tiep_nhan"})

    assert [i["documentName"] for i in items] == [
        "Tờ khai đề nghị chăm sóc, nuôi dưỡng (Mẫu số 04)", "Tờ khai đề nghị chăm sóc, nuôi dưỡng (Mẫu số 04) 2",
        "Biên bản tiếp nhận",
    ]
    assert "mo.pdf" not in [i["fileName"] for i in items]
    assert len(warnings) == 1 and "mo.pdf" in warnings[0]
    assert classified[0]["source"] == "llm"


def test_normalize_doc_type_tu_llm():
    assert ap._normalize_doc_type("to_khai_mau_04") == "to_khai_mau_04"
    assert ap._normalize_doc_type("bien_ban_tiep_nhan") == "bien_ban_tiep_nhan"
    assert ap._normalize_doc_type("to_khai_kem_bien_ban") == "to_khai_kem_bien_ban"
    assert ap._normalize_doc_type("can_cuoc") == "can_cuoc"
    assert ap._normalize_doc_type("giay_to_khac") == "giay_to_khac"
    assert ap._normalize_doc_type("xyz") == "other"


async def test_plan_goi_ocr_va_llm(monkeypatch):
    from app.process.schemas import FileItem
    from app.services import ocr as ocr_service

    async def fake_ocr(_files):
        return [{"name": "a.pdf", "text": _CCCD_TEXT}, {"name": "b.pdf", "text": _TK04_TEXT},
                {"name": "c.pdf", "text": _BB_TEXT}]

    async def fake_classify(_docs, _system_prompt=None):
        return {0: "can_cuoc", 1: "to_khai_mau_04", 2: "bien_ban_tiep_nhan"}

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(ap, "_classify_with_llm", fake_classify)

    files = [FileItem(name=n, type="application/pdf", dataUrl="data:application/pdf;base64,QUJD", role="attachment")
             for n in ("a.pdf", "b.pdf", "c.pdf")]
    result = await ap.plan(files, {}, None)

    assert [a["fileName"] for a in result["attachments"]] == ["b.pdf", "c.pdf"]
    assert result["extracted"]["notAttached"] == ["a.pdf"]
    assert not result["errors"]


# ── Registry lõi, link kê khai và trợ lý người dân ──

def test_registry_va_nhan_dien_khong_trung_thu_tuc_anh_em():
    from app.procedures import registry

    assert get_pipeline(_KEY) is process_runner.run
    assert get_attach_pipeline(_KEY) is ap.plan
    phrase = registry._BY_KEY[_KEY]["detect"]["textIncludes"][0].lower()
    assert phrase in get_procedure(_KEY)["label"].lower()
    # 1.116907 (cùng Mẫu số 04) và 1.116909 (cùng cổng) không chứa cụm nhận diện.
    for code in ("1.116907", "1.116909"):
        other = next(link for link in KE_KHAI_LINKS if link.get("code") == code)
        assert phrase not in other["label"].lower()


def test_ke_khai_link_trung_key_va_chon_phuong_xa():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    link = links[0]
    assert link["code"] == "1.116908"
    assert link["needsAgencySelect"] is True
    assert not link.get("provinceOnlyAgency") and not link.get("selectSo")


def test_tro_ly_dung_pipeline_loi_va_link_ke_khai():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert procedure["label"] == get_procedure(_KEY)["label"]
    assert procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.116908"
    assert not procedure.get("provinceOnly")
    assert procedure["detect"]["urlScope"] == ["dichvucongbyt.moh.gov.vn"]
    assert procedure["bxdFlow"]["resultGroups"][0]["name"] == "receivingKind"
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert field_review.get(_KEY)["noAsk"] == ("ghiChu",)
    assert PROCEDURE_HINTS[_KEY] and PROCEDURE_HMONG[_KEY]
