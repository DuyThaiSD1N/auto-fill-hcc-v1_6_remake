from app.pipelines.giao_thue_chuyen_muc_dich_dat_quang_ngai.attach import planner
from app.pipelines.giao_thue_chuyen_muc_dich_dat_quang_ngai.attach.prompt import SYSTEM_PROMPT
from app.pipelines.giao_thue_chuyen_muc_dich_dat_quang_ngai.process import mapper
from app.pipelines.giao_thue_chuyen_muc_dich_dat_quang_ngai.process.prompt import EXTRA_RULES
from app.pipelines.giao_thue_chuyen_muc_dich_dat_quang_ngai.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_DON_NAME = (
    "Đơn đề nghị giao đất/thuê đất/chuyển mục đích sử dụng đất/giao đất và giao rừng/"
    "cho thuê đất và cho thuê rừng"
)
_KEY = "giao-thue-chuyen-muc-dich-dat-quang-ngai"


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _ocr(files: list[dict]) -> list[dict]:
    return [{"name": item["name"], "text": "ocr"} for item in files]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row, 15 dòng)
# --------------------------------------------------------------------------------------
def test_core_doc_types_route_to_their_own_rows():
    """Các loại chính route đúng dòng; CCCD/ủy quyền đi CHUNG dòng Đơn đề nghị (index 13)."""
    files = _files(["don.pdf", "gia-han.pdf", "cccd.pdf", "uy-quyen.pdf"])
    llm_types = {0: "don_de_nghi", 1: "don_gia_han", 2: "identity", 3: "authorization"}

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    assert [item["componentIndex"] for item in attachments] == [13, 11, 13, 13]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    # KHÔNG set Bản chính/Bản sao: cán bộ tự chọn.
    assert all("loaiBan" not in item for item in attachments)
    assert [item["docType"] for item in classified] == list(llm_types.values())
    assert attachments[0]["componentName"] == _DON_NAME
    assert attachments[1]["componentName"] == "Đơn đề nghị gia hạn sử dụng đất"
    # documentName phân biệt để cán bộ đối chiếu dù đính chung một dòng.
    assert attachments[2]["documentName"] == "Căn cước công dân"
    assert attachments[3]["documentName"] == "Văn bản ủy quyền"


def test_gcn_goes_to_both_row_11_and_row_13():
    """Ảnh ánh xạ 03: dòng 11 và dòng 13 CÙNG yêu cầu Giấy chứng nhận -> phải đính CẢ HAI dòng.
    Hai dòng có componentName KHÁC nhau nên FE gom thành 2 nhóm, không bị nuốt mất một dòng."""
    files = _files(["gcn.pdf"])

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(files), {0: "gcn"})

    assert warnings == []
    assert [item["componentIndex"] for item in attachments] == [10, 12]
    assert all(item["fileIndex"] == 0 for item in attachments)
    assert classified[0]["componentIndexes"] == [10, 12]
    names = {item["componentName"] for item in attachments}
    assert len(names) == 2  # tên khác nhau -> FE tạo 2 nhóm -> 2 dòng đều nhận file
    assert any("khoản 21 Điều 3" in name for name in names)
    assert any("Bản sao một trong các giấy chứng nhận" in name for name in names)


def test_every_dedicated_row_reachable_with_expected_index():
    """Mỗi loại giấy tờ đặc thù trỏ đúng dòng (componentIndex = STT − 1 theo bảng HTML)."""
    expected = {
        "du_an_giao_rung": [0],
        "dau_gia_thue_rung": [1],
        "ket_qua_lua_chon_nha_dau_tu": [2],
        "phuong_an_tang_dat_mat": [3],
        "van_ban_phe_duyet_dau_tu": [4],
        "giay_to_dau_tu_tong_hop": [5],
        "phuong_an_to_chuc_kinh_te": [6],
        "phuong_an_dat_thu_hoi": [7],
        "phuong_an_cong_ty_nong_lam": [8],
        "gcn": [10, 12],
        "don_gia_han": [11],
        "don_de_nghi": [13],
    }
    files = _files([f"{name}.pdf" for name in expected])
    llm_types = dict(enumerate(expected))

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    by_type: dict[str, list[int]] = {}
    for item in attachments:
        by_type.setdefault(item["detectedType"], []).append(item["componentIndex"])
    assert by_type == expected


def test_duplicate_text_rows_route_to_main_row_only():
    """STT4≡STT15 và STT6≡STT10 trùng text: FE gom nhóm theo componentName nên nhân đôi là vô nghĩa
    -> chỉ route về DÒNG CHÍNH (index 3, index 5)."""
    files = _files(["mau26.pdf", "giay-to-dau-tu.pdf"])

    attachments, _, _ = planner.build_plan_items(
        files, _ocr(files), {0: "phuong_an_tang_dat_mat", 1: "giay_to_dau_tu_tong_hop"}
    )

    assert [item["componentIndex"] for item in attachments] == [3, 5]
    assert 14 not in {item["componentIndex"] for item in attachments}
    assert 9 not in {item["componentIndex"] for item in attachments}


def test_no_dedicated_row_docs_merge_into_don_row():
    """Tờ khai thuế, đơn biến động Mẫu 18, đơn thẩm định nhu cầu không có dòng riêng -> dòng Đơn (13)."""
    files = _files(["khai-thue.pdf", "mau18.pdf", "tham-dinh.pdf"])

    attachments, warnings, _ = planner.build_plan_items(
        files, _ocr(files), {0: "to_khai_thue", 1: "don_bien_dong", 2: "don_tham_dinh_nhu_cau"}
    )

    assert warnings == []
    assert {item["componentIndex"] for item in attachments} == {13}
    assert {item["componentName"] for item in attachments} == {_DON_NAME}
    assert {item["documentName"] for item in attachments} == {
        "Tờ khai thuế/lệ phí trước bạ",
        "Đơn đăng ký biến động đất đai (Mẫu số 18)",
        "Đơn đề nghị thẩm định nhu cầu sử dụng đất/chuyển mục đích",
    }


def test_other_is_routed_to_don_row_not_skipped():
    """File 'other' KHÔNG bị bỏ: bảng không có dòng 'Giấy tờ khác' -> đính CHUNG dòng Đơn đề nghị,
    giữ TÊN FILE GỐC làm documentName; vẫn cảnh báo để cán bộ soát."""
    files = _files(["gcn.pdf", "bien-ban-la.pdf"])

    attachments, warnings, classified = planner.build_plan_items(
        files, _ocr(files), {0: "gcn", 1: "other"}
    )

    other_item = next(item for item in attachments if item["fileIndex"] == 1)
    assert other_item["componentIndex"] == 13
    assert other_item["detectedType"] == "other"
    assert other_item["documentName"] == "bien-ban-la.pdf"  # giữ tên gốc
    assert len(warnings) == 1 and "bien-ban-la.pdf" in warnings[0]
    assert classified[1]["docType"] == "other"
    assert classified[1].get("routedTo") == 13
    assert "skipped" not in classified[1]


def test_unknown_llm_type_routed_to_don_row():
    files = _files(["x.pdf"])

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(files), {})

    assert len(attachments) == 1
    assert attachments[0]["componentIndex"] == 13
    assert len(warnings) == 1
    assert classified[0]["docType"] == "other"
    assert classified[0]["source"] == "unknown"
    assert classified[0].get("routedTo") == 13


def test_llm_first_no_rule_fallback():
    # LLM-first tuyệt đối: không còn hàm rule keyword, không hardcode Bản chính/Bản sao.
    assert not hasattr(planner, "_rule_doc_type")
    assert not hasattr(planner, "_LOAI_BAN")


def test_attach_prompt_lists_procedure_specific_doc_types():
    for token in (
        "don_de_nghi",
        "don_gia_han",
        "ket_qua_lua_chon_nha_dau_tu",
        "phuong_an_tang_dat_mat",
        "phuong_an_cong_ty_nong_lam",
        "du_an_giao_rung",
        "dau_gia_thue_rung",
        "to_khai_thue",
        "identity",
        "authorization",
        "Mẫu số 26",
    ):
        assert token in SYSTEM_PROMPT


# --------------------------------------------------------------------------------------
# PROCESS (mapper 2 vai + khối thửa đất)
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
                "diaChi": "Số 1 đường X, Tổ 1",
            },
        },
        {"name": "Don_NoiDungDeNghi", "value": "Đề nghị cho phép chuyển mục đích sử dụng đất sang đất ở tại đô thị"},
    ]

    fields, errors = mapper.enrich(source)
    values = _values(fields)

    assert errors == []
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[identityNumber]"] == "000000000001"
    assert values["data[phoneNumber]"] == "0900000001"
    assert values["data[province]"] == "Tỉnh Quảng Ngãi"
    assert values["data[district]"] == "Phường Cẩm Thành"
    assert values["data[address]"] == "Số 1 đường X, Tổ 1"
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "Đề nghị cho phép chuyển mục đích sử dụng đất sang đất ở tại đô thị"
    )
    assert "data[note]" not in values  # ghi chú tự sinh đã bỏ theo yêu cầu


def test_mapper_authorized_keeps_owner_facts_only_name_is_submitter():
    """Form Quảng Ngãi CHỈ có đúng một ô về người nộp: 'Họ và tên người nộp hồ sơ' (data[fullname]).
    Toàn bộ panel 'Thông tin chung' (định danh, điện thoại, địa chỉ...) là của CHỦ HỒ SƠ, kể cả khi có
    ủy quyền — không được ghi nhân thân người được ủy quyền vào các ô đó."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "000000000002"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000002"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Phường Nghĩa Lộ", "diaChi": "Số 1"},
        },
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
        {"name": "NguoiNop_SoDinhDanh", "value": "000000000003"},
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
    assert values["data[phoneNumber]"] == "0900000002"
    assert values["data[address]"] == "Số 1"
    assert values["data[district]"] == "Phường Nghĩa Lộ"
    assert "000000000003" not in str(list(values.values()))
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


def test_phone_authorized_only_and_never_borrowed():
    """data[phoneNumber1] = 'Số điện thoại ủy quyền': CHỈ khi NGƯỜI NỘP KHÁC CHỦ HỒ SƠ, lấy số của BÊN ĐƯỢC ỦY
    QUYỀN. Không ủy quyền -> không phát; có ủy quyền mà không đọc được số người nộp -> để trống,
    KHÔNG mượn số của chủ hồ sơ."""
    self_submit = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000001"},
    ]
    # Tự nộp: người nộp = chủ hồ sơ nên "SĐT ủy quyền" lấy luôn số chủ hồ sơ (suy luận tất định từ vai).
    assert "data[phoneNumber1]" not in _values(mapper.enrich(self_submit)[0])

    authorized = [
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000002"},
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
        {"name": "NguoiNop_DienThoai", "value": "0900000003"},
    ]
    assert _values(mapper.enrich(authorized)[0])["data[phoneNumber1]"] == "0900000003"

    authorized_no_phone = [
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000002"},
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
    ]
    values = _values(mapper.enrich(authorized_no_phone)[0])
    assert "data[phoneNumber1]" not in values  # không đọc được số người nộp -> để trống
    # data[phoneNumber] là ô của CHỦ HỒ SƠ nên vẫn phát số chủ hồ sơ (không phải "mượn" cho người nộp).
    assert values["data[phoneNumber]"] == "0900000002"


def test_parcel_block_maps_to_second_address_group():
    """Khối THỬA ĐẤT map đúng data[diaChiThuaDat]/province2/village2/nation2."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Quảng Ngãi",
                "xa": "Phường Cẩm Thành",
                "diaChi": "Số 1 đường X, Tổ 1",
            },
        },
        {
            "name": "ThuaDat_DiaChi",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Quảng Ngãi",
                "xa": "Phường Đăk Bla",
                "diaChi": "Thửa số 000, tờ bản đồ số 00, đường Y",
            },
        },
    ]

    values = _values(mapper.enrich(source)[0])

    assert values["data[diaChiThuaDat]"] == "Thửa số 000, tờ bản đồ số 00, đường Y"
    assert values["data[province2]"] == "Tỉnh Quảng Ngãi"
    assert values["data[village2]"] == "Phường Đăk Bla"
    assert values["data[nation2]"] == "Việt Nam"
    # Khối cư trú KHÔNG bị lẫn sang khối thửa đất và ngược lại.
    assert values["data[district]"] == "Phường Cẩm Thành"
    assert values["data[address]"] == "Số 1 đường X, Tổ 1"
    assert values["data[diaChiThuaDat]"] != values["data[address]"]
    assert values["data[village2]"] != values["data[district]"]


def test_parcel_block_absent_when_no_parcel_source():
    """Không đọc được địa chỉ thửa đất -> để TRỐNG cả khối, KHÔNG mượn địa chỉ cư trú."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Quảng Ngãi",
                "xa": "Phường Cẩm Thành",
                "diaChi": "Số 1 đường X, Tổ 1",
            },
        },
    ]

    values = _values(mapper.enrich(source)[0])

    for name in ("data[diaChiThuaDat]", "data[province2]", "data[village2]", "data[nation2]"):
        assert name not in values


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


def test_ninh_binh_only_fields_not_emitted():
    """Cổng Quảng Ngãi KHÔNG có các ô này (đã grep 'giao đất fill.html') -> mapper không được phát."""
    absent = (
        "data[isOwnerDossier]",
        "data[organization]",
        "data[hoTen]",
        "data[soCCCD]",
        "data[diaChi]",
    )
    for name in absent:
        assert name not in UI_COMP_BY_NAME

    source = [
        {"name": "ChuHoSo_HoTen", "value": "CÔNG TY TNHH MTV MẪU"},
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
        {"name": "NguoiNop_SoDinhDanh", "value": "000000000003"},
        {
            "name": "NguoiNop_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Phường Nghĩa Lộ", "diaChi": "Số 9"},
        },
    ]
    values = _values(mapper.enrich(source)[0])
    for name in absent:
        assert name not in values


def test_schema_and_prompt_cover_parcel_and_notarization_lesson():
    names = {field["name"] for field in FIELDS}
    assert {"ChuHoSo_HoTen", "NguoiNop_HoTen", "Don_NoiDungDeNghi", "ThuaDat_DiaChi"} <= names

    parcel = next(field for field in FIELDS if field["name"] == "ThuaDat_DiaChi")
    assert "ĐỊA CHỈ THỬA ĐẤT" in parcel["desc"]
    assert "không lấy địa chỉ cư trú" in parcel["desc"]

    # Bài học prompt của dang_ky_bien_dong_dat_dai_ninh_binh: khối LỜI CHỨNG THỰC vẫn là nguồn hợp lệ.
    assert "LỜI CHỨNG THỰC" in EXTRA_RULES
    assert "cán bộ thực hiện chứng thực" in EXTRA_RULES  # cấm theo VAI, không cấm đọc
    assert "danh sách người ký trong lời chứng" in EXTRA_RULES
    assert "quét lại TOÀN BỘ tài liệu" in EXTRA_RULES
    assert "không mượn của người khác" in EXTRA_RULES
    gioi_tinh = next(field for field in FIELDS if field["name"] == "NguoiNop_GioiTinh")
    assert "LỜI CHỨNG THỰC" in gioi_tinh["desc"]

    # Quy tắc tách địa chỉ thửa đất khỏi nơi cư trú phải nằm trong EXTRA_RULES.
    assert "ĐỊA CHỈ THỬA ĐẤT" in EXTRA_RULES
    assert "gia hạn sử dụng đất" in EXTRA_RULES


# --------------------------------------------------------------------------------------
# REGISTRY
# --------------------------------------------------------------------------------------
def test_registry_has_scoped_procedure_and_both_pipelines():
    procedure = get_procedure(_KEY)

    assert procedure is not None
    assert procedure["label"].startswith(
        "[Tỉnh Quảng Ngãi] Giao đất, cho thuê đất, chuyển mục đích sử dụng đất đối với trường hợp "
        "giao đất, cho thuê đất không đấu giá"
    )
    assert procedure["label"].endswith("gia hạn sử dụng đất khi hết thời hạn sử dụng đất")
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["roles"] == []
    assert procedure["useDangKyBy"] is False
    # URL SPA chỉ có ObjectId -> KHÔNG dùng urlIncludes, chỉ khóa host + cụm text đặc trưng.
    assert procedure["detect"]["urlScope"] == ["dichvucong.quangngai.gov.vn"]
    assert "urlIncludes" not in procedure["detect"]
    assert procedure["detect"]["textPriority"] is True
    assert procedure["detect"]["headingDisabled"] is True
    assert callable(get_pipeline(_KEY))
    assert callable(get_attach_pipeline(_KEY))


def test_detect_scope_isolates_quang_ngai_from_sibling_provinces():
    """Tên thủ tục gần như y hệt bản Ninh Bình/Đà Nẵng -> urlScope là thứ duy nhất chống tráo."""
    scopes = {
        key: (get_procedure(key) or {}).get("detect", {}).get("urlScope")
        for key in (
            _KEY,
            "giao-thue-chuyen-muc-dich-dat-ninh-binh",
            "giao-thue-chuyen-muc-dich-dat-da-nang",
        )
    }
    assert scopes[_KEY] == ["dichvucong.quangngai.gov.vn"]
    for key, scope in scopes.items():
        assert scope, f"{key} thiếu urlScope -> có thể khớp nhầm trang tỉnh khác"
        if key != _KEY:
            assert "dichvucong.quangngai.gov.vn" not in scope


def test_prompt_forces_phone_extraction_from_contact_lines():
    """Bug thật: LLM bỏ sót SĐT vì đơn ghi dưới nhãn chung 'Địa chỉ liên hệ (điện thoại, fax, email...)'
    chứ không ghi 'điện thoại của ông X' — rule cũ 'chỉ trả khi tài liệu ghi cho đúng vai' làm nó dè dặt.
    Prompt phải nêu rõ nguồn hợp lệ và khẳng định số trong đơn của ai là của người đó."""
    assert "SỐ ĐIỆN THOẠI — PHẢI LẤY" in EXTRA_RULES
    assert "Địa chỉ liên hệ (điện" in EXTRA_RULES
    assert "Điện thoại liên hệ" in EXTRA_RULES
    assert "MẶC NHIÊN là số của người đó" in EXTRA_RULES
    assert "chỉ trả khi tài\n   liệu ghi cho đúng vai" not in EXTRA_RULES  # rule cũ đã gỡ

    phone_desc = next(f["desc"] for f in FIELDS if f["name"] == "ChuHoSo_DienThoai")
    assert "PHẢI lấy khi hồ sơ có" in phone_desc
    assert "Mẫu số 18" in phone_desc
