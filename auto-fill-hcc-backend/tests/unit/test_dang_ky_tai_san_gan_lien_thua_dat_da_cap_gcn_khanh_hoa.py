import asyncio
import re
from types import SimpleNamespace

from app.pipelines._shared import fold
from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.attach import planner
from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.attach.prompt import SYSTEM_PROMPT
from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.process import mapper
from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.process.runner import (
    apply_printed_fallback,
)
from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.process.schema import ALLOWED
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "dang-ky-tai-san-gan-lien-thua-dat-da-cap-gcn-khanh-hoa"

# Cột "Tên giấy tờ" của 8 dòng thành phần hồ sơ trên cổng Khánh Hòa, đúng thứ tự DOM (file mapping 1.013995-1.1, Phần V).
_ROWS = [
    "(1) Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18 ban hành kèm theo Nghị định số "
    "151/2025/NĐ-CP.",
    "(7) Mảnh trích đo bản đồ địa chính thửa đất đối với trường hợp người sử dụng đất có nhu cầu đo đạc để xác định lại "
    "kích thước các cạnh, diện tích của thửa đất.",
    "(8) Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục đăng ký đất "
    "đai, tài sản gắn liền với đất thông qua người đại diện.",
    "(6) Văn bản chấp thuận gia hạn thời hạn sở hữu nhà ở của cơ quan có thẩm quyền đối với trường hợp gia hạn thời hạn "
    "sở hữu nhà ở của tổ chức nước ngoài, cá nhân nước ngoài theo quy định của pháp luật về nhà ở.",
    "(4) Sơ đồ nhà ở, công trình xây dựng, trừ trường hợp đã nộp một trong các loại giấy tờ quy định tại các Điều 148, "
    "Điều 149 của Luật Đất đai mà có sơ đồ phù hợp với hiện trạng nhà ở, công trình đã xây dựng.",
    "(2) Giấy chứng nhận đã cấp.",
    "(3) Một trong các loại giấy tờ theo quy định tại các Điều 148, Điều 149 của Luật Đất đai (nếu có).",
    "(5) Hồ sơ thiết kế xây dựng của công trình đã được cơ quan chuyên môn về xây dựng thẩm định hoặc đã có văn bản "
    "chấp thuận kết quả nghiệm thu hoàn thành hạng mục công trình, công trình xây dựng theo quy định của pháp luật về "
    "xây dựng đối với trường hợp chứng nhận quyền sở hữu công trình xây dựng trên đất nông nghiệp mà chủ sở hữu công "
    "trình không có một trong các loại giấy tờ quy định tại Điều 149 của Luật Đất đai hoặc công trình được miễn giấy "
    "phép xây dựng theo quy định của pháp luật về xây dựng.",
]
_PAGE_TITLE = (
    "Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận hoặc đăng ký thay đổi về tài sản gắn liền với "
    "đất so với nội dung đã đăng ký"
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
# ĐÍNH KÈM (attp-row 8 dòng + nút Thêm giấy tờ)
# --------------------------------------------------------------------------------------
def test_sample_bundle_routes_like_attachment_mapping():
    """Ánh xạ hồ sơ: Đơn -> dòng 1, GCN -> dòng 6, file giấy phép xây dựng + bìa hồ sơ thiết kế + bản vẽ -> dòng 7
    nguyên khối (sơ đồ nhà trong đó không tải lại ở dòng 5, dòng 8 bỏ trống); tờ khai lệ phí trước bạ và giấy nộp tiền ->
    hai dòng qua Thêm giấy tờ; Đơn liệt kê CCCD (bản sao) mà không có file -> nhắc."""
    don_text = "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI\n3. Nội dung biến động:\nBổ sung tài sản.\n- Căn cước công dân (bản sao)."
    attachments, warnings, classified = planner.build_plan_items(
        _files(["d.pdf", "g.pdf", "gp.pdf", "tk.pdf", "nt.pdf"]),
        [{"name": "d.pdf", "text": don_text}],
        {0: ["don_bien_dong"], 1: ["gcn"], 2: ["giay_to_148_149", "ho_so_thiet_ke", "so_do_nha"], 3: ["to_khai_thue"],
         4: ["chung_tu_nop_tien"]},
    )
    rows = attachments[:3]
    assert [(item["componentIndex"], item["fileName"]) for item in rows] == [(1, "d.pdf"), (6, "g.pdf"), (7, "gp.pdf")]
    assert all(item["target"] == "attp-row" and "loaiBan" not in item for item in rows)
    assert [_fe_find_row(item["componentName"], item["componentIndex"]) for item in rows] == [1, 6, 7]
    added = attachments[3:]
    assert [item["target"] for item in added] == ["add-document-dialog"] * 2
    assert len({item["componentName"] for item in added}) == 2
    assert all("componentIndex" not in item and item["needsAddComponent"] is True for item in added)
    assert all(_fe_find_row(item["fallbackComponentName"], 1) == 1 for item in added)
    assert [item.get("addDocument") for item in classified[3:]] == [True, True]
    bundled = [warning for warning in warnings if "gộp nhiều giấy tờ" in warning]
    assert len(bundled) == 1 and "gp.pdf" in bundled[0] and "dòng 7" in bundled[0]
    assert "(dòng 5)" in bundled[0] and "(dòng 8)" in bundled[0]
    assert [warning for warning in warnings if "gộp" not in warning] == [planner._IDENTITY_MISSING]


def test_component_name_resolves_to_its_own_row_on_fe():
    assert {route["row"] for route in planner._ROUTES.values()} == set(range(1, 9))
    for doc_type, route in planner._ROUTES.items():
        assert _fe_find_row(route["name"], route["row"]) == route["row"], doc_type
        # FE lệch STT thì dò theo tên vẫn ra đúng dòng (dòng 5 cũng nhắc "giấy tờ quy định tại các Điều 148" nhưng
        # không có chữ "theo").
        assert _fe_find_row(route["name"], 99) == route["row"], doc_type
    for group in planner._ADD_DOCUMENTS.values():
        assert _fe_find_row(group["componentName"], 99) is None


def test_identity_and_authorization_places():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["d.pdf", "g.pdf", "gp.pdf", "uq.pdf", "cccd.pdf"]),
        [{"name": "d.pdf", "text": "Đơn đăng ký biến động ... - Căn cước công dân (bản sao)."}],
        {0: ["don_bien_dong"], 1: ["gcn"], 2: ["giay_to_148_149"], 3: ["authorization", "identity"], 4: ["identity"]},
    )
    assert attachments[3]["target"] == "attp-row" and attachments[3]["componentIndex"] == 3
    cccd = attachments[4]
    assert cccd["target"] == "add-document-dialog" and cccd["loaiBan"] == "Bản sao"
    assert cccd["componentName"] == "Căn cước công dân"
    assert warnings == []


def test_missing_core_documents_are_reminded_but_empty_upload_is_silent():
    _attachments, warnings, _classified = planner.build_plan_items(_files(["tk.pdf"]), None, {0: ["to_khai_thue"]})
    assert warnings == [message for _doc_types, message in planner._REQUIRED_DOCS]
    # Giấy tờ tài sản: sơ đồ nhà đứng riêng cũng đủ, không nhắc giấy phép xây dựng.
    _attachments, warnings, _classified = planner.build_plan_items(
        _files(["d.pdf", "g.pdf", "sd.pdf"]), None, {0: ["don_bien_dong"], 1: ["gcn"], 2: ["so_do_nha"]})
    assert warnings == []
    assert planner.build_plan_items([], None, {}) == ([], [], [])


def test_unknown_routed_to_don_row_with_original_name():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["d.pdf", "g.pdf", "gp.pdf", "la.pdf", "trong.pdf"]), None,
        {0: ["don_bien_dong"], 1: ["gcn"], 2: ["giay_to_148_149"], 3: "abc"},
    )
    assert [item["componentIndex"] for item in attachments[3:]] == [1, 1]
    assert [item["documentName"] for item in attachments[3:]] == ["la.pdf", "trong.pdf"]
    assert sum("Chưa nhận diện chắc" in warning for warning in warnings) == 2
    assert [item["source"] for item in classified[3:]] == ["llm", "unknown"]


def test_attach_prompt_lists_every_type():
    for doc_type in list(planner._ROUTES) + list(planner._ADD_DOCUMENTS) + ["other"]:
        assert doc_type in SYSTEM_PROMPT
    assert '"docTypes"' in SYSTEM_PROMPT and "HỒ SƠ THIẾT KẾ XIN PHÉP XÂY DỰNG" in SYSTEM_PROMPT
    assert "Người được ủy quyền nộp NSNN" in SYSTEM_PROMPT


def test_plan_parses_llm_doc_type_lists(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["gcn"]},{"index":1,"docType":"chung_tu_nop_tien"}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=name, type="application/pdf", dataUrl="x") for name in ("g.pdf", "nt.pdf")]

    result = asyncio.run(planner.plan(files))

    assert [item["target"] for item in result["attachments"]] == ["attp-row", "add-document-dialog"]
    assert result["attachments"][0]["componentIndex"] == 6
    assert any("Đơn đăng ký biến động" in error for error in result["errors"])


# --------------------------------------------------------------------------------------
# ĐIỀN (Form.io ba khối, cùng template cấp đổi GCN Khánh Hòa)
# --------------------------------------------------------------------------------------
_OWNER = dict(
    ChuHoSo_HoTen="NGUYỄN VĂN AN",
    ChuHoSo_NguoiCungSuDung="TRẦN THỊ BÌNH",
    ChuHoSo_SoDinhDanh="056 090 012 345",
    ChuHoSo_NgayCap="11/11/2021",
    ChuHoSo_NoiCap="Cục Cảnh sát Quản lý hành chính về trật tự xã hội",
    ChuHoSo_DienThoai="0905.123.456",
    ChuHoSo_DiaChi={"tinh": "tỉnh Khánh Hòa", "xa": "phường Nam Nha Trang", "chiTietDuoiXa": "12/3 Đường Số 5"},
    Don_NoiDungBienDong="Bổ sung tài sản gắn liền với đất.\n- Giấy chứng nhận đã cấp; Giấy phép xây dựng số 100/GPXD-UBND "
                        "+ bản vẽ (bản chính)",
)
_PARCEL = dict(
    ThuaDat_SoThua="430",
    ThuaDat_SoTo="17",
    ThuaDat_DiaChi={"tinh": "Khánh Hòa", "xa": "Phường Nam Nha Trang", "chiTietDuoiXa": "Số 12/3 Đường Số 5"},
    ThuaDat_DiaChiDayDu="Số 12/3 Đường Số 5, phường Nam Nha Trang, tỉnh Khánh Hòa",
)


def test_self_submit_fills_all_three_blocks_and_flags_co_owner():
    fields, warnings = mapper.enrich(_facts(**_OWNER, NguoiNop_HoTen="Nguyễn Văn An", **_PARCEL))
    values = _values(fields)

    assert values["data[fullname]"] == values["data[ownerFullname]"] == "NGUYỄN VĂN AN"
    assert values["data[identityNumber]"] == values["data[ownerIdentityNumber]"] == "056090012345"
    assert values["data[identityDate]"] == values["data[ownerIdentityDate]"] == "11/11/2021"
    assert values["data[ownerIdentityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == "0905123456"
    assert (values["data[province1]"], values["data[village1]"], values["data[ownerAddress]"]) == (
        "Tỉnh Khánh Hòa", "Phường Nam Nha Trang", "12/3 Đường Số 5")
    assert values["data[noidungyeucaugiaiquyet]"] == _OWNER["Don_NoiDungBienDong"]
    assert (values["data[SoThuaDat]"], values["data[SoToBanDo]"]) == ("430", "17")
    assert values["data[diaChiThuaDat]"] == _PARCEL["ThuaDat_DiaChiDayDu"]
    assert (values["data[province2]"], values["data[village2]"]) == ("Tỉnh Khánh Hòa", "Phường Nam Nha Trang")
    assert {item["name"] for item in fields if item.get("default")} == {"data[chonDoiTuong]", "data[nation2]"}
    # Hai đồng chủ, form một chủ hồ sơ -> nhắc; ngày sinh chỉ có trên CCCD (hồ sơ không có) -> nhắc ô bắt buộc.
    assert len(warnings) == 2
    assert "TRẦN THỊ BÌNH" in warnings[0] and "NGUYỄN VĂN AN" in warnings[0]
    assert "Ngày sinh người nộp" in warnings[1] and "Ngày sinh chủ hồ sơ" in warnings[1]


def test_request_keeps_item_lines_but_joins_wrapped_lines():
    """OCR ngắt dòng theo khổ giấy giữa câu ("… ngày\\n18/6/2026") -> nối lại; dòng gạch đầu dòng giữ xuống dòng."""
    request = ("Bổ sung tài sản gắn liền với đất.\n- Giấy chứng nhận đã cấp; Giấy phép xây dựng số 100/GPXD-UBND ngày\n"
               "18/6/2026 + bản vẽ (bản chính)\n\n- Căn cước   công dân (bản sao).")
    values = _values(mapper.enrich(_facts(**dict(_OWNER, Don_NoiDungBienDong=request), **_PARCEL))[0])
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "Bổ sung tài sản gắn liền với đất.\n- Giấy chứng nhận đã cấp; Giấy phép xây dựng số 100/GPXD-UBND ngày 18/6/2026 "
        "+ bản vẽ (bản chính)\n- Căn cước công dân (bản sao).")


def test_missing_fields_are_returned_blank_not_skipped():
    """Cán bộ nộp thay ("Lấy người nộp theo tờ khai"), giấy tờ không có ngày sinh / email: cổng đổ sẵn ngày sinh của TÀI
    KHOẢN vào Phần I → phải trả ô về TRỐNG (clear, ô bắt buộc tô đỏ) chứ không bỏ qua để ngày sinh người khác nằm lại."""
    fields, warnings = mapper.enrich(_facts(**_OWNER, **_PARCEL), {"submitterMode": "owner_as_submitter"})
    cleared = {item["name"]: item for item in fields if item.get("clear")}
    assert set(cleared) == {"data[birthday]", "data[email]", "data[ownerBirthday]", "data[ownerEmail]"}
    assert all(item["value"] == "" for item in cleared.values())
    assert {name for name, item in cleared.items() if item.get("markEmpty")} == {"data[birthday]", "data[ownerBirthday]"}
    assert cleared["data[birthday]"]["comp"] == "dom-date" and cleared["data[email]"]["comp"] == "dom-input"
    assert "đã để trống" in warnings[-1] and "Ngày sinh người nộp" in warnings[-1]

    # Không có gì ngoài tên: mọi ô chữ/ngày của ba khối đều được trả về (giá trị hoặc trống); ô chọn Tỉnh/Phường-xã không
    # xoá (cổng chỉ để sẵn Tỉnh Khánh Hòa mặc định, trợ lý chưa bỏ chọn được ô Choices).
    fields, warnings = mapper.enrich(_facts(ChuHoSo_HoTen="NGUYỄN VĂN AN"))
    values = _values(fields)
    from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process import mapper as goc

    assert set(goc.BLANK_PART_ONE + goc.BLANK_PART_TWO + goc.BLANK_PART_THREE) <= set(values)
    assert values["data[fullname]"] == "NGUYỄN VĂN AN" and values["data[diaChiThuaDat]"] == ""
    assert not [item for item in fields if item.get("clear") and item["comp"] == "dom-select"]
    assert "Phường/xã của thửa đất" in warnings[-1]


def test_account_is_applicant_keeps_portal_prefilled_part_one():
    """Trợ lý: tài khoản đăng nhập chính là người nộp (formContext cùng số định danh) → Phần I cổng đổ sẵn đúng người,
    ô giấy tờ thiếu (ngày sinh) giữ giá trị cổng; khối chủ hồ sơ vẫn trả về trống."""
    context = {"formContext": {"applicantFullname": "NGUYỄN VĂN AN", "applicantIdentityNumber": "056090012345"}}
    fields, warnings = mapper.enrich(_facts(**_OWNER, **_PARCEL), context)
    cleared = {item["name"] for item in fields if item.get("clear")}
    assert cleared == {"data[ownerBirthday]", "data[ownerEmail]"}
    assert "Ngày sinh người nộp" not in warnings[-1] and "Ngày sinh chủ hồ sơ" in warnings[-1]


def test_authorized_submitter_keeps_roles_apart():
    fields, _warnings = mapper.enrich(_facts(
        **_OWNER,
        NguoiNop_HoTen="Lê Thị Hoa",
        NguoiNop_SoDinhDanh="056 165 012 345",
        NguoiNop_NgaySinh="5/3/1965",
        NguoiNop_DiaChi={"tinh": "Khánh Hòa", "xa": "xã Diên Khánh", "chiTietDuoiXa": "Thôn B"},
        **_PARCEL,
    ))
    values = _values(fields)
    assert values["data[fullname]"] == "Lê Thị Hoa"
    assert values["data[identityNumber]"] == "056165012345"
    assert values["data[birthday]"] == "05/03/1965"
    assert (values["data[province]"], values["data[village]"]) == ("Tỉnh Khánh Hòa", "Xã Diên Khánh")
    assert values["data[phoneNumber]"] == ""
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN AN" and values["data[ownerPhoneNumber]"] == "0905123456"


def test_default_request_follows_chosen_case():
    """Đơn không ghi nội dung: câu mặc định theo trường hợp công dân chọn trên cổng (2.x = đăng ký thay đổi)."""
    for options, expected in ((None, mapper.DEFAULT_REQUEST), ({}, mapper.DEFAULT_REQUEST),
                              ({"truongHop": "thay_doi"}, mapper.DEFAULT_REQUEST_THAY_DOI)):
        fields, _warnings = mapper.enrich(_facts(ChuHoSo_HoTen="NGUYỄN VĂN AN"), options)
        item = next(item for item in fields if item["name"] == "data[noidungyeucaugiaiquyet]")
        assert item["value"] == expected and item["default"] is True


def test_request_fallback_copies_don_section_verbatim():
    don = (
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\n"
        "1. Người sử dụng đất: NGUYỄN VĂN AN\n3. Nội dung biến động:\nBổ sung tài sản gắn liền với đất.\n"
        "- Giấy chứng nhận đã cấp; Giấy phép xây dựng số 100/GPXD-UBND ngày 18/6/2026 + bản vẽ (bản chính)\n"
        "- Căn cước công dân (bản sao).\nCam đoan nội dung kê khai trên đơn là đúng sự thật.\nNgười viết đơn"
    )
    fields = apply_printed_fallback({}, [{"text": don}])
    assert fields["Don_NoiDungBienDong"] == (
        "Bổ sung tài sản gắn liền với đất.\n- Giấy chứng nhận đã cấp; Giấy phép xây dựng số 100/GPXD-UBND ngày 18/6/2026 "
        "+ bản vẽ (bản chính)\n- Căn cước công dân (bản sao).")
    # LLM đã đọc được -> giữ nguyên; giấy khác không phải Đơn -> không bù.
    assert apply_printed_fallback({"Don_NoiDungBienDong": "Bổ sung nhà"}, [{"text": don}])["Don_NoiDungBienDong"] == (
        "Bổ sung nhà")
    assert "Don_NoiDungBienDong" not in apply_printed_fallback({}, [{"text": "Tờ khai\nNội dung biến động: x"}])


def test_schema_and_prompt_cover_traps():
    assert {"ChuHoSo_NguoiCungSuDung", "Don_NoiDungBienDong", "ThuaDat_DiaChiDayDu"} <= ALLOWED
    for phrase in ("NGƯỜI THỨ NHẤT", "MUỘN NHẤT", "Thửa 401", "Nam Nha Trang", "KHÔNG suy năm sinh"):
        assert phrase in EXTRA_RULES, phrase


# --------------------------------------------------------------------------------------
# REGISTRY + LINK KÊ KHAI + TRỢ LÝ
# --------------------------------------------------------------------------------------
def test_registry_wires_both_pipelines_and_locks_khanh_hoa():
    procedure = get_procedure(_KEY)
    assert procedure["label"].startswith("Khánh Hòa - Đăng ký tài sản gắn liền với thửa đất")
    assert procedure["detect"]["urlScope"] == ["khanhhoa.gov.vn"]
    assert procedure_province_slugs(procedure) == ["khanhhoa"]
    assert get_pipeline(_KEY).__module__.startswith("app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.")
    assert get_attach_pipeline(_KEY).__module__.startswith(
        "app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn_khanh_hoa.")
    # Bản Đà Nẵng cùng mã vẫn đi pipeline riêng của nó.
    assert get_procedure("dang-ky-tai-san-gan-lien-thua-dat-da-cap-gcn")["detect"]["urlScope"] == [
        "dichvucong.danang.gov.vn"]


def test_khanh_hoa_pages_do_not_cross_detect():
    page = fold(_PAGE_TITLE + " " + " ".join(_ROWS))
    khanh_hoa = [p for p in PROCEDURES if "khanhhoa.gov.vn" in (p.get("detect") or {}).get("urlScope", [])]
    assert _KEY in {p["key"] for p in khanh_hoa}
    for procedure in khanh_hoa:
        hits = all(fold(text) in page for text in procedure["detect"]["textIncludes"])
        assert hits == (procedure["key"] == _KEY), procedure["key"]


def test_ke_khai_link_shares_registry_key_and_ward_cards():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    assert links[0]["code"] == "1.013995"
    assert links[0]["label"] == get_procedure(_KEY)["label"]
    assert links[0]["provinceOnlyAgency"] is True and not links[0].get("selectSo")
    cap_doi = next(link for link in KE_KHAI_LINKS if link["key"] == "cap-doi-gcn-khanh-hoa")
    assert links[0]["submitCardIncludesByWard"] == cap_doi["submitCardIncludesByWard"]


def test_tro_ly_chi_tai_khoan_khanh_hoa_hoi_truong_hop_giai_quyet():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review_registry
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    core = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Khánh Hòa - " + procedure["label"] == core["label"]
    assert "Khánh Hòa" not in procedure["shortLabel"]
    assert procedure["detect"] == core["detect"]
    assert procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.013995"
    # Luồng chung "xay-dung": đọc ô "Trường hợp giải quyết" của trang nps/apply, hỏi công dân, chọn hộ.
    assert procedure["flowProfile"] == "xay-dung" and procedure["maePortal"] is True
    assert procedure["maeDialogChoice"] == {"enabled": True}
    assert procedure["bxdFlow"]["capability"] == "supportsBxdFlowKhanhHoa"
    assert procedure["agencyProvince"] == "Khánh Hòa" and procedure["agencyProvinceOnly"] is True
    assert procedure["agencyCardIncludesByWard"] == link["submitCardIncludesByWard"]
    assert handfree.is_allowed_in_province(procedure, "khanhhoa")
    assert not handfree.is_allowed_in_province(procedure, "danang")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"don", "gcn", "giay_phep"}
    assert PROCEDURE_HMONG[_KEY] and PROCEDURE_HINTS[_KEY]
    assert field_review_registry.get(_KEY)["required"] == ()
    # Quy trình 2.x "đăng ký thay đổi về tài sản" -> câu nội dung mặc định riêng; 1.x -> mặc định.
    labels = [
        "1.013995-1.1 Đối với trường hợp đăng ký quyền sở hữu tài sản gắn liền với thửa đất đã cấp Giấy chứng nhận",
        "1.013995-2.1 Đối với trường hợp đăng ký thay đổi về tài sản gắn liền với đất so với nội dung đã đăng ký",
    ]
    for picked, expected in ((0, {}), (1, {"truongHop": "thay_doi"})):
        conv = {"mae_dialog_options": {"process": {"options": labels}}, "mae_dialog_choice": {"process": picked}}
        assert handfree.case_pipeline_options(procedure, conv) == expected
