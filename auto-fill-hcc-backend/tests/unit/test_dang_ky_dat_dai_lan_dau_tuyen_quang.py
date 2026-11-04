import asyncio
import re
from types import SimpleNamespace

from app.pipelines._shared import fold
from app.pipelines.dang_ky_dat_dai_lan_dau_tuyen_quang.attach import planner
from app.pipelines.dang_ky_dat_dai_lan_dau_tuyen_quang.attach.prompt import SYSTEM_PROMPT
from app.pipelines.dang_ky_dat_dai_lan_dau_tuyen_quang.process import mapper
from app.pipelines.dang_ky_dat_dai_lan_dau_tuyen_quang.process import runner as process_runner
from app.pipelines.dang_ky_dat_dai_lan_dau_tuyen_quang.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.pipelines.dang_ky_dat_dai_lan_dau_tuyen_quang.process_ilis import mapper as ilis_mapper
from app.pipelines.dang_ky_dat_dai_lan_dau_tuyen_quang.process_ilis.schema import UI_COMP_BY_NAME as ILIS_UI
from app.pipelines.dang_ky_dat_dai_lan_dau_tuyen_quang.process_vbdlis import mapper as vbdlis_mapper
from app.pipelines.dang_ky_dat_dai_lan_dau_tuyen_quang.process_vbdlis.schema import UI_COMP_BY_NAME as VBDLIS_UI
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "dang-ky-dat-dai-lan-dau-tuyen-quang"
_ILIS_KEY = "dang-ky-dat-dai-lan-dau-tuyen-quang-ilis"
_VBDLIS_KEY = "dang-ky-dat-dai-lan-dau-tuyen-quang-vbdlis"

# Cột "Tên giấy tờ" của 20 dòng thành phần hồ sơ trên cổng Tuyên Quang, đúng thứ tự DOM (file mapping, ba form chung).
_ROWS = [
    "Chứng từ thực hiện nghĩa vụ tài chính, giấy tờ liên quan đến việc miễn, giảm nghĩa vụ tài chính về đất đai, tài sản "
    "gắn liền với đất (nếu có).",
    "Giấy tờ liên quan đến xử phạt vi phạm hành chính trong lĩnh vực đất đai đối với trường hợp có vi phạm hành chính "
    "trong lĩnh vực đất đai.",
    "Giấy tờ về giao đất không đúng thẩm quyền hoặc giấy tờ về việc mua, nhận thanh lý, hóa giá, phân phối nhà ở, công "
    "trình xây dựng gắn liền với đất theo quy định tại Điều 140 Luật Đất đai (nếu có).",
    "Giấy tờ về việc chuyển quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất có chữ ký của bên chuyển quyền và "
    "bên nhận chuyển quyền đối với trường hợp nhận chuyển quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng mà "
    "chưa thực hiện thủ tục chuyển quyền theo quy định của pháp luật",
    "Giấy tờ về việc nhận thừa kế quyền sử dụng đất theo quy định của pháp luật về dân sự và giấy tờ về việc chuyển "
    "quyền sử dụng đất đối với trường hợp quy định tại khoản 4 Điều 45 Luật Đất đai.",
    "Giấy tờ về việc nhận thừa kế quyền sử dụng đất theo quy định của pháp luật về dân sự đối với trường hợp nhận thừa "
    "kế quyền sử dụng đất chưa được cấp Giấy chứng nhận theo quy định pháp luật về đất đai.",
    "Giấy xác nhận của cơ quan có chức năng quản lý về xây dựng cấp huyện trước ngày 01 tháng 7 năm 2025 về đủ điều kiện "
    "tồn tại nhà ở, công trình xây dựng đó theo quy định của pháp luật về xây dựng đối với trường hợp hộ gia đình, cá "
    "nhân có nhu cầu cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất đối với nhà ở, công "
    "trình xây dựng thuộc trường hợp phải xin phép xây dựng quy định tại khoản 3 Điều 148, khoản 3 Điều 149 Luật Đất "
    "đai (nếu có).",
    "Hồ sơ thiết kế xây dựng công trình đã được cơ quan chuyên môn về xây dựng thẩm định hoặc đã có văn bản chấp thuận "
    "kết quả nghiệm thu hoàn thành hạng mục công trình, công trình xây dựng theo quy định của pháp luật về xây dựng đối "
    "với trường hợp chứng nhận quyền sở hữu công trình xây dựng trên đất nông nghiệp mà chủ sở hữu công trình không có "
    "một trong các loại giấy tờ quy định tại Điều 149 Luật Đất đai hoặc công trình được miễn giấy phép xây dựng theo "
    "quy định của pháp luật về xây dựng.",
    "Hợp đồng hoặc văn bản thỏa thuận hoặc quyết định của Tòa án nhân dân về việc xác lập quyền đối với thửa đất liền "
    "kề kèm theo sơ đồ thể hiện vị trí, kích thước phần diện tích thửa đất liền kề được quyền sử dụng hạn chế đối với "
    "trường hợp có đăng ký quyền đối với thửa đất liền kề.",
    "Mảnh trích đo bản đồ địa chính thửa đất (nếu có).",
    "Một trong các loại giấy tờ quy định tại Điều 137, khoản 1, khoản 5 Điều 148, khoản 1, khoản 5 Điều 149 Luật Đất "
    "đai, sơ đồ nhà ở, công trình xây dựng (nếu có).  Trường hợp thửa đất gốc có giấy tờ về quyền sử dụng đất quy định "
    "tại Điều 137 Luật Đất đai mà có phần diện tích đất tăng thêm đã được cấp Giấy chứng nhận thì nộp giấy tờ về việc "
    "chuyển quyền sử dụng đất và Giấy chứng nhận đã cấp cho phần diện tích tăng thêm.",
    "Quyết định xử phạt vi phạm hành chính trong lĩnh vực đất đai; chứng từ nộp phạt của người sử dụng đất đối với "
    "trường hợp quy định tại điểm a khoản 6 Điều 25 Nghị định số 101/2024/NĐ-CP.",
    "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận đối với trường hợp có nhiều người chung quyền sử dụng "
    "đất, chung quyền sở hữu tài sản gắn liền với đất",
    "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục đăng ký đất "
    "đai, tài sản gắn liền với đất thông qua người đại diện.",
    "Văn bản xác định các thành viên có chung quyền sử dụng đất của hộ gia đình đang sử dụng đất đối với trường hợp hộ "
    "gia đình đang sử dụng đất",
    "Đơn đăng ký đất đai, tài sản gắn liền với đất",
    "Thông báo xác nhận kết quả đăng ký đất đai.",
    "Giấy tờ về việc nhận thừa kế quyền sử dụng đất theo quy định của pháp luật về dân sự.",
    "Một trong các loại giấy tờ quy định tại Điều 137, khoản 4, khoản 5 Điều 148, khoản 4, khoản 5 Điều 149 Luật Đất "
    "đai (nếu có).",
    "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận đối với trường hợp có nhiều người chung quyền sử dụng "
    "đất, chung quyền sở hữu tài sản gắn liền với đất.",
]


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
    return {item["name"]: item["value"] for item in fields if not item.get("clear")}


def _cleared(fields: list[dict]) -> set[str]:
    """Ô gửi cờ clear: extension xoá trắng giá trị cổng điền sẵn và tô đỏ cho cán bộ nhập tay."""
    cleared = {item["name"] for item in fields if item.get("clear")}
    assert all(item["value"] == "" and item.get("markEmpty") for item in fields if item.get("clear"))
    return cleared


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row 20 dòng, chung ba form)
# --------------------------------------------------------------------------------------
def test_sample_bundle_follows_attachment_mapping():
    """Bộ mẫu: 3 tệp, mỗi tệp có bản thường + bản ký số. Đính đúng ba bản ký số, nguyên file, mỗi tệp một dòng: Đơn →
    16, giấy tờ nguồn gốc → 4, trích đo → 10; dòng 1 (tờ khai) và 11 (Điều 137) chỉ được báo là đã nằm chung file."""
    files = _files(["DON.pdf", "DON.signed.pdf", "GIAY TO.pdf", "GIAY TO.signed.pdf", "TD.pdf", "TD.signed.pdf"])
    llm_types = {1: ["don_dang_ky", "to_khai_thue"], 3: ["giay_to_dieu_137", "giay_to_chuyen_quyen", "identity"],
                 5: ["manh_trich_do"]}
    attachments, warnings, classified = planner.build_plan_items(files, None, llm_types)

    assert [(item["fileName"], item["componentIndex"]) for item in attachments] == [
        ("DON.signed.pdf", 16), ("GIAY TO.signed.pdf", 4), ("TD.signed.pdf", 10)]
    assert all(item["target"] == "attp-row" and "sourceSegments" not in item and "loaiBan" not in item
               for item in attachments)
    assert [item["docType"] for item in classified].count("duplicate") == 3
    twins = [w for w in warnings if "trùng bản ký số" in w]
    assert len(twins) == 3 and "'DON.pdf' trùng bản ký số 'DON.signed.pdf'" in twins[0]
    bundle = [w for w in warnings if "gộp nhiều giấy tờ" in w]
    assert len(bundle) == 2
    assert "dòng 16" in bundle[0] and "(dòng 1)" in bundle[0]
    assert "dòng 4" in bundle[1] and "(dòng 11)" in bundle[1] and "dòng 16" not in bundle[1]


def test_component_name_resolves_to_its_own_row_on_fe():
    assert sorted(planner._ROW_NAMES) == list(range(1, 17))  # dòng 17-20: kết quả / trùng danh mục, không đính
    for row, name in planner._ROW_NAMES.items():
        assert _fe_find_row(name, row) == row, row
    # FE gom item theo componentName: mỗi dòng một tên riêng.
    assert len({_fe_fold(name) for name in planner._ROW_NAMES.values()}) == len(planner._ROW_NAMES)
    # Tên dòng 13 cũng khớp chữ dòng 20 (chỉ thêm dấu chấm): chỉ STT giữ file ở dòng 13.
    assert _fe_matches(_ROWS[19], planner._ROW_NAMES[13])


def test_every_route_points_to_a_declared_row_and_duplicates_never_used():
    rows = {row for row, _name in planner._ROUTES.values()}
    assert rows <= set(planner._ROW_NAMES) and not rows & {17, 18, 19, 20}
    assert set(planner._PRIORITY) == set(planner._ROUTES)
    assert planner._PRIORITY[0] == "don_dang_ky"


def test_identity_goes_to_don_row_without_bundle_warning():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["cccd.pdf", "don-cccd.pdf"]), None, {0: ["identity"], 1: ["don_dang_ky", "identity"]})
    assert [(item["componentIndex"], item["documentName"]) for item in attachments] == [
        (16, "Giấy tờ nhân thân (CCCD/giấy khai sinh)"), (16, "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 19)")]
    assert warnings == []


def test_separate_documents_go_to_their_own_rows():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["uq.pdf", "ho.pdf", "thoa-thuan.pdf", "bien-lai.pdf", "thua-ke.pdf"]), None,
        {0: ["authorization"], 1: ["van_ban_thanh_vien_ho_gia_dinh"], 2: ["thoa_thuan_cap_chung"],
         3: ["chung_tu_tai_chinh"], 4: ["thua_ke"]},
    )
    assert [item["componentIndex"] for item in attachments] == [14, 15, 13, 1, 6]
    assert warnings == []


def test_unknown_or_missing_type_routed_to_don_row_with_original_name():
    attachments, warnings, classified = planner.build_plan_items(_files(["la.pdf", "trong.pdf"]), None, {0: "abc"})
    assert [item["componentIndex"] for item in attachments] == [16, 16]
    assert [item["documentName"] for item in attachments] == ["la.pdf", "trong.pdf"]
    assert len(warnings) == 2 and "dòng 16" in warnings[0]
    assert [item["source"] for item in classified] == ["llm", "unknown"]


def test_unsigned_copy_only_skipped_when_signed_twin_has_same_name_and_type():
    files = [
        {"name": "GIAY TO.pdf", "type": "application/pdf"},
        {"name": "GIAY_TO.signed.pdf", "type": "application/pdf"},  # gạch dưới thay khoảng trắng vẫn là một tệp
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "DON-signed.pdf", "type": "application/pdf"},
        {"name": "anh.jpg", "type": "image/jpeg"},
        {"name": "anh.signed.pdf", "type": "application/pdf"},  # khác loại tệp → không coi là bản sao
        {"name": "td.pdf", "type": "application/pdf"},  # không có bản ký số → giữ
    ]
    assert process_runner.unsigned_copies(files) == {0: 1, 2: 3}
    kept = process_runner.without_unsigned_copies({"": files})[""]
    assert [item["name"] for item in kept] == ["GIAY_TO.signed.pdf", "DON-signed.pdf", "anh.jpg", "anh.signed.pdf",
                                               "td.pdf"]


def test_attach_prompt_lists_every_route_type():
    for doc_type in list(planner._ROUTES) + ["other"]:
        assert doc_type in SYSTEM_PROMPT
    assert '"docTypes"' in SYSTEM_PROMPT and "Tuyên Quang" in SYSTEM_PROMPT


def test_plan_skips_unsigned_twins_and_sends_every_page_to_llm(monkeypatch):
    """Bản chưa ký số không OCR, không phân loại, không đính; LLM thấy đầu MỌI trang của file gộp."""
    pages = ["ĐƠN XIN LÀM NHÀ " + "x " * 3000, "GIẤY CHUYỂN NHƯỢNG QUYỀN SỬ DỤNG NHÀ VÀ ĐẤT " + "y " * 3000,
             "GIẤY KHAI SINH"]
    text = pages[0] + "".join(f"\n───── Trang {n}/3 ─────\n{page}" for n, page in enumerate(pages[1:], start=2))
    ocr_names: list[str] = []
    sent: list[str] = []

    async def fake_ocr(files):
        ocr_names.extend(item["name"] for item in files)
        return [{"name": item["name"], "type": item["type"], "text": text} for item in files]

    async def fake_chat(messages, **kwargs):
        sent.append(messages[1]["content"])
        return '{"documents":[{"index":1,"docTypes":["giay_to_dieu_137","giay_to_chuyen_quyen","identity"]}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name="GIAY TO.pdf", type="application/pdf", dataUrl="a"),
             SimpleNamespace(name="GIAY TO.signed.pdf", type="application/pdf", dataUrl="b")]

    result = asyncio.run(planner.plan(files))

    assert ocr_names == ["GIAY TO.signed.pdf"]
    assert "GIẤY KHAI SINH" in sent[0] and '"index": 0' not in sent[0]
    assert [(item["fileIndex"], item["componentIndex"]) for item in result["attachments"]] == [(1, 4)]
    assert any("trùng bản ký số" in error for error in result["errors"])


# --------------------------------------------------------------------------------------
# ĐIỀN — ba form theo quy trình
# --------------------------------------------------------------------------------------
_OWNER = dict(
    ChuHoSo_HoTen="Trần Thị Bình",
    ChuHoSo_NgaySinh="05/03/1985",
    ChuHoSo_GioiTinh="Nữ",
    ChuHoSo_SoDinhDanh="008 185 012 345",
    ChuHoSo_NoiCuTru={"quocGia": "Việt Nam", "tinh": "Tuyên Quang", "xa": "Xã Thượng Lâm", "chiTietDuoiXa": "Thôn Bản Bó"},
    ChuHoSo_DienThoai="0912.345.678",
    Don_NoiDungDeNghi="Đề nghị đăng ký đất đai, tài sản gắn liền với đất; Đề nghị cấp Giấy chứng nhận",
    ThuaDat_DiaChi={"quocGia": "Việt Nam", "tinh": "", "xa": "Xã Thượng Lâm", "chiTietDuoiXa": "Thôn Bản Bó"},
    ThuaDat_SoThua="thửa đất số 45",
    ThuaDat_SoTo="12 (123456-7-a)",
)
_AGENT = dict(
    NguoiNop_HoTen="Lê Văn An",
    NguoiNop_SoDinhDanh="008090054321",
    NguoiNop_GioiTinh="Nam",
    NguoiNop_NoiCuTru={"tinh": "Tuyên Quang", "xa": "Phường Minh Xuân", "chiTietDuoiXa": "Tổ 5"},
)


def test_form_5_buoc_self_submit_fills_part_one_from_owner_and_clears_account_defaults():
    fields, warnings = mapper.enrich(_facts(**_OWNER))
    values = _values(fields)
    assert values == {
        "data[fullname]": "Trần Thị Bình", "data[identityNumber]": "008185012345", "data[gender]": "Nữ",
        "data[birthday]": "05/03/1985", "data[nation]": "Việt Nam", "data[province]": "Tỉnh Tuyên Quang",
        "data[district]": "Xã Thượng Lâm", "data[address]": "Thôn Bản Bó", "data[phoneNumber]": "0912345678",
        "data[hinhThucNop]": "Trực tuyến",
    }
    # Không có CCCD → ngày cấp, nơi cấp cổng đổ sẵn theo tài khoản bị xoá trắng.
    assert _cleared(fields) == {"data[identityDate]", "data[identityAgency]", "data[email]"}
    assert not {"data[Hovaten]", "data[tenHoSo]", "data[textField]"} & set(values)
    assert warnings == []


def test_form_5_buoc_authorized_submitter_in_part_one_and_owner_in_part_two():
    fields, _warnings = mapper.enrich(_facts(**_OWNER, **_AGENT))
    values = _values(fields)
    assert values["data[fullname]"] == "Lê Văn An" and values["data[gender]"] == "Nam"
    assert values["data[district]"] == "Phường Minh Xuân"
    # Bên được ủy quyền không có ngày sinh → không mượn của chủ hồ sơ, xoá ngày sinh tài khoản.
    assert "data[birthday]" in _cleared(fields)
    assert values["data[Hovaten]"] == "Trần Thị Bình" and values["data[Sogiaytotuythan]"] == "008185012345"
    assert values["data[diachi]"] == "Thôn Bản Bó, xã Thượng Lâm, tỉnh Tuyên Quang"


def test_form_ilis_fills_applicant_parcel_and_owner_blocks():
    fields, warnings = ilis_mapper.enrich(_facts(**_OWNER))
    values = _values(fields)
    # Tự nộp: người nộp và chủ hồ sơ là cùng một người.
    for applicant, owner in (("fullname", "ownerFullname"), ("birthday", "ownerBirthday"), ("gender", "gender1"),
                             ("identityNumber", "ownerIdentityNumber"), ("province", "province1"),
                             ("village", "village1"), ("address", "ownerAddress"), ("phoneNumber", "ownerPhoneNumber")):
        assert values[f"data[{applicant}]"] == values[f"data[{owner}]"], applicant
    # Đơn chỉ ghi xã của thửa đất → tỉnh suy từ danh mục (cổng đổ sẵn tỉnh Tuyên Quang theo tài khoản).
    assert values["data[province2]"] == "Tỉnh Tuyên Quang" and values["data[village2]"] == "Xã Thượng Lâm"
    assert not {"data[ghiChu]", "data[organization]", "data[licenseCode]"} & set(values)
    assert {"data[identityAgency]", "data[ownerIdentityAgency]"} <= _cleared(fields)
    assert any("Nơi cấp CMND/CCCD người nộp" in warning for warning in warnings)


def test_form_ilis_authorized_blocks_never_borrow_each_other():
    fields, _warnings = ilis_mapper.enrich(_facts(**_OWNER, **_AGENT))
    values = _values(fields)
    assert values["data[fullname]"] == "Lê Văn An" and values["data[ownerFullname]"] == "Trần Thị Bình"
    assert values["data[village]"] == "Phường Minh Xuân" and values["data[village1]"] == "Xã Thượng Lâm"
    assert "data[birthday]" in _cleared(fields) and values["data[ownerBirthday]"] == "05/03/1985"


def test_form_vbdlis_owner_name_request_and_parcel_numbers():
    fields, warnings = vbdlis_mapper.enrich(_facts(**_OWNER))
    values = _values(fields)
    assert values["data[ownerFullname]"] == values["data[fullname]"] == "Trần Thị Bình"
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "Đề nghị đăng ký đất đai, tài sản gắn liền với đất; Đề nghị cấp Giấy chứng nhận")
    assert values["data[chonDoiTuong]"] == "Cá nhân" and values["data[hinhThucNop]"] == "Trực tuyến"
    assert values["data[SoThuTuThua]"] == "45" and values["data[SoHieuToBanDo]"] == "12"
    assert values["data[diaChiThuaDat1]"] == "Thôn Bản Bó, xã Thượng Lâm, tỉnh Tuyên Quang"
    assert values["data[province2]"] == "Tỉnh Tuyên Quang" and values["data[district2]"] == "Xã Thượng Lâm"
    assert not {"data[note]", "data[tenHoSo]", "data[fullname1]"} & set(values)
    assert warnings == []


def test_form_vbdlis_organization_and_missing_owner():
    fields, warnings = vbdlis_mapper.enrich(_facts(ChuHoSo_HoTen="Công ty TNHH Minh Phát"))
    assert _values(fields)["data[chonDoiTuong]"] == "Tổ chức"
    _fields, warnings = vbdlis_mapper.enrich(_facts(ThuaDat_SoThua="7"))
    assert warnings[0] == mapper.MISSING_OWNER


def test_parcel_province_not_guessed_from_ambiguous_ward():
    area = mapper.parcel_area({"ThuaDat_DiaChi": {"tinh": "", "xa": "Phường 1", "chiTietDuoiXa": "Tổ 2"}})
    assert not area.get("tinh")


def test_mappers_only_emit_declared_controls():
    for enrich, ui in ((mapper.enrich, UI_COMP_BY_NAME), (ilis_mapper.enrich, ILIS_UI),
                       (vbdlis_mapper.enrich, VBDLIS_UI)):
        fields, _warnings = enrich(_facts(**_OWNER, **_AGENT))
        assert {item["name"] for item in fields} <= set(ui)
        assert all(item["comp"] == ui[item["name"]] for item in fields)
    assert {"ChuHoSo_GioiTinh", "ThuaDat_DiaChi", "Don_NoiDungDeNghi", "NguoiNop_NoiCuTru"} <= ALLOWED


def test_gender_fallback_reads_birth_certificate_or_title_of_the_same_person():
    """LLM hay bỏ sót giới tính nằm ở giấy khai sinh giữa xấp giấy tờ nguồn gốc đất → đọc lại thẳng từ OCR theo tên."""
    birth = {"text": "GIẤY KHAI SINH\nHọ và tên: TRẦN THỊ BÌNH    Giới tính: Nữ\nNgày, tháng, năm sinh: 05/03/1985"}
    other = {"text": "Họ và tên: LÊ VĂN AN    Giới tính: Nam\nHọ và tên cha: TRẦN VĂN CƯỜNG"}
    cccd = {"text": "Họ và tên / Full name:\nTRẦN THỊ BÌNH\nNgày sinh / Date of birth: 05/03/1985\nGiới tính / Sex: Nữ"}
    contract = {"text": "II/ Bên nhận chuyển nhượng quyền sử dụng đất:\nBà Trần Thị Bình. Sinh năm 1985"}
    fallback = process_runner.apply_ocr_fallback
    for documents in ([other, birth], [cccd], [contract]):
        assert fallback({"ChuHoSo_HoTen": "Trần Thị Bình"}, documents)["ChuHoSo_GioiTinh"] == "Nữ"
    # Dòng của người khác không được gán sang chủ hồ sơ; hai nguồn vênh nhau thì để trống.
    assert "ChuHoSo_GioiTinh" not in fallback({"ChuHoSo_HoTen": "Trần Thị Bình"}, [other])
    conflict = {"text": "Ông Trần Thị Bình"}
    assert "ChuHoSo_GioiTinh" not in fallback({"ChuHoSo_HoTen": "Trần Thị Bình"}, [birth, conflict])
    # LLM đã trả thì giữ; bên được ủy quyền cũng được bù theo đúng tên của họ.
    assert fallback({"ChuHoSo_HoTen": "Trần Thị Bình", "ChuHoSo_GioiTinh": "Nam"}, [birth])["ChuHoSo_GioiTinh"] == "Nam"
    assert fallback({"NguoiNop_HoTen": "Lê Văn An"}, [other])["NguoiNop_GioiTinh"] == "Nam"
    assert fallback(None, [birth]) is None


def test_each_key_runs_its_own_form_and_skips_unsigned_copies(monkeypatch):
    """Ba key dùng chung bước đọc giấy tờ, mỗi key xếp vào bộ ô của form mình; bản chưa ký số bỏ trước OCR."""
    seen_files: list[list[str]] = []

    async def fake_run(files_by_role, **kwargs):
        seen_files.append([item["name"] for files in files_by_role.values() for item in files])
        return {"fields": _facts(**_OWNER), "errors": []}

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    files = {"": [{"name": "DON.pdf", "type": "application/pdf"}, {"name": "DON.signed.pdf", "type": "application/pdf"}]}

    base = _values(asyncio.run(get_pipeline(_KEY)(files, {}))["fields"])
    ilis = _values(asyncio.run(get_pipeline(_ILIS_KEY)(files, {}))["fields"])
    vbdlis = _values(asyncio.run(get_pipeline(_VBDLIS_KEY)(files, {}))["fields"])

    assert seen_files == [["DON.signed.pdf"]] * 3
    assert "data[district]" in base and "data[ownerFullname]" not in base
    assert "data[village2]" in ilis and "data[gender1]" in ilis
    assert "data[SoThuTuThua]" in vbdlis and "data[village2]" not in vbdlis
    # Trợ lý: công dân chọn quy trình ở hộp thoại → options.quyTrinh → key gốc điền đúng form như key biến thể.
    assert _values(asyncio.run(get_pipeline(_KEY)(files, {"quyTrinh": "ilis"}))["fields"]) == ilis
    assert _values(asyncio.run(get_pipeline(_KEY)(files, {"quyTrinh": "vbdlis"}))["fields"]) == vbdlis


# --------------------------------------------------------------------------------------
# REGISTRY + NHẬN DIỆN + LINK KÊ KHAI
# --------------------------------------------------------------------------------------
def _detect(url: str, body: str) -> str:
    """Như bước 0 của detectProcedureKeyFromSignals (popup.js): entry textPriority đúng cổng, đủ mọi cụm, tổng dài nhất."""
    text = fold(body)
    best, best_score = "", 0
    for procedure in PROCEDURES:
        detect = procedure.get("detect") or {}
        if not detect.get("textPriority"):
            continue
        if detect.get("urlScope") and not any(scope.lower() in url for scope in detect["urlScope"]):
            continue
        phrases = [fold(phrase) for phrase in detect.get("textIncludes") or []]
        if phrases and all(phrase in text for phrase in phrases) and sum(map(len, phrases)) > best_score:
            best, best_score = procedure["key"], sum(map(len, phrases))
    return best


def test_each_process_page_detected_as_its_form():
    url = "https://dichvucong.tuyenquang.gov.vn/vi/padsvc/apply-online/abc"
    title = get_procedure(_KEY)["label"].removeprefix("Tuyên Quang - ")
    assert _detect(url, f"{title} 5 bước 20 ngày Họ và tên") == _KEY
    assert _detect(url, f"{title} iLis cấp xã - 30 ngày Thông tin chủ hồ sơ") == _ILIS_KEY
    assert _detect(url, f"{title} 1.013978_VBDLIS_20 Số thửa đất") == _VBDLIS_KEY
    # Cùng tên thủ tục trên cổng tỉnh khác → không nhận nhầm sang Tuyên Quang.
    assert _detect("https://dichvucong.khanhhoa.gov.vn/vi/x", f"{title} iLis") == "dang-ky-dat-dai-lan-dau-khanh-hoa"


def test_registry_wires_three_forms_and_shared_attach():
    for key, module in ((_KEY, "process."), (_ILIS_KEY, "process_ilis."), (_VBDLIS_KEY, "process_vbdlis.")):
        procedure = get_procedure(key)
        assert procedure["label"].startswith("Tuyên Quang - Đăng ký đất đai")
        assert procedure["detect"]["urlScope"] == ["tuyenquang.gov.vn"]
        assert procedure_province_slugs(procedure) == ["tuyenquang"]
        assert get_pipeline(key).__module__.startswith(f"app.pipelines.dang_ky_dat_dai_lan_dau_tuyen_quang.{module}")
        assert get_attach_pipeline(key) is get_attach_pipeline(_KEY)
    assert get_procedure(_ILIS_KEY)["formVariantOf"] == get_procedure(_VBDLIS_KEY)["formVariantOf"] == _KEY
    assert "formVariantOf" not in get_procedure(_KEY)


def test_ke_khai_link_shares_registry_key():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    assert links[0]["code"] == "1.013978"
    assert links[0]["label"] == get_procedure(_KEY)["label"]


def test_tro_ly_chi_tai_khoan_tuyen_quang_dung_pipeline_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    core = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Tuyên Quang - " + procedure["label"] == core["label"]
    assert "Tuyên Quang" not in procedure["shortLabel"]
    assert procedure["detect"] == core["detect"]
    assert procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.013978"
    assert handfree.is_allowed_in_province(procedure, "tuyenquang")
    assert not handfree.is_allowed_in_province(procedure, "khanhhoa")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert PROCEDURE_HMONG[_KEY]
    # Hộp thoại "Chọn trường hợp giải quyết": nhãn quy trình đọc từ cổng → tuỳ chọn pipeline.
    for label, options in (("5 bước 20 ngày", {}), ("iLis cấp xã - 30 ngày", {"quyTrinh": "ilis"}),
                           ("1.013978_VBDLIS_20", {"quyTrinh": "vbdlis"})):
        conv = {"mae_dialog_options": {"process": {"options": [label], "current": label}}}
        assert handfree.case_pipeline_options(procedure, conv) == options, label
