import asyncio
from types import SimpleNamespace

from app.pipelines._shared import fold
from app.pipelines.giao_thue_chuyen_muc_dich_dat_khanh_hoa.attach import planner
from app.pipelines.giao_thue_chuyen_muc_dich_dat_khanh_hoa.attach.prompt import SYSTEM_PROMPT
from app.pipelines.giao_thue_chuyen_muc_dich_dat_khanh_hoa.process import mapper
from app.pipelines.giao_thue_chuyen_muc_dich_dat_khanh_hoa.process.prompt import EXTRA_RULES
from app.pipelines.giao_thue_chuyen_muc_dich_dat_khanh_hoa.process.schema import ALLOWED
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "giao-thue-chuyen-muc-dich-dat-khanh-hoa"
_DON_INDEX = 13

_INVEST = (
    "+ Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư, quyết định chấp thuận chủ "
    "trương đầu tư đồng thời chấp thuận nhà đầu tư theo quy định của pháp luật về đầu tư công, pháp luật về đầu tư; "
    "văn bản phê duyệt kết quả lựa chọn nhà đầu tư đối với dự án đầu tư theo phương thức đối tác công tư (nếu có); "
    "+ Bản sao văn bản của cơ quan nhà nước có thẩm quyền chấp thuận nhà đầu tư theo quy định của pháp luật về đầu tư "
    "đối với trường hợp quy định tại khoản 5 Điều 124 Luật Đất đai; + Bản sao văn bản của đơn vị được giao tổ chức "
    "thực hiện việc đấu giá quyền sử dụng đất về kết quả đấu giá quyền sử dụng đất không thành quy định tại điểm b "
    "khoản 6 Điều 125 Luật Đất đai; + Bản sao văn bản về kết quả thực hiện việc nhận chuyển nhượng dự án bất động sản "
    "theo quy định của pháp luật về kinh doanh bất động sản đối với trường hợp quy định tại khoản 7 Điều 124 Luật Đất "
    "đai; + Bản sao các văn bản theo quy định của pháp luật đối với trường hợp quy định tại điểm i khoản 1 Điều 133 "
    "Luật Đất đai mà phải thu hồi đất."
)
# Cột "Tên giấy tờ" của 15 dòng thành phần hồ sơ trên cổng Khánh Hòa, đúng thứ tự DOM.
_ROWS = [
    "Dự án đầu tư đối với khu rừng đề nghị giao; báo cáo điều tra, đánh giá hiện trạng rừng và bản đồ hiện trạng rừng "
    "theo quy định của pháp luật về lâm nghiệp (đối với trường hợp đề nghị giao đất và giao rừng);",
    "Kết quả đấu giá thuê rừng; biên bản đấu giá cho thuê rừng; danh sách người trúng đấu giá thuê rừng; thông báo "
    "hoàn thành nghĩa vụ tài chính đối với người trúng đấu giá thuê rừng (đối với trường hợp cho thuê đất và cho thuê "
    "rừng).",
    "Bản sao văn bản phê duyệt kết quả lựa chọn nhà đầu tư của cơ quan nhà nước có thẩm quyền đối với trường hợp quy "
    "định tại khoản 2 Điều 116 Luật Đất đai.",
    "- Phương án sử dụng tầng đất mặt theo Mẫu số 26 ban hành kèm theo Nghị định số 151/2025/NĐ-CP (đối với trường "
    "hợp chuyển mục đích sử dụng đất chuyên trồng lúa);",
    "Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư, quyết định chấp thuận chủ trương "
    "đầu tư đồng thời chấp thuận nhà đầu tư theo quy định của pháp luật về đầu tư công, pháp luật về đầu tư; văn bản "
    "phê duyệt kết quả lựa chọn nhà đầu tư đối với dự án đầu tư theo phương thức đối tác công tư (nếu có).",
    "Một trong các loại giấy tờ sau: " + _INVEST,
    "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với tổ chức kinh tế, đơn vị sự "
    "nghiệp công lập đã được Nhà nước giao đất, cho thuê đất trước ngày Luật Đất đai có hiệu lực thi hành;",
    "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với diện tích đất thu hồi của "
    "công ty nông, lâm nghiệp quản lý, sử dụng để giao đất, cho thuê đất quy định tại các điểm c, d và đ khoản 2 Điều "
    "181 Luật Đất đai;",
    "Bản sao Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương đã được cơ quan, tổ chức có thẩm quyền "
    "phê duyệt",
    "Một trong các loại giấy tờ sau: " + _INVEST,
    "Một trong các giấy tờ sau: + Bản sao một trong các giấy chứng nhận: Giấy chứng nhận quyền sử dụng đất, quyền sở "
    "hữu tài sản gắn liền với đất, Giấy chứng nhận quyền sử dụng đất, Giấy chứng nhận quyền sở hữu nhà ở và quyền sử "
    "dụng đất ở, Giấy chứng nhận quyền sở hữu nhà ở, Giấy chứng nhận quyền sở hữu công trình xây dựng, Giấy chứng nhận "
    "quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn liền với đất đã được cấp theo quy định của pháp luật về "
    "đất đai, pháp luật về nhà ở, pháp luật về xây dựng trước ngày Luật này có hiệu lực thi hành vẫn có giá trị pháp "
    "lý và không phải cấp đổi sang Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất. + Quyết "
    "định giao đất, quyết định cho thuê đất, quyết định cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có "
    "thẩm quyền theo quy định của pháp luật về đất đai qua các thời kỳ. + Văn bản của cơ quan có thẩm quyền cho phép "
    "gia hạn thời hạn hoạt động của dự án đầu tư hoặc thể hiện thời hạn hoạt động của dự án đầu tư theo quy định của "
    "pháp luật về đầu tư đối với trường hợp sử dụng đất để thực hiện dự án đầu tư.",
    "Đơn đề nghị gia hạn sử dụng đất",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai hoặc một trong các loại "
    "giấy tờ quy định tại Điều 137 Luật Đất đai hoặc quyết định giao đất, quyết định cho thuê đất, quyết định cho phép "
    "chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền theo quy định của pháp luật về đất đai qua các thời "
    "kỳ.",
    "Đơn đề nghị giao đất/thuê đất/chuyển mục đích sử dụng đất/giao đất và giao rừng/cho thuê đất và cho thuê rừng",
    "Phương án sử dụng tầng đất mặt theo Mẫu số 26 ban hành kèm theo Nghị định số 151/2025/NĐ-CP (đối với trường hợp "
    "chuyển mục đích sử dụng đất chuyên trồng lúa).",
]


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _facts(**values) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row 15 dòng + nút Thêm giấy tờ)
# --------------------------------------------------------------------------------------
def test_sample_bundle_routes_like_attachment_mapping():
    """Ánh xạ hồ sơ: Đơn -> dòng 14, GCN -> dòng 11 (không đính dòng 13), file ủy quyền -> Thêm giấy tờ."""
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["don.pdf", "gcn.pdf", "uq.pdf"]), None,
        {0: ["don_de_nghi"], 1: ["gcn"], 2: ["authorization"]},
    )
    assert warnings == []
    assert [item["componentIndex"] for item in attachments[:2]] == [_DON_INDEX, 10]
    assert all(item["target"] == "attp-row" and "loaiBan" not in item for item in attachments[:2])
    uq = attachments[2]
    assert uq["target"] == "add-document-dialog" and uq["needsAddComponent"] is True
    assert "componentIndex" not in uq
    assert uq["fallbackComponentName"] == _ROWS[_DON_INDEX]
    assert uq["formOptionHints"][0] == uq["componentName"] == "Giấy ủy quyền"


def test_component_name_first_matches_its_own_row():
    rows = [fold(row) for row in _ROWS]
    for doc_type, route in planner._ROUTES.items():
        hits = [index for index, row in enumerate(rows) if fold(route["name"]) in row]
        assert hits and hits[0] == route["index"], (doc_type, hits)
    assert fold(planner._DON_DE_NGHI_NAME) == rows[_DON_INDEX]


def test_duplicate_rows_and_row_13_never_used():
    used = {route["index"] for route in planner._ROUTES.values()}
    assert not used & {9, 12, 14}


def _fe_find_row(component_name: str, component_index: int) -> int:
    """Mô phỏng findAttachmentRowByComponent của FE: thử rows[componentIndex - 1], tên khớp hai chiều thì lấy, không
    thì dòng khớp tên đầu tiên."""
    want = fold(component_name)

    def matches(row: str) -> bool:
        text = fold(row)
        return want in text or text in want

    if component_index and matches(_ROWS[component_index - 1]):
        return component_index - 1
    return next(index for index, row in enumerate(_ROWS) if matches(row))


def test_gcn_lands_on_row_11_not_row_13_on_frontend():
    attachments, _warnings, _classified = planner.build_plan_items(_files(["gcn.pdf"]), None, {0: ["gcn"]})
    item = attachments[0]
    assert _fe_find_row(item["componentName"], item["componentIndex"]) == 10
    assert item["documentName"] == "Giấy chứng nhận quyền sử dụng đất"


def test_bundle_file_stays_whole_on_highest_priority_place():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["tat-ca.pdf"]), None, {0: ["authorization", "gcn", "don_de_nghi", "identity"]}
    )
    assert attachments[0]["componentIndex"] == _DON_INDEX
    assert classified[0]["docTypes"] == ["authorization", "gcn", "don_de_nghi", "identity"]
    assert len(warnings) == 1
    assert "dòng 11" in warnings[0] and "Thêm giấy tờ" in warnings[0] and "nhân thân" not in warnings[0]


def test_authorization_bundle_with_identity_goes_to_add_dialog_without_warning():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["uq.pdf"]), None, {0: ["authorization", "identity"]}
    )
    assert attachments[0]["target"] == "add-document-dialog"
    assert warnings == []


def test_unknown_routed_to_don_row_with_original_name():
    attachments, warnings, classified = planner.build_plan_items(_files(["la.pdf", "trong.pdf"]), None, {0: "abc"})
    assert [item["componentIndex"] for item in attachments] == [_DON_INDEX, _DON_INDEX]
    assert [item["documentName"] for item in attachments] == ["la.pdf", "trong.pdf"]
    assert len(warnings) == 2
    assert [item["source"] for item in classified] == ["llm", "unknown"]


def test_attach_prompt_lists_every_type():
    for doc_type in list(planner._ROUTES) + ["authorization", "other"]:
        assert doc_type in SYSTEM_PROMPT
    assert '"docTypes"' in SYSTEM_PROMPT


def test_plan_parses_llm_doc_type_lists(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["gcn"]},{"index":1,"docType":"authorization"}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=name, type="application/pdf", dataUrl="x") for name in ("gcn.pdf", "uq.pdf")]

    result = asyncio.run(planner.plan(files))

    assert [item["target"] for item in result["attachments"]] == ["attp-row", "add-document-dialog"]
    assert result["attachments"][0]["componentIndex"] == 10


# --------------------------------------------------------------------------------------
# ĐIỀN (Form.io ba khối, cùng template đăng ký đất đai lần đầu Khánh Hòa)
# --------------------------------------------------------------------------------------
_OWNER = dict(
    ChuHoSo_HoTen="Trần Thị Bình",
    ChuHoSo_NgaySinh="5/6/1975",
    ChuHoSo_SoDinhDanh="056 175 012 345",
    ChuHoSo_NgayCap="01/02/2025",
    ChuHoSo_NoiCap="Bộ Công An",
    ChuHoSo_DienThoai="0912.345.678",
    ChuHoSo_DiaChi={"tinh": "Khánh Hòa", "xa": "phường Nam Nha Trang", "chiTietDuoiXa": "thửa 12- tbđ 3, Thôn A"},
)
_PARCEL = dict(
    ThuaDat_DiaChi={"tinh": "Khánh Hòa", "xa": "Xã Phước Đồng", "chiTietDuoiXa": "thôn A"},
    ThuaDat_DiaChiDayDu="thôn A, xã Phước Đồng, thành phố Nha Trang (nay là phường Nam Nha Trang), tỉnh Khánh Hòa",
    ThuaDat_SoThua="Thửa đất số: 12",
    ThuaDat_SoTo="3",
)


def test_authorized_submitter_fills_part_one_from_submitter_only():
    fields, warnings = mapper.enrich(_facts(
        **_OWNER,
        NguoiNop_HoTen="Lê Văn An",
        NguoiNop_NgaySinh="20/10/1990",
        NguoiNop_SoDinhDanh="052 090 012 345",
        NguoiNop_NgayCap="01/01/2022",
        NguoiNop_NoiCap="Cục cảnh sát quản lý hành chính về trật tự xã hội",
        NguoiNop_DiaChi={"tinh": "Gia Lai", "xa": "xã Bình Hiệp", "chiTietDuoiXa": "Thôn B"},
        Don_NoiDungDeNghi="Đề nghị chuyển mục đích sử dụng đất đối với thửa đất số 12, tờ bản đồ số 3",
        **_PARCEL,
    ))
    values = _values(fields)

    assert values["data[fullname]"] == "Lê Văn An"
    assert values["data[identityNumber]"] == "052090012345"
    assert values["data[identityAgency_text]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert (values["data[province]"], values["data[village]"], values["data[address]"]) == (
        "Tỉnh Gia Lai", "Xã Bình Hiệp", "Thôn B")
    # Số ở Đơn mục 3 là của người đề nghị: không gán cho người nộp — trả về TRỐNG + cảnh báo cán bộ nhập.
    assert values["data[phoneNumber]"] == ""
    assert any("Số điện thoại người nộp" in warning for warning in warnings)
    assert values["data[ownerFullname]"] == "Trần Thị Bình"
    assert values["data[ownerPhoneNumber]"] == "0912345678"
    assert values["data[ownerBirthday]"] == "05/06/1975"
    assert values["data[ownerIdentityAgency]"] == "Bộ Công an"
    assert (values["data[province1]"], values["data[village1]"], values["data[ownerAddress]"]) == (
        "Tỉnh Khánh Hòa", "Phường Nam Nha Trang", "thửa 12- tbđ 3, Thôn A")


def test_self_submit_uses_owner_for_part_one():
    fields, warnings = mapper.enrich(_facts(**_OWNER, NguoiNop_HoTen="Trần Thị Bình"))
    values = _values(fields)
    assert values["data[fullname]"] == values["data[ownerFullname]"]
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == "0912345678"
    assert values["data[village]"] == values["data[village1]"]
    assert not any("Số điện thoại người nộp" in warning for warning in warnings)


def test_parcel_block_uses_full_address_text_and_current_ward():
    fields, warnings = mapper.enrich(_facts(**_OWNER, **_PARCEL, ThuaDat_SoToMoi="nay là tờ bản đồ số 99"))
    values = _values(fields)
    assert values["data[diaChiThuaDat]"] == _PARCEL["ThuaDat_DiaChiDayDu"]
    assert values["data[SoThuaDat]"] == "12"
    assert values["data[SoToBanDo]"] == "3"
    assert values["data[province2]"] == "Tỉnh Khánh Hòa"
    assert values["data[village2]"] == "Phường Nam Nha Trang"
    assert any("tờ bản đồ mới số 99" in warning for warning in warnings)


def test_printed_authorization_facts_override_handwritten_reads():
    """Tên/địa chỉ in trong giấy ủy quyền thắng bản đọc từ chữ ký tay trên Đơn và bản quét GCN."""
    fields, _warnings = mapper.enrich(_facts(
        **_OWNER,
        NguoiNop_HoTen="Lê Văn A",
        UyQuyen_HoTenNguoiDuocUyQuyen="LÊ VĂN AN",
        UyQuyen_DiaChiThuaDat="thôn A, xã Phước Đồng, thành phố Nha Trang (nay là phường D), tỉnh Khánh Hòa",
        **dict(_PARCEL, ThuaDat_DiaChiDayDu="thôn A, xã Phước Đông, thành phố Nha Trang, tỉnh Khánh Hòa"),
    ))
    values = _values(fields)
    assert values["data[fullname]"] == "LÊ VĂN AN"
    assert values["data[diaChiThuaDat]"] == (
        "thôn A, xã Phước Đồng, thành phố Nha Trang (nay là phường D), tỉnh Khánh Hòa")


def test_printed_fallback_fixes_name_and_area_from_ocr():
    from app.pipelines.giao_thue_chuyen_muc_dich_dat_khanh_hoa.process.runner import apply_printed_fallback

    documents = [
        {"text": "5. Diện tích đất (m²): 1504, trong đó:\nNgười làm đơn\nUQ\nLê Văn A"},
        {"text": "II. Thửa đất\nc) Diện tích: 150,4m², (bằng chữ: ...)\nb) Diện tích xây dựng: 70,0m²"},
        {"text": "BÊN ĐƯỢC ỦY QUYỀN:\nNGÂN HÀNG TMCP VÍ DỤ\nBằng giấy này, tôi ủy quyền cho:\n"
                 "Ông : LÊ VĂN AN - Sinh ngày: 01/02/1990\ndiện tích: 150,4 m²"},
    ]
    raw = [
        {"name": "UyQuyen_HoTenNguoiDuocUyQuyen", "value": "Lê Văn A"},
        {"name": "Don_NoiDungDeNghi", "value": "Đề nghị chuyển mục đích sử dụng đất; diện tích đất 1504 m², trong đó "
                                              "chuyển mục đích 100 m²"},
    ]

    fields = apply_printed_fallback(raw, documents)

    assert fields["UyQuyen_HoTenNguoiDuocUyQuyen"] == "LÊ VĂN AN"
    assert fields["Don_NoiDungDeNghi"] == (
        "Đề nghị chuyển mục đích sử dụng đất; diện tích đất 150,4 m², trong đó chuyển mục đích 100 m²")


def test_printed_fallback_leaves_fields_when_ambiguous():
    from app.pipelines.giao_thue_chuyen_muc_dich_dat_khanh_hoa.process.runner import apply_printed_fallback

    documents = [{"text": "tôi ủy quyền cho:\nÔng : LÊ VĂN AN - Sinh ngày\ntôi ủy quyền cho:\nBà : TRẦN THỊ BÌNH -"
                          "\nDiện tích: 100m²\ndiện tích: 120 m²"}]
    raw = {"UyQuyen_HoTenNguoiDuocUyQuyen": "Lê Văn An", "Don_NoiDungDeNghi": "diện tích đất 99 m²"}
    assert apply_printed_fallback(raw, documents) == raw


def test_nay_la_note_moved_before_province():
    parcel = dict(_PARCEL, ThuaDat_DiaChiDayDu="thôn A, xã B, thành phố C, tỉnh Khánh Hòa (nay là phường D)")
    fields, _warnings = mapper.enrich(_facts(**_OWNER, **parcel))
    assert _values(fields)["data[diaChiThuaDat]"] == "thôn A, xã B, thành phố C (nay là phường D), tỉnh Khánh Hòa"


def test_parcel_text_falls_back_to_detail_and_ward():
    parcel = {key: value for key, value in _PARCEL.items() if key != "ThuaDat_DiaChiDayDu"}
    fields, _warnings = mapper.enrich(_facts(**_OWNER, **parcel))
    assert _values(fields)["data[diaChiThuaDat]"] == "thôn A, Phường Nam Nha Trang"


def test_schema_and_prompt_cover_submitter_and_sheet_rules():
    assert {"ThuaDat_SoToMoi", "ThuaDat_DiaChiDayDu", "Don_NoiDungDeNghi"} <= ALLOWED
    assert "TỔ CHỨC" in EXTRA_RULES and "UQ" in EXTRA_RULES and "nay là tờ bản đồ" in EXTRA_RULES


# --------------------------------------------------------------------------------------
# REGISTRY + LINK KÊ KHAI
# --------------------------------------------------------------------------------------
def test_registry_wires_both_pipelines_and_locks_khanh_hoa():
    procedure = get_procedure(_KEY)
    assert procedure["label"].startswith("Khánh Hòa - Giao đất, cho thuê đất, chuyển mục đích")
    assert procedure["detect"]["urlScope"] == ["khanhhoa.gov.vn"]
    assert procedure_province_slugs(procedure) == ["khanhhoa"]
    assert get_pipeline(_KEY).__module__.startswith("app.pipelines.giao_thue_chuyen_muc_dich_dat_khanh_hoa.")
    assert get_attach_pipeline(_KEY).__module__.startswith("app.pipelines.giao_thue_chuyen_muc_dich_dat_khanh_hoa.")


def test_ke_khai_link_shares_registry_key():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    assert links[0]["code"] == "1.013949"
    assert links[0]["label"].startswith("Khánh Hòa - ")


def test_tro_ly_chi_tai_khoan_khanh_hoa_dung_pipeline_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    core = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Khánh Hòa - " + procedure["label"] == core["label"]
    assert "Khánh Hòa" not in procedure["shortLabel"]
    assert procedure["detect"] == core["detect"]
    assert procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.013949"
    # Luồng chung "xay-dung" + bxdFlow như Tuyên Quang (09/11/2026): đọc trang "Chọn trường hợp giải quyết", bổ sung ô,
    # nút sang Thành phần hồ sơ / Hình thức nhận kết quả, nộp hồ sơ.
    from app.channels.handfree.chat.field_review import registry as field_review_registry

    assert procedure["flowProfile"] == "xay-dung" and procedure["maePortal"] is True
    assert procedure["maeDialogChoice"] == {"enabled": True}
    assert procedure["bxdFlow"]["capability"] == "supportsBxdFlowKhanhHoa"
    assert field_review_registry.get(_KEY)["required"] == ()
    assert procedure["agencyProvince"] == "Khánh Hòa"
    assert "agencyProvinceOnly" not in procedure and "agencySoFirst" not in procedure
    assert handfree.is_allowed_in_province(procedure, "khanhhoa")
    assert not handfree.is_allowed_in_province(procedure, "tuyenquang")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert PROCEDURE_HMONG[_KEY]
