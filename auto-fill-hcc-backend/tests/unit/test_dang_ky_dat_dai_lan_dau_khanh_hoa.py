import asyncio
from types import SimpleNamespace

from app.pipelines._shared import fold
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.attach import planner
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.attach.prompt import SYSTEM_PROMPT
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process import mapper
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "dang-ky-dat-dai-lan-dau-khanh-hoa"
_DON_INDEX = 18

# Cột "Tên giấy tờ" của 20 dòng thành phần hồ sơ trên cổng Khánh Hòa, đúng thứ tự DOM.
_ROWS = [
    "Giấy tờ về việc chuyển quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất có chữ ký của bên chuyển quyền "
    "và bên nhận chuyển quyền đối với trường hợp nhận chuyển quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây "
    "dựng mà chưa thực hiện thủ tục chuyển quyền theo quy định của pháp luật",
    "Chứng từ thực hiện nghĩa vụ tài chính, giấy tờ liên quan đến việc miễn, giảm nghĩa vụ tài chính về đất đai, tài "
    "sản gắn liền với đất (nếu có).",
    "Hợp đồng hoặc văn bản thỏa thuận hoặc quyết định của Tòa án nhân dân về việc xác lập quyền đối với thửa đất liền "
    "kề kèm theo sơ đồ thể hiện vị trí, kích thước phần diện tích thửa đất liền kề được quyền sử dụng hạn chế đối "
    "với trường hợp có đăng ký quyền đối với thửa đất liền kề.",
    "Giấy tờ liên quan đến xử phạt vi phạm hành chính trong lĩnh vực đất đai đối với trường hợp có vi phạm hành chính "
    "trong lĩnh vực đất đai.",
    "Văn bản xác định các thành viên có chung quyền sử dụng đất của hộ gia đình đang sử dụng đất đối với trường hợp "
    "hộ gia đình đang sử dụng đất",
    "Giấy tờ về việc nhận thừa kế quyền sử dụng đất theo quy định của pháp luật về dân sự và giấy tờ về việc chuyển "
    "quyền sử dụng đất đối với trường hợp quy định tại khoản 4 Điều 45 Luật Đất đai.",
    "Một trong các loại giấy tờ quy định tại Điều 137, khoản 1, khoản 5 Điều 148, khoản 1, khoản 5 Điều 149 Luật Đất "
    "đai, sơ đồ nhà ở, công trình xây dựng (nếu có). Trường hợp thửa đất gốc có giấy tờ về quyền sử dụng đất quy "
    "định tại Điều 137 Luật Đất đai mà có phần diện tích đất tăng thêm đã được cấp Giấy chứng nhận thì nộp giấy tờ "
    "về việc chuyển quyền sử dụng đất và Giấy chứng nhận đã cấp cho phần diện tích tăng thêm.",
    "Mảnh trích đo bản đồ địa chính thửa đất (nếu có).",
    "Hồ sơ thiết kế xây dựng công trình đã được cơ quan chuyên môn về xây dựng thẩm định hoặc đã có văn bản chấp "
    "thuận kết quả nghiệm thu hoàn thành hạng mục công trình, công trình xây dựng theo quy định của pháp luật về xây "
    "dựng đối với trường hợp chứng nhận quyền sở hữu công trình xây dựng trên đất nông nghiệp mà chủ sở hữu công "
    "trình không có một trong các loại giấy tờ quy định tại Điều 149 Luật Đất đai hoặc công trình được miễn giấy "
    "phép xây dựng theo quy định của pháp luật về xây dựng.",
    "Giấy tờ về giao đất không đúng thẩm quyền hoặc giấy tờ về việc mua, nhận thanh lý, hóa giá, phân phối nhà ở, "
    "công trình xây dựng gắn liền với đất theo quy định tại Điều 140 Luật Đất đai (nếu có).",
    "Giấy tờ về việc nhận thừa kế quyền sử dụng đất theo quy định của pháp luật về dân sự đối với trường hợp nhận "
    "thừa kế quyền sử dụng đất chưa được cấp Giấy chứng nhận theo quy định pháp luật về đất đai.",
    "Quyết định xử phạt vi phạm hành chính trong lĩnh vực đất đai; chứng từ nộp phạt của người sử dụng đất đối với "
    "trường hợp quy định tại điểm a khoản 6 Điều 25 Nghị định số 101/2024/NĐ-CP.",
    "Giấy xác nhận của cơ quan có chức năng quản lý về xây dựng cấp huyện trước ngày 01 tháng 7 năm 2025 về đủ điều "
    "kiện tồn tại nhà ở, công trình xây dựng đó theo quy định của pháp luật về xây dựng đối với trường hợp hộ gia "
    "đình, cá nhân có nhu cầu cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất đối với "
    "nhà ở, công trình xây dựng thuộc trường hợp phải xin phép xây dựng quy định tại khoản 3 Điều 148, khoản 3 Điều "
    "149 Luật Đất đai (nếu có).",
    "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận đối với trường hợp có nhiều người chung quyền sử dụng "
    "đất, chung quyền sở hữu tài sản gắn liền với đất",
    "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận đối với trường hợp có nhiều người chung quyền sử dụng "
    "đất, chung quyền sở hữu tài sản gắn liền với đất.",
    "Một trong các loại giấy tờ quy định tại Điều 137, khoản 4, khoản 5 Điều 148, khoản 4, khoản 5 Điều 149 Luật Đất "
    "đai (nếu có).",
    "Giấy tờ về việc nhận thừa kế quyền sử dụng đất theo quy định của pháp luật về dân sự.",
    "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục đăng ký đất "
    "đai, tài sản gắn liền với đất thông qua người đại diện.",
    "Đơn đăng ký đất đai, tài sản gắn liền với đất",
    "Thông báo xác nhận kết quả đăng ký đất đai.",
]

_EXPECTED_ROW = {
    "giay_to_chuyen_quyen": 0,
    "chung_tu_tai_chinh": 1,
    "to_khai_thue": 1,
    "thua_dat_lien_ke": 2,
    "xu_phat_hanh_chinh": 3,
    "van_ban_thanh_vien_ho_gia_dinh": 4,
    "thua_ke_chuyen_quyen": 5,
    "giay_to_dieu_137": 6,
    "manh_trich_do": 7,
    "ho_so_thiet_ke_xay_dung": 8,
    "giao_dat_khong_dung_tham_quyen": 9,
    "thua_ke": 10,
    "quyet_dinh_xu_phat": 11,
    "giay_xac_nhan_xay_dung": 12,
    "thoa_thuan_cap_chung": 13,
    "authorization": 17,
    "don_dang_ky": 18,
    "identity": 18,
    "xac_nhan_cmnd_cccd": 18,
}


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _facts(**values) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row, 20 dòng)
# --------------------------------------------------------------------------------------
def test_every_route_points_to_expected_row():
    assert set(_EXPECTED_ROW) == set(planner._ROUTES)
    for doc_type, row in _EXPECTED_ROW.items():
        attachments, _warnings, _classified = planner.build_plan_items(_files(["a.pdf"]), None, {0: [doc_type]})
        assert attachments[0]["componentIndex"] == row, doc_type
        assert attachments[0]["target"] == "attp-row"
        assert attachments[0]["needsAddComponent"] is False
        assert "loaiBan" not in attachments[0]


def test_component_name_first_matches_its_own_row():
    """FE khớp componentName theo substring sau khi fold dấu, lấy dòng khớp ĐẦU TIÊN."""
    rows = [fold(row) for row in _ROWS]
    for doc_type, route in planner._ROUTES.items():
        hits = [index for index, row in enumerate(rows) if fold(route["name"]) in row]
        assert hits and hits[0] == route["index"], (doc_type, hits)


def test_duplicate_and_result_rows_never_used():
    used = {route["index"] for route in planner._ROUTES.values()}
    assert not used & {14, 15, 16, 19}


def test_don_file_with_tax_forms_stays_whole_on_don_row():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["don.pdf"]), None, {0: ["don_dang_ky", "to_khai_thue"]}
    )
    assert attachments[0]["componentIndex"] == _DON_INDEX
    assert attachments[0]["detectedType"] == "don_dang_ky"
    assert classified[0]["docTypes"] == ["don_dang_ky", "to_khai_thue"]
    assert len(warnings) == 1 and "dòng 19" in warnings[0] and "dòng 2" in warnings[0]


def test_bundle_of_land_origin_papers_goes_to_transfer_row():
    """Đơn xin làm nhà cũ + giấy chuyển nhượng + giấy khai sinh trong MỘT file -> nguyên file ở dòng 1."""
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["giay-to.pdf"]), None, {0: ["giay_to_dieu_137", "giay_to_chuyen_quyen", "identity"]}
    )
    assert attachments[0]["componentIndex"] == 0
    assert len(warnings) == 1 and "dòng 7" in warnings[0]
    # Giấy nhân thân không có dòng riêng nên không bị nhắc.
    assert "nhân thân" not in warnings[0]


def test_survey_bundle_goes_to_trich_do_row_without_warning():
    attachments, warnings, _classified = planner.build_plan_items(_files(["td.pdf"]), None, {0: ["manh_trich_do"]})
    assert attachments[0]["componentIndex"] == 7
    assert warnings == []


def test_unknown_or_missing_type_routed_to_don_row_with_original_name():
    files = _files(["la.pdf", "khong-ocr.pdf"])
    attachments, warnings, classified = planner.build_plan_items(files, None, {0: ["khong-hop-le"]})
    assert [item["componentIndex"] for item in attachments] == [_DON_INDEX, _DON_INDEX]
    assert [item["documentName"] for item in attachments] == ["la.pdf", "khong-ocr.pdf"]
    assert len(warnings) == 2
    assert [item["source"] for item in classified] == ["llm", "unknown"]


def test_single_doc_type_string_still_accepted():
    assert planner._doc_types({"docType": "Authorization"}) == ["authorization"]
    attachments, _warnings, _classified = planner.build_plan_items(_files(["uq.pdf"]), None, {0: "authorization"})
    assert attachments[0]["componentIndex"] == 17


def test_attach_prompt_lists_every_route_type():
    for doc_type in list(planner._ROUTES) + ["other"]:
        assert doc_type in SYSTEM_PROMPT
    assert '"docTypes"' in SYSTEM_PROMPT


def test_classify_ocr_uses_cached_full_text_and_trims_only_misses(monkeypatch):
    from app.services import ocr, ocr_cache

    files = [
        {"name": "co-cache.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AAA"},
        {"name": "moi.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,BBB"},
    ]
    sent: list[dict] = []

    async def fake_get_many(keys):
        return {"k-AAA": {"text": "Trang 1/9 ... đủ trang", "provider": "tiengnoi"}}

    async def fake_ocr(batch):
        sent.extend(batch)
        return [{"name": item["name"], "type": item["type"], "text": "hai trang đầu"} for item in batch]

    monkeypatch.setattr(ocr_cache, "content_key", lambda data_url: "k-" + data_url.rsplit(",", 1)[-1])
    monkeypatch.setattr(ocr_cache, "get_many", fake_get_many)
    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "trim_files_for_classify",
                        lambda batch, pages: [{**item, "dataUrl": f"trim{pages}"} for item in batch])

    results = asyncio.run(planner._ocr_for_classify(files))

    assert [item["text"] for item in results] == ["Trang 1/9 ... đủ trang", "hai trang đầu"]
    assert [item["name"] for item in sent] == ["moi.pdf"]
    assert sent[0]["dataUrl"] == f"trim{planner._OCR_MAX_PAGES}"


def test_plan_parses_llm_doc_type_lists(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["don_dang_ky","to_khai_thue"]},{"index":1,"docType":"manh_trich_do"}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=name, type="application/pdf", dataUrl="x") for name in ("don.pdf", "td.pdf")]

    result = asyncio.run(planner.plan(files))

    assert [item["componentIndex"] for item in result["attachments"]] == [_DON_INDEX, 7]
    assert result["extracted"]["classified"][0]["docTypes"] == ["don_dang_ky", "to_khai_thue"]


# --------------------------------------------------------------------------------------
# ĐIỀN (Form.io ba khối)
# --------------------------------------------------------------------------------------
_OWNER = dict(
    ChuHoSo_HoTen="Trần Thị Bình",
    ChuHoSo_NgaySinh="05/06/1975",
    ChuHoSo_SoDinhDanh="056 175 012 345",
    ChuHoSo_DiaChi={"quocGia": "Việt Nam", "tinh": "Khánh Hoà", "xa": "p. Nam Nha Trang", "chiTietDuoiXa": "Tổ dân phố 3"},
    ChuHoSo_DienThoai="0912.345.678",
)
_PARCEL = dict(
    ThuaDat_DiaChi={"quocGia": "Việt Nam", "tinh": "Khánh Hòa", "xa": "Phường Nam Nha Trang", "chiTietDuoiXa": "Tổ dân phố 3"},
    ThuaDat_SoThua="Thửa đất số: 120",
    ThuaDat_SoTo="12 (123456-7-a)",
)


def test_self_submit_fills_both_person_blocks_from_owner():
    fields, warnings = mapper.enrich(_facts(
        **_OWNER,
        NguoiNop_HoTen="Trần Thị Bình",
        # Người nộp đọc từ giấy tờ cũ còn ghi xã trước sắp xếp: tự nộp thì phải theo địa chỉ trên Đơn.
        NguoiNop_DiaChi={"tinh": "Khánh Hòa", "xa": "Xã Phước Đồng", "chiTietDuoiXa": "Thôn 2"},
        Don_NoiDungDeNghi="Đề nghị đăng ký đất đai, tài sản gắn liền với đất; Đề nghị cấp Giấy chứng nhận",
        **_PARCEL,
    ))
    values = _values(fields)

    assert warnings == []
    for applicant, owner in (
        ("data[fullname]", "data[ownerFullname]"),
        ("data[phoneNumber]", "data[ownerPhoneNumber]"),
        ("data[birthday]", "data[ownerBirthday]"),
        ("data[identityNumber]", "data[ownerIdentityNumber]"),
        ("data[province]", "data[province1]"),
        ("data[village]", "data[village1]"),
        ("data[address]", "data[ownerAddress]"),
    ):
        assert values[applicant] == values[owner], applicant
    assert values["data[phoneNumber]"] == "0912345678"
    assert values["data[identityNumber]"] == "056175012345"
    assert values["data[province]"] == "Tỉnh Khánh Hòa"
    assert values["data[village]"] == "Phường Nam Nha Trang"
    assert values["data[address]"] == "Tổ dân phố 3"
    assert values["data[chonDoiTuong]"] == "Cá nhân"
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "Đề nghị đăng ký đất đai, tài sản gắn liền với đất; Đề nghị cấp Giấy chứng nhận"
    )


def test_authorized_submitter_never_borrows_owner_facts():
    fields, _warnings = mapper.enrich(_facts(
        **_OWNER,
        NguoiNop_HoTen="Lê Văn An",
        NguoiNop_SoDinhDanh="001090012345",
        NguoiNop_DiaChi={"tinh": "Khánh Hòa", "xa": "Phường Nha Trang", "chiTietDuoiXa": "12 Lê Lợi"},
    ))
    values = _values(fields)

    assert values["data[fullname]"] == "Lê Văn An"
    assert values["data[identityNumber]"] == "001090012345"
    assert values["data[address]"] == "12 Lê Lợi"
    # Người nộp không có điện thoại/ngày sinh riêng -> trả về TRỐNG (xoá giá trị cổng đổ theo tài khoản), không lấy
    # của chủ hồ sơ.
    assert values["data[phoneNumber]"] == values["data[birthday]"] == ""
    assert {item["name"] for item in fields if item.get("markEmpty")} >= {"data[phoneNumber]", "data[birthday]"}
    assert values["data[ownerFullname]"] == "Trần Thị Bình"
    assert values["data[ownerPhoneNumber]"] == "0912345678"
    assert values["data[ownerAddress]"] == "Tổ dân phố 3"


def test_parcel_block_only_from_parcel_facts():
    fields, _warnings = mapper.enrich(_facts(**_OWNER, **_PARCEL))
    values = _values(fields)
    assert values["data[SoThuaDat]"] == "120"
    assert values["data[SoToBanDo]"] == "12"
    assert values["data[diaChiThuaDat]"] == "Tổ dân phố 3, Phường Nam Nha Trang"
    assert values["data[province2]"] == "Tỉnh Khánh Hòa"
    assert values["data[village2]"] == "Phường Nam Nha Trang"
    assert values["data[nation2]"] == "Việt Nam"

    # Không có nguồn thửa đất: không mượn nơi cư trú — ô chữ trả về TRỐNG, ô chọn không đụng tới.
    fields, _warnings = mapper.enrich(_facts(**_OWNER))
    values = _values(fields)
    assert values["data[diaChiThuaDat]"] == values["data[SoThuaDat]"] == values["data[SoToBanDo]"] == ""
    assert not set(values) & {"data[province2]", "data[village2]", "data[nation2]"}


def test_year_only_birthday_and_province_only_address_dropped():
    fields, _warnings = mapper.enrich(_facts(
        ChuHoSo_HoTen="Trần Thị Bình",
        ChuHoSo_NgaySinh="1975",
        ChuHoSo_DiaChi={"tinh": "Khánh Hòa"},
    ))
    values = _values(fields)
    # Chỉ có năm sinh -> ngày sinh trả về TRỐNG (không ghi năm trơn); chỉ có tỉnh -> bỏ cả cụm địa chỉ.
    assert values["data[birthday]"] == values["data[ownerBirthday]"] == ""
    assert not set(values) & {"data[province]", "data[province1]"}


def test_organization_owner_and_missing_owner_warning():
    fields, _warnings = mapper.enrich(_facts(ChuHoSo_HoTen="Công ty TNHH Ví Dụ"))
    assert _values(fields)["data[chonDoiTuong]"] == "Tổ chức"
    _fields, warnings = mapper.enrich(_facts(ThuaDat_SoThua="120"))
    assert warnings and "chủ hồ sơ" in warnings[0]


def test_hidden_and_random_key_fields_never_declared():
    for name in UI_COMP_BY_NAME:
        assert not any(part in name for part in ("district", "CaNhan_ToChuc", "is_BuuChinh", "thongtinTC"))
    assert UI_COMP_BY_NAME["data[identityAgency_text]"] == "dom-input"
    assert UI_COMP_BY_NAME["data[ownerIdentityAgency]"] == "dom-input"
    assert {"ThuaDat_SoThua", "ThuaDat_SoTo", "ThuaDat_DiaChi", "Don_NoiDungDeNghi"} <= ALLOWED


# --------------------------------------------------------------------------------------
# REGISTRY + LINK KÊ KHAI
# --------------------------------------------------------------------------------------
def test_registry_wires_both_pipelines_and_locks_khanh_hoa():
    procedure = get_procedure(_KEY)
    assert procedure["label"].startswith("Khánh Hòa - Đăng ký đất đai")
    assert procedure["detect"]["urlScope"] == ["khanhhoa.gov.vn"]
    assert procedure_province_slugs(procedure) == ["khanhhoa"]
    assert get_pipeline(_KEY).__module__.startswith("app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.")
    assert get_attach_pipeline(_KEY).__module__.startswith("app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.")


def test_ke_khai_link_shares_registry_key():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    assert links[0]["code"] == "1.013978"
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
    assert handfree.procedure_code(procedure) == "1.013978"
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
    assert not handfree.is_allowed_in_province(procedure, "quangngai")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert PROCEDURE_HMONG[_KEY]


# --------------------------------------------------------------------------------------
# CÀI ĐẶT "CÓ TÁCH HỒ SƠ KHI ĐÍNH KÈM" — chung 7 thủ tục đất đai iGate Khánh Hòa
# --------------------------------------------------------------------------------------
_KHANH_HOA_KEYS = (
    "dang-ky-dat-dai-lan-dau-khanh-hoa",
    "giao-thue-chuyen-muc-dich-dat-khanh-hoa",
    "cap-doi-gcn-khanh-hoa",
    "dang-ky-bien-dong-chuyen-nhuong-thua-ke-tang-cho-khanh-hoa",
    "dang-ky-tai-san-gan-lien-thua-dat-da-cap-gcn-khanh-hoa",
    "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-khanh-hoa",
    "dinh-chinh-gcn-da-cap-khanh-hoa",
)


def _pdf_item(name: str, pages: int):
    import base64

    import fitz

    from app.process.schemas import FileItem

    doc = fitz.open()
    for n in range(pages):
        doc.new_page().insert_text((72, 72), f"page {n + 1}")
    data = base64.b64encode(doc.tobytes()).decode("ascii")
    doc.close()
    return FileItem(name=name, type="application/pdf", dataUrl=f"data:application/pdf;base64,{data}", role="")


def test_bay_thu_tuc_khanh_hoa_bat_cai_dat_tach_ca_auto_fill_lan_tro_ly():
    from app.channels.handfree import procedure_registry as handfree

    for key in _KHANH_HOA_KEYS:
        assert get_procedure(key)["supportsSplitDocuments"] is True, key
        assert handfree.get_procedure(key)["supportsSplitDocuments"] is True, key


def test_bay_thu_tuc_khanh_hoa_chi_tach_khi_bat_cai_dat(monkeypatch):
    calls: list[str] = []

    async def fake_split(plan_fn, files, options=None, session=None):
        calls.append("tach")
        return {"attachments": [], "errors": []}

    async def fake_ocr(files):
        calls.append("nguyen-tep")
        return []

    monkeypatch.setattr(planner, "plan_with_split", fake_split)
    for key in _KHANH_HOA_KEYS:
        module = __import__(get_attach_pipeline(key).__module__, fromlist=["_ocr_for_classify"])
        monkeypatch.setattr(module, "_ocr_for_classify", fake_ocr)
        attach = get_attach_pipeline(key)
        for options, expected in (
            ({"splitDocuments": True}, "tach"),
            ({"splitDocuments": False}, "nguyen-tep"),
            (None, "nguyen-tep"),
            # Trợ lý bản cũ không cắt được trang → không tách dù cán bộ bật.
            ({"splitDocuments": True, "supportsSourceSegments": False}, "nguyen-tep"),
        ):
            calls.clear()
            asyncio.run(attach([_pdf_item("a.pdf", 1)], options))
            assert calls == [expected], (key, options)


def test_tep_gop_tach_tung_giay_vao_dung_dong_ocr_mot_lan(monkeypatch):
    import json

    from app.pipelines._shared import khanh_hoa_tach_giay_to as tach
    from app.services import ocr, ocr_cache

    texts = "\n".join(
        f"───── Trang {n + 1}/3 ─────\n{page}" for n, page in enumerate(
            ["ĐƠN ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT", "tiếp theo đơn, chữ ký người viết đơn",
             "MẢNH TRÍCH ĐO BẢN ĐỒ ĐỊA CHÍNH THỬA ĐẤT"])
    )
    sent: list[list[str]] = []

    async def fake_ocr(files, *, classify):
        sent.append([f["name"] for f in files])
        return [{"name": f["name"], "type": f["type"], "text": texts, "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, **_):
        if messages[0]["content"] == tach.SYSTEM_PROMPT:
            return json.dumps({"trang": [{"tep": 0, "trang": 1, "moGiay": True, "ten": "Đơn đăng ký"},
                                         {"tep": 0, "trang": 2, "moGiay": False},
                                         {"tep": 0, "trang": 3, "moGiay": True, "ten": "Mảnh trích đo"}]})
        user = messages[1]["content"]
        assert "MẢNH TRÍCH ĐO" in user and "ĐƠN ĐĂNG KÝ" in user  # phân loại đọc chữ nạp sẵn của từng giấy
        return '{"documents":[{"index":0,"docTypes":["don_dang_ky"]},{"index":1,"docTypes":["manh_trich_do"]}]}'

    async def no_cache(keys):
        return {}

    monkeypatch.setattr(ocr, "_ocr_per_file", fake_ocr)
    monkeypatch.setattr(ocr_cache, "get_many", no_cache)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    result = asyncio.run(planner.plan([_pdf_item("ho_so.pdf", 3)], {"splitDocuments": True}))

    # OCR tệp gốc đúng một lượt; bước phân loại dùng lại chữ của từng đoạn, không OCR lần hai.
    assert sent == [["ho_so.pdf"]]
    items = result["attachments"]
    assert [(i["componentIndex"], i["target"]) for i in items] == [(_DON_INDEX, "attp-row"), (7, "attp-row")]
    assert [i["sourceSegments"] for i in items] == [
        [{"fileIndex": 0, "pageIndexes": [0, 1]}],
        [{"fileIndex": 0, "pageIndexes": [2]}],
    ]
    assert all(i["fileIndex"] == 0 for i in items)


def test_tach_giay_gop_trang_lien_nhau_cung_ten():
    """Model đánh dấu mọi trang của một tờ khai là "mở giấy" (cùng tên) → vẫn là MỘT giấy, không cắt từng trang."""
    from app.pipelines._shared import khanh_hoa_tach_giay_to as tach

    pages = {0: ["a", "b", "c"], 1: ["x", "y"]}
    data = {"trang": [
        {"tep": 0, "trang": 1, "moGiay": True, "ten": "Tờ khai lệ phí trước bạ"},
        {"tep": 0, "trang": 2, "moGiay": True, "ten": "Tờ khai lệ phí trước bạ"},
        {"tep": 0, "trang": 3, "moGiay": True, "ten": "TỜ KHAI LỆ PHÍ TRƯỚC BẠ"},
        {"tep": 1, "trang": 1, "moGiay": True, "ten": "CCCD người A"},
        {"tep": 1, "trang": 2, "moGiay": True, "ten": "CCCD người B"},
    ]}
    assert tach._page_starts(data, pages) == {
        0: [(0, "Tờ khai lệ phí trước bạ")],
        1: [(0, "CCCD người A"), (1, "CCCD người B")],
    }


def test_tach_giay_trang_noi_tiep_va_trang_ngoai_tep():
    from app.pipelines._shared import khanh_hoa_tach_giay_to as tach

    data = {"trang": [
        {"tep": 0, "trang": 1, "moGiay": False, "ten": "Đơn"},  # trang 1 luôn mở giấy
        {"tep": 0, "trang": 2, "moGiay": False},
        {"tep": 0, "trang": 9, "moGiay": True, "ten": "Ngoài tệp"},
        {"tep": 5, "trang": 1, "moGiay": True, "ten": "Tệp không có"},
    ]}
    assert tach._page_starts(data, {0: ["a", "b"]}) == {0: [(0, "Đơn")]}
