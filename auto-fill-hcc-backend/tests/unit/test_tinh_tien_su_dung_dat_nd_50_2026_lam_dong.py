"""Test [Tỉnh Lâm Đồng] "Thủ tục tính hoặc tính lại tiền sử dụng đất theo quy định tại các điểm a, b, c và d khoản 2 Điều
12 Nghị định số 50/2026/NĐ-CP" (1.115148, cổng dichvucong.lamdong.gov.vn).

Khoá:
1. ĐIỀN: Phần I-III theo file mapping (Phần IV giấy phép để trống); tự nộp bấm nút "Người nộp là chủ hồ sơ"; có giấy
   người nộp thay điền cả hai khối; tài khoản là người khác mà không có giấy của họ → giữ Phần I của cổng, điền Phần III;
   ô Ghi chú ghi số thửa / tờ bản đồ / diện tích + địa chỉ thửa.
2. ĐÍNH KÈM KHÔNG TÁCH: bảng một dòng "Văn bản đề nghị tính hoặc tính lại tiền sử dụng đất", mọi tệp vào dòng đó, mỗi
   tệp một lần; thiếu Văn bản đề nghị thì cảnh báo.
3. ĐÍNH KÈM TÁCH: mỗi giấy một mục có sourceSegments, không sót trang, ghép hai mặt CCCD, tách lỗi quay về không tách,
   tắt tách đính nguyên tệp.
Dữ liệu người trong test là BỊA. Không gọi LLM / OCR thật.
"""

import asyncio
import base64
from types import SimpleNamespace

import fitz

from app.pipelines._shared import fold
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong import attach
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.attach import planner as dispatcher
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.attach.dinh_kem_khong_tach import planner
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.attach.dinh_kem_khong_tach.prompt import SYSTEM_PROMPT
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.attach.dinh_kem_tach import planner as tach
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT as TACH_PROMPT,
)
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.process import mapper
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.process.prompt import EXTRA_RULES
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "tinh-tien-su-dung-dat-nd-50-2026-lam-dong"
_ROW_NAME = "Văn bản đề nghị tính hoặc tính lại tiền sử dụng đất"


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _don_facts() -> list[dict]:
    """Chỉ những gì Đơn đề nghị cấp GPXD có: tên chủ đầu tư, số định danh + SĐT viết tay, địa điểm xây dựng."""
    return [
        {"name": "ChuHoSo_HoTen", "value": "PHẠM THỊ HOA"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "068185000123"},
        {"name": "ChuHoSo_DienThoai", "value": "0900.00.0123"},
        {"name": "ThuaDat_DiaChi", "value": {"tinh": "Lâm Đồng", "xa": "Đơn Dương", "diaChi": "Thôn Thử Nghiệm"}},
        {"name": "ThuaDat_SoThua", "value": "Thửa Đất Số 45"},
        {"name": "ThuaDat_SoTo", "value": "TBĐ 7"},
        {"name": "ThuaDat_DienTich", "value": "250,5 m2"},
    ]


def _cccd_facts() -> list[dict]:
    return [
        {"name": "ChuHoSo_NgaySinh", "value": "15/08/1985"},
        {"name": "ChuHoSo_GioiTinh", "value": "Nữ"},
        {"name": "ChuHoSo_NgayCapCccd", "value": "20/08/2025"},
        {"name": "ChuHoSo_NoiCapCccd", "value": "BỘ CÔNG AN"},
        {"name": "ChuHoSo_ThuongTru", "value": {"tinh": "Lâm Đồng", "xa": "Xã Đơn Dương", "diaChi": "Thôn Thử Nghiệm"}},
    ]


# --------------------------------------------------------------------------------------
# ĐIỀN
# --------------------------------------------------------------------------------------
def test_tu_nop_dien_phan_i_ii_ghi_chu_va_bam_nut_nguoi_nop_la_chu_ho_so():
    out, warnings = mapper.enrich(_don_facts() + _cccd_facts())
    values = _values(out)

    assert values["data[fullname]"] == "PHẠM THỊ HOA"
    assert values["data[birthday]"] == "15/08/1985"
    assert values["data[gender]"] == "Nữ"
    assert values["data[identityNumber]"] == "068185000123"
    assert values["data[identityDate]"] == "20/08/2025"
    assert values["data[identityAgency]"] == "Bộ Công an"
    assert values["data[phoneNumber]"] == "0900000123"
    assert values["data[nation]"] == "Việt Nam"
    assert values["data[province]"] == "Tỉnh Lâm Đồng"
    assert values["data[district]"] == "Xã Đơn Dương"
    assert values["data[address]"] == "Thôn Thử Nghiệm"
    assert values["data[province2]"] == "Tỉnh Lâm Đồng"
    assert values["data[village2]"] == "Xã Đơn Dương"
    assert values["data[ghiChu]"] == (
        "Thửa đất số 45, tờ bản đồ số 7, diện tích 250,5 m², Thôn Thử Nghiệm, Xã Đơn Dương, Tỉnh Lâm Đồng")
    assert values["data[BUTTON3]"] is True
    assert not [name for name in values if name.startswith("data[owner")]
    assert "data[organization]" not in values
    assert warnings == []


def test_tai_khoan_nguoi_khac_khong_co_giay_giu_phan_i_cong_dien_phan_iii():
    """Bộ mẫu của file mapping: chỉ có Đơn của chủ đầu tư, tài khoản đăng nhập là người nộp thay khác tên."""
    options = {"formContext": {"applicantFullname": "LÊ VĂN AN", "applicantIdentityNumber": "001203000456"}}
    out, warnings = mapper.enrich(_don_facts(), options)
    values = _values(out)
    expects = {item["name"] for item in out if item["comp"] == "dom-expect"}

    # Phần I: cổng đã đổ họ tên / ngày sinh / số định danh theo tài khoản → không ghi đè, chỉ tô đỏ ô bắt buộc còn trống.
    assert not {"data[fullname]", "data[identityNumber]", "data[birthday]", "data[gender]"} & set(values)
    assert {"data[phoneNumber]", "data[province]", "data[district]", "data[address]"} <= expects
    assert "data[BUTTON3]" not in values
    # Phần III theo Đơn; giới tính suy từ chữ số thứ 4 của số định danh (1 = nữ); Đơn GPXD không có nơi ở chủ đầu tư.
    assert values["data[ownerFullname]"] == "PHẠM THỊ HOA"
    assert values["data[ownerIdentityNumber]"] == "068185000123"
    assert values["data[ownerPhoneNumber]"] == "0900000123"
    assert values["data[gender1]"] == "Nữ"
    assert values["data[nation1]"] == "Việt Nam"
    assert {"data[ownerBirthday]", "data[province1]", "data[district1]", "data[ownerAddress]"} <= expects
    assert values["data[village2]"] == "Xã Đơn Dương"
    assert len(warnings) == 1 and "Tài khoản đăng nhập không phải chủ hồ sơ" in warnings[0]


def test_tai_khoan_cung_ten_chu_ho_so_la_tu_nop_du_so_doc_lech():
    """Số định danh viết tay trên Đơn đọc lệch một chữ số không được coi là người khác khi họ tên trùng."""
    options = {"formContext": {"applicantFullname": "Phạm Thị Hoa", "applicantIdentityNumber": "068185000128"}}
    values = _values(mapper.enrich(_don_facts(), options)[0])
    assert values["data[BUTTON3]"] is True and values["data[fullname]"] == "PHẠM THỊ HOA"
    assert mapper.account_is_other_person({}, "PHẠM THỊ HOA", "068185000123") is False
    assert mapper.account_is_other_person({"formContext": {"applicantIdentityNumber": "001203000456"}},
                                          None, "068185000123") is True


def test_cccd_nguoi_khac_la_nguoi_nop_thay_dien_ca_hai_khoi():
    fields = _don_facts() + _cccd_facts() + [{"name": "NguoiNopThay", "value": {
        "hoTen": "LÊ VĂN AN", "soDinhDanh": "001203000456", "ngaySinh": "03/12/2003", "ngayCapCccd": "01/07/2024",
        "thuongTru": {"tinh": "Lâm Đồng", "xa": "Phường Xuân Hương - Đà Lạt", "diaChi": "Tổ dân phố Thử"},
    }}]
    values = _values(mapper.enrich(fields)[0])

    assert "data[BUTTON3]" not in values
    assert values["data[fullname]"] == "LÊ VĂN AN"
    assert values["data[gender]"] == "Nam"  # chữ số thứ 4 là 2 → nam sinh thế kỷ 21
    assert values["data[identityAgency]"] == "Bộ Công an"  # thẻ cấp từ 01/7/2024
    assert values["data[district]"] == "Phường Xuân Hương - Đà Lạt"
    assert values["data[ownerFullname]"] == "PHẠM THỊ HOA"
    assert values["data[district1]"] == "Xã Đơn Dương"
    # SĐT trong Đơn là của chủ hồ sơ — không mượn sang ô người nộp thay (FE tô đỏ ô trống).
    assert values["data[ownerPhoneNumber]"] == "0900000123"
    assert values["data[phoneNumber]"] == ""


def test_nguoi_nop_thay_trung_chu_ho_so_van_la_tu_nop():
    fields = _don_facts() + [{"name": "NguoiNopThay", "value": {"hoTen": "Phạm Thị Hoa", "soDinhDanh": "068185000123"}}]
    values = _values(mapper.enrich(fields)[0])
    assert values["data[BUTTON3]"] is True and not [n for n in values if n.startswith("data[owner")]


def test_ghi_chu_va_gioi_tinh_suy_tat_dinh():
    assert mapper.ghi_chu({"ThuaDat_SoThua": "12"}, None) == "Thửa đất số 12"
    assert mapper.ghi_chu({}, {"tinh": "Lâm Đồng", "xa": "Xã Đơn Dương"}) is None
    assert mapper._gender("Ông", None) == "Nam" and mapper._gender("bà", None) == "Nữ"
    assert mapper._gender(None, "068090000001") == "Nam" and mapper._gender(None, "068195000001") == "Nữ"
    assert mapper._gender(None, "123456789") is None


def test_khong_dien_phan_iv_giay_phep():
    values = _values(mapper.enrich(_don_facts() + _cccd_facts())[0])
    assert not [name for name in UI_COMP_BY_NAME if name.startswith(("data[license", "data[effective", "data[expir"))]
    assert set(values) <= set(UI_COMP_BY_NAME)


def test_thieu_nguoi_va_thua_dat_thi_canh_bao():
    out, warnings = mapper.enrich([])
    assert {item["comp"] for item in out} == {"dom-expect", "dom-owner-copy"}
    assert len(warnings) == 2


def test_prompt_dien_neu_ro_hai_loai_don_va_nguoi_nop_thay():
    assert "ĐƠN ĐỀ NGHỊ CẤP GIẤY PHÉP XÂY DỰNG" in EXTRA_RULES and "TÍNH (TÍNH LẠI) TIỀN SỬ DỤNG ĐẤT" in EXTRA_RULES
    assert "Địa điểm" in EXTRA_RULES and "số ĐẦU TIÊN" in EXTRA_RULES and "NguoiNopThay" in EXTRA_RULES
    assert {"NguoiNopThay", "ChuHoSo_HoTen", "ThuaDat_DiaChi", "ThuaDat_SoThua", "ThuaDat_DienTich"} <= ALLOWED


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — KHÔNG TÁCH
# --------------------------------------------------------------------------------------
def test_moi_tep_dinh_mot_lan_vao_dong_duy_nhat():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["don.pdf", "cccd.pdf", "gcn.pdf", "tb.pdf", "la.pdf"]), None,
        {0: ["van_ban_de_nghi"], 1: ["identity"], 2: ["gcn"], 3: ["thong_bao_nop_tien"], 4: "abc"},
    )
    assert [(item["fileIndex"], item["componentIndex"], item["componentName"]) for item in attachments] == [
        (i, 1, _ROW_NAME) for i in range(5)]
    assert [item["documentName"] for item in attachments] == [
        _ROW_NAME, "Căn cước công dân", "Giấy chứng nhận quyền sử dụng đất", "Thông báo nộp tiền sử dụng đất", "la.pdf"]
    assert all(item["target"] == "attp-row" and "loaiBan" not in item for item in attachments)
    assert len(warnings) == 1 and "la.pdf" in warnings[0]
    assert [item["source"] for item in classified] == ["llm"] * 5


def test_chi_co_don_gpxd_thi_canh_bao_thieu_van_ban_de_nghi():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["don-gpxd.pdf", "cccd.pdf"]), None, {0: ["don_gpxd"], 1: ["identity"]})
    assert [item["documentName"] for item in attachments] == ["Đơn đề nghị cấp giấy phép xây dựng", "Căn cước công dân"]
    assert len(warnings) == 1 and "giấy phép xây dựng" in warnings[0] and _ROW_NAME in warnings[0]
    assert planner.build_plan_items([], None, {})[1] == []


def test_file_gop_giu_ten_goc_va_bao_giay_nam_chung():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["ho-so.pdf"]), None, {0: ["identity", "van_ban_de_nghi", "gcn"]})
    assert [(item["componentIndex"], item["documentName"], item["detectedType"]) for item in attachments] == [
        (1, "ho-so.pdf", "van_ban_de_nghi")]
    assert len(warnings) == 1 and "gộp nhiều giấy tờ" in warnings[0]


def test_do_dong_that_tren_trang_khi_co_attachment_context():
    rows = [(1, "Bản sao giấy tờ khác"), (2, _ROW_NAME)]
    options = {"attachmentContext": {"components": [{"index": i, "componentName": n} for i, n in rows]}}
    attachments, warnings, _ = planner.build_plan_items(
        _files(["don.pdf"]), None, {0: ["van_ban_de_nghi"]}, planner.portal_rows(options))
    assert [(item["componentIndex"], item["componentName"]) for item in attachments] == [(2, _ROW_NAME)]
    assert warnings == []
    # Trang không có dòng Văn bản đề nghị → dòng đầu của trang + cảnh báo.
    other = [(3, "Tờ khai", fold("Tờ khai"))]
    assert planner.resolve_row(other)[:2] == (3, "Tờ khai") and planner.resolve_row(other)[2]


def test_prompt_dinh_kem_liet_ke_du_loai():
    for doc_type in list(planner._NAMES) + ["other"]:
        assert doc_type in SYSTEM_PROMPT and doc_type in TACH_PROMPT, doc_type
    assert '"docTypes"' in SYSTEM_PROMPT and '"trangDau"' in TACH_PROMPT


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — TÁCH
# --------------------------------------------------------------------------------------
_PAGE = "Nội dung trang đủ dài để không bị coi là trang trắng của bản scan hồ sơ tính lại tiền sử dụng đất. " * 2


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


def test_tach_ho_so_gop_moi_giay_mot_muc_khong_sot_trang():
    """PDF gộp: Văn bản đề nghị (2 trang, trang 2 trắng) + CCCD hai mặt + Giấy chứng nhận 2 trang + thông báo 1 trang."""
    pages = [_PAGE, "", _PAGE, _PAGE, _PAGE, _PAGE, _PAGE]
    documents = {0: [(0, "van_ban_de_nghi", "Văn bản đề nghị tính lại tiền sử dụng đất"),
                     (2, "identity", "Căn cước công dân"),
                     (4, "gcn", "Giấy chứng nhận quyền sử dụng đất"),
                     (6, "thong_bao_nop_tien", "")]}
    attachments, warnings, segments = tach.build_plan_items(_files(["ho-so.pdf"]), {0: pages}, documents)

    assert [(item["componentIndex"], item["sourceSegments"][0]["pageIndexes"]) for item in attachments] == [
        (1, [0]), (1, [2, 3]), (1, [4, 5]), (1, [6])]
    assert attachments[3]["documentName"] == "Thông báo nộp tiền sử dụng đất"
    covered = sorted(p for item in attachments for p in item["sourceSegments"][0]["pageIndexes"])
    assert covered == [p for p in range(len(pages)) if pages[p]]  # chỉ bỏ trang trắng
    assert warnings == [] and segments[1]["pages"] == [3, 4]


def test_tach_tep_mot_giay_khong_cat_va_tep_khong_cat_duoc_dinh_nguyen():
    attachments, warnings, _segments = tach.build_plan_items(
        _files(["don.pdf", "gop.jpg"]), {0: [_PAGE, _PAGE], 1: ["trích đoạn"]},
        {0: [(0, "don_gpxd", "")], 1: [(0, "gcn", ""), (0, "identity", "")]},
    )
    assert [(item["documentName"], "sourceSegments" in item) for item in attachments] == [
        ("Đơn đề nghị cấp giấy phép xây dựng", False), ("gop.jpg", False)]
    assert len(warnings) == 1 and "giấy phép xây dựng" in warnings[0]


def test_tach_cat_dung_trang_pdf_that(monkeypatch):
    from app.services import ocr

    text = "\n".join(f"───── Trang {n}/3 ─────\n{_PAGE}" for n in range(1, 4))

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": text} for item in files]

    async def fake_chat(messages, **kwargs):
        return ('{"tep":[{"fileIndex":0,"giayTo":[{"trangDau":1,"docType":"van_ban_de_nghi","ten":"Văn bản đề nghị"},'
                '{"trangDau":2,"docType":"identity","ten":"Căn cước công dân"}]}]}')

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl=_pdf_data_url(3))]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [(item["componentIndex"], item["sourceSegments"]) for item in result["attachments"]] == [
        (1, [{"fileIndex": 0, "pageIndexes": [0]}]), (1, [{"fileIndex": 0, "pageIndexes": [1, 2]}])]
    assert result["errors"] == []


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    from app.services import ocr

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def broken_segment(units):
        raise ValueError("JSON hỏng")

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["van_ban_de_nghi","identity"]}]}'

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(tach, "_segment", broken_segment)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl="x")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [item["componentIndex"] for item in result["attachments"]] == [1]
    assert "sourceSegments" not in result["attachments"][0]
    assert result["errors"][0].startswith("Tách giấy tờ: JSON hỏng")


def test_tat_tach_dinh_nguyen_tep(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["van_ban_de_nghi","gcn"]},{"index":1,"docTypes":["identity"]}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=n, type="application/pdf", dataUrl="x") for n in ("ho-so.pdf", "cccd.pdf")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": False}))

    assert [(item["componentIndex"], "sourceSegments" in item) for item in result["attachments"]] == [
        (1, False), (1, False)]


# --------------------------------------------------------------------------------------
# REGISTRY + TRỢ LÝ
# --------------------------------------------------------------------------------------
def test_registry_va_link_ke_khai_cung_key():
    procedure = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert link["code"] == "1.115148"
    assert procedure["mode"] == "agent" and procedure["hasAttachmentStep"] is True
    assert procedure["supportsSplitDocuments"] is True
    assert procedure["detect"]["urlScope"] == ["lamdong.gov.vn"]
    # Cùng mã 1.115148 với bản Quảng Ninh / Quảng Ngãi: cùng cụm chữ nhận diện, chỉ khác urlScope theo tỉnh.
    for other in ("tinh-tien-su-dung-dat-nd-50-2026-quang-ninh", "tinh-tien-su-dung-dat-nd-50-2026-quang-ngai"):
        assert not set(get_procedure(other)["detect"]["urlScope"]) & set(procedure["detect"]["urlScope"]), other
    assert all(fold(phrase) in fold(link["label"]) for phrase in procedure["detect"]["textIncludes"])
    assert get_pipeline(_KEY) is not None and get_attach_pipeline(_KEY) is attach.plan


def test_tro_ly_mo_rieng_lam_dong_cung_key_voi_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    proc = handfree.get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "[Tỉnh Lâm Đồng] " + proc["label"] == get_procedure(_KEY)["label"]
    assert proc["detect"]["urlScope"] == get_procedure(_KEY)["detect"]["urlScope"]
    assert proc["detect"]["textIncludes"] == get_procedure(_KEY)["detect"]["textIncludes"]
    assert proc["keKhaiUrl"] == link["url"] and handfree.procedure_code(proc) == "1.115148"
    assert proc["provinceOnly"] == ["lamdong"] and proc["bxdFlow"]["capability"] == "supportsBxdFlowLamDong"
    assert proc["supportsSplitDocuments"] is True
    assert handfree.is_allowed_in_province(proc, "lamdong") and not handfree.is_allowed_in_province(proc, "quangninh")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert PROCEDURE_HMONG[_KEY]
    assert field_review.get(_KEY) is not None
