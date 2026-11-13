import asyncio
import re
from types import SimpleNamespace

from app.pipelines._shared import fold
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_khanh_hoa.attach import planner
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_khanh_hoa.attach.prompt import SYSTEM_PROMPT
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_khanh_hoa.process import mapper
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_khanh_hoa.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_khanh_hoa.process.runner import (
    apply_printed_fallback,
)
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_khanh_hoa.process.schema import ALLOWED
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "dang-ky-bien-dong-chuyen-nhuong-thua-ke-tang-cho-khanh-hoa"
_DON_ROW = 7

_DAT = "quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất"
# Cột "Tên giấy tờ" của 13 dòng thành phần hồ sơ trên cổng Khánh Hòa, đúng thứ tự DOM (file mapping, Phần V).
_ROWS = [
    "Mảnh trích đo bản đồ địa chính thửa đất đối với trường hợp người sử dụng đất có nhu cầu đo đạc để xác định lại "
    "kích thước các cạnh, diện tích của thửa đất.",
    f"Văn bản của bên nhận thế chấp về việc đồng ý cho bên thế chấp được chuyển nhượng, tặng cho {_DAT} đối với trường "
    f"hợp chuyển nhượng, tặng cho {_DAT} mà {_DAT} đang được thế chấp và đã đăng ký tại Văn phòng đăng ký đất đai, Chi "
    "nhánh Văn phòng đăng ký đất đai.",
    "Bản gốc Giấy chứng nhận đã cấp.",
    f"Hợp đồng hoặc văn bản về việc chuyển {_DAT} đối với trường hợp chuyển đổi, chuyển nhượng, thừa kế, góp vốn bằng "
    f"{_DAT}",
    f"Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận {_DAT} đối với trường hợp có nhiều người nhận chuyển "
    f"{_DAT}.",
    "Hợp đồng hoặc văn bản về việc bán hoặc tặng cho hoặc để thừa kế hoặc góp vốn bằng tài sản gắn liền với đất theo "
    "quy định của pháp luật về dân sự đối với trường hợp đất thuê của Nhà nước theo hình thức thuê đất trả tiền hằng "
    "năm.",
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
    "Văn bản về việc cho thuê, cho thuê lại quyền sử dụng đất đối với trường hợp cho thuê, cho thuê lại quyền sử dụng "
    "đất trong dự án xây dựng kinh doanh kết cấu hạ tầng.",
    "Văn bản của người sử dụng đất đồng ý cho chủ sở hữu tài sản gắn liền với đất được chuyển nhượng, tặng cho, góp vốn "
    "bằng tài sản gắn liền với đất đối với trường hợp chuyển nhượng, tặng cho, góp vốn bằng tài sản gắn liền với đất mà "
    "chủ sở hữu tài sản không có quyền sử dụng đất đối với thửa đất đó, trừ trường hợp tổ chức nước ngoài, cá nhân nước "
    "ngoài được sở hữu nhà ở theo quy định của pháp luật về nhà ở.",
    "- Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục đăng ký đất "
    "đai, tài sản gắn liền với đất thông qua người đại diện;",
    "Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 22 ban hành kèm theo Nghị định số 151/2025/NĐ-CP đối với trường hợp "
    "đăng ký biến động đất đai mà phải tách thửa đất, hợp thửa đất.",
    "Văn bản tặng cho quyền sử dụng đất hoặc biên bản họp giữa đại diện thôn, ấp, làng, bản, buôn, bom, phum, sóc, tổ "
    "dân phố, điểm dân cư với người sử dụng đất về việc tặng cho quyền sử dụng đất và bản gốc Giấy chứng nhận đã cấp",
    "Trường hợp có biên bản họp giữa Ủy ban nhân dân cấp xã với người sử dụng đất về việc tặng cho quyền sử dụng đất "
    "thì người sử dụng đất chỉ nộp bản gốc Giấy chứng nhận đã cấp cho Ủy ban nhân dân cấp xã nơi có đất.",
]
_PAGE_TITLE = (
    "Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất trong các trường hợp chuyển đổi quyền "
    "sử dụng đất nông nghiệp mà không theo phương án dồn điền, đổi thửa; chuyển nhượng, thừa kế, tặng cho quyền sử dụng "
    "đất, quyền sở hữu tài sản gắn liền với đất"
)


def _fe_fold(value: str) -> str:
    """Như foldChoiceText của FE: bỏ dấu, gộp mọi dấu gạch cùng khoảng trắng quanh nó thành một khoảng trắng."""
    return re.sub(r"\s+", " ", re.sub(r"\s*[-–—]+\s*", " ", fold(value))).strip()


def _fe_matches(row_text: str, name: str) -> bool:
    row, want = _fe_fold(row_text), _fe_fold(name)
    return row == want or want in row or row in want


def _fe_find_row(name: str, index: int) -> int | None:
    """Như findAttachmentRowByComponent của FE: dòng theo STT trước, không khớp tên mới dò dòng khớp đầu tiên."""
    if 1 <= index <= len(_ROWS) and _fe_matches(_ROWS[index - 1], name):
        return index
    return next((stt for stt, row in enumerate(_ROWS, start=1) if _fe_matches(row, name)), None)


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _facts(**values) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row 13 dòng + nút Thêm giấy tờ)
# --------------------------------------------------------------------------------------
def test_sample_bundle_routes_like_attachment_mapping():
    """Ánh xạ hồ sơ: phiếu đo đạc -> dòng 1, GCN -> dòng 3, file văn bản thừa kế + hợp đồng tặng cho -> dòng 4 nguyên
    khối, Đơn -> dòng 7; tờ khai thuế và file giấy nộp tiền + quyết định xử phạt -> hai dòng qua Thêm giấy tờ."""
    attachments, warnings, classified = planner.build_plan_items(
        _files(["td.pdf", "g.pdf", "vb.pdf", "d.pdf", "tk.pdf", "nt.pdf"]), None,
        {0: ["manh_trich_do"], 1: ["gcn"], 2: ["hop_dong_chuyen_quyen"], 3: ["don_bien_dong"], 4: ["to_khai_thue"],
         5: ["chung_tu_nop_tien", "quyet_dinh_xu_phat"]},
    )
    rows = attachments[:4]
    assert [(item["componentIndex"], item["fileName"]) for item in rows] == [
        (1, "td.pdf"), (3, "g.pdf"), (4, "vb.pdf"), (_DON_ROW, "d.pdf")]
    assert all(item["target"] == "attp-row" and "loaiBan" not in item for item in rows)
    assert [_fe_find_row(item["componentName"], item["componentIndex"]) for item in rows] == [1, 3, 4, _DON_ROW]
    added = attachments[4:]
    assert [item["target"] for item in added] == ["add-document-dialog"] * 2
    assert len({item["componentName"] for item in added}) == 2
    assert all("componentIndex" not in item and item["needsAddComponent"] is True for item in added)
    assert all(_fe_find_row(item["fallbackComponentName"], _DON_ROW) == _DON_ROW for item in added)
    assert [item.get("addDocument") for item in classified[4:]] == [True, True]
    # Giấy nộp tiền + quyết định xử phạt chung một dòng Thêm giấy tờ: không phải "gộp nhiều chỗ".
    assert warnings == []


def test_component_name_resolves_to_its_own_row_on_fe():
    rows = {route["row"] for route in planner._ROUTES.values()}
    assert rows == set(range(1, 13))  # dòng 13 là câu hướng dẫn, không đính
    for doc_type, route in planner._ROUTES.items():
        assert _fe_find_row(route["name"], route["row"]) == route["row"], doc_type
        # FE lệch STT thì dò theo tên vẫn ra đúng dòng (tên dòng 3 cũng nằm trong chữ dòng 12, 13 nhưng dòng 3 đứng trước).
        assert _fe_find_row(route["name"], 99) == route["row"], doc_type
    for group in planner._ADD_DOCUMENTS.values():
        assert _fe_find_row(group["componentName"], 99) is None


def test_authorization_has_its_own_row():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["g.pdf", "vb.pdf", "d.pdf", "uq.pdf"]), None,
        {0: ["gcn"], 1: ["hop_dong_chuyen_quyen"], 2: ["don_bien_dong"], 3: ["authorization", "identity"]},
    )
    assert attachments[3]["target"] == "attp-row" and attachments[3]["componentIndex"] == 10
    assert warnings == []


def test_bundle_file_stays_whole_on_highest_priority_place():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["tat-ca.pdf"]), None, {0: ["hop_dong_chuyen_quyen", "gcn", "identity", "to_khai_thue"]}
    )
    assert [item["componentIndex"] for item in attachments] == [3]
    assert classified[0]["docTypes"] == ["hop_dong_chuyen_quyen", "gcn", "identity", "to_khai_thue"]
    bundled = [warning for warning in warnings if "gộp nhiều giấy tờ" in warning]
    assert len(bundled) == 1
    assert "dòng 4" in bundled[0] and "Thêm giấy tờ" in bundled[0] and "nhân thân" not in bundled[0]
    # Thiếu Đơn -> nhắc; GCN và hợp đồng đã có trong file gộp -> không nhắc.
    assert [warning for warning in warnings if "chưa có" in warning] == [planner._REQUIRED_DOCS[2][1]]


def test_missing_core_documents_are_reminded_but_empty_upload_is_silent():
    _attachments, warnings, _classified = planner.build_plan_items(_files(["tk.pdf"]), None, {0: ["to_khai_thue"]})
    assert warnings == [message for _doc_type, message in planner._REQUIRED_DOCS]
    assert planner.build_plan_items([], None, {}) == ([], [], [])


def test_unknown_routed_to_don_row_with_original_name():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["g.pdf", "vb.pdf", "d.pdf", "la.pdf", "trong.pdf"]), None,
        {0: ["gcn"], 1: ["hop_dong_chuyen_quyen"], 2: ["don_bien_dong"], 3: "abc"},
    )
    assert [item["componentIndex"] for item in attachments[3:]] == [_DON_ROW, _DON_ROW]
    assert [item["documentName"] for item in attachments[3:]] == ["la.pdf", "trong.pdf"]
    assert sum("Chưa nhận diện chắc" in warning for warning in warnings) == 2
    assert [item["source"] for item in classified[3:]] == ["llm", "unknown"]


def test_attach_prompt_lists_every_type():
    for doc_type in list(planner._ROUTES) + list(planner._ADD_GROUP) + ["other"]:
        assert doc_type in SYSTEM_PROMPT
    assert '"docTypes"' in SYSTEM_PROMPT and "THÀNH VIÊN HỘ GIA ĐÌNH" in SYSTEM_PROMPT and "KT. CHỦ TỊCH" in SYSTEM_PROMPT


def test_plan_parses_llm_doc_type_lists(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["gcn"]},{"index":1,"docType":"to_khai_thue"}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=name, type="application/pdf", dataUrl="x") for name in ("g.pdf", "tk.pdf")]

    result = asyncio.run(planner.plan(files))

    assert [item["target"] for item in result["attachments"]] == ["attp-row", "add-document-dialog"]
    assert result["attachments"][0]["componentIndex"] == 3
    assert any("Đơn đăng ký biến động" in error for error in result["errors"])


# --------------------------------------------------------------------------------------
# ĐIỀN (Form.io ba khối, cùng template cấp đổi GCN Khánh Hòa)
# --------------------------------------------------------------------------------------
_OWNER = dict(
    ChuHoSo_HoTen="TRẦN VĂN BÌNH",
    ChuHoSo_NgaySinh="20/10/1990",
    ChuHoSo_SoDinhDanh="056 090 012 345",
    # Thẻ căn cước cấp sau 01/07/2024, văn bản công chứng chép nhầm cơ quan cấp thẻ cũ.
    ChuHoSo_NgayCap="05/12/2025",
    ChuHoSo_NoiCap="Cục CS QLHC về TTXH",
    ChuHoSo_DienThoai="0905.123.456",
    ChuHoSo_Email="vidu.binh@example.com",
    # Đơn viết tay: đường + tổ dân phố + phường, không tách tỉnh.
    ChuHoSo_DiaChi={"xa": "phường Nam Nha Trang", "chiTietDuoiXa": "Đường Số 5 - Tổ dân phố Hòa Bình"},
    Don_NoiDungBienDong="Nhận tặng cho quyền sử dụng đất thửa đất số 12 tờ bản đồ số 3. Có nhu cầu cấp đổi Giấy chứng "
                        "nhận mới.",
)
_PARCEL = dict(
    ThuaDat_SoThua="1016",
    ThuaDat_SoThuaCu="12 (trích một phần)",
    ThuaDat_SoTo="255",
    ThuaDat_SoToCu="3 (350 599-4-c)",
    ThuaDat_DiaChi={"tinh": "Khánh Hòa", "xa": "Phường Nam Nha Trang", "chiTietDuoiXa": "Đường Số 5, tổ dân phố Hòa Bình"},
    ThuaDat_DiaChiDayDu="Đường Số 5, tổ dân phố Hòa Bình - phường Nam Nha Trang - Tỉnh Khánh Hòa",
)


def test_self_submit_fills_all_three_blocks():
    fields, warnings = mapper.enrich(_facts(**_OWNER, NguoiNop_HoTen="Trần Văn Bình", **_PARCEL))
    values = _values(fields)

    assert values["data[fullname]"] == values["data[ownerFullname]"] == "TRẦN VĂN BÌNH"
    assert values["data[birthday]"] == values["data[ownerBirthday]"] == "20/10/1990"
    assert values["data[identityNumber]"] == values["data[ownerIdentityNumber]"] == "056090012345"
    assert values["data[identityDate]"] == values["data[ownerIdentityDate]"] == "05/12/2025"
    # Thẻ căn cước từ 01/07/2024 do Bộ Công an cấp.
    assert values["data[identityAgency_text]"] == values["data[ownerIdentityAgency]"] == "Bộ Công an"
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == "0905123456"
    assert values["data[email]"] == values["data[ownerEmail]"] == "vidu.binh@example.com"
    assert (values["data[province1]"], values["data[village1]"], values["data[ownerAddress]"]) == (
        "Tỉnh Khánh Hòa", "Phường Nam Nha Trang", "Đường Số 5 - Tổ dân phố Hòa Bình")
    assert values["data[noidungyeucaugiaiquyet]"] == _OWNER["Don_NoiDungBienDong"]
    # Thửa đất sau đo đạc chỉnh lý: số mới kèm số cũ như tờ khai thuế ghi.
    assert (values["data[SoThuaDat]"], values["data[SoToBanDo]"]) == ("1016 (12 cũ)", "255 (3 cũ)")
    assert values["data[diaChiThuaDat]"] == _PARCEL["ThuaDat_DiaChiDayDu"]
    assert (values["data[province2]"], values["data[village2]"]) == ("Tỉnh Khánh Hòa", "Phường Nam Nha Trang")
    assert {item["name"] for item in fields if item.get("default")} == {"data[chonDoiTuong]", "data[nation2]"}
    assert warnings == []


def test_old_card_keeps_its_issuer_and_parcel_without_resurvey_keeps_plain_number():
    owner = dict(_OWNER, ChuHoSo_NgayCap="28/06/2021", ChuHoSo_NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội")
    parcel = dict(_PARCEL, ThuaDat_SoThua="12", ThuaDat_SoThuaCu="12", ThuaDat_SoTo="3 (350 599-4-c)")
    del parcel["ThuaDat_SoToCu"]
    values = _values(mapper.enrich(_facts(**owner, **parcel))[0])
    assert values["data[ownerIdentityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert (values["data[SoThuaDat]"], values["data[SoToBanDo]"]) == ("12", "3")


def test_authorized_submitter_keeps_roles_apart():
    fields, warnings = mapper.enrich(_facts(
        **_OWNER,
        NguoiNop_HoTen="Lê Thị Hoa",
        NguoiNop_SoDinhDanh="056 165 012 345",
        NguoiNop_NgaySinh="5/3/1965",
        NguoiNop_DiaChi={"tinh": "Gia Lai", "xa": "xã Bình Hiệp", "chiTietDuoiXa": "Thôn B"},
        **_PARCEL,
    ))
    values = _values(fields)
    assert values["data[fullname]"] == "Lê Thị Hoa"
    assert values["data[identityNumber]"] == "056165012345"
    assert (values["data[province]"], values["data[village]"]) == ("Tỉnh Gia Lai", "Xã Bình Hiệp")
    assert values["data[phoneNumber]"] == values["data[identityAgency_text]"] == ""
    assert values["data[ownerFullname]"] == "TRẦN VĂN BÌNH"
    assert values["data[ownerPhoneNumber]"] == "0905123456"
    assert len(warnings) == 1 and "Số điện thoại người nộp" in warnings[0]


def test_missing_request_and_required_fields():
    fields, warnings = mapper.enrich(_facts(ChuHoSo_HoTen="TRẦN VĂN BÌNH", ChuHoSo_NgaySinh="1990"))
    item = next(item for item in fields if item["name"] == "data[noidungyeucaugiaiquyet]")
    assert item["value"] == mapper.DEFAULT_REQUEST and item["default"] is True
    assert len(warnings) == 1
    for label in ("Số điện thoại người nộp", "Ngày sinh chủ hồ sơ", "Phường/xã của thửa đất"):
        assert label in warnings[0]
    assert "đã để trống" in warnings[0]

    fields, warnings = mapper.enrich(_facts(**_OWNER, ChuHoSo_NguoiCungSuDung="Lê Thị Hoa", **_PARCEL))
    assert len(warnings) == 1 and "Lê Thị Hoa" in warnings[0] and "TRẦN VĂN BÌNH" in warnings[0]


def test_handwritten_mobile_with_extra_digit_is_not_filled():
    """OCR đọc "090.5123456" viết tay thành 11 chữ số: di động phải đủ 10 số -> không điền, nhắc cán bộ; máy bàn 02x
    11 chữ số vẫn hợp lệ."""
    fields, warnings = mapper.enrich(_facts(**dict(_OWNER, ChuHoSo_DienThoai="09051234567"), **_PARCEL))
    values = _values(fields)
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == ""
    assert [warning for warning in warnings if "09051234567" in warning] == [
        "Số điện thoại đọc được '09051234567' không hợp lệ (di động phải đủ 10 chữ số) — có thể đọc sai chữ viết tay, "
        "cán bộ nhập lại."]
    values = _values(mapper.enrich(_facts(**dict(_OWNER, ChuHoSo_DienThoai="0258 3812 345"), **_PARCEL))[0])
    assert values["data[ownerPhoneNumber]"] == "02583812345"


def test_misread_parcel_numbers_in_request_are_fixed_from_printed_gcn():
    """OCR chữ viết tay: "12" đọc thành "17", "tờ bản đồ số 3 (350.599-4-c)" thành "đồ bản đồ Số 30350599-A-CT)"."""
    owner = dict(_OWNER, Don_NoiDungBienDong=(
        "Nhận tặng cho thuộc Thửa đất Số 17 (trích một phần) đồ bản đồ Số 30350599-A-CT) tọa lạc tại tổ dân phố A."))
    fields, warnings = mapper.enrich(_facts(**owner, **_PARCEL))
    assert _values(fields)["data[noidungyeucaugiaiquyet]"] == (
        "Nhận tặng cho thuộc Thửa đất Số 12 (trích một phần) tờ bản đồ Số 3 (350 599-4-c) tọa lạc tại tổ dân phố A.")
    assert len(warnings) == 1
    assert "'17' -> '12'" in warnings[0] and "'30350599-A-CT)' -> '3 (350 599-4-c)'" in warnings[0]
    # Số trong câu trùng số mới hoặc số cũ -> giữ nguyên, kể cả mã mảnh.
    for text in ("Nhận tặng cho thửa đất số 12, tờ bản đồ số 3 (350.599-4-c).", "Nhận tặng cho thửa đất số 1016 tờ "
                                                                                 "bản đồ số 255"):
        owner = dict(_OWNER, Don_NoiDungBienDong=text)
        fields, warnings = mapper.enrich(_facts(**owner, **_PARCEL))
        assert _values(fields)["data[noidungyeucaugiaiquyet]"] == text and warnings == []


def test_don_ward_fallback_reads_form_18_layout():
    """LLM lấy tên tổ dân phố làm phường (áp quy tắc CCCD) -> phường ghi rõ trên Đơn Mẫu 18 thắng."""
    text = (
        "Mẫu số 18. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất\nI. Người sử dụng đất:\n"
        "- Tên(2): TRẦN VĂN BÌNH\n- Địa chỉ(4): Đường Số 5 - Tổ dân phố Hòa Bình -\n"
        "- phường Nam Nha Trang - Tỉnh Khánh Hòa.\n- Mã số thuế (nếu có):\nII. Nội dung biến động(5): nhận tặng cho"
    )
    wrong = {"tinh": "Khánh Hòa", "xa": "Phường Hòa Bình", "chiTietDuoiXa": "Đường Số 5"}
    raw = {"ChuHoSo_HoTen": "TRẦN VĂN BÌNH", "ChuHoSo_DiaChi": dict(wrong), "NguoiNop_DiaChi": dict(wrong)}
    fields = apply_printed_fallback(raw, [{"text": text}])
    assert fields["ChuHoSo_DiaChi"]["xa"] == fields["NguoiNop_DiaChi"]["xa"] == "Phường Nam Nha Trang"


def test_parcel_address_taken_verbatim_from_don_toa_lac_tai():
    """Địa chỉ thửa đất: nguyên văn cụm "tọa lạc tại …" của Đơn (nhiều dòng viết tay), thắng địa chỉ LLM lấy từ tờ khai."""
    don = (
        "Mẫu số 18. Đơn đăng ký biến động đất đai\nII. Nội dung biến động(5):\nNhận tặng cho thửa đất số 12 tọa lạc "
        "tại Đường Số 5\ntổ dân phố Hòa Bình - phường Nam Nha Trang - Tỉnh Khánh Hòa.\nCó nhu cầu cấp đổi Giấy chứng "
        "nhận mới.\nIII. Thông tin"
    )
    raw = {"ThuaDat_DiaChiDayDu": "TDP Hòa Bình, phường Nam Nha Trang, tỉnh Khánh Hòa"}
    fields = apply_printed_fallback(raw, [{"text": don}, {"text": "[20.3] Địa chỉ: TDP Hòa Bình"}])
    assert fields["ThuaDat_DiaChiDayDu"] == "Đường Số 5 tổ dân phố Hòa Bình - phường Nam Nha Trang - Tỉnh Khánh Hòa"
    # Không có Đơn / cụm không có phường-xã -> giữ giá trị LLM.
    assert apply_printed_fallback(raw, [{"text": "tọa lạc tại tổ dân phố Hòa Bình."}]) == raw
    no_ward = "Đơn đăng ký biến động\nNhận tặng cho thửa đất tọa lạc tại tổ dân phố Hòa Bình.\n"
    assert apply_printed_fallback(raw, [{"text": no_ward}]) == raw


def test_owner_phone_from_joint_don_when_name_line_shows_spouse():
    """Vợ chồng cùng đứng Đơn: dòng Tên ghi chồng (bên tặng cho), dòng giấy tờ kê cả CCCD của vợ (chủ hồ sơ) -> LLM bỏ
    SĐT; số "Điện thoại liên hệ" của mục I vẫn là của chủ hồ sơ."""
    don = (
        "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\n1. Người sử dụng đất:\n"
        "a) Tên(2): Ông: Trần Văn Bình; - Sinh ngày: 01/02/1985\n"
        "b) Giấy tờ nhân thân/pháp nhân(2): 0560 8500 1111 cấp ngày 01/01/2021 + 0561 9000 2222 cấp ngày 01/01/2021\n"
        "c) Địa chỉ(2): 12 Đường Số 5, phường Nam Nha Trang, tỉnh Khánh Hòa\n"
        "d) Điện thoại liên hệ (nếu có): 0905123456... Hộp thư điện tử (nếu có): ...\n"
        "2. Nội dung biến động (3):\n- Tặng cho ½ quyền sử dụng đất\nNgười viết đơn\nLê Thị Hoa\nTrần Văn Bình\n"
    )
    raw = {"ChuHoSo_HoTen": "Lê Thị Hoa", "ChuHoSo_SoDinhDanh": "056190002222", "NguoiNop_HoTen": "Lê Thị Hoa"}
    fields = apply_printed_fallback(raw, [{"text": don}])
    assert fields["ChuHoSo_DienThoai"] == "0905123456"
    facts = {key: value for key, value in fields.items() if key != "ThuaDat_DiaChiDayDu"}
    values = _values(mapper.enrich(_facts(**facts, **_PARCEL))[0])
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == "0905123456"
    # LLM đã có số -> giữ; mục I không có tên/CCCD của chủ hồ sơ (Đơn của người khác) -> không bù.
    assert apply_printed_fallback(dict(raw, ChuHoSo_DienThoai="0912000111"), [{"text": don}])[
        "ChuHoSo_DienThoai"] == "0912000111"
    other = dict(raw, ChuHoSo_HoTen="Phạm Văn Nam", ChuHoSo_SoDinhDanh="001090003333")
    assert "ChuHoSo_DienThoai" not in apply_printed_fallback(other, [{"text": don}])
    # Dòng điện thoại để chấm trống -> không bù.
    blank = don.replace("0905123456...", "....")
    assert "ChuHoSo_DienThoai" not in apply_printed_fallback(raw, [{"text": blank}])


def test_schema_and_prompt_cover_transfer_traps():
    assert {"ThuaDat_SoThuaCu", "ThuaDat_SoToCu", "Don_NoiDungBienDong", "ChuHoSo_NguoiCungSuDung"} <= ALLOWED
    for phrase in ("BÊN NHẬN", "THỬA ĐẤT KHÁC", "MỚI NHẤT", "[04.x]", "Nam Nha Trang"):
        assert phrase in EXTRA_RULES, phrase


# --------------------------------------------------------------------------------------
# REGISTRY + LINK KÊ KHAI + TRỢ LÝ
# --------------------------------------------------------------------------------------
def test_registry_wires_both_pipelines_and_locks_khanh_hoa():
    procedure = get_procedure(_KEY)
    assert procedure["label"].startswith("Khánh Hòa - Đăng ký biến động quyền sử dụng đất")
    assert procedure["detect"]["urlScope"] == ["khanhhoa.gov.vn"]
    assert procedure_province_slugs(procedure) == ["khanhhoa"]
    assert get_pipeline(_KEY).__module__.startswith(
        "app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_khanh_hoa.")
    assert get_attach_pipeline(_KEY).__module__.startswith(
        "app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_khanh_hoa.")


def test_khanh_hoa_pages_do_not_cross_detect():
    page = fold(_PAGE_TITLE + " " + " ".join(_ROWS))
    khanh_hoa = [p for p in PROCEDURES if "khanhhoa.gov.vn" in (p.get("detect") or {}).get("urlScope", [])]
    assert _KEY in {p["key"] for p in khanh_hoa}
    for procedure in khanh_hoa:
        hits = all(fold(text) in page for text in procedure["detect"]["textIncludes"])
        assert hits == (procedure["key"] == _KEY), procedure["key"]
    cap_doi_page = fold("Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất (2) Bản gốc "
                        "Giấy chứng nhận đã cấp. (1) Đơn đăng ký biến động đất đai, tài sản gắn liền với đất")
    assert not all(fold(text) in cap_doi_page for text in get_procedure(_KEY)["detect"]["textIncludes"])


def test_ke_khai_link_shares_registry_key():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    assert links[0]["code"] == "1.013831"
    assert links[0]["label"] == get_procedure(_KEY)["label"]
    assert links[0]["provinceOnlyAgency"] is True and not links[0].get("selectSo")


def test_tro_ly_chi_tai_khoan_khanh_hoa_dung_pipeline_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    core = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Khánh Hòa - " + procedure["label"] == core["label"]
    assert "Khánh Hòa" not in procedure["shortLabel"]
    assert procedure["detect"] == core["detect"]
    assert procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.013831"
    # Luồng chung "xay-dung" + bxdFlow như Tuyên Quang (09/11/2026): đọc trang "Chọn trường hợp giải quyết", bổ sung ô,
    # nút sang Thành phần hồ sơ / Hình thức nhận kết quả, nộp hồ sơ.
    from app.channels.handfree.chat.field_review import registry as field_review_registry

    assert procedure["flowProfile"] == "xay-dung" and procedure["maePortal"] is True
    assert procedure["maeDialogChoice"] == {"enabled": True}
    assert procedure["bxdFlow"]["capability"] == "supportsBxdFlowKhanhHoa"
    assert field_review_registry.get(_KEY)["required"] == ()
    assert procedure["agencyProvince"] == "Khánh Hòa"
    assert procedure["agencyProvinceOnly"] is True and "agencySoFirst" not in procedure
    assert procedure["agencyCardIncludesByWard"] == link["submitCardIncludesByWard"]
    assert procedure["agencyCardIncludesByWard"]["Phường Nam Nha Trang"] == (
        "Chi nhánh Văn phòng Đăng ký đất đai Nha Trang")
    assert handfree.is_allowed_in_province(procedure, "khanhhoa")
    assert not handfree.is_allowed_in_province(procedure, "bacninh")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"don", "gcn", "hop_dong"}
    assert PROCEDURE_HMONG[_KEY] and PROCEDURE_HINTS[_KEY]
