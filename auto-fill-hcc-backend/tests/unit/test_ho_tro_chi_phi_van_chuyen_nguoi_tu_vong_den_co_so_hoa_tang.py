from app.pipelines.ho_tro_chi_phi_van_chuyen_nguoi_tu_vong_den_co_so_hoa_tang.attach import planner
from app.pipelines.ho_tro_chi_phi_van_chuyen_nguoi_tu_vong_den_co_so_hoa_tang.attach.prompt import SYSTEM_PROMPT
from app.pipelines.ho_tro_chi_phi_van_chuyen_nguoi_tu_vong_den_co_so_hoa_tang.process import mapper
from app.pipelines.ho_tro_chi_phi_van_chuyen_nguoi_tu_vong_den_co_so_hoa_tang.process.prompt import EXTRA_RULES
from app.pipelines.ho_tro_chi_phi_van_chuyen_nguoi_tu_vong_den_co_so_hoa_tang.process.schema import (
    FIELDS,
    UI_COMP_BY_NAME,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "ho-tro-chi-phi-van-chuyen-nguoi-tu-vong-den-co-so-hoa-tang"
_ROW_DON = "Đơn đề nghị hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng"
_ROW_HOP_DONG = "Hợp đồng dịch vụ hỏa táng"
_ROW_QUYET_DINH = "Quyết định hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng"


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row, 3 dòng)
# --------------------------------------------------------------------------------------
def test_combined_pdf_attached_to_row_1_and_row_3_without_split():
    """Ảnh ánh xạ: 1 PDF gộp Đơn + Biên bản + Hợp đồng -> đính CHUNG cùng file vào dòng 1 và dòng 3."""
    files = _files(["ho-so.pdf"])
    llm_types = {0: ["don_de_nghi", "bien_ban_giao_nhan_tro_cot", "hop_dong_hoa_tang"]}

    attachments, warnings, classified = planner.build_plan_items(files, None, llm_types)

    assert warnings == []
    assert [item["componentIndex"] for item in attachments] == [0, 2]
    assert {item["fileIndex"] for item in attachments} == {0}
    assert [item["componentName"] for item in attachments] == [_ROW_DON, _ROW_HOP_DONG]
    assert [item["loaiBan"] for item in attachments] == ["Bản chính", "Bản sao"]
    assert attachments[1]["documentName"] == "Hợp đồng hỏa táng và biên bản giao nhận hũ tro cốt"
    assert all(item["target"] == "attp-row" and item["needsAddComponent"] is False for item in attachments)
    assert all(item["untickRows"] == [_ROW_QUYET_DINH] for item in attachments)
    assert classified[0]["componentIndexes"] == [0, 2]


def test_separate_files_route_to_their_rows():
    files = _files(["don.pdf", "hop-dong.pdf", "bien-ban.pdf", "cccd.jpg"])
    llm_types = {
        0: ["don_de_nghi"],
        1: ["hop_dong_hoa_tang"],
        2: ["bien_ban_giao_nhan_tro_cot"],
        3: ["identity"],
    }

    attachments, warnings, _ = planner.build_plan_items(files, None, llm_types)

    assert warnings == []
    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [(0, 0), (1, 2), (2, 2), (3, 0)]
    assert [item["documentName"] for item in attachments] == [
        "Đơn đề nghị hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng",
        "Hợp đồng dịch vụ hỏa táng",
        "Biên bản giao nhận hũ đựng tro cốt",
        "Căn cước công dân",
    ]


def test_row_names_do_not_cross_match():
    """Dòng Đơn và dòng Quyết định cùng đuôi; componentName phải giữ tiền tố để FE không khớp chéo."""
    names = [_ROW_DON, _ROW_HOP_DONG, _ROW_QUYET_DINH]
    for one in names:
        for other in names:
            if one is not other:
                assert one not in other
    assert {row["componentName"] for row in planner._ROWS.values()} == {_ROW_DON, _ROW_HOP_DONG}


def test_quyet_dinh_is_result_and_never_attached():
    files = _files(["don.pdf", "quyet-dinh.pdf"])
    attachments, warnings, classified = planner.build_plan_items(
        files, None, {0: ["don_de_nghi", "hop_dong_hoa_tang"], 1: ["quyet_dinh_ho_tro"]}
    )

    assert {item["fileIndex"] for item in attachments} == {0}
    assert classified[1]["skipped"] is True
    assert any("quyet-dinh.pdf" in warning for warning in warnings)


def test_unknown_file_is_kept_on_don_row_with_warning():
    files = _files(["don.pdf", "la.pdf"])
    attachments, warnings, classified = planner.build_plan_items(
        files, None, {0: ["don_de_nghi", "hop_dong_hoa_tang"]}
    )

    other = next(item for item in attachments if item["fileIndex"] == 1)
    assert other["componentIndex"] == 0
    assert other["documentName"] == "la.pdf"
    assert len(warnings) == 1 and "la.pdf" in warnings[0]
    assert classified[1]["source"] == "unknown"


def test_missing_required_components_warn():
    files = _files(["cccd.pdf"])
    _, warnings, _ = planner.build_plan_items(files, None, {0: ["identity"]})
    assert any("Chưa có Đơn đề nghị" in warning for warning in warnings)
    assert any("Chưa có Hợp đồng dịch vụ hỏa táng" in warning for warning in warnings)


def test_normalize_doc_types_accepts_single_and_drops_other():
    assert planner._normalize_doc_types({"docType": "hop_dong_hoa_tang"}) == ["hop_dong_hoa_tang"]
    assert planner._normalize_doc_types({"docTypes": ["don_de_nghi", "xyz", "don_de_nghi"]}) == ["don_de_nghi"]
    assert planner._normalize_doc_types({"docTypes": "la"}) == ["other"]


def test_attach_prompt_lists_doc_types():
    for token in (
        "don_de_nghi",
        "hop_dong_hoa_tang",
        "bien_ban_giao_nhan_tro_cot",
        "quyet_dinh_ho_tro",
        "docTypes",
        "GỘP",
    ):
        assert token in SYSTEM_PROMPT


# --------------------------------------------------------------------------------------
# PROCESS (contact block cổng Đà Nẵng)
# --------------------------------------------------------------------------------------
def test_mapper_self_submit_fills_submitter_block_with_owner():
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NgaySinh", "value": "05.06.1985"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "001.085.000.001"},
        {"name": "ChuHoSo_NgayCap", "value": "01/02/2024"},
        {"name": "ChuHoSo_NoiCap", "value": "Cục CSQLHC về TTXH"},
        {"name": "ChuHoSo_DienThoai", "value": "0900 000 001"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Tp Đà Nẵng", "xa": "Hải Châu", "diaChi": "K1/2 Lê Lợi"},
        },
        {"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"},
    ]

    fields, warnings = mapper.enrich(source)
    values = _values(fields)

    assert warnings == []
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[isOwnerDossier]"] is True
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[birthday]"] == "05/06/1985"
    assert values["data[identityNumber]"] == "001085000001"
    assert values["data[identityDate]"] == "01/02/2024"
    assert values["data[identityAgency]"]
    assert values["data[gender]"] == "Nam"  # suy từ chữ số thứ 4 của CCCD
    assert values["data[phoneNumber]"] == "0900000001"
    assert values["data[province]"] == "Thành phố Đà Nẵng"
    assert values["data[district]"] == "Phường Hải Châu"
    assert values["data[address]"] == "K1/2 Lê Lợi"
    assert values["data[chonDoiTuong]"] == "Cá nhân"
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "ÔNG/BÀ: NGUYỄN VĂN A (chủ hồ sơ) ĐỀ NGHỊ GIẢI QUYẾT "
        "Hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng"
    )
    assert "data[organization]" not in values


def test_mapper_authorized_uses_submitter_facts_only():
    source = [
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "001185000002"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000002"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "Số 1"},
        },
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
        {"name": "NguoiNop_SoDinhDanh", "value": "001095000003"},
        {"name": "NguoiNop_DienThoai", "value": "0900000003"},
    ]

    values = _values(mapper.enrich(source)[0])

    assert values["data[ownerFullname]"] == "TRẦN THỊ B"
    assert values["data[isOwnerDossier]"] is False
    assert values["data[fullname]"] == "LÊ VĂN C"
    assert values["data[identityNumber]"] == "001095000003"
    assert values["data[phoneNumber]"] == "0900000003"
    # Không mượn địa chỉ/số của chủ hồ sơ cho người nộp.
    assert "data[address]" not in values
    assert "0900000002" not in str(list(values.values()))


def test_mapper_organization_case():
    source = [
        {"name": "ChuHoSo_HoTen", "value": "PHAN VĂN D"},
        {"name": "ChuHoSo_TenToChuc", "value": "Hội Chữ thập đỏ phường X"},
    ]
    values = _values(mapper.enrich(source)[0])
    assert values["data[organization]"] == "Hội Chữ thập đỏ phường X"
    assert values["data[ownerFullname]"] == "PHAN VĂN D"
    assert values["data[chonDoiTuong]"] == "Tổ chức"


def test_explicit_gender_wins_over_id_digit():
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN THỊ E"},
        {"name": "ChuHoSo_GioiTinh", "value": "Nữ"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "001085000001"},
    ]
    assert _values(mapper.enrich(source)[0])["data[gender]"] == "Nữ"


def test_admin_and_note_fields_never_declared():
    for name in ("data[hinhThucNop]", "data[taxCode]", "data[note]", "data[tenCoQuan]", "data[donvihotrophidiagioi]"):
        assert name not in UI_COMP_BY_NAME


def test_schema_has_no_deceased_slot_and_prompt_forbids_it():
    names = {field["name"] for field in FIELDS}
    assert {"ChuHoSo_HoTen", "ChuHoSo_TenToChuc", "NguoiNop_HoTen"} <= names
    assert not any(name.startswith("NguoiChet_") for name in names)
    assert "NGƯỜI CHẾT" in EXTRA_RULES
    assert "SỐ TÀI KHOẢN" in EXTRA_RULES
    assert "CƠ SỞ HỎA" in EXTRA_RULES


# --------------------------------------------------------------------------------------
# REGISTRY
# --------------------------------------------------------------------------------------
def test_registry_entry_matches_ke_khai_link_and_pipelines():
    procedure = get_procedure(_KEY)
    assert procedure is not None
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert "urlScope" not in procedure["detect"]
    assert procedure["detect"]["textIncludes"] == ["Hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng"]
    assert callable(get_pipeline(_KEY))
    assert callable(get_attach_pipeline(_KEY))

    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "3.000721"


def test_detect_does_not_collide_with_other_cremation_procedures():
    mine = get_procedure(_KEY)["detect"]["textIncludes"][0].lower()
    for key in ("ho-tro-chi-phi-hoa-tang-quang-ngai", "ho-tro-chi-phi-hoa-tang-bac-ninh"):
        other = get_procedure(key) or {}
        for phrase in (other.get("detect") or {}).get("textIncludes") or []:
            assert mine not in phrase.lower()
            assert phrase.lower() not in mine
