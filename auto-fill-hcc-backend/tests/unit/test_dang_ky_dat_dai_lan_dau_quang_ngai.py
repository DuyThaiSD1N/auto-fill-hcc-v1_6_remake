from app.pipelines.dang_ky_dat_dai_lan_dau_quang_ngai.attach import planner
from app.pipelines.dang_ky_dat_dai_lan_dau_quang_ngai.attach.prompt import SYSTEM_PROMPT
from app.pipelines.dang_ky_dat_dai_lan_dau_quang_ngai.process import mapper
from app.pipelines.dang_ky_dat_dai_lan_dau_quang_ngai.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_dat_dai_lan_dau_quang_ngai.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_DON_NAME = "Đơn đăng ký đất đai, tài sản gắn liền với đất"
_DON_INDEX = 0
_TAI_CHINH_NAME = "Chứng từ thực hiện nghĩa vụ tài chính"
_TAI_CHINH_INDEX = 12
_KEY = "dang-ky-dat-dai-lan-dau-quang-ngai"


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _ocr(files: list[dict]) -> list[dict]:
    return [{"name": item["name"], "text": "ocr"} for item in files]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row, 20 dòng)
# --------------------------------------------------------------------------------------
def test_core_doc_types_route_to_their_own_rows():
    """Đơn/văn bản đại diện/trích đo có dòng riêng; CCCD đi CHUNG dòng Đơn đăng ký (index 0)."""
    files = _files(["don.pdf", "dai-dien.pdf", "trich-do.pdf", "cccd.pdf"])
    llm_types = {0: "don_dang_ky", 1: "authorization", 2: "manh_trich_do", 3: "identity"}

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    assert [item["componentIndex"] for item in attachments] == [0, 1, 9, 0]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    # KHÔNG set Bản chính/Bản sao: cán bộ tự chọn.
    assert all("loaiBan" not in item for item in attachments)
    assert [item["docType"] for item in classified] == list(llm_types.values())
    assert attachments[0]["componentName"] == _DON_NAME
    # documentName phân biệt để cán bộ đối chiếu dù CCCD đính chung dòng Đơn.
    assert attachments[3]["documentName"] == "Căn cước công dân"
    assert attachments[3]["componentName"] == _DON_NAME


def test_every_dedicated_row_reachable_with_expected_index():
    """Mỗi loại giấy tờ có dòng riêng trỏ đúng dòng (componentIndex = STT − 1 theo bảng HTML 20 dòng)."""
    expected = {
        "don_dang_ky": 0,
        "authorization": 1,
        "giay_to_dieu_137": 2,
        "thua_ke": 3,
        "thua_ke_chuyen_quyen": 4,
        "giao_dat_khong_dung_tham_quyen": 5,
        "xu_phat_hanh_chinh": 6,
        "thua_dat_lien_ke": 7,
        "van_ban_thanh_vien_ho_gia_dinh": 8,
        "manh_trich_do": 9,
        "ho_so_thiet_ke_xay_dung": 10,
        "quyet_dinh_xu_phat": 11,
        "chung_tu_tai_chinh": 12,
        "giay_to_chuyen_quyen": 13,
        "giay_xac_nhan_xay_dung": 14,
        "thoa_thuan_cap_chung": 15,
    }
    files = _files([f"{name}.pdf" for name in expected])
    llm_types = dict(enumerate(expected))

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    assert {item["detectedType"]: item["componentIndex"] for item in attachments} == expected
    # Mỗi file chỉ sinh ĐÚNG một plan item (không nhân bản một tài liệu sang nhiều dòng).
    assert len(attachments) == len(expected)


def test_duplicate_text_rows_route_to_main_row_only():
    """Ảnh ánh xạ 03: STT17≡STT3, STT18≡STT4, STT19≡STT16 trùng nội dung — FE gom nhóm theo
    componentName nên nhân đôi là vô nghĩa -> chỉ route DÒNG CHÍNH (index 2, 3, 15)."""
    files = _files(["dieu137.pdf", "thua-ke.pdf", "thoa-thuan.pdf"])

    attachments, _, _ = planner.build_plan_items(
        files, _ocr(files), {0: "giay_to_dieu_137", 1: "thua_ke", 2: "thoa_thuan_cap_chung"}
    )

    assert [item["componentIndex"] for item in attachments] == [2, 3, 15]
    # Không bao giờ đụng tới các dòng trùng text (16, 17, 18) hay dòng kết quả (19).
    assert {16, 17, 18, 19}.isdisjoint({item["componentIndex"] for item in attachments})


def test_no_route_touches_duplicate_or_result_rows():
    """Khóa cứng: không docType nào được cấu hình trỏ vào index 16/17/18 (trùng text) hoặc 19
    (Thông báo xác nhận kết quả — cơ quan phát hành SAU khi giải quyết, dân không nộp)."""
    used = {route["index"] for route in planner._ROUTES.values()}
    assert used.isdisjoint({16, 17, 18, 19})
    assert max(used) == 15


def test_no_dedicated_row_docs_merge_into_expected_rows():
    """Giấy tờ không có dòng riêng: CCCD + giấy xác nhận số định danh -> dòng Đơn (0);
    tờ khai thuế/lệ phí trước bạ -> dòng Chứng từ nghĩa vụ tài chính (12) theo ảnh ánh xạ 03."""
    files = _files(["cccd.pdf", "gxn-dinh-danh.pdf", "khai-thue.pdf"])

    attachments, warnings, _ = planner.build_plan_items(
        files, _ocr(files), {0: "identity", 1: "xac_nhan_cmnd_cccd", 2: "to_khai_thue"}
    )

    assert warnings == []
    assert [item["componentIndex"] for item in attachments] == [0, 0, _TAI_CHINH_INDEX]
    assert [item["componentName"] for item in attachments] == [_DON_NAME, _DON_NAME, _TAI_CHINH_NAME]
    assert [item["documentName"] for item in attachments] == [
        "Căn cước công dân",
        "Giấy xác nhận số định danh cá nhân/số CMND 9 số",
        "Tờ khai thuế/lệ phí trước bạ",
    ]


def test_other_is_routed_to_don_row_not_skipped():
    """File 'other' KHÔNG bị bỏ: bảng không có dòng 'Giấy tờ khác' -> đính CHUNG dòng Đơn đăng ký,
    giữ TÊN FILE GỐC làm documentName; vẫn cảnh báo để cán bộ soát."""
    files = _files(["don.pdf", "bien-ban-la.pdf"])

    attachments, warnings, classified = planner.build_plan_items(
        files, _ocr(files), {0: "don_dang_ky", 1: "other"}
    )

    other_item = next(item for item in attachments if item["fileIndex"] == 1)
    assert other_item["componentIndex"] == _DON_INDEX
    assert other_item["componentName"] == _DON_NAME
    assert other_item["detectedType"] == "other"
    assert other_item["documentName"] == "bien-ban-la.pdf"  # giữ tên gốc
    assert len(warnings) == 1 and "bien-ban-la.pdf" in warnings[0]
    assert classified[1]["docType"] == "other"
    assert classified[1].get("routedTo") == _DON_INDEX
    assert "skipped" not in classified[1]


def test_unknown_llm_type_routed_to_don_row():
    files = _files(["x.pdf"])

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(files), {})

    assert len(attachments) == 1
    assert attachments[0]["componentIndex"] == _DON_INDEX
    assert len(warnings) == 1
    assert classified[0]["docType"] == "other"
    assert classified[0]["source"] == "unknown"
    assert classified[0].get("routedTo") == _DON_INDEX


def test_llm_first_no_rule_fallback():
    # LLM-first tuyệt đối: không còn hàm rule keyword, không hardcode Bản chính/Bản sao.
    assert not hasattr(planner, "_rule_doc_type")
    assert not hasattr(planner, "_LOAI_BAN")


def test_attach_prompt_lists_procedure_specific_doc_types():
    for token in (
        "don_dang_ky",
        "authorization",
        "giay_to_dieu_137",
        "thua_ke_chuyen_quyen",
        "giao_dat_khong_dung_tham_quyen",
        "thua_dat_lien_ke",
        "van_ban_thanh_vien_ho_gia_dinh",
        "manh_trich_do",
        "ho_so_thiet_ke_xay_dung",
        "quyet_dinh_xu_phat",
        "chung_tu_tai_chinh",
        "to_khai_thue",
        "giay_to_chuyen_quyen",
        "giay_xac_nhan_xay_dung",
        "thoa_thuan_cap_chung",
        "xac_nhan_cmnd_cccd",
        "Mẫu số 15",
        "khoản 4 Điều 45",
        "Thông báo xác nhận kết quả đăng ký đất đai",
    ):
        assert token in SYSTEM_PROMPT
    # Mọi docType khai trong planner phải được prompt liệt kê, nếu không LLM không bao giờ trả ra.
    for doc_type in planner._ROUTES:
        assert doc_type in SYSTEM_PROMPT


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
        {
            "name": "Don_NoiDungDangKy",
            "value": "Đề nghị đăng ký đất đai và cấp Giấy chứng nhận quyền sử dụng đất lần đầu",
        },
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
        "Đề nghị đăng ký đất đai và cấp Giấy chứng nhận quyền sử dụng đất lần đầu"
    )
    assert "data[note]" not in values  # ghi chú tự sinh đã bỏ theo yêu cầu


def test_mapper_authorized_keeps_owner_facts_only_name_is_submitter():
    """Form Quảng Ngãi CHỈ có đúng một ô về người nộp: 'Họ và tên người nộp hồ sơ' (data[fullname]).
    Toàn bộ panel 'Thông tin chung' (định danh, điện thoại, địa chỉ...) là của CHỦ HỒ SƠ, kể cả khi có
    ủy quyền — không được ghi nhân thân người được ủy quyền vào các ô đó."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_NgaySinh", "value": "01/02/1980"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "000000000002"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000002"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Phường Nghĩa Lộ", "diaChi": "Số 1"},
        },
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
        {"name": "NguoiNop_NgaySinh", "value": "03/04/1995"},
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
        {
            "name": "NguoiNop_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Phường Cẩm Thành", "diaChi": "Số 1"},
        },
    ]

    values = _values(mapper.enrich(source)[0])

    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[identityNumber]"] == "000000000001"
    assert values["data[phoneNumber]"] == "0900000001"
    assert values["data[district]"] == "Phường Cẩm Thành"
    # Không ủy quyền: người nộp CHÍNH LÀ chủ hồ sơ -> ô "SĐT ủy quyền" dùng luôn số chủ hồ sơ.
    # Người nộp = chủ hồ sơ -> KHÔNG có việc ủy quyền nên ô "SĐT ủy quyền" phải TRỐNG (không fallback).
    assert "data[phoneNumber1]" not in values


def test_phone1_two_branches_and_never_borrowed():
    """data[phoneNumber1] = 'Số điện thoại ủy quyền'. Tự nộp (người nộp = chủ hồ sơ) -> ô này để TRỐNG, KHÔNG fallback. Có ủy quyền -> số BÊN ĐƯỢC ỦY QUYỀN; đọc không ra thì để TRỐNG, KHÔNG mượn số chủ hồ sơ."""
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
    """Thủ tục LÀ về đất -> có khối THỬA ĐẤT: data[diaChiThuaDat]/province2/village2/nation2."""
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
                "xa": "Phường Nghĩa Lộ",
                "diaChi": "Thửa số 000, tờ bản đồ số 00, đường Y",
            },
        },
    ]

    values = _values(mapper.enrich(source)[0])

    assert values["data[diaChiThuaDat]"] == "Thửa số 000, tờ bản đồ số 00, đường Y"
    assert values["data[province2]"] == "Tỉnh Quảng Ngãi"
    assert values["data[village2]"] == "Phường Nghĩa Lộ"
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
    """Cổng Quảng Ngãi KHÔNG có các ô này (đã grep 'đki dd fill.html' — 23 ô data[...]) -> không phát.
    Đây là điểm KHÁC bản Ninh Bình cùng tên thủ tục, đừng copy nhầm."""
    absent = (
        "data[isOwnerDossier]",
        "data[organization]",
        "data[hoTen]",
        "data[soCCCD]",
        "data[diaChi]",
        "data[district2]",
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


def test_ui_field_set_matches_quang_ngai_template():
    """Form dùng ĐÚNG template 23 ô data[...] của cổng Quảng Ngãi, trừ 2 ô hành chính -> 21 ô."""
    assert len(UI_COMP_BY_NAME) == 21
    assert {"data[phoneNumber1]", "data[diaChiThuaDat]", "data[province2]", "data[village2]",
            "data[nation2]"} <= set(UI_COMP_BY_NAME)


def test_schema_and_prompt_cover_parcel_and_notarization_lesson():
    names = {field["name"] for field in FIELDS}
    assert {"ChuHoSo_HoTen", "NguoiNop_HoTen", "Don_NoiDungDangKy", "ThuaDat_DiaChi"} <= names

    parcel = next(field for field in FIELDS if field["name"] == "ThuaDat_DiaChi")
    assert "ĐỊA CHỈ THỬA ĐẤT" in parcel["desc"]
    assert "không lấy địa chỉ cư trú" in parcel["desc"]

    # Nội dung đăng ký LẦN ĐẦU, không phải biến động/đính chính/cấp đổi.
    noi_dung = next(field for field in FIELDS if field["name"] == "Don_NoiDungDangKy")
    assert "Mẫu số 15" in noi_dung["desc"]
    assert "CẤP GIẤY CHỨNG NHẬN" in noi_dung["desc"]
    assert "KHÔNG PHẢI nội dung đăng ký biến động" in noi_dung["desc"]
    assert "lần đầu" in EXTRA_RULES
    assert "KHÔNG PHẢI nội dung đăng ký biến động" in EXTRA_RULES

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
    # Rule 8b SỐ ĐIỆN THOẠI của cổng Quảng Ngãi (bug thật ở thủ tục giao đất cùng cổng).
    assert "SỐ ĐIỆN THOẠI — PHẢI LẤY" in EXTRA_RULES
    assert "MẶC NHIÊN là số của người đó" in EXTRA_RULES
    phone_desc = next(f["desc"] for f in FIELDS if f["name"] == "ChuHoSo_DienThoai")
    assert "PHẢI lấy khi hồ sơ có" in phone_desc


# --------------------------------------------------------------------------------------
# REGISTRY
# --------------------------------------------------------------------------------------
def test_registry_has_scoped_procedure_and_both_pipelines():
    procedure = get_procedure(_KEY)

    assert procedure is not None
    assert procedure["label"].startswith(
        "[Tỉnh Quảng Ngãi] Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử "
        "dụng đất, quyền sở hữu tài sản gắn liền với đất lần đầu"
    )
    assert procedure["label"].endswith("người gốc Việt Nam định cư ở nước ngoài")
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


def test_detect_scope_isolates_quang_ngai_from_ninh_binh():
    """TÊN THỦ TỤC TRÙNG KHÍT bản Ninh Bình -> urlScope là thứ DUY NHẤT chống tráo hai tỉnh.
    Cụm textIncludes của hai entry giống nhau nên nếu một bên mất urlScope là cướp trang của bên kia."""
    quang_ngai = get_procedure(_KEY) or {}
    ninh_binh = get_procedure("dang-ky-dat-dai-lan-dau-ninh-binh") or {}

    qn_detect = quang_ngai.get("detect", {})
    nb_detect = ninh_binh.get("detect", {})
    assert qn_detect.get("urlScope") == ["dichvucong.quangngai.gov.vn"]
    assert nb_detect.get("urlScope") == ["dichvucong.ninhbinh.gov.vn"]
    assert set(qn_detect["urlScope"]).isdisjoint(nb_detect["urlScope"])
    # Nhãn hai tỉnh chỉ khác đúng tiền tố [Tỉnh ...] -> không thể dựa vào label/heading để tách.
    assert quang_ngai["label"].split("]", 1)[1] == ninh_binh["label"].split("]", 1)[1]


def test_detect_text_isolates_from_sibling_quang_ngai_procedures():
    """Ba thủ tục cùng host quangngai phải có cụm text đôi một khác nhau, nếu không sẽ cướp trang."""
    keys = (
        _KEY,
        "giao-thue-chuyen-muc-dich-dat-quang-ngai",
        "ho-tro-chi-phi-hoa-tang-quang-ngai",
    )
    phrases = {}
    for key in keys:
        detect = (get_procedure(key) or {}).get("detect", {})
        assert detect.get("urlScope") == ["dichvucong.quangngai.gov.vn"]
        assert detect.get("textPriority") is True
        assert detect.get("headingDisabled") is True
        phrases[key] = " ".join(detect.get("textIncludes") or [])
        assert phrases[key], f"{key} thiếu textIncludes -> không tách được trên cùng host"

    for key, phrase in phrases.items():
        for other_key, other_phrase in phrases.items():
            if key == other_key:
                continue
            # Không cụm nào được là con của cụm khác (FE khớp substring trên body).
            assert phrase not in other_phrase
