from app.pipelines.dang_ky_nha_o_xa_hoi_tuyen_quang.attach.planner import build_plan_items
from app.pipelines.dang_ky_nha_o_xa_hoi_tuyen_quang.process import mapper
from app.pipelines.dang_ky_nha_o_xa_hoi_tuyen_quang.process.schema import UI_COMP_BY_NAME
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "dang-ky-nha-o-xa-hoi-tuyen-quang"


def test_registry_and_ke_khai_link_use_the_pipeline_key():
    link = next(item for item in KE_KHAI_LINKS if item.get("key") == KEY)
    assert link["code"] == "1.014632"
    assert get_procedure(KEY)["detect"]["urlScope"] == ["dvc.moc.gov.vn"]
    assert procedure_province_slugs(get_procedure(KEY)) == ["tuyenquang"]
    assert get_pipeline(KEY) is not None
    assert get_attach_pipeline(KEY) is not None


def test_mapper_fills_both_forms_and_converts_household_relations():
    fields = [
        {"name": "NguoiKeKhai_HoTen", "value": "NGUYEN VAN A"},
        {"name": "NguoiKeKhai_SoDinhDanh", "value": "001201000001"},
        {"name": "NguoiKeKhai_NgaySinh", "value": "01/02/1990"},
        {"name": "NguoiKeKhai_NgayCap", "value": "03/04/2022"},
        {"name": "NguoiKeKhai_DienThoai", "value": "0912 345 678"},
        {"name": "NguoiKeKhai_ThuongTru", "value": {
            "tinh": "Tuyên Quang", "xa": "Xã Thượng Lâm", "diaChi": "NHÀ 12, THÔN BẢN"},
        },
        {"name": "NguoiKeKhai_NoiOHienTai", "value": {
            "tinh": "Tuyên Quang", "xa": "Xã Thượng Lâm", "diaChi": "SỐ 5, ĐƯỜNG ABC"},
        },
        {"name": "NguoiKeKhai_QuanHeChuHo", "value": "Chủ hộ"},
        {"name": "Ho_ThanhVien", "value": [
            {"hoTen": "NGUYEN VAN B", "soDinhDanh": "001201000002", "quanHeVoiChuHo": "Vợ"},
            {"hoTen": "NGUYEN VAN C", "soDinhDanh": "001201000003", "quanHeVoiChuHo": "Con"},
        ]},
        {"name": "NguoiKeKhai_DoiTuong", "value": "Công nhân"},
        {"name": "ToKhai_NoiKy", "value": "Tuyên Quang"},
        {"name": "ToKhai_NgayKy", "value": "05/04/2026"},
    ]

    mapped, warnings = mapper.enrich(fields, {})
    by_name = {item["name"]: item for item in mapped}

    assert by_name["data[fullname]"]["value"] == "NGUYEN VAN A"
    assert by_name["data[identityNumber]"]["value"] == "001201000001"
    assert by_name["data[phoneNumber]"]["value"] == "0912345678"
    assert by_name["data[province]"]["value"] == "Tỉnh Tuyên Quang"
    assert by_name["data[gender]"]["value"] in {"Nam", "Nữ"}
    assert by_name["data[fullname]"]["comp"] == UI_COMP_BY_NAME["data[fullname]"]
    assert by_name["data[panel_chung][address1]"]["value"].startswith("Nhà 12, Thôn Bản")
    assert by_name["data[panel_chung][thanhVien]"]["value"] == "NGUYEN VAN B (vợ); NGUYEN VAN C (con)"
    assert by_name["data[panel_chung][identityNumber2]"]["value"] == (
        "001201000002 (NGUYEN VAN B); 001201000003 (NGUYEN VAN C)"
    )
    assert by_name["data[panel_chung][TinTTTe]"]["value"] == "Tỉnh Tuyên Quang"
    assert by_name["data[panel_chung][TDTTK]"]["value"] == "05/04/2026"
    assert not any("ngày ký" in warning for warning in warnings)
    assert all(item["name"] in UI_COMP_BY_NAME for item in mapped)


def test_mapper_clears_prepopulated_required_blanks_when_applicant_is_not_account():
    mapped, warnings = mapper.enrich([], {})
    by_name = {item["name"]: item for item in mapped}

    assert by_name["data[fullname]"]["clear"] is True
    assert by_name["data[fullname]"]["markEmpty"] is True
    assert by_name["data[panel_chung][TDTTK]"]["clear"] is True
    assert by_name["data[panel_chung][TDTTK]"]["markEmpty"] is True
    assert any("Thiếu họ tên" in warning for warning in warnings)
    assert any("ngày ký" in warning for warning in warnings)


def test_attachment_planner_routes_combined_documents_to_each_matching_row():
    files = [{"name": "bo-ho-so.pdf"}]
    attachments, warnings, classified = build_plan_items(
        files,
        llm_types={0: ["mau_02", "giay_chung_nhan", "cccd", "cu_tru", "hon_nhan", "doi_tuong_thu_nhap"]},
    )

    assert [item["componentIndex"] for item in attachments] == [3, 7]
    assert all(item["fileName"] == "bo-ho-so.pdf" for item in attachments)
    assert all(item["target"] == "attp-row" and item["untickUnplannedRows"] for item in attachments)
    assert classified[0]["rows"] == [3, 7]
    assert any("nhiều giấy tờ" in warning for warning in warnings)


def test_attachment_planner_uses_mau03_row_and_keeps_unknown_file():
    attachments, warnings, classified = build_plan_items(
        [{"name": "mau03.pdf"}, {"name": "chua-ro.pdf"}],
        llm_types={0: ["mau_03"], 1: ["other"]},
    )

    assert [item["componentIndex"] for item in attachments] == [6, 6]
    assert classified[0]["rows"] == [6] and classified[1]["rows"] == [6]
    assert any("chua-ro.pdf" in warning for warning in warnings)
