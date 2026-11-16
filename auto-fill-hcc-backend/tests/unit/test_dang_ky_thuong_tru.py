"""Đăng ký thường trú (Cổng DVC Bộ Công an): mapper ô form + nối registry + luồng trợ lý."""
from app.channels.handfree.chat import flow
from app.channels.handfree.chat.intents import Intent
from app.pipelines.dang_ky_thuong_tru.process import mapper
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "dang-ky-thuong-tru"
PERSON = {
    "CoQuan_Tinh": "Hà Nội", "CoQuan_Xa": "Phường Ba Đình",
    "TruongHop": "nhân khẩu", "HinhThuc": "vào hộ đã có",
    "NguoiDangKy_HoTen": "Tran Thi B", "NguoiDangKy_NgaySinh": "5/3/1998", "NguoiDangKy_GioiTinh": "Nữ",
    "NguoiDangKy_SoDinhDanh": "0011 9800 0002", "NguoiDangKy_SoDienThoai": "0912 345 678",
    "ChuHo_HoTen": "Nguyen Van A", "ChuHo_QuanHe": "Vợ", "ChuHo_SoDinhDanh": "001090000001",
    "NoiDangKy_DiaChiChiTiet": "Số 1 ngõ 2, phường Ba Đình, thành phố Hà Nội",
    "NoiDungDeNghi": "Đăng ký thường trú vào hộ chồng",
    "ThanhVien": [{"hoTen": "Nguyen Van C", "ngaySinh": "1/2/2023", "gioiTinh": "Nam", "soDinhDanh": "001223000003",
                   "quanHeVoiChuHo": "Con"}],
}


def _enrich(values: dict, options=None) -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def test_thu_tu_va_gia_tri_o_form():
    out = _enrich(PERSON)
    by = {f["name"]: f for f in out}
    names = [f["name"] for f in out]
    # Cơ quan → Trường hợp → Hình thức trước khối người đề nghị; định dạng trước ngày sinh; nội dung sau địa chỉ.
    assert names[:3] == ["cboORG", "cboBPROC_CASE_CODE", "radIsHouseHold"]
    assert names.index("cboFORMAT_DATE") < names.index("txtBIRTH_DATE") < names.index("txtFULLNAME")
    assert names.index("txtSUGGEST_DETAIL_ADDR") < names.index("txtCHANGED_CONTENT_NOTE")
    agency = by["cboORG"]
    assert agency["comp"] == "bca-agency" and agency["onlyIfEmpty"] is True
    assert agency["value"] == {"province": "Thành phố Hà Nội", "ward": "Phường Ba Đình",
                               "cityId": "cboRECEIVE_ADDR_CITY_ID", "wardId": "cboRECEIVE_ADDR_VILLAGE_ID",
                               "readySelect": "cboBPROC_CASE_CODE"}
    assert by["cboBPROC_CASE_CODE"]["value"] == "Đăng ký thường trú nhân khẩu"
    assert by["radIsHouseHold"]["value"] == "Đăng ký thường trú vào hộ đã có"
    assert by["txtBIRTH_DATE"]["value"] == "05/03/1998" and by["cboFORMAT_DATE"]["value"] == "Ngày tháng năm"
    assert by["txtID_CARD_NUMBER"]["value"] == "001198000002"
    assert by["txtSUGGEST_DETAIL_ADDR"]["value"] == "Số 1 ngõ 2"
    assert by["cboRELATIONSHIP_WITH_HHHEAD_ID"]["value"] == "Vợ"
    rows = by["tblNguoi_CUNGTD"]["value"]["rows"]
    assert {c["id"]: c["value"] for c in rows[0]} == {
        "txtFULLNAME_CUNGTD0": "NGUYEN VAN C", "txtDOB_CUNGTD0": "01/02/2023", "cboGENDER_CUNGTD0": "Nam",
        "txtIDENTIFIER_NOCARD_NUMBER_CUNGTD0": "001223000003", "cboRELATIONSHIP_CHUHO_CUNGTD0": "Con"}


def test_lap_ho_moi_khong_dien_khoi_chu_ho():
    out = {f["name"]: f["value"] for f in _enrich({**PERSON, "HinhThuc": "lập hộ mới", "ChuHo_QuanHe": "Chủ hộ"})}
    assert out["radIsHouseHold"] == "Đăng ký thường trú lập hộ mới"
    assert not {"txtHH_HEAD_FULLNAME", "cboRELATIONSHIP_WITH_HHHEAD_ID", "txtID_CARD_NUMBER_HHEAD"} & set(out)


def test_lan_dau_thi_cong_ep_vao_ho_da_co():
    out = {f["name"]: f["value"] for f in _enrich({**PERSON, "TruongHop": "lần đầu", "HinhThuc": "lập hộ mới"})}
    assert out["radIsHouseHold"] == "Đăng ký thường trú vào hộ đã có"


def test_giay_khong_ghi_co_quan_thi_lay_xa_tai_khoan_to_vang():
    values = {k: v for k, v in PERSON.items() if not k.startswith("CoQuan_")}
    options = mapper.with_account_process_options({}, {"tinh": "Tỉnh Mẫu", "xa": "Phường Mẫu"}, KEY)
    agency = next(f for f in _enrich(values, options) if f["name"] == "cboORG")
    assert agency["value"]["ward"] == "Phường Mẫu" and agency["default"] is True


def test_registry_link_va_entry_handfree():
    from app.channels.handfree.procedure_registry import get_procedure

    assert registry.get_pipeline(KEY) is not None
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.004222" and get_procedure(KEY)["keKhaiUrl"] == link["url"]
    hf = get_procedure(KEY)
    assert hf["submitCommitCheckbox"] == "chkRULE" and hf["requiresCapability"] == "supportsBcaThuongTru"


def test_tro_ly_ban_cu_thi_bao_cap_nhat_ban_moi_hoi_noi_dang_ky_thuong_tru():
    conv = {"state": "greet", "procedure_key": None, "location": {}}
    r = flow._to_confirm_procedure(conv, KEY)
    assert "chưa hỗ trợ" in r.display_md
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": {"supportsBcaThuongTru": True},
            "location": {"province": "Thành phố Hà Nội", "province_slug": "ha_noi", "ward": "Phường Ba Đình"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert "nơi đăng ký thường trú" in r.display_md and "tạm trú" not in r.display_md


def test_luat_bat_nut_nop_trang_thuong_tru():
    import re

    from app.procedures.portal_submit import portal_submit_rules

    rule = portal_submit_rules()["dichvucong.dancuquocgia.gov.vn"]
    assert re.match(rule["urlPattern"], "/portal/p/home/dang-ky-thuong-tru.html")
    assert "btn_Save_Send" in rule["buttonIds"]



# ── Đính kèm ──
from app.pipelines.dang_ky_thuong_tru.attach import planner  # noqa: E402

FILES = [{"name": n} for n in ("to-khai.pdf", "ket-hon.pdf", "khai-sinh.pdf", "cccd.jpg")]


def test_planner_nhom_chu_ho_dong_y_giay_quan_he_vao_dong_them_moi():
    llm = {"case": "consented", "documents": [
        {"index": 0, "docType": "to_khai"}, {"index": 1, "docType": "quan_he", "documentName": "Giấy chứng nhận kết hôn"},
        {"index": 2, "docType": "quan_he", "documentName": "Giấy khai sinh"}, {"index": 3, "docType": "cccd"}]}
    kinds, names, case, source = planner.resolve(len(FILES), llm)
    items, warnings, _ = planner.build_plan_items(FILES, kinds, names, case)
    assert source == "llm" and {i["groupIndex"] for i in items} == {2}
    assert [i["rowKey"] for i in items] == ["to khai thay doi thong tin cu tru", "", "", "to khai thay doi thong tin cu tru"]
    assert items[1]["newRow"] and items[1]["componentName"] == items[2]["componentName"] == "Giấy tờ chứng minh quan hệ nhân thân"
    assert items[1]["documentName"] == "Giấy chứng nhận kết hôn"
    assert len(items) == len(FILES) and "cccd.jpg" in warnings[0], "không bỏ sót tệp nào"


def test_planner_thue_muon_co_dong_hop_dong_va_dien_tich():
    llm = {"case": "rented", "documents": [{"index": 0, "docType": "hop_dong"}, {"index": 1, "docType": "dien_tich"}]}
    kinds, names, case, _ = planner.resolve(2, llm)
    items, _, _ = planner.build_plan_items(FILES[:2], kinds, names, case)
    assert [i["rowKey"] for i in items] == ["hop dong cho thue", "du dien tich nha o"] and items[0]["groupIndex"] == 3


def test_planner_llm_loi_van_dinh_du_tep_va_bao_can_bo():
    kinds, names, case, source = planner.resolve(len(FILES), {})
    items, warnings, _ = planner.build_plan_items(FILES, kinds, names, case)
    assert source == "default" and len(items) == len(FILES)
    assert all(i["rowKey"] == "to khai thay doi thong tin cu tru" for i in items)
    assert registry.get_attach_pipeline(KEY) is not None
