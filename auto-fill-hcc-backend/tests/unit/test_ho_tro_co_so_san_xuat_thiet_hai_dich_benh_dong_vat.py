"""Mapper/attach/registry tests cho thủ tục hỗ trợ cơ sở sản xuất bị thiệt hại do dịch bệnh động vật (1.013997)."""

from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat import process as agent
from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat.attach import planner
from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat.process import mapper
from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat.process.schema import (
    ALLOWED,
    UI_COMP_BY_NAME,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat"


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _values(mapped: list[dict]) -> dict:
    return {field["name"]: field["value"] for field in mapped}


def _reports():
    return [
        {"so": "12/BBTH", "ngay": "5/9/2026", "doiTuong": [{"ten": "Lợn thịt", "soLuong": "01 con", "khoiLuong": "60 kg"}],
         "tongSoLuong": "01", "tongKhoiLuong": "60"},
        {"so": "20/BBTH", "ngay": "18/09/2026", "doiTuong": [{"ten": "Lợn nái", "soLuong": "01", "khoiLuong": "110"}],
         "tongSoLuong": "01", "tongKhoiLuong": "110"},
    ]


def test_registered_with_ke_khai_link_key():
    procedure = get_procedure(KEY)

    assert procedure
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert get_pipeline(KEY) is agent.run
    assert get_attach_pipeline(KEY) is planner.plan
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.013997"
    assert link["needsAgencySelect"] is True


def test_owner_differs_from_account_fills_part_two_and_note():
    fields = [
        _field("ChuHo_HoTen", "Lò Văn An"),
        _field("ChuHo_DanhXung", "Ông"),
        _field("ChuHo_ThuongTru", {"quocGia": "Việt Nam", "tinh": "tỉnh Lai Châu", "xa": "xã Bình Lư",
                                   "diaChi": "Bản Đông"}),
        _field("DichBenh_Ten", "Bệnh Dịch tả lợn Châu Phi"),
        _field("BienBan_DanhSach", _reports()),
    ]
    options = {"formContext": {"applicantFullname": "Trần Thị Bình", "applicantIdentityNumber": "001190012345"}}

    mapped, warnings = mapper.enrich(fields, options)
    values = _values(mapped)

    assert mapped[0]["name"] == "data[chonDoiTuong]"
    assert values["data[chonDoiTuong]"] == "Cá nhân"
    assert "data[fullname]" not in values
    assert "data[isOwnerDossierCheck]" not in values
    assert values["data[ownerFullname]"] == "Lò Văn An"
    assert values["data[ownerGender]"] == "Nam"
    assert values["data[ownerProvince]"] == "Tỉnh Lai Châu"
    assert values["data[ownerDistrict]"] == "Xã Bình Lư"
    assert values["data[ownerAddress]"] == "Bản Đông"
    assert values["data[ownerNation]"] == "Việt Nam"
    assert values["data[ghiChu]"] == (
        "Bệnh Dịch tả lợn Châu Phi – Biên bản tiêu hủy số 12/BBTH ngày 05/09/2026: Lợn thịt 01 con, 60 kg"
        " – Biên bản tiêu hủy số 20/BBTH ngày 18/09/2026: Lợn nái 01 con, 110 kg"
        " – Cộng 2 biên bản: 02 con, 170 kg"
    )
    assert any("Tài khoản nộp khác chủ hộ" in w for w in warnings)
    # Cổng đổ sẵn ngày sinh/CCCD của tài khoản vào Phần II: Biên bản không có thì phải xoá trắng, không để lại.
    cleared = {field["name"] for field in mapped if field.get("clear")}
    assert {"data[ownerBirthday]", "data[ownerIdentityNumber]", "data[ownerIdentityDate]",
            "data[ownerIdIssuePlace]", "data[ownerPhoneNumber]", "data[ownerEmail]"} <= cleared
    assert all(field["value"] == "" for field in mapped if field.get("clear"))
    assert "data[ownerFullname]" not in cleared
    assert any("Ngày sinh, CC/CCCD/CMND" in w for w in warnings)
    assert all(field["comp"] == UI_COMP_BY_NAME[field["name"]] for field in mapped)


def test_owner_is_account_fills_part_one_and_ticks_owner_check():
    fields = [
        _field("ChuHo_HoTen", "LÒ VĂN AN"),
        _field("ChuHo_SoDinhDanh", "012 089 001234"),
        _field("ChuHo_NgayCap", "06/8/2023"),
        _field("ChuHo_NoiCap", "Cục Cảnh sát quản lý hành chính về trật tự xã hội"),
        _field("ChuHo_ThuongTru", "Bản Đông, xã Bình Lư, tỉnh Lai Châu"),
        _field("ChuHo_DienThoai", "0912 345 678"),
        _field("Cccd1_HoTen", "Lò Văn An"),
        _field("Cccd1_SoDinhDanh", "012089001234"),
        _field("Cccd1_NgaySinh", "02/03/1989"),
        _field("Cccd1_GioiTinh", "Nam"),
        _field("BienBan_DanhSach", _reports()[:1]),
    ]
    options = {"formContext": {"applicantFullname": "Lò Văn An", "applicantIdentityNumber": "012089001234"}}

    values = _values(mapper.enrich(fields, options)[0])

    assert values["data[fullname]"] == "Lò Văn An"
    assert values["data[birthday]"] == "02/03/1989"
    assert values["data[gender]"] == "Nam"
    assert values["data[identityNumber]"] == "012089001234"
    assert values["data[identityDate]"] == "06/08/2023"
    assert values["data[province]"] == "Tỉnh Lai Châu"
    assert values["data[address]"] == "Bản Đông"
    assert values["data[phoneNumber]"] == "0912345678"
    assert values["data[isOwnerDossierCheck]"] is True
    assert not any(name.startswith("data[owner") for name in values)
    assert "Cộng" not in values["data[ghiChu]"]


def test_account_name_matches_but_identity_differs_keeps_part_one():
    fields = [_field("ChuHo_HoTen", "Lò Văn An"), _field("ChuHo_SoDinhDanh", "012089001234")]
    options = {"formContext": {"applicantFullname": "Lò Văn An", "applicantIdentityNumber": "012089009999"}}

    values = _values(mapper.enrich(fields, options)[0])

    assert "data[isOwnerDossierCheck]" not in values
    assert values["data[ownerIdentityNumber]"] == "012089001234"


def test_organization_only_with_name_and_tax_code():
    base = [_field("ChuHo_HoTen", "Lò Văn An"), _field("CoSo_Ten", "Trang trại Đông Sơn")]
    assert _values(mapper.enrich(base, {})[0])["data[chonDoiTuong]"] == "Cá nhân"

    values = _values(mapper.enrich(base + [_field("CoSo_MaSoThue", "6200123456")], {})[0])
    assert values["data[chonDoiTuong]"] == "Tổ chức/Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "Trang trại Đông Sơn"
    assert values["data[ownerTaxCode]"] == "6200123456"


def test_schema_has_report_list_field():
    assert "BienBan_DanhSach" in ALLOWED
    assert "data[ghiChu]" in UI_COMP_BY_NAME


def _seg(file_index, page_from, page_to, doc_type):
    return {"fileIndex": file_index, "pageFrom": page_from, "pageTo": page_to, "type": doc_type, "documentName": ""}


def test_attach_merges_reports_into_single_don_row_and_warns_missing_don():
    files = [{"name": "bien-ban.pdf", "type": "application/pdf"}]
    segments = [_seg(0, 1, 2, "bien_ban_tieu_huy"), _seg(0, 3, 3, "bien_ban_tieu_huy")]
    meta = {0: {"pageCount": 3, "pageBoundariesAvailable": True}}

    attachments, classified, warnings = planner.build_plan_items(files, segments, meta, {0: {}})

    assert len(attachments) == 1
    item = attachments[0]
    assert item["target"] == "attp-row"
    assert item["componentName"].startswith("Đơn đề nghị hỗ trợ")
    assert item["loaiBan"] == "Bản chính"
    assert item["includedTypes"] == ["bien_ban_tieu_huy"]
    assert item["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": None}]
    assert any("Chưa có Đơn đề nghị" in w for w in warnings)
    assert len(classified) == 1


def test_attach_puts_don_first_and_skips_cccd():
    files = [{"name": "ho-so.pdf", "type": "application/pdf"}, {"name": "don.pdf", "type": "application/pdf"}]
    segments = [_seg(0, 1, 2, "bien_ban_tieu_huy"), _seg(0, 3, 3, "cccd"), _seg(1, 1, 1, "don_de_nghi")]
    meta = {0: {"pageCount": 3, "pageBoundariesAvailable": True}, 1: {"pageCount": 1, "pageBoundariesAvailable": True}}

    attachments, classified, warnings = planner.build_plan_items(files, segments, meta, {0: {}, 1: {}})

    item = attachments[0]
    assert item["fileIndex"] == 1
    assert item["includedTypes"] == ["don_de_nghi", "bien_ban_tieu_huy"]
    assert item["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": None}, {"fileIndex": 0, "pageIndexes": [0, 1]}]
    assert any(c["type"] == "cccd" and c["attached"] is False for c in classified)
    assert warnings == []


def test_attach_rule_type_fallback():
    assert planner._rule_type("ĐƠN ĐỀ NGHỊ Hỗ trợ thiệt hại do dịch bệnh động vật trên cạn") == "don_de_nghi"
    assert planner._rule_type("UBND XÃ\nBIÊN BẢN Tiêu hủy động vật, sản phẩm động vật trên cạn") == "bien_ban_tieu_huy"
    assert planner._normalize_type("Biên bản tiêu hủy") == "bien_ban_tieu_huy"
