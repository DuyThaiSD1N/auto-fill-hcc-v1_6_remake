"""Test thủ tục [Tỉnh Quảng Ngãi] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót (1.012796).

Mirror bộ test của package nền xac_dinh_lai_dien_tich_dat_o_quang_ngai (cùng cổng, cùng biến thể
form 19 ô) + các điểm RIÊNG của thủ tục đính chính: bảng thành phần hồ sơ 4 dòng THẬT (không có dòng
ghi chú pháp lý), CCCD route sang dòng "Giấy tờ chứng minh sai sót".

KHÔNG chạy LLM live (môi trường test không có key): mọi test đính kèm inject sẵn llm_types.
"""

import re
import unicodedata

from app.pipelines.dinh_chinh_sai_sot_quang_ngai.attach import planner
from app.pipelines.dinh_chinh_sai_sot_quang_ngai.attach.prompt import SYSTEM_PROMPT
from app.pipelines.dinh_chinh_sai_sot_quang_ngai.process import mapper
from app.pipelines.dinh_chinh_sai_sot_quang_ngai.process.prompt import EXTRA_RULES
from app.pipelines.dinh_chinh_sai_sot_quang_ngai.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_DON_NAME = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18"
_DON_INDEX = 0
_GCN_NAME = "Bản gốc Giấy chứng nhận đã cấp"
_GCN_INDEX = 1
_PROOF_NAME = "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận"
_PROOF_INDEX = 2
_UY_QUYEN_NAME = "văn bản về việc ủy quyền theo quy định của pháp luật về dân sự"
_UY_QUYEN_INDEX = 3
# Khối THỬA ĐẤT của template Quảng Ngãi — panel mặc định THU GỌN nên form thủ tục này KHÔNG render.
_PARCEL_FIELDS = ("data[diaChiThuaDat]", "data[province2]", "data[village2]", "data[nation2]")
_KEY = "dinh-chinh-sai-sot-quang-ngai"

# 4 dòng DOM thật, lấy VERBATIM từ cột "Tên giấy tờ" của 'đính chính đính kèm.html'.
_ROWS = [
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
    "- Bản gốc Giấy chứng nhận đã cấp;",
    "- Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận so với thông tin tại "
    "thời điểm đề nghị đính chính hoặc sai sót thông tin về thửa đất, tài sản gắn liền với đất so "
    "với thông tin trên Giấy chứng nhận đã cấp",
    "- Trường hợp người sử dụng đất, chủ sở hữu tài sản gắn liền với đất thực hiện thủ tục thông qua "
    "người đại diện theo quy định của pháp luật về dân sự thì phải có văn bản về việc ủy quyền theo "
    "quy định của pháp luật về dân sự",
]


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _ocr(files: list[dict]) -> list[dict]:
    return [{"name": item["name"], "text": "ocr"} for item in files]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row, 4 dòng DOM — tất cả đều là giấy tờ thật)
# --------------------------------------------------------------------------------------
def test_core_doc_types_route_to_their_own_rows():
    """Đơn/GCN/giấy tờ chứng minh sai sót/ủy quyền có dòng riêng; CCCD đi vào dòng chứng minh sai sót."""
    files = _files(["don.pdf", "gcn.pdf", "khai-sinh.pdf", "uy-quyen.pdf", "cccd.pdf"])
    llm_types = {
        0: "don_bien_dong",
        1: "land_certificate",
        2: "giay_to_chung_minh_sai_sot",
        3: "authorization",
        4: "identity",
    }

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    assert [item["componentIndex"] for item in attachments] == [0, 1, 2, 3, 2]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    # KHÔNG set Bản chính/Bản sao: cán bộ tự chọn (dòng 1 còn có cả "1 Bản photo").
    assert all("loaiBan" not in item for item in attachments)
    assert [item["docType"] for item in classified] == list(llm_types.values())
    assert attachments[0]["componentName"] == _DON_NAME
    assert attachments[1]["componentName"] == _GCN_NAME
    assert attachments[2]["componentName"] == _PROOF_NAME
    assert attachments[3]["componentName"] == _UY_QUYEN_NAME
    # CCCD dùng CHUNG dòng chứng minh sai sót nhưng documentName vẫn phân biệt để cán bộ đối chiếu.
    assert attachments[4]["componentName"] == _PROOF_NAME
    assert "Căn cước công dân" in attachments[4]["documentName"]
    assert attachments[4]["documentName"] != attachments[2]["documentName"]


def test_every_dedicated_row_reachable_with_expected_index():
    """Mỗi docType trỏ đúng dòng (componentIndex = STT − 1 theo bảng HTML 4 dòng DOM)."""
    expected = {
        "don_bien_dong": _DON_INDEX,
        "land_certificate": _GCN_INDEX,
        "giay_to_chung_minh_sai_sot": _PROOF_INDEX,
        "identity": _PROOF_INDEX,
        "authorization": _UY_QUYEN_INDEX,
    }
    files = _files([f"{name}.pdf" for name in expected])
    llm_types = dict(enumerate(expected))

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    assert {item["detectedType"]: item["componentIndex"] for item in attachments} == expected
    # Mỗi file chỉ sinh ĐÚNG một plan item (không nhân bản một tài liệu sang nhiều dòng).
    assert len(attachments) == len(expected)


def test_cccd_goes_to_error_proof_row_not_don_row():
    """Điểm RIÊNG của thủ tục đính chính (theo ảnh ánh xạ): CCCD là CHỨNG CỨ đối chiếu tên đúng với
    tên sai trên Giấy chứng nhận -> phải nằm ở dòng 'Giấy tờ chứng minh sai sót', KHÔNG phải dòng Đơn
    (để dòng đó trống là hồ sơ bị trả lại)."""
    files = _files(["cccd.pdf"])

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), {0: "identity"})

    assert warnings == []
    assert attachments[0]["componentIndex"] == _PROOF_INDEX
    assert attachments[0]["componentName"] == _PROOF_NAME
    assert attachments[0]["componentIndex"] != _DON_INDEX


def test_table_has_no_note_rows_and_no_duplicate_rows():
    """Khóa cứng cấu trúc bảng: 4 dòng DOM, KHÔNG có dòng ghi chú pháp lý (khác thủ tục xác định lại
    diện tích đất ở cùng cổng) và KHÔNG có dòng trùng text. Cổng đổi bảng thì test này vỡ trước."""
    assert planner._ROW_COUNT == len(_ROWS) == 4
    assert planner._NOTE_ROW_INDEXES == set()

    folded = [_fold(row) for row in _ROWS]
    assert len(set(folded)) == len(folded), "bảng có dòng trùng text -> phải chỉ route DÒNG CHÍNH"
    for row in folded:
        assert "khi nop cac giay to quy dinh" not in row
        assert "truong hop nop ban sao hoac ban so hoa" not in row

    used = {route["index"] for route in planner._ROUTES.values()}
    assert used == {_DON_INDEX, _GCN_INDEX, _PROOF_INDEX, _UY_QUYEN_INDEX}
    assert used.isdisjoint(planner._NOTE_ROW_INDEXES)
    assert max(used) < planner._ROW_COUNT

    # Kể cả khi mọi file đều không nhận diện được, không file nào rơi ra ngoài 4 dòng thật.
    files = _files(["a.pdf", "b.pdf", "c.pdf"])
    attachments, _, _ = planner.build_plan_items(files, _ocr(files), {})
    assert {item["componentIndex"] for item in attachments} <= used


def test_component_names_are_verbatim_and_do_not_cross_match():
    """FE khớp componentName bằng substring hai chiều sau khi fold dấu -> mỗi chuỗi phải chỉ trúng
    đúng dòng của nó trong 4 dòng thật trên 'đính chính đính kèm.html'."""
    folded_rows = [_fold(row) for row in _ROWS]
    for name, index in (
        (_DON_NAME, _DON_INDEX),
        (_GCN_NAME, _GCN_INDEX),
        (_PROOF_NAME, _PROOF_INDEX),
        (_UY_QUYEN_NAME, _UY_QUYEN_INDEX),
    ):
        want = _fold(name)
        hits = [
            i for i, row in enumerate(folded_rows)
            if row == want or want in row or row in want
        ]
        assert hits == [index], f"{name!r} khớp {hits}, mong đợi [{index}]"


def test_other_is_routed_to_don_row_not_skipped():
    """File 'other' KHÔNG bị bỏ: bảng không có dòng 'Giấy tờ khác' -> đính CHUNG dòng Đơn Mẫu số 18,
    giữ TÊN FILE GỐC làm documentName; vẫn cảnh báo để cán bộ soát."""
    files = _files(["don.pdf", "xac-nhan-cu-tru.pdf"])

    attachments, warnings, classified = planner.build_plan_items(
        files, _ocr(files), {0: "don_bien_dong", 1: "other"}
    )

    other_item = next(item for item in attachments if item["fileIndex"] == 1)
    assert other_item["componentIndex"] == _DON_INDEX
    assert other_item["componentName"] == _DON_NAME
    assert other_item["detectedType"] == "other"
    assert other_item["documentName"] == "xac-nhan-cu-tru.pdf"  # giữ tên gốc
    assert len(warnings) == 1 and "xac-nhan-cu-tru.pdf" in warnings[0]
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
    assert not hasattr(planner, "_is_identity_text")
    assert not hasattr(planner, "_LOAI_BAN")


def test_attach_prompt_lists_procedure_specific_doc_types():
    for token in (
        "don_bien_dong",
        "land_certificate",
        "giay_to_chung_minh_sai_sot",
        "identity",
        "authorization",
        "Mẫu số 18",
        "Mẫu số 11/ĐK",
        "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
    ):
        assert token in SYSTEM_PROMPT
    # Mọi docType khai trong planner phải được prompt liệt kê, nếu không LLM không bao giờ trả ra.
    for doc_type in planner._ROUTES:
        assert doc_type in SYSTEM_PROMPT
    # Thẻ căn cước vẫn phải trả "identity" (planner tự định tuyến), không được tự đổi sang chứng cứ.
    assert "vẫn phải trả \"identity\"" in SYSTEM_PROMPT


# --------------------------------------------------------------------------------------
# PROCESS (mapper 2 vai, KHÔNG có khối thửa đất)
# --------------------------------------------------------------------------------------
def test_mapper_owner_self_submits():
    """Không ủy quyền: người nộp = chủ hồ sơ, khối định danh lấy fact chủ hồ sơ."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NgaySinh", "value": "26/07/1990"},
        {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "000 000 000 001"},
        {"name": "ChuHoSo_DienThoai", "value": "0900.000.001"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Quảng Ngãi",
                "xa": "Xã An Phú",
                "diaChi": "Số 1 đường X, Tổ 1",
            },
        },
        {
            "name": "Don_NoiDungDeNghi",
            "value": "Đề nghị đính chính họ tên người sử dụng đất trên Giấy chứng nhận đã cấp",
        },
    ]

    fields, errors = mapper.enrich(source)
    values = _values(fields)

    assert errors == []
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[identityNumber]"] == "000000000001"
    assert values["data[phoneNumber]"] == "0900000001"  # bỏ dấu chấm trong số điện thoại trên đơn
    assert values["data[province]"] == "Tỉnh Quảng Ngãi"
    assert values["data[district]"] == "Xã An Phú"
    assert values["data[address]"] == "Số 1 đường X, Tổ 1"
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "Đề nghị đính chính họ tên người sử dụng đất trên Giấy chứng nhận đã cấp"
    )
    # Ghi chú tự sinh đã BỎ theo yêu cầu -> không phát data[note] nữa.
    assert "data[note]" not in values


def test_mapper_authorized_keeps_owner_facts_only_name_is_submitter():
    """Form Quảng Ngãi CHỈ có đúng một ô về người nộp: 'Họ và tên người nộp hồ sơ' (data[fullname]).
    Toàn bộ khối 'Thông tin chủ hồ sơ' (định danh, điện thoại, địa chỉ...) là của CHỦ HỒ SƠ, kể cả
    khi có ủy quyền — không được ghi nhân thân người được ủy quyền vào các ô đó."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_NgaySinh", "value": "01/02/1980"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "000000000002"},
        {"name": "ChuHoSo_DienThoai", "value": "0900000002"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Xã Ba Tơ", "diaChi": "Số 1"},
        },
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
        {"name": "NguoiNop_NgaySinh", "value": "03/04/1995"},
        {"name": "NguoiNop_SoDinhDanh", "value": "000000000003"},
        {"name": "NguoiNop_DienThoai", "value": "0900000003"},
        {
            "name": "NguoiNop_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Xã Mộ Đức", "diaChi": "Số 9"},
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
    assert values["data[district]"] == "Xã Ba Tơ"
    # Số/ngày sinh/địa chỉ của người nộp CHỈ được phép xuất hiện ở ô SĐT ủy quyền, không ở đâu khác.
    other_values = [value for name, value in values.items() if name != "data[phoneNumber1]"]
    assert "000000000003" not in str(other_values)
    assert "03/04/1995" not in str(other_values)
    assert "Số 9" not in str(other_values)


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
            "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Xã An Phú", "diaChi": "Số 1"},
        },
    ]

    values = _values(mapper.enrich(source)[0])

    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[identityNumber]"] == "000000000001"
    assert values["data[phoneNumber]"] == "0900000001"
    assert values["data[district]"] == "Xã An Phú"
    # Người nộp = chủ hồ sơ -> KHÔNG có việc ủy quyền nên ô "SĐT ủy quyền" phải TRỐNG (không fallback).
    assert "data[phoneNumber1]" not in values


def test_phone1_two_branches_and_never_borrowed():
    """data[phoneNumber1] = 'Số điện thoại ủy quyền'. Tự nộp (người nộp = chủ hồ sơ) -> ô này để
    TRỐNG, KHÔNG fallback. Có ủy quyền -> số BÊN ĐƯỢC ỦY QUYỀN; đọc không ra thì để TRỐNG, KHÔNG mượn
    số chủ hồ sơ."""
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


def test_parcel_block_never_declared_nor_emitted():
    """KHÓA CỨNG: trang điền 'đính chính fill.html' CHỈ có 19 ô data[...]; panel 'Địa chỉ thửa đất/
    địa chỉ xây dựng' ở trạng thái THU GỌN nên 4 ô diaChiThuaDat/province2/village2/nation2 KHÔNG
    render. Không được khai trong UI_COMP_BY_NAME, không được phát ra, và schema cũng KHÔNG có field
    nguồn ThuaDat_DiaChi."""
    for name in _PARCEL_FIELDS + ("data[district2]",):
        assert name not in UI_COMP_BY_NAME

    # Không có field nguồn địa chỉ thửa đất -> LLM không được yêu cầu đọc, mapper không có đường phát.
    assert "ThuaDat_DiaChi" not in {field["name"] for field in FIELDS}
    assert not any("ThuaDat" in field["name"] for field in FIELDS)

    # Kể cả khi upstream lỡ nhét fact thửa đất vào, mapper vẫn KHÔNG phát khối này.
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Xã An Phú", "diaChi": "Số 1"},
        },
        {
            "name": "ThuaDat_DiaChi",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Quảng Ngãi",
                "xa": "Xã Ba Tơ",
                "diaChi": "Thửa số 000, tờ bản đồ số 00",
            },
        },
    ]
    values = _values(mapper.enrich(source)[0])
    for name in _PARCEL_FIELDS:
        assert name not in values
    # Khối cư trú KHÔNG bị địa chỉ thửa đất ghi đè.
    assert values["data[district]"] == "Xã An Phú"
    assert values["data[address]"] == "Số 1"


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
    """Cổng Quảng Ngãi KHÔNG có các ô này (đó là ô của cổng Ninh Bình) -> không phát."""
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
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
        {"name": "NguoiNop_SoDinhDanh", "value": "000000000003"},
    ]
    values = _values(mapper.enrich(source)[0])
    for name in absent:
        assert name not in values


def test_ui_field_set_matches_19_field_form():
    """Form có ĐÚNG 19 ô data[...]; trừ 2 ô hành chính -> khai 17 ô.
    (data[note] vẫn KHAI nhưng mapper cố ý KHÔNG phát — ghi chú tự sinh đã bỏ theo yêu cầu.)"""
    assert len(UI_COMP_BY_NAME) == 17
    assert "data[phoneNumber1]" in UI_COMP_BY_NAME
    expected = {
        "data[ownerFullname]", "data[fullname]", "data[birthday]", "data[gender]", "data[email]",
        "data[phoneNumber]", "data[phoneNumber1]", "data[identityNumber]", "data[identityDate]",
        "data[identityAgency]", "data[chonDoiTuong]", "data[nation]", "data[province]",
        "data[district]", "data[address]", "data[note]", "data[noidungyeucaugiaiquyet]",
    }
    assert set(UI_COMP_BY_NAME) == expected


def test_schema_and_prompt_cover_don_bien_dong_and_source_priority():
    names = {field["name"] for field in FIELDS}
    assert {"ChuHoSo_HoTen", "NguoiNop_HoTen", "Don_NoiDungDeNghi"} <= names

    # Đơn của thủ tục này là Mẫu số 18 (cổng treo Mus18DKBD.docx), KHÔNG phải Mẫu số 15 của lần đầu.
    noi_dung = next(field for field in FIELDS if field["name"] == "Don_NoiDungDeNghi")
    assert "Mẫu số 18" in noi_dung["desc"]
    assert "ĐÍNH CHÍNH" in noi_dung["desc"]
    assert "KHÔNG lấy tiêu đề thủ tục" in noi_dung["desc"]
    assert "KHÔNG PHẢI nội dung đăng ký đất đai lần" in noi_dung["desc"]
    assert "KHÔNG PHẢI xác định lại diện tích đất ở" in noi_dung["desc"]
    assert "Mẫu số 15" not in noi_dung["desc"]
    assert "Mẫu số 15" not in EXTRA_RULES
    assert "Mẫu số 18" in EXTRA_RULES
    assert "ĐÍNH CHÍNH GIẤY CHỨNG NHẬN ĐÃ CẤP LẦN ĐẦU CÓ SAI SÓT" in EXTRA_RULES

    # Rule NƠI CƯ TRÚ: ưu tiên ĐƠN (mẫu nào cũng nhận) -> ... -> CCCD là nguồn CUỐI.
    assert "QUY TẮC NƠI CƯ TRÚ" in EXTRA_RULES
    assert "KHÔNG đòi đúng một số hiệu mẫu" in EXTRA_RULES
    assert "CUỐI CÙNG mới đến địa chỉ trên giấy tờ tùy thân" in EXTRA_RULES
    assert "CCCD/CMND là nguồn CUỐI" in EXTRA_RULES
    assert "sắp xếp đơn vị hành chính" in EXTRA_RULES
    assert "nghe giống địa danh của tỉnh cũ" in EXTRA_RULES
    cu_tru = next(field for field in FIELDS if field["name"] == "ChuHoSo_NoiCuTru")
    assert "CUỐI CÙNG mới đến CCCD" in cu_tru["desc"]
    assert "không đòi đúng một số hiệu mẫu" in cu_tru["desc"]

    # Rule LỜI CHỨNG THỰC: cấm theo VAI, KHÔNG cấm đọc phần chứng thực.
    assert "LỜI CHỨNG THỰC" in EXTRA_RULES
    assert "cán bộ thực hiện chứng thực" in EXTRA_RULES
    assert "danh sách người ký trong lời chứng" in EXTRA_RULES
    assert "quét lại TOÀN BỘ tài liệu" in EXTRA_RULES
    assert "không mượn của người khác" in EXTRA_RULES
    gioi_tinh = next(field for field in FIELDS if field["name"] == "NguoiNop_GioiTinh")
    assert "LỜI CHỨNG THỰC" in gioi_tinh["desc"]

    # Rule 9b SỐ ĐIỆN THOẠI "PHẢI LẤY khi hồ sơ có" (bug thật ở các thủ tục cùng cổng).
    assert "SỐ ĐIỆN THOẠI — PHẢI LẤY" in EXTRA_RULES
    assert "MẶC NHIÊN là số của người đó" in EXTRA_RULES
    phone_desc = next(f["desc"] for f in FIELDS if f["name"] == "ChuHoSo_DienThoai")
    assert "PHẢI lấy khi hồ sơ có" in phone_desc

    # Form không có ô địa chỉ thửa đất -> prompt phải cấm đẩy địa chỉ thửa đất vào nơi cư trú.
    assert "KHÔNG CÓ Ô ĐỊA CHỈ THỬA ĐẤT" in EXTRA_RULES

    # Bẫy RIÊNG của thủ tục đính chính: người đứng đơn ≠ người bị sai thông tin.
    assert "NGƯỜI ĐỨNG ĐƠN ≠ NGƯỜI BỊ SAI THÔNG TIN" in EXTRA_RULES


# --------------------------------------------------------------------------------------
# REGISTRY
# --------------------------------------------------------------------------------------
def test_registry_has_scoped_procedure_and_both_pipelines():
    procedure = get_procedure(_KEY)

    assert procedure is not None
    assert procedure["label"] == "[Tỉnh Quảng Ngãi] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["roles"] == []
    assert procedure["useDangKyBy"] is False
    assert procedure["uploadHint"]
    # URL SPA chỉ có ObjectId -> KHÔNG dùng urlIncludes, chỉ khóa host + cụm text đặc trưng.
    assert procedure["detect"]["urlScope"] == ["dichvucong.quangngai.gov.vn"]
    assert "urlIncludes" not in procedure["detect"]
    assert procedure["detect"]["textPriority"] is True
    assert procedure["detect"]["headingDisabled"] is True
    assert callable(get_pipeline(_KEY))
    assert callable(get_attach_pipeline(_KEY))


def test_detect_text_isolates_from_sibling_quang_ngai_procedures():
    """Năm thủ tục cùng host quangngai phải có cụm text đôi một khác nhau, nếu không sẽ cướp trang.
    (Đã pre-check thêm trên 10 snapshot HTML thật: mỗi trang chỉ khớp đúng một entry.)"""
    keys = (
        _KEY,
        "giao-thue-chuyen-muc-dich-dat-quang-ngai",
        "dang-ky-dat-dai-lan-dau-quang-ngai",
        "ho-tro-chi-phi-hoa-tang-quang-ngai",
        "xac-dinh-lai-dien-tich-dat-o-quang-ngai",
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
            assert _fold(phrase) not in _fold(other_phrase)


def test_detect_url_scope_isolates_from_same_named_procedures_in_other_provinces():
    """Tên thủ tục TRÙNG KHÍT với Lai Châu/Bắc Ninh/Lâm Đồng/Ninh Bình/Đà Nẵng: cụm text KHÔNG tách
    được, thứ chống tráo DUY NHẤT là urlScope -> mỗi entry phải khóa đúng host của tỉnh mình."""
    same_named = {
        _KEY: "dichvucong.quangngai.gov.vn",
        "dinh-chinh-sai-sot": "dichvucong.laichau.gov.vn",
        "dinh-chinh-sai-sot-lam-dong": "lamdong.gov.vn",
        "dinh-chinh-gcn-da-cap-ninh-binh": "dichvucong.ninhbinh.gov.vn",
        "dinh-chinh-gcn-da-cap-da-nang": "dichvucong.danang.gov.vn",
        "dinh-chinh-sai-sot-bac-ninh": "dichvucong.bacninh.gov.vn",
    }
    hosts = []
    for key, host in same_named.items():
        procedure = get_procedure(key)
        assert procedure is not None, f"thiếu entry {key}"
        scope = procedure["detect"].get("urlScope") or []
        assert scope == [host], f"{key} phải khóa host {host}, đang là {scope}"
        hosts.append(host)
    # Không hai thủ tục cùng tên nào được dùng chung host.
    assert len(set(hosts)) == len(hosts)


def test_detect_phrase_matches_only_this_procedure_label():
    """Cụm textIncludes phải nằm trong nhãn thủ tục này và KHÔNG nằm trong nhãn thủ tục Quảng Ngãi
    nào khác (nhãn thủ tục được in trên breadcrumb + ô 'Nội dung yêu cầu giải quyết' của trang đó)."""
    phrase = _fold(" ".join(get_procedure(_KEY)["detect"]["textIncludes"]))
    assert phrase in _fold(get_procedure(_KEY)["label"])
    for key in (
        "giao-thue-chuyen-muc-dich-dat-quang-ngai",
        "dang-ky-dat-dai-lan-dau-quang-ngai",
        "ho-tro-chi-phi-hoa-tang-quang-ngai",
        "xac-dinh-lai-dien-tich-dat-o-quang-ngai",
    ):
        assert phrase not in _fold(get_procedure(key)["label"])


# --------------------------------------------------------------------------------------
# ĐỊA CHỈ: field nguồn riêng lấy ĐỘC QUYỀN từ đơn, thắng địa chỉ suy từ CCCD
# --------------------------------------------------------------------------------------
_CCCD_AREA = {"quocGia": "Việt Nam", "tinh": "Tỉnh Khác", "xa": "Phường Cũ", "diaChi": "Tổ 4"}
_DON_AREA = {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Phường Nghĩa Lộ", "diaChi": "Số 1 Đường A"}


def test_don_dia_chi_thang_dia_chi_tu_cccd():
    """Bug thật: CCCD ghi nơi thường trú CŨ/khác tỉnh (trước sáp nhập), đơn ghi địa chỉ hành chính
    hiện hành -> phải theo ĐƠN."""
    got = _values(mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NoiCuTru", "value": _CCCD_AREA},
        {"name": "ChuHoSo_DonDiaChi", "value": _DON_AREA},
    ])[0])
    assert got["data[province]"] == "Tỉnh Quảng Ngãi"
    assert got["data[district]"] == "Phường Nghĩa Lộ"
    assert got["data[address]"] == "Số 1 Đường A"
    assert "Tỉnh Khác" not in str(list(got.values()))


def test_tu_nop_dung_duoc_don_dia_chi_cua_nguoi_nop():
    """Không ủy quyền: người nộp CHÍNH LÀ chủ hồ sơ nên NguoiNop_DonDiaChi dùng thay được."""
    got = _values(mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NoiCuTru", "value": _CCCD_AREA},
        {"name": "NguoiNop_DonDiaChi", "value": _DON_AREA},
    ])[0])
    assert got["data[province]"] == "Tỉnh Quảng Ngãi"


def test_co_uy_quyen_khong_lay_don_dia_chi_cua_nguoi_nop_cho_chu_ho_so():
    """Có ủy quyền: địa chỉ người được ủy quyền KHÔNG được điền vào khối chủ hồ sơ."""
    got = _values(mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "NguoiNop_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_NoiCuTru", "value": _CCCD_AREA},
        {"name": "NguoiNop_DonDiaChi", "value": _DON_AREA},
    ])[0])
    assert got["data[province]"] == "Tỉnh Khác"      # rơi về nơi cư trú chủ hồ sơ
    assert got["data[district]"] == "Phường Cũ"


def test_khong_co_don_thi_van_dung_noi_cu_tru():
    got = _values(mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NoiCuTru", "value": _CCCD_AREA},
    ])[0])
    assert got["data[province]"] == "Tỉnh Khác"


def test_don_dia_chi_fields_declared_and_exclusive_to_don():
    names = {f["name"] for f in FIELDS}
    assert {"ChuHoSo_DonDiaChi", "NguoiNop_DonDiaChi"} <= names
    desc = next(f["desc"] for f in FIELDS if f["name"] == "ChuHoSo_DonDiaChi")
    assert "TUYỆT ĐỐI KHÔNG lấy từ CCCD" in desc
    assert "BỎ FIELD" in desc
    # Hướng dẫn tách chuỗi địa chỉ viết liền trên đơn (đơn viết tay không có nhãn con).
    assert "cụm CUỐI làm tinh" in desc
    assert "Mẫu số 18" in desc
