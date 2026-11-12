"""Test [Tỉnh Lâm Đồng] "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất …; giao đất và giao rừng; cho thuê đất và cho
thuê rừng, gia hạn sử dụng đất khi hết thời hạn sử dụng đất" (1.116366, cổng dichvucong.lamdong.gov.vn).

Khoá:
1. ĐIỀN: Phần I-III theo file mapping (không có Phần IV), tự nộp bấm nút "Người nộp là chủ hồ sơ", nộp thay điền cả hai
   khối; SĐT Đơn ghi hai số → lấy số đầu; ô Ghi chú / Cơ quan tổ chức để trống.
2. ĐÍNH KÈM KHÔNG TÁCH: bảng 26 dòng crawl — Đơn + ủy quyền + CCCD dòng 13, Giấy chứng nhận / mảnh trích đo / giấy lạ
   dòng 24, mỗi tên dòng chỉ khớp đúng dòng của nó theo thuật toán FE, dò dòng thật khi có attachmentContext.
3. ĐÍNH KÈM TÁCH: mỗi giấy một mục có sourceSegments, không sót trang, ghép hai mặt CCCD, tách lỗi quay về không tách,
   tắt tách đính nguyên tệp.
Dữ liệu người trong test là BỊA. Không gọi LLM / OCR thật.
"""

import asyncio
import base64
import re
from types import SimpleNamespace

import fitz

from app.pipelines._shared import fold
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat import attach
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.attach import planner as dispatcher
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.attach.dinh_kem_khong_tach import planner
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.attach.dinh_kem_khong_tach.prompt import SYSTEM_PROMPT
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.attach.dinh_kem_tach import planner as tach
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT as TACH_PROMPT,
)
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.process import mapper
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.process.prompt import EXTRA_RULES
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "giao-thue-dat-giao-rung-gia-han-su-dung-dat"

# Cột "Tên giấy tờ" của 26 dòng thành phần hồ sơ, đúng thứ tự DOM (crawl-dinh-kem-1.116366.json, 12/11/2026).
_ROWS = [planner._ROWS[stt] for stt in range(1, 27)]


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


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _owner_facts() -> list[dict]:
    return [
        {"name": "Nguoi_HoTen", "value": "NGUYỄN THỊ LAN"},
        {"name": "Nguoi_NgaySinh", "value": "03/04/1990"},
        {"name": "Nguoi_GioiTinh", "value": "Nữ"},
        {"name": "Nguoi_SoDinhDanh", "value": "068190000001"},
        {"name": "Nguoi_NgayCapCccd", "value": "10/05/2021"},
        {"name": "Nguoi_NoiCapCccd", "value": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"},
        {"name": "Nguoi_DienThoai", "value": "0900.000.001 (0900000002)"},
        {"name": "Nguoi_ThuongTru", "value": {"tinh": "Lâm Đồng", "xa": "Phường Lâm Viên - Đà Lạt",
                                              "diaChi": "10 Đường Thử Nghiệm"}},
        {"name": "ThuaDat_DiaChi", "value": {"tinh": "Tỉnh Lâm Đồng", "xa": "Phường Lâm Viên - Đà Lạt"}},
    ]


# --------------------------------------------------------------------------------------
# ĐIỀN
# --------------------------------------------------------------------------------------
def test_tu_nop_dien_phan_i_ii_va_bam_nut_nguoi_nop_la_chu_ho_so():
    out, warnings = mapper.enrich(_owner_facts())
    values = _values(out)

    assert values["data[fullname]"] == "NGUYỄN THỊ LAN"
    assert values["data[birthday]"] == "03/04/1990"
    assert values["data[gender]"] == "Nữ"
    assert values["data[identityNumber]"] == "068190000001"
    assert values["data[identityDate]"] == "10/05/2021"
    assert values["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[nation]"] == "Việt Nam"
    assert values["data[province]"] == "Tỉnh Lâm Đồng"
    assert values["data[district]"] == "Phường Lâm Viên - Đà Lạt"
    assert values["data[address]"] == "10 Đường Thử Nghiệm"
    assert values["data[province2]"] == "Tỉnh Lâm Đồng"
    assert values["data[village2]"] == "Phường Lâm Viên - Đà Lạt"
    assert values["data[BUTTON3]"] is True
    assert not [name for name in values if name.startswith("data[owner")]
    assert warnings == []


def test_sdt_hai_so_chi_lay_so_dau():
    values = _values(mapper.enrich(_owner_facts())[0])
    assert values["data[phoneNumber]"] == "0900000001"
    assert mapper._phone("0900 000 003 - 0900000004") == "0900000003"
    assert mapper._phone("+84 900 000 005") == "0900000005"
    assert mapper._phone("không có") is None


def test_nop_thay_dien_ca_hai_khoi_va_khong_bam_nut():
    fields = _owner_facts() + [{"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "TRẦN VĂN BÌNH", "soDinhDanh": "068095000002", "ngaySinh": "13/09/1995", "gioiTinh": "Nam",
        "ngayCapCccd": "05/06/2022", "noiCapCccd": "Bộ Công an",
        "thuongTru": {"tinh": "Lâm Đồng", "xa": "Phường Xuân Hương - Đà Lạt", "diaChi": "Tổ dân phố Thử"},
    }}]
    values = _values(mapper.enrich(fields)[0])

    assert "data[BUTTON3]" not in values
    assert values["data[fullname]"] == "TRẦN VĂN BÌNH"
    assert values["data[identityAgency]"] == "Bộ Công an"
    assert values["data[district]"] == "Phường Xuân Hương - Đà Lạt"
    assert values["data[ownerFullname]"] == "NGUYỄN THỊ LAN"
    assert values["data[ownerIdentityNumber]"] == "068190000001"
    assert values["data[district1]"] == "Phường Lâm Viên - Đà Lạt"
    # SĐT ghi trong Đơn là của người đề nghị — không mượn sang ô người nộp thay (FE tô đỏ ô trống).
    assert values["data[ownerPhoneNumber]"] == "0900000001"
    assert values["data[phoneNumber]"] == ""


def test_khong_dien_phan_iv_ghi_chu_va_co_quan_to_chuc():
    values = _values(mapper.enrich(_owner_facts())[0])
    assert "data[ghiChu]" not in values and "data[organization]" not in values
    assert not [name for name in UI_COMP_BY_NAME if name.startswith(("data[license", "data[effective", "data[expir"))]
    assert {name for name in values} <= set(UI_COMP_BY_NAME)


def test_thieu_nguoi_va_thua_dat_thi_canh_bao():
    out, warnings = mapper.enrich([])
    # Không có giấy ủy quyền → vẫn coi là tự nộp (bấm nút chủ hồ sơ); mọi ô người tô đỏ.
    assert {item["comp"] for item in out} == {"dom-expect", "dom-owner-copy"}
    assert len(warnings) == 2


def test_prompt_dien_neu_ro_don_mau_01_va_muc_6_gcn():
    assert "Mẫu số 01" in EXTRA_RULES and "mục 6" in EXTRA_RULES and "số ĐẦU TIÊN" in EXTRA_RULES
    assert {"NguoiDuocUyQuyen", "Nguoi_HoTen", "ThuaDat_DiaChi"} <= ALLOWED
    assert not [name for name in ALLOWED if name.startswith("Gcn_")]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — KHÔNG TÁCH
# --------------------------------------------------------------------------------------
def test_bo_ho_so_mau_dinh_dung_dong():
    """Bộ mẫu: Đơn, CCCD → dòng 13; Giấy chứng nhận, mảnh trích đo → dòng 24 'Giấy tờ khác'."""
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["gcn.pdf", "trich-do.pdf", "cccd.pdf", "don.pdf"]), None,
        {0: ["gcn"], 1: ["trich_do"], 2: ["identity"], 3: ["don_de_nghi"]},
    )
    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [(0, 24), (1, 24), (2, 13), (3, 13)]
    assert [item["documentName"] for item in attachments] == [
        "Giấy chứng nhận quyền sử dụng đất", "Mảnh trích đo bản đồ địa chính", "Căn cước công dân",
        "Đơn đề nghị giao đất, cho thuê đất, chuyển mục đích sử dụng đất (Mẫu số 01)"]
    assert all(item["target"] == "attp-row" and "loaiBan" not in item for item in attachments)
    assert warnings == []


def test_uy_quyen_di_chung_dong_don_giay_la_di_dong_giay_to_khac():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["uq.pdf", "la.pdf", "trong.pdf"]), None, {0: ["authorization"], 1: "abc"},
    )
    assert [(item["componentIndex"], item["documentName"]) for item in attachments] == [
        (13, "Giấy ủy quyền"), (24, "la.pdf"), (24, "trong.pdf")]
    assert len(warnings) == 2
    assert [item["source"] for item in classified] == ["llm", "llm", "unknown"]


def test_file_gop_dinh_nguyen_mot_lan_vao_dong_don():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["ho-so.pdf"]), None, {0: ["gcn", "identity", "don_de_nghi", "xac_nhan_ho_ngheo"]},
    )
    assert [(item["componentIndex"], item["documentName"]) for item in attachments] == [(13, "ho-so.pdf")]
    assert len(warnings) == 1 and "dòng 13" in warnings[0] and "không tách sang dòng 7, 24" in warnings[0]


def test_moi_loai_giay_rieng_vao_dung_dong():
    expected = {
        "to_khai_le_phi_truoc_ba": 1, "to_khai_thue_phi_nong_nghiep": 2, "giay_to_nguoi_co_cong": 3,
        "quyet_dinh_mien_giam": 4, "giay_chung_nhan_dau_tu": 5, "xac_nhan_cu_tru": 6, "xac_nhan_ho_ngheo": 7,
        "quyet_dinh_giao_dat": 8, "van_ban_thuc_hien_du_an": 9, "van_ban_de_nghi_mgth": 10,
        "quyet_dinh_tai_dinh_cu": 11, "phe_duyet_du_an_dau_tu": 14, "nang_luc_tai_chinh": 15,
        "dau_gia_khong_thanh": 16, "thu_hoi_dieu_133": 17, "phuong_an_to_chuc_kinh_te": 18,
        "phuong_an_cong_ty_nong_lam": 19, "phuong_an_dat_thu_hoi": 20, "du_an_lan_bien": 21,
        "chuyen_nhuong_du_an_bds": 22, "giay_to_mien_giam": 23, "bao_cao_hien_trang_rung": 25,
        "dau_gia_thue_rung": 26,
    }
    types = list(expected)
    attachments, warnings, _classified = planner.build_plan_items(
        _files([f"{i}.pdf" for i in range(len(types))]), None, {i: [t] for i, t in enumerate(types)},
    )
    assert [item["componentIndex"] for item in attachments] == list(expected.values())
    assert warnings == []


def test_ten_dong_chi_khop_dung_dong_cua_no_tren_fe():
    for row, name in planner._ROWS.items():
        assert _fe_find_row(name, row) == row, row
        # Kể cả khi FE bỏ qua STT và chỉ dò tên: không dòng nào khác khớp tên này.
        assert [stt for stt, text in enumerate(_ROWS, start=1) if _fe_matches(text, name)] == [row], row
    assert len(planner._ROWS) == 26


def test_do_dong_that_tren_trang_khi_co_attachment_context():
    """Trường hợp khác của cổng có thể ẩn bớt dòng / đổi thứ tự → gửi STT + tên nguyên văn của dòng thật."""
    rows = [(1, _ROWS[12]), (2, _ROWS[0]), (3, _ROWS[23])]  # chỉ còn Đơn, tờ khai trước bạ, giấy tờ khác
    options = {"attachmentContext": {"components": [{"index": i, "componentName": n} for i, n in rows]}}
    page = planner.portal_rows(options)
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["don.pdf", "gcn.pdf", "ho-ngheo.pdf"]), None,
        {0: ["don_de_nghi"], 1: ["gcn"], 2: ["xac_nhan_ho_ngheo"]}, page,
    )
    assert [(item["componentIndex"], item["componentName"]) for item in attachments] == [
        (1, _ROWS[12]), (3, _ROWS[23]), (3, _ROWS[23])]
    assert len(warnings) == 1 and "hộ nghèo" in warnings[0]
    # Mọi dòng của bảng đầy đủ tự dò ra chính nó.
    full = [(stt, name, fold(name)) for stt, name in planner._ROWS.items()]
    assert all(planner.resolve_row(stt, full)[:2] == (stt, name) for stt, name in planner._ROWS.items())


def test_prompt_dinh_kem_liet_ke_du_loai():
    for doc_type in list(planner._ROUTES) + ["other"]:
        assert doc_type in SYSTEM_PROMPT and doc_type in TACH_PROMPT, doc_type
    assert '"docTypes"' in SYSTEM_PROMPT and '"trangDau"' in TACH_PROMPT


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — TÁCH
# --------------------------------------------------------------------------------------
_PAGE = "Nội dung trang đủ dài để không bị coi là trang trắng của bản scan hồ sơ giao đất, chuyển mục đích. " * 2


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
    """PDF gộp: Đơn (2 trang, trang 2 trắng) + CCCD hai mặt + Giấy chứng nhận 2 trang + mảnh trích đo 2 trang."""
    pages = [_PAGE, "", _PAGE, _PAGE, _PAGE, _PAGE, _PAGE, _PAGE]
    documents = {0: [(0, "don_de_nghi", "Đơn đề nghị cho phép chuyển mục đích sử dụng đất"),
                     (2, "identity", "Căn cước công dân"),
                     (4, "gcn", "Giấy chứng nhận quyền sử dụng đất"),
                     (6, "trich_do", "Mảnh trích đo địa chính")]}
    attachments, warnings, segments = tach.build_plan_items(_files(["ho-so.pdf"]), {0: pages}, documents)

    assert [(item["componentIndex"], item["sourceSegments"][0]["pageIndexes"]) for item in attachments] == [
        (13, [0]), (13, [2, 3]), (24, [4, 5]), (24, [6, 7])]
    covered = sorted(p for item in attachments for p in item["sourceSegments"][0]["pageIndexes"])
    assert covered == [p for p in range(len(pages)) if pages[p]]  # chỉ bỏ trang trắng
    assert warnings == [] and segments[1]["pages"] == [3, 4]


def test_tach_tep_mot_giay_khong_cat_va_tep_khong_cat_duoc_dinh_nguyen():
    attachments, warnings, _segments = tach.build_plan_items(
        _files(["don.pdf", "gop.jpg"]), {0: [_PAGE, _PAGE], 1: ["trích đoạn"]},
        {0: [(0, "don_de_nghi", "")], 1: [(0, "gcn", ""), (0, "don_de_nghi", ""), (0, "identity", "")]},
    )
    assert [(item["componentIndex"], item["documentName"], "sourceSegments" in item) for item in attachments] == [
        (13, "Đơn đề nghị giao đất, cho thuê đất, chuyển mục đích sử dụng đất (Mẫu số 01)", False),
        (13, "gop.jpg", False)]
    assert len(warnings) == 1 and "dòng 24" in warnings[0]


def test_tach_cat_dung_trang_pdf_that(monkeypatch):
    from app.services import ocr

    text = "\n".join(f"───── Trang {n}/3 ─────\n{_PAGE}" for n in range(1, 4))

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": text} for item in files]

    async def fake_chat(messages, **kwargs):
        return ('{"tep":[{"fileIndex":0,"giayTo":[{"trangDau":1,"docType":"don_de_nghi","ten":"Đơn"},'
                '{"trangDau":2,"docType":"gcn","ten":"Giấy chứng nhận"}]}]}')

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl=_pdf_data_url(3))]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [(item["componentIndex"], item["sourceSegments"]) for item in result["attachments"]] == [
        (13, [{"fileIndex": 0, "pageIndexes": [0]}]), (24, [{"fileIndex": 0, "pageIndexes": [1, 2]}])]


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    from app.services import ocr

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def broken_segment(units):
        raise ValueError("JSON hỏng")

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["gcn","don_de_nghi"]}]}'

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(tach, "_segment", broken_segment)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl="x")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [item["componentIndex"] for item in result["attachments"]] == [13]
    assert "sourceSegments" not in result["attachments"][0]
    assert result["errors"][0].startswith("Tách giấy tờ: JSON hỏng")


def test_tat_tach_dinh_nguyen_tep(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["don_de_nghi","gcn"]},{"index":1,"docTypes":["trich_do"]}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=n, type="application/pdf", dataUrl="x") for n in ("ho-so.pdf", "trich-do.pdf")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": False}))

    assert [(item["componentIndex"], "sourceSegments" in item) for item in result["attachments"]] == [
        (13, False), (24, False)]


# --------------------------------------------------------------------------------------
# REGISTRY + TRỢ LÝ
# --------------------------------------------------------------------------------------
def test_registry_va_link_ke_khai_cung_key():
    procedure = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert link["code"] == "1.116366"
    assert procedure["mode"] == "agent" and procedure["hasAttachmentStep"] is True
    assert procedure["supportsSplitDocuments"] is True
    assert procedure["detect"]["urlScope"] == ["lamdong.gov.vn"]
    assert "1.116366" in procedure["detect"]["textIncludes"]
    # Cụm nhận diện có trong cả tên quốc gia (ke_khai_links) lẫn tên cổng tỉnh (đuôi "…lấn biển").
    phrase = procedure["detect"]["textIncludes"][0]
    assert phrase in link["label"].lower()
    assert phrase in ("giao đất và giao rừng; cho thuê đất và cho thuê rừng; giao đất, cho thuê đất đồng thời giao khu "
                      "vực biển để thực hiện hoạt động lấn biển")
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
    assert proc["keKhaiUrl"] == link["url"] and handfree.procedure_code(proc) == "1.116366"
    assert proc["provinceOnly"] == ["lamdong"] and proc["bxdFlow"]["capability"] == "supportsBxdFlowLamDong"
    assert proc["supportsSplitDocuments"] is True
    assert handfree.is_allowed_in_province(proc, "lamdong") and not handfree.is_allowed_in_province(proc, "khanhhoa")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert PROCEDURE_HMONG[_KEY]
    assert field_review.get(_KEY) is not None
