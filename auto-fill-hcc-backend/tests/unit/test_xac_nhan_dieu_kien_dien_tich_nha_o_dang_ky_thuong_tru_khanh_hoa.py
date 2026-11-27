"""Test "Khánh Hòa - Xác nhận về điều kiện diện tích bình quân nhà ở để đăng ký thường trú vào chỗ ở do thuê, mượn, ở nhờ …"
(1.013314, cổng iGate dichvucong.khanhhoa.gov.vn, quy trình 1.013314.H32.01).

Khoá:
1. LINK + PHẠM VI: link kê khai mang tiền tố "Khánh Hòa - ", chỉ tài khoản Khánh Hòa thấy (Auto Fill + trợ lý); detect thắng
   bản chung cùng mã trên cổng Khánh Hòa, không lọt sang tỉnh khác.
2. ĐIỀN theo file "Mapping_XN-cho-o-hop-phap_Mau02_KhanhHoa.xlsx": chủ hồ sơ = người đề nghị Tờ khai Mẫu 02 (owner*, địa
   chỉ một ô chữ), ô "Người nộp hồ sơ đồng thời là chủ hồ sơ", khối người nộp (data[district] = Phường/xã), nội dung yêu cầu
   ghép từ mục II.1 + III; ô giấy tờ không có thì trả về trống.
3. ĐÍNH KÈM: bảng một dòng Tờ khai Mẫu 02 — tách đúng dòng + không sót trang, tắt tách đính nguyên tệp, tách lỗi quay về
   không tách.
Dữ liệu người trong test là BỊA. Không gọi LLM / OCR thật.
"""

import asyncio
import base64
from types import SimpleNamespace

import fitz
import pytest

from app.pipelines._shared import fold
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru_khanh_hoa import attach
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru_khanh_hoa.attach import planner as dispatcher
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru_khanh_hoa.attach.dinh_kem_khong_tach import (
    planner,
)
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru_khanh_hoa.attach.dinh_kem_khong_tach.prompt import (
    SYSTEM_PROMPT,
)
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru_khanh_hoa.attach.dinh_kem_tach import (
    planner as tach,
)
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru_khanh_hoa.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT as TACH_PROMPT,
)
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru_khanh_hoa.process import mapper
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru_khanh_hoa.process.prompt import EXTRA_RULES
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru_khanh_hoa.process.schema import (
    ALLOWED,
    TEN_THU_TUC,
    UI_COMP_BY_NAME,
)
from app.procedures import router as procedures_router
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "xac-nhan-dieu-kien-dien-tich-nha-o-dang-ky-thuong-tru-khanh-hoa"
_BASE_KEY = "xac-nhan-dieu-kien-dien-tich-nha-o-dang-ky-thuong-tru"
_ROW_NAME = planner.ROW_NAME


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _to_khai_facts() -> list[dict]:
    """Những gì Tờ khai Mẫu 02 có: người đề nghị (mục I), chỗ ở hợp pháp (II.1), nội dung đề nghị (III)."""
    return [
        {"name": "ChuHoSo_HoTen", "value": "Trần Văn Thử"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "056 200 000 123"},
        {"name": "ChuHoSo_NgaySinh", "value": "03/12/2000"},
        {"name": "ChuHoSo_ThuongTru", "value": {"tinh": "Khánh Hòa", "xa": "Phường Cam Ranh", "diaChi": "Tổ dân phố Thử"}},
        {"name": "ChoO_DiaChi", "value": {"xa": "Phường Nha Trang", "diaChi": "Số 25 đường Thử Nghiệm"}},
        {"name": "ToKhai_TinhTrangChoO", "value": (
            "Đề nghị xác nhận chỗ ở hợp pháp tại địa chỉ nêu trên đang sử dụng ổn định, không có tranh chấp, không "
            "thuộc địa điểm không được đăng ký thường trú mới, để làm thủ tục đăng ký thường trú.")},
        {"name": "ToKhai_SoNguoiThueMuon", "value": "01 người"},
        {"name": "ToKhai_DienTichThueMuon", "value": "20 m2"},
    ]


def _cccd_facts() -> list[dict]:
    return [
        {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
        {"name": "ChuHoSo_NgayCapCccd", "value": "10/08/2024"},
        {"name": "ChuHoSo_NoiCapCccd", "value": "BỘ CÔNG AN"},
    ]


_REQUEST = (
    "Đề nghị xác nhận chỗ ở hợp pháp tại địa chỉ Số 25 đường Thử Nghiệm, phường Nha Trang, tỉnh Khánh Hòa đang sử dụng "
    "ổn định, không có tranh chấp, không thuộc địa điểm không được đăng ký thường trú mới, để làm thủ tục đăng ký thường "
    "trú. Tổng số người thuê, mượn, ở nhờ: 01 người. Tổng số diện tích chỗ ở hợp pháp thuê, mượn, ở nhờ: 20 m²."
)


# --------------------------------------------------------------------------------------
# LINK + PHẠM VI TỈNH + NHẬN DIỆN
# --------------------------------------------------------------------------------------
def test_registry_va_link_ke_khai_cung_key_tien_to_khanh_hoa():
    procedure = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    base_link = next(link for link in KE_KHAI_LINKS if link["key"] == _BASE_KEY)
    assert link["code"] == base_link["code"] == "1.013314" and link["url"] == base_link["url"]
    assert link["label"] == "Khánh Hòa - " + base_link["label"]
    assert "provinceOnlyAgency" not in link and "selectSo" not in link  # UBND phường/xã: DVCQG chọn Tỉnh + Xã
    assert procedure["mode"] == "agent" and procedure["hasAttachmentStep"] is True
    assert procedure["supportsSplitDocuments"] is True and procedure["collectFormContext"] is True
    assert procedure["label"] == link["label"]
    assert get_pipeline(_KEY) is not None and get_attach_pipeline(_KEY) is attach.plan
    assert get_pipeline(_KEY) is not get_pipeline(_BASE_KEY)


def test_detect_thang_ban_chung_tren_cong_khanh_hoa():
    """Bản chung chỉ khớp tên thủ tục; bản Khánh Hòa khoá urlScope tỉnh + thêm mã quy trình → tổng cụm dài hơn."""
    detect = get_procedure(_KEY)["detect"]
    base = get_procedure(_BASE_KEY)["detect"]
    assert detect["urlScope"] == ["khanhhoa.gov.vn"] and "urlScope" not in base
    assert detect["textPriority"] is True and base["textPriority"] is True
    assert set(base["textIncludes"]) < set(detect["textIncludes"]) and "1.013314" in detect["textIncludes"]
    page = fold(f"Quy trình: 1.013314.H32.01 - Trường hợp công dân nộp hồ sơ … {TEN_THU_TUC}")
    assert all(fold(phrase) in page for phrase in detect["textIncludes"])


@pytest.mark.parametrize("tinh, visible", [("Tỉnh Khánh Hòa", True), ("Tỉnh Quảng Ngãi", False),
                                           ("Thành phố Hà Nội", False)])
def test_link_chi_tai_khoan_khanh_hoa_thay(tinh, visible):
    user = {"role": "commune", "tinh": tinh, "xa": ""}
    links = {link["key"]: link for link in asyncio.run(procedures_router.ke_khai_links(user))["links"]}
    assert _BASE_KEY in links
    if visible:
        assert links[_KEY]["provinceOnly"] == ["khanhhoa"]
    else:
        assert _KEY not in links


def test_tro_ly_mo_rieng_khanh_hoa_cung_key_voi_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    proc = handfree.get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Khánh Hòa - " + proc["label"] == get_procedure(_KEY)["label"]
    assert proc["detect"]["urlScope"] == get_procedure(_KEY)["detect"]["urlScope"]
    assert proc["detect"]["textIncludes"] == get_procedure(_KEY)["detect"]["textIncludes"]
    assert proc["keKhaiUrl"] == link["url"] and handfree.procedure_code(proc) == "1.013314"
    assert proc["provinceOnly"] == ["khanhhoa"] and proc["bxdFlow"]["capability"] == "supportsBxdFlowKhanhHoa"
    assert proc["supportsSplitDocuments"] is True
    assert handfree.is_allowed_in_province(proc, "khanhhoa") and not handfree.is_allowed_in_province(proc, "quangngai")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert PROCEDURE_HMONG[_KEY] and PROCEDURE_HINTS[_KEY]
    config = field_review.get(_KEY)
    assert config is not None and config["required"] == ()
    assert "district" not in config["noAsk"] and "noidungyeucaugiaiquyet" in config["noAsk"]


# --------------------------------------------------------------------------------------
# ĐIỀN
# --------------------------------------------------------------------------------------
def test_tu_nop_tick_chu_ho_so_va_dien_nguoi_nop_bang_nguoi_de_nghi():
    out, warnings = mapper.enrich(_to_khai_facts() + _cccd_facts())
    values = _values(out)

    assert values["data[ownerFullname]"] == "Trần Văn Thử"
    assert values["data[ownerIdentityNumber]"] == "056200000123"
    assert values["data[ownerBirthday]"] == "03/12/2000"
    # Nơi cư trú hiện tại (mục I.4 / CCCD), KHÔNG phải chỗ ở đề nghị xác nhận.
    assert values["data[ownerAddress]"] == "Tổ dân phố Thử, Phường Cam Ranh, Tỉnh Khánh Hòa"
    assert values["data[isOwnerDossier]"] is True
    assert values["data[fullname]"] == "Trần Văn Thử"
    assert values["data[birthday]"] == "03/12/2000"
    assert values["data[gender]"] == "Nam"
    assert values["data[identityNumber]"] == "056200000123"
    assert values["data[identityDate]"] == "10/08/2024"
    assert values["data[identityAgency]"] == "Bộ Công an"
    assert values["data[nation]"] == "Việt Nam"
    assert values["data[province]"] == "Tỉnh Khánh Hòa"
    assert values["data[district]"] == "Phường Cam Ranh"
    assert values["data[address]"] == "Tổ dân phố Thử"
    assert values["data[chonDoiTuong]"] == "Cá nhân"
    assert values["data[noidungyeucaugiaiquyet]"] == _REQUEST
    # Tờ khai Mẫu 02 không có điện thoại / email → trả về trống; SĐT người nộp bắt buộc → tô đỏ.
    blanks = {item["name"]: item for item in out if item["value"] == ""}
    assert set(blanks) == {"data[email]", "data[phoneNumber]", "data[ownerPhoneNumber]"}
    assert all(item["clear"] for item in blanks.values())
    assert blanks["data[phoneNumber]"]["markEmpty"] is True and "markEmpty" not in blanks["data[ownerPhoneNumber]"]
    assert set(values) <= set(UI_COMP_BY_NAME)
    assert warnings == ["Ô bắt buộc chưa có trong giấy tờ: Số điện thoại người nộp — đã để trống, cán bộ nhập tay."]


def test_noi_dung_yeu_cau_khi_thieu_muc_iii():
    home = {"name": "ChoO_DiaChi", "value": {"tinh": "Khánh Hòa", "xa": "Phường Nha Trang", "diaChi": "Số 25 đường Thử"}}
    values = _values(mapper.enrich([home])[0])
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "Đề nghị xác nhận chỗ ở hợp pháp tại địa chỉ Số 25 đường Thử, phường Nha Trang, tỉnh Khánh Hòa.")

    # Mục III.1 không nhắc "địa chỉ nêu trên" → thêm câu địa chỉ chỗ ở đứng trước.
    status = {"name": "ToKhai_TinhTrangChoO", "value": "chỗ ở ổn định, không tranh chấp"}
    values = _values(mapper.enrich([home, status])[0])
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "Địa chỉ chỗ ở hợp pháp: Số 25 đường Thử, phường Nha Trang, tỉnh Khánh Hòa. Chỗ ở ổn định, không tranh chấp.")


def test_thieu_nguoi_va_cho_o_thi_canh_bao_va_noi_dung_mac_dinh():
    out, warnings = mapper.enrich([])
    values = _values(out)
    assert values["data[noidungyeucaugiaiquyet]"] == TEN_THU_TUC
    assert values["data[isOwnerDossier]"] is True
    assert any("Thiếu họ tên" in w for w in warnings) and any("chỗ ở hợp pháp" in w for w in warnings)


def test_khong_muon_dia_chi_cho_o_lam_noi_cu_tru_chu_ho_so():
    fields = [item for item in _to_khai_facts() if item["name"] != "ChuHoSo_ThuongTru"]
    out, _warnings = mapper.enrich(fields)
    values = _values(out)
    assert values["data[ownerAddress]"] == "" and values["data[address]"] == ""
    assert "data[province]" not in values and "data[district]" not in values


def test_cccd_nguoi_khac_la_nguoi_nop_thay_bo_tick_dien_ca_hai_khoi():
    fields = _to_khai_facts() + _cccd_facts() + [{"name": "NguoiNopThay", "value": {
        "hoTen": "LÊ THỊ AN", "soDinhDanh": "056301000456", "ngaySinh": "05/06/2001", "ngayCapCccd": "01/07/2024",
        "dienThoai": "0900000456",
        "thuongTru": {"tinh": "Khánh Hòa", "xa": "Phường Nha Trang", "diaChi": "Tổ dân phố Hai"},
    }}]
    out, _warnings = mapper.enrich(fields)
    values = _values(out)

    assert values["data[isOwnerDossier]"] is False
    assert values["data[fullname]"] == "LÊ THỊ AN" and values["data[identityNumber]"] == "056301000456"
    assert values["data[gender]"] == "Nữ"  # chữ số thứ 4 là 3 → nữ sinh thế kỷ 21
    assert values["data[phoneNumber]"] == "0900000456"
    assert values["data[district]"] == "Phường Nha Trang" and values["data[address]"] == "Tổ dân phố Hai"
    assert values["data[ownerFullname]"] == "Trần Văn Thử"
    assert values["data[ownerAddress]"] == "Tổ dân phố Thử, Phường Cam Ranh, Tỉnh Khánh Hòa"
    assert values["data[noidungyeucaugiaiquyet]"] == _REQUEST


def test_lay_nguoi_nop_theo_to_khai_bo_nguoi_nop_thay():
    fields = _to_khai_facts() + [{"name": "NguoiNopThay", "value": {"hoTen": "LÊ THỊ AN", "soDinhDanh": "056301000456"}}]
    values = _values(mapper.enrich(fields, {"submitterMode": "owner_as_submitter"})[0])
    assert values["data[isOwnerDossier]"] is True and values["data[fullname]"] == "Trần Văn Thử"


def test_nguoi_nop_thay_trung_chu_ho_so_van_la_tu_nop():
    fields = _to_khai_facts() + [{"name": "NguoiNopThay", "value": {"hoTen": "TRẦN VĂN THỬ"}}]
    values = _values(mapper.enrich(fields)[0])
    assert values["data[isOwnerDossier]"] is True and values["data[fullname]"] == "Trần Văn Thử"


def test_tai_khoan_la_nguoi_nop_giu_khoi_nguoi_nop_cua_cong():
    options = {"formContext": {"applicantIdentityNumber": "056200000123"}}
    out, warnings = mapper.enrich(_to_khai_facts(), options)
    blanks = {item["name"] for item in out if item["value"] == ""}
    assert blanks == {"data[ownerPhoneNumber]"}
    assert not any("Ô bắt buộc" in w for w in warnings)


def test_prompt_dien_khoa_vai_nguoi_de_nghi_va_hai_dia_chi():
    assert "NGƯỜI ĐỀ NGHỊ" in EXTRA_RULES and "Khánh Hòa" in EXTRA_RULES
    assert "ChoO_DiaChi" in EXTRA_RULES and "ChuHoSo_ThuongTru" in EXTRA_RULES
    assert {"NguoiNopThay", "ChuHoSo_HoTen", "ChuHoSo_ThuongTru", "ChoO_DiaChi", "ToKhai_TinhTrangChoO",
            "ToKhai_SoNguoiThueMuon", "ToKhai_DienTichThueMuon"} <= ALLOWED


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — KHÔNG TÁCH
# --------------------------------------------------------------------------------------
def test_moi_tep_dinh_mot_lan_vao_dong_duy_nhat():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["to-khai.pdf", "cccd.pdf", "hop-dong.pdf", "la.pdf"]), None,
        {0: ["to_khai"], 1: ["identity"], 2: ["giay_to_cho_o"], 3: "abc"},
    )
    assert [(item["fileIndex"], item["componentIndex"], item["componentName"]) for item in attachments] == [
        (i, 1, _ROW_NAME) for i in range(4)]
    assert [item["documentName"] for item in attachments] == [
        "Tờ khai xác nhận tình trạng chỗ ở hợp pháp", "Căn cước công dân", "Giấy tờ chứng minh chỗ ở hợp pháp",
        "la.pdf"]
    assert all(item["target"] == "attp-row" and "loaiBan" not in item for item in attachments)
    assert len(warnings) == 1 and "la.pdf" in warnings[0]


def test_thieu_to_khai_thi_canh_bao():
    _attachments, warnings, _classified = planner.build_plan_items(
        _files(["cccd.pdf", "gcn.pdf"]), None, {0: ["identity"], 1: ["gcn"]})
    assert len(warnings) == 1 and "Mẫu số 02" in warnings[0]


def test_do_dong_that_tren_trang_theo_attachment_context():
    options = {"attachmentContext": {"components": [
        {"index": 1, "componentName": "Tờ khai xác nhận tình trạng chỗ ở hợp pháp, diện tích nhà ở tối thiểu để đăng ký "
                                      "thường trú, đăng ký tạm trú (Mẫu số 02)"}]}}
    assert planner.resolve_row(planner.portal_rows(options))[0] == 1
    other = {"attachmentContext": {"components": [{"index": 1, "componentName": "Giấy tờ khác"}]}}
    index, name, note = planner.resolve_row(planner.portal_rows(other))
    assert (index, name) == (1, "Giấy tờ khác") and "Giấy tờ khác" in note


def test_prompt_dinh_kem_ghi_cong_khanh_hoa_du_loai():
    for doc_type in list(planner._NAMES) + ["other"]:
        assert doc_type in SYSTEM_PROMPT and doc_type in TACH_PROMPT, doc_type
    assert "Khánh Hòa" in SYSTEM_PROMPT and "Khánh Hòa" in TACH_PROMPT


def test_tat_tach_dinh_nguyen_tep(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        assert "Khánh Hòa" in messages[0]["content"]
        return '{"documents":[{"index":0,"docTypes":["to_khai","gcn"]},{"index":1,"docTypes":["identity"]}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=n, type="application/pdf", dataUrl="x") for n in ("ho-so.pdf", "cccd.pdf")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": False}))

    assert [(item["componentIndex"], item["componentName"], item["documentName"], "sourceSegments" in item)
            for item in result["attachments"]] == [(1, _ROW_NAME, "ho-so.pdf", False),
                                                   (1, _ROW_NAME, "Căn cước công dân", False)]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — TÁCH
# --------------------------------------------------------------------------------------
_PAGE = "Nội dung trang đủ dài để không bị coi là trang trắng của bản scan hồ sơ xác nhận chỗ ở hợp pháp. " * 2


def _pdf_data_url(pages: int) -> str:
    with fitz.open() as doc:
        for _ in range(pages):
            doc.new_page()
        return "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()


def test_dieu_phoi_theo_cai_dat_tach(monkeypatch):
    calls = []

    async def fake_tach(files, options, session):
        calls.append("tach")
        return {}

    async def fake_khong_tach(files, options, session):
        calls.append("khong_tach")
        return {}

    monkeypatch.setattr(dispatcher, "plan_with_split", fake_tach)
    monkeypatch.setattr(dispatcher, "plan_without_split", fake_khong_tach)
    for options in ({"splitDocuments": True}, {}, None, {"splitDocuments": "true"},
                    {"splitDocuments": True, "supportsSourceSegments": False}):
        asyncio.run(attach.plan([], options))
    assert calls == ["tach", "khong_tach", "khong_tach", "khong_tach", "khong_tach"]


def test_tach_ho_so_gop_dung_dong_khong_sot_trang(monkeypatch):
    """PDF gộp 6 trang: Tờ khai 2 trang (1-2) + CCCD hai mặt (3-4) + hợp đồng thuê nhà (5-6) → 3 mục, phủ đủ 6 trang."""
    from app.services import ocr

    text = "\n".join(f"───── Trang {n}/6 ─────\n{_PAGE}" for n in range(1, 7))

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": text} for item in files]

    async def fake_chat(messages, **kwargs):
        assert "Khánh Hòa" in messages[0]["content"]
        return ('{"tep":[{"fileIndex":0,"giayTo":[{"trangDau":1,"docType":"to_khai","ten":""},'
                '{"trangDau":3,"docType":"identity","ten":"Căn cước công dân"},'
                '{"trangDau":5,"docType":"giay_to_cho_o","ten":"Hợp đồng thuê nhà ở"}]}]}')

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl=_pdf_data_url(6))]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    items = result["attachments"]
    assert [(item["componentIndex"], item["componentName"], item["sourceSegments"]) for item in items] == [
        (1, _ROW_NAME, [{"fileIndex": 0, "pageIndexes": [0, 1]}]),
        (1, _ROW_NAME, [{"fileIndex": 0, "pageIndexes": [2, 3]}]),
        (1, _ROW_NAME, [{"fileIndex": 0, "pageIndexes": [4, 5]}]),
    ]
    assert [item["documentName"] for item in items] == [
        "Tờ khai xác nhận tình trạng chỗ ở hợp pháp", "Căn cước công dân", "Hợp đồng thuê nhà ở"]
    covered = sorted(p for item in items for p in item["sourceSegments"][0]["pageIndexes"])
    assert covered == list(range(6))
    assert result["errors"] == []


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    from app.services import ocr

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def broken_segment(units):
        raise ValueError("JSON hỏng")

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["to_khai","identity"]}]}'

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(tach, "_segment", broken_segment)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl="x")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [item["componentIndex"] for item in result["attachments"]] == [1]
    assert "sourceSegments" not in result["attachments"][0]
    assert result["errors"][0].startswith("Tách giấy tờ: JSON hỏng")
