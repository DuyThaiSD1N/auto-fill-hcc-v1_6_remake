"""Unit test "[Quảng Ngãi] Tính hoặc tính lại tiền sử dụng đất (khoản 2 Điều 12 NĐ 50/2026/NĐ-CP)" (1.115148).

Điền: form Form.io 23 ô của cổng Quảng Ngãi. Đính kèm: bảng không có danh mục sẵn → 3 dòng tạo bằng
"+ Thêm giấy tờ": Đơn đề nghị (đính chung Bản cam kết + GCN), Thông báo nộp tiền, Biên lai.
"""

from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_quang_ngai.attach import planner
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_quang_ngai.attach.prompt import SYSTEM_PROMPT
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_quang_ngai.process import mapper
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_quang_ngai.process.prompt import EXTRA_RULES
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_quang_ngai.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures import ke_khai_links
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "tinh-tien-su-dung-dat-nd-50-2026-quang-ngai"
_DON_ROW = "Đơn đề nghị tính lại tiền sử dụng đất"
_THONG_BAO_ROW = "Bản sao thông báo nộp tiền sử dụng đất"
_BIEN_LAI_ROW = "Biên lai đã nộp tiền vào Ngân sách nhà nước"

_NOI_DUNG = (
    "Tôi nhận thấy hồ sơ/thửa đất của tôi thuộc trường hợp được xem xét tính lại tiền sử dụng đất. "
    "Do đó, tôi kính đề nghị UBND Phường An Hòa xem xét tính tiền sử dụng đất theo quy định."
)

# PDF gộp: Đơn (tr.1–2) + Bản cam kết (tr.3) + GCN (tr.4–5). Mục 4 của Đơn nhắc "giấy chứng nhận" thường.
_DON_GOP_TEXT = (
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐỀ NGHỊ TÍNH LẠI TIỀN SỬ DỤNG ĐẤT\n"
    "1. Thông tin người sử dụng đất: NGUYỄN VĂN BA\n4. Giấy tờ liên quan kèm theo: a. Bản sao giấy chứng "
    "nhận quyền sử dụng đất; b. Bản sao thông báo nộp tiền sử dụng đất\n"
    "BẢN CAM KẾT\nTên tôi là: Nguyễn Văn Ba\n"
    "GIẤY CHỨNG NHẬN\nQUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU TÀI SẢN GẮN LIỀN VỚI ĐẤT"
)


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


# --------------------------------------------------------------------------------------
# REGISTRY
# --------------------------------------------------------------------------------------
def test_registry_wires_fill_and_attach():
    proc = get_procedure(_KEY)
    assert proc["mode"] == "agent" and proc["hasAttachmentStep"] is True
    assert proc["detect"]["urlScope"] == ["dichvucong.quangngai.gov.vn"]
    assert get_pipeline(_KEY) is not None
    assert get_attach_pipeline(_KEY) is not None
    # Key trùng ke_khai_links để chọn ở panel là vào đúng pipeline.
    assert any(link["key"] == _KEY and link["code"] == "1.115148" for link in ke_khai_links.KE_KHAI_LINKS)


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM
# --------------------------------------------------------------------------------------
def test_combined_don_file_goes_whole_to_don_row():
    files = _files(["ho-so-gop.pdf"])
    ocr = [{"name": "ho-so-gop.pdf", "text": _DON_GOP_TEXT}]

    attachments, warnings, classified = planner.build_plan_items(files, ocr, {0: "don_de_nghi"})

    assert len(attachments) == 1
    item = attachments[0]
    assert item["componentName"] == _DON_ROW and item["loaiBan"] == "Bản chính"
    assert item["target"] == "add-document-dialog" and item["needsAddComponent"] is True
    assert item["documentName"] == "Đơn đề nghị + Bản cam kết + Bản sao Giấy chứng nhận"
    assert "sourceSegments" not in item  # không tách trang
    assert classified[0]["docType"] == "don_de_nghi"
    # Thiếu thông báo nộp tiền + biên lai (mục 4.b, 4.c) → nhắc bổ sung.
    assert any(_THONG_BAO_ROW in w for w in warnings)
    assert any(_BIEN_LAI_ROW in w for w in warnings)


def test_rows_order_and_loai_ban():
    files = _files(["bien-lai.pdf", "thong-bao.pdf", "gcn.pdf", "don.pdf", "cccd.pdf"])
    llm = {0: "bien_lai_nop_tien", 1: "thong_bao_nop_tien", 2: "giay_chung_nhan", 3: "don_de_nghi", 4: "identity"}

    attachments, warnings, _ = planner.build_plan_items(files, [], llm)

    assert [a["fileName"] for a in attachments] == ["gcn.pdf", "don.pdf", "cccd.pdf", "thong-bao.pdf", "bien-lai.pdf"]
    assert [a["componentName"] for a in attachments] == [_DON_ROW] * 3 + [_THONG_BAO_ROW, _BIEN_LAI_ROW]
    assert [a["loaiBan"] for a in attachments] == ["Bản chính"] * 3 + ["Bản sao", "Bản sao"]
    assert all(a["target"] == "add-document-dialog" for a in attachments)
    # Ô "Giấy tờ" của modal là danh sách chọn cố định → mỗi dòng mang gợi ý chọn mục danh mục.
    assert attachments[0]["formOptionHints"][0] == "Đơn đề nghị tính lại tiền sử dụng đất"
    assert all(a["formOptionHints"] for a in attachments)
    assert warnings == []


def test_unknown_file_attached_to_don_row_with_original_name():
    files = _files(["don.pdf", "la.pdf"])

    attachments, warnings, classified = planner.build_plan_items(files, [], {0: "don_de_nghi", 1: "other"})

    other = next(a for a in attachments if a["fileName"] == "la.pdf")
    assert other["componentName"] == _DON_ROW and other["documentName"] == "la.pdf"
    assert any("la.pdf" in w for w in warnings)
    assert classified[1]["docType"] == "other"


def test_rule_fallback_only_when_llm_missing():
    files = _files(["a.pdf", "b.pdf"])
    ocr = [
        {"name": "a.pdf", "text": "THÔNG BÁO NỘP TIỀN SỬ DỤNG ĐẤT\nGiấy chứng nhận quyền sử dụng đất số CN 1"},
        {"name": "b.pdf", "text": "ĐƠN ĐỀ NGHỊ TÍNH LẠI TIỀN SỬ DỤNG ĐẤT"},
    ]

    attachments, _, classified = planner.build_plan_items(files, ocr, {1: "other"})

    assert classified[0] == {**classified[0], "docType": "thong_bao_nop_tien", "source": "rule"}
    # LLM đã trả other thì không để rule ghi đè.
    assert classified[1]["docType"] == "other"
    assert {a["fileName"]: a["componentName"] for a in attachments}["a.pdf"] == _THONG_BAO_ROW


def test_prompt_lists_every_doc_type():
    for doc_type in planner._ROUTES:
        assert doc_type in SYSTEM_PROMPT


# --------------------------------------------------------------------------------------
# ĐIỀN (mapper)
# --------------------------------------------------------------------------------------
def _source(**extra) -> list[dict]:
    base = {
        "ChuHoSo_HoTen": "Nguyễn Văn Ba",
        "ChuHoSo_NgaySinh": "05/06/1960",
        "ChuHoSo_GioiTinh": "Nam",
        "ChuHoSo_SoDinhDanh": "000 160 000 111",
        "ChuHoSo_NgayCap": "10.10.2021",
        "ChuHoSo_NoiCap": "Cục Cảnh sát QLHC về TTXH",
        "ChuHoSo_DienThoai": "0900.000.111",
        "ChuHoSo_DonDiaChi": {"quocGia": "Việt Nam", "tinh": "T. Quảng Ngãi", "xa": "P. Cẩm Thành", "diaChi": "12/3 Lê Lợi"},
        "NguoiNop_HoTen": "Nguyễn Văn Ba",
        "Don_NoiDungDeNghi": _NOI_DUNG,
        "ThuaDat_SoThua": "45",
        "ThuaDat_SoTo": "9",
        "ThuaDat_DiaChi": {"quocGia": "Việt Nam", "tinh": "Tỉnh Quảng Ngãi", "xa": "Phường Cẩm Thành", "diaChi": ""},
    }
    base.update(extra)
    return [{"name": name, "value": value} for name, value in base.items()]


def test_mapper_owner_self_submits():
    fields, warnings = mapper.enrich(_source(), {})
    values = _values(fields)

    assert warnings == []
    assert values["data[ownerFullname]"] == "Nguyễn Văn Ba"
    assert values["data[fullname]"] == "Nguyễn Văn Ba"
    assert values["data[birthday]"] == "05/06/1960"
    assert values["data[identityNumber]"] == "000160000111"
    assert values["data[identityDate]"] == "10/10/2021"
    assert values["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[phoneNumber]"] == "0900000111"
    # Ô bắt buộc "Số điện thoại ủy quyền": tự nộp → nhập lại số chủ hồ sơ.
    assert values["data[phoneNumber1]"] == "0900000111"
    assert values["data[chonDoiTuong]"] == "Cá nhân"
    assert values["data[province]"] == "Tỉnh Quảng Ngãi"
    assert values["data[district]"] == "Phường Cẩm Thành"
    assert values["data[address]"] == "12/3 Lê Lợi"
    assert values["data[noidungyeucaugiaiquyet]"] == _NOI_DUNG
    assert values["data[diaChiThuaDat]"] == "Thửa đất số 45, tờ bản đồ số 9, phường Cẩm Thành, tỉnh Quảng Ngãi"
    assert values["data[province2]"] == "Tỉnh Quảng Ngãi"
    assert values["data[village2]"] == "Phường Cẩm Thành"
    assert values["data[nation2]"] == "Việt Nam"
    assert set(values) <= set(UI_COMP_BY_NAME)


def test_mapper_authorized_submitter_keeps_owner_block():
    fields, _ = mapper.enrich(
        _source(NguoiNop_HoTen="Trần Thị Bốn", NguoiNop_DienThoai="0911222333"), {}
    )
    values = _values(fields)

    assert values["data[ownerFullname]"] == "Nguyễn Văn Ba"
    assert values["data[fullname]"] == "Trần Thị Bốn"
    assert values["data[phoneNumber]"] == "0900000111"
    assert values["data[phoneNumber1]"] == "0911222333"


def test_mapper_parcel_never_borrows_residence():
    source = [f for f in _source() if f["name"] not in ("ThuaDat_DiaChi", "ThuaDat_SoThua", "ThuaDat_SoTo")]

    values = _values(mapper.enrich(source, {})[0])

    assert not {"data[diaChiThuaDat]", "data[province2]", "data[village2]"} & set(values)


def test_schema_and_prompt_guard_known_traps():
    names = {field["name"] for field in FIELDS}
    assert {"ChuHoSo_DonDiaChi", "Don_NoiDungDeNghi", "ThuaDat_DiaChi", "ThuaDat_SoThua"} <= names
    # Ngày cấp GCN không được lẫn vào ngày cấp CCCD.
    assert "ngày cấp GCN" in EXTRA_RULES
    assert "Tôi cam kết chọn thửa đất" in EXTRA_RULES
