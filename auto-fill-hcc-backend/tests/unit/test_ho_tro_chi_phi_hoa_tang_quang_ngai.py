from app.pipelines.ho_tro_chi_phi_hoa_tang_quang_ngai.attach import planner
from app.pipelines.ho_tro_chi_phi_hoa_tang_quang_ngai.attach.prompt import SYSTEM_PROMPT
from app.pipelines.ho_tro_chi_phi_hoa_tang_quang_ngai.process import mapper
from app.pipelines.ho_tro_chi_phi_hoa_tang_quang_ngai.process.prompt import EXTRA_RULES
from app.pipelines.ho_tro_chi_phi_hoa_tang_quang_ngai.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "ho-tro-chi-phi-hoa-tang-quang-ngai"

# VERBATIM theo cột "Tên giấy tờ" của 'quảng ngãi khuyến khích hoả táng đính kèm.html' (4 dòng).
_ROW_MAU_01 = (
    "Tờ khai đề nghị hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng theo Mẫu số 01 "
    "(dành cho cá nhân)."
)
_ROW_MAU_02 = (
    "Tờ khai đề nghị hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng theo Mẫu số 02 "
    "(dành cho cơ quan, tổ chức)."
)
_ROW_HOP_DONG = "Bản chính Hợp đồng và Hóa đơn tài chính của cơ sở hỏa táng."
_ROW_UY_QUYEN = (
    "Văn bản ủy quyền của cá nhân được chứng thực hoặc giấy giới thiệu của cơ quan, tổ chức (nếu có)."
)


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _ocr(files: list[dict]) -> list[dict]:
    return [{"name": item["name"], "text": "ocr"} for item in files]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row, 4 dòng)
# --------------------------------------------------------------------------------------
def test_core_doc_types_route_to_their_own_rows():
    """Mỗi loại chính trỏ đúng dòng (componentIndex = STT − 1 theo bảng HTML)."""
    files = _files(["to-khai.pdf", "hop-dong.pdf", "hoa-don.pdf", "uy-quyen.pdf"])
    llm_types = {
        0: "to_khai_ca_nhan",
        1: "hop_dong_hoa_tang",
        2: "hoa_don_hoa_tang",
        3: "authorization",
    }

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    assert [item["componentIndex"] for item in attachments] == [0, 2, 2, 3]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    # KHÔNG set Bản chính/Bản sao: cán bộ tự chọn.
    assert all("loaiBan" not in item for item in attachments)
    assert [item["docType"] for item in classified] == list(llm_types.values())
    assert attachments[0]["componentName"] == _ROW_MAU_01
    assert attachments[3]["componentName"] == _ROW_UY_QUYEN


def test_component_names_are_verbatim_and_do_not_cross_match():
    """FE khớp dòng bằng substring componentName đã fold dấu: hai dòng Tờ khai chỉ khác nhau ở đuôi
    '(dành cho cá nhân)' / '(dành cho cơ quan, tổ chức)' nên phải giữ NGUYÊN cả câu."""
    assert planner._ROW_NAMES == {
        0: _ROW_MAU_01,
        1: _ROW_MAU_02,
        2: _ROW_HOP_DONG,
        3: _ROW_UY_QUYEN,
    }
    # Không chuỗi nào là substring của chuỗi khác -> không có dòng nào khớp chéo.
    names = list(planner._ROW_NAMES.values())
    for one in names:
        for other in names:
            if one is not other:
                assert one not in other


def test_hop_dong_and_hoa_don_share_one_row():
    """Ảnh ánh xạ: 'ĐÍNH KÈM CHUNG — 02 tệp trong 01 mục'. Hai chứng từ vào CÙNG dòng index 2, nhưng
    documentName khác nhau để cán bộ vẫn phân biệt được trong cùng ô upload."""
    files = _files(["hop-dong.pdf", "hoa-don.pdf"])

    attachments, warnings, _ = planner.build_plan_items(
        files, _ocr(files), {0: "hop_dong_hoa_tang", 1: "hoa_don_hoa_tang"}
    )

    assert warnings == []
    assert {item["componentIndex"] for item in attachments} == {2}
    # Cùng componentName -> FE gom một nhóm, set cả hai file một lượt (ô upload nhận nhiều file).
    assert {item["componentName"] for item in attachments} == {_ROW_HOP_DONG}
    assert {item["documentName"] for item in attachments} == {
        "Hợp đồng dịch vụ hỏa táng",
        "Hóa đơn tài chính của cơ sở hỏa táng",
    }
    assert len(attachments) == 2


def test_to_khai_mau_01_and_mau_02_never_cross():
    """Hai dòng Tờ khai loại trừ nhau: ảnh ánh xạ cảnh báo tuyệt đối không đính nhầm tệp Mẫu số 01
    vào dòng Mẫu số 02."""
    ca_nhan = _files(["to-khai-ca-nhan.pdf"])
    attachments, _, _ = planner.build_plan_items(ca_nhan, _ocr(ca_nhan), {0: "to_khai_ca_nhan"})
    assert [item["componentIndex"] for item in attachments] == [0]
    assert attachments[0]["componentName"] == _ROW_MAU_01

    to_chuc = _files(["to-khai-to-chuc.pdf"])
    attachments, _, _ = planner.build_plan_items(to_chuc, _ocr(to_chuc), {0: "to_khai_to_chuc"})
    assert [item["componentIndex"] for item in attachments] == [1]
    assert attachments[0]["componentName"] == _ROW_MAU_02


def test_trich_luc_and_identity_merge_into_to_khai_row():
    """Trích lục khai tử và CCCD KHÔNG có dòng riêng (ảnh ánh xạ xếp vào ô 'PHẢI BỔ SUNG — eForm không
    có dòng sẵn'). Không được rớt file -> đính chung dòng Tờ khai chính, documentName mô tả rõ."""
    files = _files(["trich-luc.pdf", "cccd.pdf"])

    attachments, warnings, classified = planner.build_plan_items(
        files, _ocr(files), {0: "trich_luc_khai_tu", 1: "identity"}
    )

    assert warnings == []
    assert {item["componentIndex"] for item in attachments} == {0}
    assert {item["componentName"] for item in attachments} == {_ROW_MAU_01}
    assert [item["documentName"] for item in attachments] == [
        "Trích lục khai tử/Giấy báo tử",
        "Căn cước công dân",
    ]
    assert [item["docType"] for item in classified] == ["trich_luc_khai_tu", "identity"]
    assert all("skipped" not in item for item in classified)


def test_main_row_follows_mau_02_when_dossier_is_organization():
    """Hồ sơ của cơ quan, tổ chức chỉ dùng Mẫu số 02 -> giấy tờ không có dòng riêng phải theo dòng đó,
    không dồn vào dòng Mẫu số 01 đang bỏ trống."""
    files = _files(["to-khai-to-chuc.pdf", "trich-luc.pdf", "la.pdf"])

    attachments, warnings, classified = planner.build_plan_items(
        files, _ocr(files), {0: "to_khai_to_chuc", 1: "trich_luc_khai_tu", 2: "other"}
    )

    assert [item["componentIndex"] for item in attachments] == [1, 1, 1]
    assert {item["componentName"] for item in attachments} == {_ROW_MAU_02}
    assert len(warnings) == 1
    assert classified[2]["routedTo"] == 1

    # Có Mẫu số 01 trong hồ sơ -> dòng chính quay về index 0 (trường hợp cá nhân, phổ biến nhất).
    files = _files(["to-khai-ca-nhan.pdf", "trich-luc.pdf"])
    attachments, _, _ = planner.build_plan_items(
        files, _ocr(files), {0: "to_khai_ca_nhan", 1: "trich_luc_khai_tu"}
    )
    assert [item["componentIndex"] for item in attachments] == [0, 0]


def test_other_is_routed_to_to_khai_row_not_skipped():
    """File 'other' KHÔNG bị bỏ: bảng không có dòng 'Giấy tờ khác' -> đính chung dòng Tờ khai chính,
    giữ TÊN FILE GỐC làm documentName; vẫn cảnh báo để cán bộ soát."""
    files = _files(["to-khai.pdf", "bien-ban-la.pdf"])

    attachments, warnings, classified = planner.build_plan_items(
        files, _ocr(files), {0: "to_khai_ca_nhan", 1: "other"}
    )

    other_item = next(item for item in attachments if item["fileIndex"] == 1)
    assert other_item["componentIndex"] == 0
    assert other_item["detectedType"] == "other"
    assert other_item["documentName"] == "bien-ban-la.pdf"  # giữ tên gốc
    assert len(warnings) == 1 and "bien-ban-la.pdf" in warnings[0]
    assert classified[1]["docType"] == "other"
    assert classified[1]["source"] == "llm"
    assert classified[1].get("routedTo") == 0
    assert "skipped" not in classified[1]


def test_unknown_llm_type_routed_to_to_khai_row():
    files = _files(["x.pdf"])

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(files), {})

    assert len(attachments) == 1
    assert attachments[0]["componentIndex"] == 0
    assert len(warnings) == 1
    assert classified[0]["docType"] == "other"
    assert classified[0]["source"] == "unknown"
    assert classified[0].get("routedTo") == 0


def test_llm_first_no_rule_fallback():
    # LLM-first tuyệt đối: không có hàm rule keyword, không hardcode Bản chính/Bản sao.
    assert not hasattr(planner, "_rule_doc_type")
    assert not hasattr(planner, "_LOAI_BAN")


def test_attach_prompt_lists_procedure_specific_doc_types():
    for token in (
        "to_khai_ca_nhan",
        "to_khai_to_chuc",
        "hop_dong_hoa_tang",
        "hoa_don_hoa_tang",
        "trich_luc_khai_tu",
        "authorization",
        "identity",
        "Mẫu số 01",
        "Mẫu số 02",
    ):
        assert token in SYSTEM_PROMPT


# --------------------------------------------------------------------------------------
# PROCESS (mapper 2 vai trên template dùng chung của cổng Quảng Ngãi)
# --------------------------------------------------------------------------------------
def test_mapper_owner_self_submits():
    """Không ủy quyền: người nộp = chủ hồ sơ, khối định danh lấy fact chủ hồ sơ, có data[note]."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NgaySinh", "value": "26/07/1990"},
        {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "000 000 000 001"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000001"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Quảng Ngãi",
                "xa": "Phường Cẩm Thành",
                "diaChi": "Tổ dân phố số 1",
            },
        },
        {
            "name": "Don_NoiDungDeNghi",
            "value": "Đề nghị xem xét, hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng theo quy định",
        },
    ]

    fields, errors = mapper.enrich(source)
    values = _values(fields)

    assert errors == []
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[identityNumber]"] == "000000000001"
    assert values["data[phoneNumber]"] == "0900000001"
    assert values["data[birthday]"] == "26/07/1990"
    assert values["data[province]"] == "Tỉnh Quảng Ngãi"
    assert values["data[district]"] == "Phường Cẩm Thành"
    assert values["data[address]"] == "Tổ dân phố số 1"
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "Đề nghị xem xét, hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng theo quy định"
    )
    # Ghi chú nêu rõ chỗ đính giấy tờ không có dòng riêng (Trích lục khai tử/CCCD).
    assert "data[note]" not in values  # ghi chú tự sinh đã bỏ theo yêu cầu
    # "Chọn đối tượng" là mặc định của cổng, phải đánh dấu default để extension tô viền vàng.
    doi_tuong = next(item for item in fields if item["name"] == "data[chonDoiTuong]")
    assert doi_tuong["value"] == "Cá nhân" and doi_tuong.get("default") is True


def test_mapper_authorized_keeps_owner_facts_only_name_is_submitter():
    """Form Quảng Ngãi CHỈ có đúng một ô về người nộp: 'Họ và tên người nộp hồ sơ' (data[fullname]).
    Toàn bộ panel 'Thông tin chung' (định danh, điện thoại, địa chỉ...) là của CHỦ HỒ SƠ, kể cả khi có
    ủy quyền — không được ghi nhân thân người được ủy quyền vào các ô đó."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "000000000002"},
        {"name": "ChuHoSo_NgaySinh", "value": "01/02/1980"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000002"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Phường Nghĩa Lộ", "diaChi": "Số 1"},
        },
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
        {"name": "NguoiNop_SoDinhDanh", "value": "000000000003"},
        {"name": "NguoiNop_NgaySinh", "value": "03/04/1995"},
        {"name": "NguoiNop_DienThoai", "value": "0900000003"},
        {
            "name": "NguoiNop_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Phường Trương Quang Trọng", "diaChi": "Số 9"},
        },
    ]

    values = _values(mapper.enrich(source)[0])

    assert values["data[ownerFullname]"] == "TRẦN THỊ B"
    assert values["data[fullname]"] == "LÊ VĂN C"        # ô DUY NHẤT của người nộp
    # Khối còn lại bám CHỦ HỒ SƠ, tuyệt đối không lấy của người được ủy quyền.
    assert values["data[identityNumber]"] == "000000000002"
    assert values["data[birthday]"] == "01/02/1980"
    assert values["data[phoneNumber]"] == "0900000002"
    assert values["data[address]"] == "Số 1"
    assert values["data[district]"] == "Phường Nghĩa Lộ"
    assert "000000000003" not in str(list(values.values()))
    assert "03/04/1995" not in str(list(values.values()))
    assert "Số 9" not in str(list(values.values()))


def test_mapper_self_submit_uses_owner_for_every_field():
    """Không có ủy quyền: người nộp CHÍNH LÀ chủ hồ sơ. Thiếu fact ChuHoSo_* thì NguoiNop_* dùng thay
    được vì hai vai là một người."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "NguoiNop_SoDinhDanh", "value": "000000000001"},
        {"name": "NguoiNop_DienThoai", "value": "0900000001"},
    ]

    values = _values(mapper.enrich(source)[0])

    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[identityNumber]"] == "000000000001"
    assert values["data[phoneNumber]"] == "0900000001"
    # Không ủy quyền: người nộp CHÍNH LÀ chủ hồ sơ -> ô "SĐT ủy quyền" dùng luôn số chủ hồ sơ.
    # Người nộp = chủ hồ sơ -> KHÔNG có việc ủy quyền nên ô "SĐT ủy quyền" phải TRỐNG (không fallback).
    assert "data[phoneNumber1]" not in values


def test_phone_authorized_branch_and_never_borrowed():
    """data[phoneNumber1] = 'Số điện thoại ủy quyền' — số của người trực tiếp đi nộp. Tự nộp (người nộp = chủ hồ sơ) -> ô này để TRỐNG, KHÔNG fallback."""
    self_submit = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000001"},
    ]
    assert "data[phoneNumber1]" not in _values(mapper.enrich(self_submit)[0])

    authorized = [
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000002"},
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
        {"name": "NguoiNop_DienThoai", "value": "0900000003"},
    ]
    values = _values(mapper.enrich(authorized)[0])
    assert values["data[phoneNumber1]"] == "0900000003"
    assert values["data[phoneNumber]"] == "0900000002"

    authorized_no_phone = [
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000002"},
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
    ]
    values = _values(mapper.enrich(authorized_no_phone)[0])
    assert "data[phoneNumber1]" not in values
    # data[phoneNumber] là ô của CHỦ HỒ SƠ nên vẫn phát số chủ hồ sơ (không phải "mượn" cho người nộp).
    assert values["data[phoneNumber]"] == "0900000002"


def test_parcel_block_never_emitted():
    """Khối 'Địa chỉ thửa đất/ địa chỉ xây dựng' là panel THỪA của template đất đai/xây dựng dùng
    chung. Thủ tục hỏa táng KHÔNG có thửa đất -> 4 ô này không được khai và không bao giờ được phát,
    kể cả khi hồ sơ có địa chỉ cư trú hay địa điểm cơ sở hỏa táng."""
    parcel_names = ("data[diaChiThuaDat]", "data[province2]", "data[village2]", "data[nation2]")
    for name in parcel_names:
        assert name not in UI_COMP_BY_NAME

    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Quảng Ngãi",
                "xa": "Phường Cẩm Thành",
                "diaChi": "Tổ dân phố số 1",
            },
        },
        # Fact rác cố tình bơm vào để chắc chắn không có đường nào chảy sang khối thửa đất.
        {
            "name": "ThuaDat_DiaChi",
            "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Phường X", "diaChi": "Thửa số 000"},
        },
    ]
    values = _values(mapper.enrich(source)[0])
    for name in parcel_names:
        assert name not in values
    assert "Thửa số 000" not in str(list(values.values()))
    # Khối cư trú vẫn phát bình thường.
    assert values["data[address]"] == "Tổ dân phố số 1"


def test_admin_fields_never_emitted():
    """Số bộ hồ sơ + Hình thức nộp hồ sơ do portal để sẵn, không lấy từ giấy tờ -> KHÔNG emit."""
    assert "data[ProcedureDossierQuantity]" not in UI_COMP_BY_NAME
    assert "data[hinhThucNop]" not in UI_COMP_BY_NAME

    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "000000000001"},
    ]
    values = _values(mapper.enrich(source)[0])
    assert "data[ProcedureDossierQuantity]" not in values
    assert "data[hinhThucNop]" not in values


def test_schema_has_two_roles_and_no_deceased_slot():
    """Form không có ô nào cho NGƯỜI CHẾT -> schema cố ý không có field NguoiChet_*; prompt phải cấm
    tường minh việc lấy người chết làm chủ hồ sơ/người nộp."""
    names = {field["name"] for field in FIELDS}
    assert {"ChuHoSo_HoTen", "NguoiNop_HoTen", "Don_NoiDungDeNghi"} <= names
    assert not any(name.startswith("NguoiChet_") for name in names)
    assert not any(name.startswith("ThuaDat_") for name in names)

    owner_desc = next(f["desc"] for f in FIELDS if f["name"] == "ChuHoSo_HoTen")
    assert "Tờ khai đề nghị" in owner_desc
    assert "KHÔNG lấy NGƯỜI CHẾT" in owner_desc

    assert "NGƯỜI CHẾT (người được hỏa táng) KHÔNG có ô nào trên form" in EXTRA_RULES
    assert "Trích lục khai tử" in EXTRA_RULES


def test_prompt_keeps_notarization_and_phone_lessons():
    """Hai bài học đã chốt ở bản Quảng Ngãi giao đất phải được giữ nguyên cho thủ tục này."""
    # Khối LỜI CHỨNG THỰC vẫn là nguồn hợp lệ (cấm theo VAI, không cấm đọc).
    assert "LỜI CHỨNG THỰC" in EXTRA_RULES
    assert "cán bộ thực hiện chứng thực" in EXTRA_RULES
    assert "danh sách người ký trong lời chứng thực" in EXTRA_RULES
    assert "quét lại TOÀN BỘ tài liệu" in EXTRA_RULES
    assert "không mượn của người khác" in EXTRA_RULES
    gioi_tinh = next(f["desc"] for f in FIELDS if f["name"] == "NguoiNop_GioiTinh")
    assert "LỜI CHỨNG THỰC" in gioi_tinh

    # Rule số điện thoại: phải lấy, kèm hai cái bẫy riêng của hồ sơ hỏa táng.
    assert "SỐ ĐIỆN THOẠI — PHẢI LẤY" in EXTRA_RULES
    assert "Điện thoại liên hệ" in EXTRA_RULES
    assert "MẶC NHIÊN là số của người đó" in EXTRA_RULES
    assert "SỐ TÀI KHOẢN" in EXTRA_RULES
    assert "CƠ SỞ HỎA TÁNG" in EXTRA_RULES
    phone_desc = next(f["desc"] for f in FIELDS if f["name"] == "ChuHoSo_DienThoai")
    assert "PHẢI lấy khi hồ sơ có" in phone_desc


# --------------------------------------------------------------------------------------
# REGISTRY
# --------------------------------------------------------------------------------------
def test_registry_has_scoped_procedure_and_both_pipelines():
    procedure = get_procedure(_KEY)

    assert procedure is not None
    assert procedure["label"] == (
        "[Tỉnh Quảng Ngãi] Hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng"
    )
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["roles"] == []
    assert procedure["useDangKyBy"] is False
    # URL SPA chỉ có ObjectId -> KHÔNG dùng urlIncludes, chỉ khóa host + cụm text đặc trưng.
    assert procedure["detect"]["urlScope"] == ["dichvucong.quangngai.gov.vn"]
    assert "urlIncludes" not in procedure["detect"]
    assert procedure["detect"]["textIncludes"] == [
        "Hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng"
    ]
    assert procedure["detect"]["textPriority"] is True
    assert procedure["detect"]["headingDisabled"] is True
    assert callable(get_pipeline(_KEY))
    assert callable(get_attach_pipeline(_KEY))


def test_detect_does_not_collide_with_siblings():
    """Cùng host với thủ tục đất đai Quảng Ngãi và cùng nghiệp vụ với bản Bắc Ninh -> hai chiều đều
    phải tách được: cụm text không lồng nhau, và bản Bắc Ninh nằm ở host khác."""
    quang_ngai_land = get_procedure("giao-thue-chuyen-muc-dich-dat-quang-ngai") or {}
    bac_ninh = get_procedure("ho-tro-chi-phi-hoa-tang-bac-ninh") or {}
    mine = get_procedure(_KEY) or {}

    phrase = mine["detect"]["textIncludes"][0].lower()
    for other in quang_ngai_land["detect"]["textIncludes"]:
        assert phrase not in other.lower()
        assert other.lower() not in phrase

    # Bản Bắc Ninh khóa host riêng nên không bao giờ được xét trên trang Quảng Ngãi.
    assert bac_ninh["detect"]["urlScope"] == ["dichvucong.bacninh.gov.vn"]
    assert "dichvucong.quangngai.gov.vn" not in bac_ninh["detect"]["urlScope"]
