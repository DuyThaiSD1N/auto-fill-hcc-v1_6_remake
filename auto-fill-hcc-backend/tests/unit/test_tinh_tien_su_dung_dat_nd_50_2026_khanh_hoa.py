"""Test "Khánh Hòa - Thủ tục tính hoặc tính lại tiền sử dụng đất theo quy định tại các điểm a, b, c và d khoản 2 Điều 12
Nghị định số 50/2026/NĐ-CP" (1.115148, cổng iGate dichvucong.khanhhoa.gov.vn).

Khoá:
1. LINK + PHẠM VI: link kê khai mang tiền tố "Khánh Hòa - ", chỉ tài khoản Khánh Hòa thấy (Auto Fill + trợ lý).
2. ĐIỀN theo file "Mapping_HoSo_NopTrucTuyen": chủ hồ sơ owner* (địa chỉ một ô chữ), ô "Người nộp hồ sơ đồng thời là chủ
   hồ sơ" (tự nộp tick, có giấy người nộp thay bỏ tick), khối người nộp (data[district] = Phường/xã), nội dung yêu cầu ghép
   tất định; ô giấy tờ không có thì trả về trống (cổng đổ sẵn theo tài khoản).
3. ĐÍNH KÈM: bảng một dòng "Văn bản đề nghị tính hoặc tính lại tiền sử dụng đất" — tách đúng dòng + không sót trang,
   tắt tách đính nguyên tệp, tách lỗi quay về không tách.
Dữ liệu người trong test là BỊA. Không gọi LLM / OCR thật.
"""

import asyncio
import base64
from types import SimpleNamespace

import fitz
import pytest

from app.pipelines._shared import fold
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa import attach
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa.attach import planner as dispatcher
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa.attach.dinh_kem_khong_tach import planner
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa.attach.dinh_kem_khong_tach.prompt import SYSTEM_PROMPT
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa.attach.dinh_kem_tach import planner as tach
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT as TACH_PROMPT,
)
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa.process import mapper
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa.process.prompt import EXTRA_RULES
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_khanh_hoa.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures import router as procedures_router
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "tinh-tien-su-dung-dat-nd-50-2026-khanh-hoa"
_ROW_NAME = "Văn bản đề nghị tính hoặc tính lại tiền sử dụng đất"


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _don_facts() -> list[dict]:
    """Chỉ những gì Đơn đề nghị cấp GPXD (bộ mẫu của file mapping) có: tên, số định danh + SĐT viết tay, địa điểm XD."""
    return [
        {"name": "ChuHoSo_HoTen", "value": "Phạm Thị Hoa"},
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


_REQUEST = ("Tính hoặc tính lại tiền sử dụng đất tại TĐ 45 TBĐ 7 diện tích 250,5 m² địa chỉ Thôn Thử Nghiệm, Xã Đơn "
            "Dương, Tỉnh Lâm Đồng - PHẠM THỊ HOA")


# --------------------------------------------------------------------------------------
# LINK + PHẠM VI TỈNH
# --------------------------------------------------------------------------------------
def test_registry_va_link_ke_khai_cung_key_tien_to_khanh_hoa():
    procedure = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert link["code"] == "1.115148" and link["label"].startswith("Khánh Hòa - ")
    assert "provinceOnlyAgency" not in link and "selectSo" not in link  # UBND phường/xã: DVCQG chọn Tỉnh + Xã
    # Link chung không tiền tố đã đổi thành bản Khánh Hòa.
    assert not any(item["key"] == "tinh-tien-su-dung-dat-nd-50-2026" for item in KE_KHAI_LINKS)
    assert procedure["mode"] == "agent" and procedure["hasAttachmentStep"] is True
    assert procedure["supportsSplitDocuments"] is True
    assert procedure["detect"]["urlScope"] == ["khanhhoa.gov.vn"]
    # Cùng mã 1.115148 với bản tỉnh khác: cùng cụm chữ nhận diện, chỉ khác urlScope theo tỉnh.
    for other in ("tinh-tien-su-dung-dat-nd-50-2026-quang-ninh", "tinh-tien-su-dung-dat-nd-50-2026-quang-ngai",
                  "tinh-tien-su-dung-dat-nd-50-2026-lam-dong"):
        assert not set(get_procedure(other)["detect"]["urlScope"]) & set(procedure["detect"]["urlScope"]), other
    assert all(fold(phrase) in fold(link["label"]) for phrase in procedure["detect"]["textIncludes"])
    assert get_pipeline(_KEY) is not None and get_attach_pipeline(_KEY) is attach.plan


@pytest.mark.parametrize("tinh, visible", [("Tỉnh Khánh Hòa", True), ("Tỉnh Lâm Đồng", False),
                                           ("Thành phố Hà Nội", False)])
def test_link_chi_tai_khoan_khanh_hoa_thay(tinh, visible):
    user = {"role": "commune", "tinh": tinh, "xa": ""}
    links = {link["key"]: link for link in asyncio.run(procedures_router.ke_khai_links(user))["links"]}
    if visible:
        assert links[_KEY]["provinceOnly"] == ["khanhhoa"]
    else:
        assert _KEY not in links


def test_tro_ly_mo_rieng_khanh_hoa_cung_key_voi_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    proc = handfree.get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Khánh Hòa - " + proc["label"] == get_procedure(_KEY)["label"]
    assert proc["detect"]["urlScope"] == get_procedure(_KEY)["detect"]["urlScope"]
    assert proc["detect"]["textIncludes"] == get_procedure(_KEY)["detect"]["textIncludes"]
    assert proc["keKhaiUrl"] == link["url"] and handfree.procedure_code(proc) == "1.115148"
    assert proc["provinceOnly"] == ["khanhhoa"] and proc["bxdFlow"]["capability"] == "supportsBxdFlowKhanhHoa"
    assert proc["supportsSplitDocuments"] is True
    assert handfree.is_allowed_in_province(proc, "khanhhoa") and not handfree.is_allowed_in_province(proc, "lamdong")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert PROCEDURE_HMONG[_KEY]
    assert field_review.get(_KEY) is not None and "district" not in field_review.get(_KEY)["noAsk"]


# --------------------------------------------------------------------------------------
# ĐIỀN
# --------------------------------------------------------------------------------------
def test_tu_nop_tick_chu_ho_so_va_dien_nguoi_nop_bang_chu_ho_so():
    out, warnings = mapper.enrich(_don_facts() + _cccd_facts())
    values = _values(out)

    assert values["data[ownerFullname]"] == "Phạm Thị Hoa"
    assert values["data[ownerIdentityNumber]"] == "068185000123"
    assert values["data[ownerBirthday]"] == "15/08/1985"
    assert values["data[ownerPhoneNumber]"] == "0900000123"
    assert values["data[ownerAddress]"] == "Thôn Thử Nghiệm, Xã Đơn Dương, Tỉnh Lâm Đồng"
    assert values["data[isOwnerDossier]"] is True
    assert values["data[fullname]"] == "Phạm Thị Hoa"
    assert values["data[birthday]"] == "15/08/1985"
    assert values["data[gender]"] == "Nữ"
    assert values["data[phoneNumber]"] == "0900000123"
    assert values["data[identityNumber]"] == "068185000123"
    assert values["data[identityDate]"] == "20/08/2025"
    assert values["data[identityAgency]"] == "Bộ Công an"
    assert values["data[nation]"] == "Việt Nam"
    assert values["data[province]"] == "Tỉnh Lâm Đồng"
    assert values["data[district]"] == "Xã Đơn Dương"
    assert values["data[address]"] == "Thôn Thử Nghiệm"
    assert values["data[chonDoiTuong]"] == "Cá nhân"
    assert values["data[noidungyeucaugiaiquyet]"] == _REQUEST
    # Không email trong giấy → ô trả về trống (cổng có thể đổ email tài khoản).
    assert [(i["name"], i.get("clear"), i.get("markEmpty")) for i in out if i["value"] == ""] == [
        ("data[email]", True, None)]
    assert set(values) <= set(UI_COMP_BY_NAME)
    assert warnings == []


def test_chi_co_don_gpxd_dia_chi_tam_theo_dia_diem_xay_dung_va_tra_trong_o_thieu():
    """Bộ mẫu của file mapping: chỉ có Đơn GPXD — không ngày sinh, ngày cấp; cổng đổ sẵn ngày sinh tài khoản."""
    options = {"formContext": {"applicantFullname": "LÊ VĂN AN", "applicantIdentityNumber": "001203000456"}}
    out, warnings = mapper.enrich(_don_facts(), options)
    values = _values(out)
    blanks = {item["name"]: item for item in out if item["value"] == ""}

    assert values["data[fullname]"] == "Phạm Thị Hoa" and values["data[isOwnerDossier]"] is True
    assert values["data[gender]"] == "Nữ"  # chữ số thứ 4 của số định danh = 1 → nữ
    assert values["data[ownerAddress]"] == "Thôn Thử Nghiệm, Xã Đơn Dương, Tỉnh Lâm Đồng"
    assert values["data[district]"] == "Xã Đơn Dương" and values["data[address]"] == "Thôn Thử Nghiệm"
    assert "data[identityAgency]" not in values
    assert {"data[birthday]", "data[ownerBirthday]", "data[identityDate]", "data[email]"} == set(blanks)
    assert all(item["clear"] for item in blanks.values())
    assert blanks["data[birthday]"]["markEmpty"] and blanks["data[ownerBirthday]"]["markEmpty"]
    assert any("địa điểm xây dựng" in w for w in warnings)
    assert any("Ngày sinh chủ hồ sơ" in w and "Ngày sinh người nộp" in w for w in warnings)


def test_tai_khoan_la_nguoi_nop_giu_khoi_nguoi_nop_cua_cong():
    options = {"formContext": {"applicantIdentityNumber": "068185000123"}}
    out, _warnings = mapper.enrich(_don_facts(), options)
    blanks = {item["name"] for item in out if item["value"] == ""}
    assert blanks == {"data[ownerBirthday]"}


def test_cccd_nguoi_khac_la_nguoi_nop_thay_bo_tick_dien_ca_hai_khoi():
    fields = _don_facts() + _cccd_facts() + [{"name": "NguoiNopThay", "value": {
        "hoTen": "LÊ VĂN AN", "soDinhDanh": "001203000456", "ngaySinh": "03/12/2003", "ngayCapCccd": "01/07/2024",
        "thuongTru": {"tinh": "Khánh Hòa", "xa": "Phường Cam Ranh", "diaChi": "Tổ dân phố Thử"},
    }}]
    out, _warnings = mapper.enrich(fields)
    values = _values(out)

    assert values["data[isOwnerDossier]"] is False
    assert values["data[fullname]"] == "LÊ VĂN AN"
    assert values["data[gender]"] == "Nam"  # chữ số thứ 4 là 2 → nam sinh thế kỷ 21
    assert values["data[identityAgency]"] == "Bộ Công an"  # thẻ cấp từ 01/7/2024
    assert values["data[province]"] == "Tỉnh Khánh Hòa" and values["data[district]"] == "Phường Cam Ranh"
    assert values["data[ownerFullname]"] == "Phạm Thị Hoa"
    assert values["data[ownerAddress]"] == "Thôn Thử Nghiệm, Xã Đơn Dương, Tỉnh Lâm Đồng"
    # SĐT trong Đơn là của chủ hồ sơ — không mượn sang người nộp thay; ô trống tô đỏ.
    assert values["data[ownerPhoneNumber]"] == "0900000123" and values["data[phoneNumber]"] == ""
    assert next(i for i in out if i["name"] == "data[phoneNumber]")["markEmpty"] is True
    assert values["data[noidungyeucaugiaiquyet]"] == _REQUEST


def test_lay_nguoi_nop_theo_to_khai_bo_nguoi_nop_thay():
    fields = _don_facts() + [{"name": "NguoiNopThay", "value": {"hoTen": "LÊ VĂN AN", "soDinhDanh": "001203000456"}}]
    values = _values(mapper.enrich(fields, {"submitterMode": "owner_as_submitter"})[0])
    assert values["data[isOwnerDossier]"] is True and values["data[fullname]"] == "Phạm Thị Hoa"


def test_nguoi_nop_thay_trung_chu_ho_so_van_la_tu_nop():
    fields = _don_facts() + [{"name": "NguoiNopThay", "value": {"hoTen": "PHẠM THỊ HOA", "soDinhDanh": "068185000123"}}]
    values = _values(mapper.enrich(fields)[0])
    assert values["data[isOwnerDossier]"] is True and values["data[fullname]"] == "Phạm Thị Hoa"


def test_thieu_nguoi_va_thua_dat_thi_canh_bao_va_noi_dung_mac_dinh():
    out, warnings = mapper.enrich([])
    values = _values(out)
    assert values["data[noidungyeucaugiaiquyet]"] == "Tính hoặc tính lại tiền sử dụng đất"
    assert values["data[isOwnerDossier]"] is True
    assert any("Thiếu họ tên" in w for w in warnings) and any("thửa đất" in w for w in warnings)


def test_to_chuc_canh_bao_chon_to_chuc():
    fields = _don_facts() + [{"name": "ToChuc_Ten", "value": "Công ty TNHH Thử Nghiệm"}]
    warnings = mapper.enrich(fields)[1]
    assert any("tổ chức" in w and "Công ty TNHH Thử Nghiệm" in w for w in warnings)


def test_prompt_dien_dung_lai_ban_lam_dong_doi_ten_cong():
    from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.process.prompt import EXTRA_RULES as LAM_DONG

    assert "(cổng DVC Lâm Đồng)" in LAM_DONG
    assert "Lâm Đồng" not in EXTRA_RULES and "cổng DVC Khánh Hòa" in EXTRA_RULES
    assert "ĐƠN ĐỀ NGHỊ CẤP GIẤY PHÉP XÂY DỰNG" in EXTRA_RULES and "NguoiNopThay" in EXTRA_RULES
    assert {"NguoiNopThay", "ChuHoSo_HoTen", "ThuaDat_DiaChi", "ThuaDat_SoThua", "ThuaDat_DienTich"} <= ALLOWED


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — KHÔNG TÁCH
# --------------------------------------------------------------------------------------
def test_moi_tep_dinh_mot_lan_vao_dong_duy_nhat():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["don.pdf", "cccd.pdf", "gcn.pdf", "la.pdf"]), None,
        {0: ["van_ban_de_nghi"], 1: ["identity"], 2: ["gcn"], 3: "abc"},
    )
    assert [(item["fileIndex"], item["componentIndex"], item["componentName"]) for item in attachments] == [
        (i, 1, _ROW_NAME) for i in range(4)]
    assert all(item["target"] == "attp-row" and "loaiBan" not in item for item in attachments)
    assert len(warnings) == 1 and "la.pdf" in warnings[0]


def test_chi_co_don_gpxd_thi_canh_bao_thieu_van_ban_de_nghi():
    _attachments, warnings, _classified = planner.build_plan_items(
        _files(["don-gpxd.pdf", "cccd.pdf"]), None, {0: ["don_gpxd"], 1: ["identity"]})
    assert len(warnings) == 1 and "giấy phép xây dựng" in warnings[0] and _ROW_NAME in warnings[0]


def test_prompt_dinh_kem_ghi_cong_khanh_hoa_du_loai():
    for doc_type in list(planner._NAMES) + ["other"]:
        assert doc_type in SYSTEM_PROMPT and doc_type in TACH_PROMPT, doc_type
    assert "Khánh Hòa" in SYSTEM_PROMPT and "Lâm Đồng" not in SYSTEM_PROMPT
    assert "Khánh Hòa" in TACH_PROMPT and "Lâm Đồng" not in TACH_PROMPT


def test_tat_tach_dinh_nguyen_tep(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        assert "Khánh Hòa" in messages[0]["content"]
        return '{"documents":[{"index":0,"docTypes":["van_ban_de_nghi","gcn"]},{"index":1,"docTypes":["identity"]}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=n, type="application/pdf", dataUrl="x") for n in ("ho-so.pdf", "cccd.pdf")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": False}))

    assert [(item["componentIndex"], item["componentName"], "sourceSegments" in item)
            for item in result["attachments"]] == [(1, _ROW_NAME, False), (1, _ROW_NAME, False)]


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


def test_tach_ho_so_gop_dung_dong_khong_sot_trang(monkeypatch):
    """PDF gộp 5 trang: Đơn GPXD (trang 1) + CCCD hai mặt (2-3) + Giấy chứng nhận (4-5) → 3 mục, phủ đủ 5 trang."""
    from app.services import ocr

    text = "\n".join(f"───── Trang {n}/5 ─────\n{_PAGE}" for n in range(1, 6))

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": text} for item in files]

    async def fake_chat(messages, **kwargs):
        assert "Khánh Hòa" in messages[0]["content"]
        return ('{"tep":[{"fileIndex":0,"giayTo":[{"trangDau":1,"docType":"don_gpxd","ten":""},'
                '{"trangDau":2,"docType":"identity","ten":"Căn cước công dân"},'
                '{"trangDau":4,"docType":"gcn","ten":""}]}]}')

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl=_pdf_data_url(5))]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    items = result["attachments"]
    assert [(item["componentIndex"], item["componentName"], item["sourceSegments"]) for item in items] == [
        (1, _ROW_NAME, [{"fileIndex": 0, "pageIndexes": [0]}]),
        (1, _ROW_NAME, [{"fileIndex": 0, "pageIndexes": [1, 2]}]),
        (1, _ROW_NAME, [{"fileIndex": 0, "pageIndexes": [3, 4]}]),
    ]
    assert [item["documentName"] for item in items] == [
        "Đơn đề nghị cấp giấy phép xây dựng", "Căn cước công dân", "Giấy chứng nhận quyền sử dụng đất"]
    covered = sorted(p for item in items for p in item["sourceSegments"][0]["pageIndexes"])
    assert covered == list(range(5))
    # Chỉ cảnh báo thiếu Văn bản đề nghị (bộ chỉ có Đơn GPXD).
    assert len(result["errors"]) == 1 and _ROW_NAME in result["errors"][0]


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
