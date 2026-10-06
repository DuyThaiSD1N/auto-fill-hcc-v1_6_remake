"""Unit test "Đăng ký, cấp GCN cho người nhận chuyển nhượng trong dự án BĐS" — cổng DVC Đà Nẵng (1.012787).

Kiểm: registry khớp ke_khai_links + tách detect với bản Lào Cai, mapper hai vai theo file mapping (giữ nguyên
nội dung yêu cầu, SĐT quốc tế, chặn nhầm chủ đầu tư), planner mỗi dòng MỘT tệp + đính lại dòng 8/11 + khớp
dòng theo đúng cách FE attp-row gom và tìm dòng. Dữ liệu đều là ví dụ bịa."""

import re
import unicodedata

import pytest

from app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.attach import planner as P
from app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.process.mapper import enrich
from app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.process.schema import (
    ALLOWED,
    UI_COMP_BY_NAME,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san"
_LAO_CAI = "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai"


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


# --------------------------------------------------------------------------------------
# REGISTRY + DETECT
# --------------------------------------------------------------------------------------
def test_registry_khop_ke_khai_links():
    procedure = get_procedure(_KEY)
    assert procedure and procedure["hasAttachmentStep"] is True
    assert procedure["detect"]["urlScope"] == ["dichvucong.danang.gov.vn"]
    assert procedure["detect"]["textPriority"] is True
    assert get_pipeline(_KEY).__module__.startswith(
        "app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.")
    assert get_attach_pipeline(_KEY).__module__.startswith(
        "app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.")
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.012787"


def test_key_cu_khong_con_trong_registry():
    assert get_procedure("dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bds-da-nang") is None
    assert sum(1 for p in PROCEDURES if p["key"] == _KEY) == 1


def _popup_priority_pick(body: str, url: str) -> str:
    """Mô phỏng nhánh textPriority của popup.js: đúng host, đủ cụm, tổng độ dài cụm dài nhất thắng."""
    best, best_score = "", 0
    for p in PROCEDURES:
        detect = p.get("detect") or {}
        if not detect.get("textPriority"):
            continue
        scope = detect.get("urlScope") or []
        if scope and not any(s.lower() in url for s in scope):
            continue
        phrases = [_fold(x) for x in detect.get("textIncludes") or [] if x]
        if not phrases or not all(ph in body for ph in phrases):
            continue
        score = sum(len(ph) for ph in phrases)
        if score > best_score:
            best, best_score = p["key"], score
    return best


def test_trang_da_nang_nhan_dung_thu_tuc_khong_lan_ban_lao_cai():
    body = _fold(
        "Đăng ký, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất cho người nhận "
        "chuyển nhượng quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng trong dự án bất động sản "
        "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18"
    )
    assert _popup_priority_pick(body, "https://dichvucong.danang.gov.vn/vi/padsvc/apply-online/abc") == _KEY
    assert "dichvucong.danang.gov.vn" not in (get_procedure(_LAO_CAI)["detect"].get("urlScope") or [])


def test_schema_ui_key_theo_file_mapping():
    for key in ("data[ownerFullname]", "data[isOwnerDossier]", "data[organization]", "data[fullname]",
                "data[birthday]", "data[gender]", "data[email]", "data[phoneNumber]", "data[identityNumber]",
                "data[identityDate]", "data[identityAgency]", "data[taxCode]", "data[chonDoiTuong]",
                "data[province]", "data[district]", "data[address]"):
        assert key in UI_COMP_BY_NAME
    # STT 13 "Nội dung yêu cầu giải quyết": cổng điền sẵn, mapping yêu cầu giữ nguyên.
    assert "data[noidungyeucaugiaiquyet]" not in UI_COMP_BY_NAME
    assert not any(name.startswith("data[") for name in ALLOWED)


# --------------------------------------------------------------------------------------
# MAPPER
# --------------------------------------------------------------------------------------
def _map(vals: dict) -> tuple[dict, list[str]]:
    fields, warnings = enrich([{"name": k, "value": v} for k, v in vals.items()], {})
    return {f["name"]: f["value"] for f in fields}, warnings


_TU_NOP = {
    "ChuHoSo_LoaiChuThe": "Cá nhân",
    "ChuHoSo_HoTen": "TRẦN VĂN BÌNH",
    "ChuHoSo_SoDinhDanh": "001080001234",
    "ChuHoSo_DiaChi": {"tinh": "Thành phố Hà Nội", "xa": "Phường Ba Đình", "diaChi": "Số 12 ngõ 3 phố Mẫu"},
    "ChuHoSo_DienThoai": "00420 111 222 333",
    "ChuHoSo_Email": "Email: binhtran.mau@example.com",
    "ChuDauTu_Ten": "CÔNG TY CỔ PHẦN ĐẦU TƯ BẤT ĐỘNG SẢN MẪU",
    "NguoiNop_HoTen": "TRẦN VĂN BÌNH",
    "NguoiNop_SoDinhDanh": "001080001234",
    "NguoiNop_NgaySinh": "05/06/1980",
    "NguoiNop_NgayCap": "10/03/2022",
    "NguoiNop_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
}


def test_tu_nop_dien_du_theo_mapping():
    out, warnings = _map(_TU_NOP)
    assert out["data[ownerFullname]"] == "TRẦN VĂN BÌNH"
    assert out["data[isOwnerDossier]"] is True
    assert out["data[fullname]"] == "TRẦN VĂN BÌNH"
    assert out["data[chonDoiTuong]"] == "Cá nhân"
    assert out["data[birthday]"] == "05/06/1980"
    assert out["data[gender]"] == "Nam"  # chữ số thứ 4 của số định danh là 0
    assert out["data[identityNumber]"] == "001080001234"
    assert out["data[identityDate]"] == "10/03/2022"
    assert out["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert out["data[phoneNumber]"] == "00420111222333"  # số quốc tế: nhập liền
    assert out["data[email]"] == "binhtran.mau@example.com"
    assert out["data[province]"] == "Thành phố Hà Nội"
    assert out["data[district]"] == "Phường Ba Đình"
    assert out["data[address]"] == "Số 12 ngõ 3 phố Mẫu"
    assert "data[noidungyeucaugiaiquyet]" not in out
    assert "data[organization]" not in out and "data[taxCode]" not in out
    assert warnings == []


def test_ngay_cap_ghi_dao_tren_to_khai_thue_bi_bo():
    out, _ = _map({**_TU_NOP, "NguoiNop_NgayCap": "001080001234"})
    assert "data[identityDate]" not in out


def test_thieu_ngay_sinh_canh_bao_va_gioi_tinh_nu_tu_so_dinh_danh():
    vals = {**_TU_NOP, "ChuHoSo_HoTen": "LÊ THỊ HOA", "NguoiNop_HoTen": "LÊ THỊ HOA",
            "NguoiNop_SoDinhDanh": "001190004321", "NguoiNop_NgaySinh": "1990"}
    out, warnings = _map(vals)
    assert out["data[gender]"] == "Nữ"
    assert "data[birthday]" not in out
    assert any("Ngày sinh" in w for w in warnings)


def test_tu_nop_thieu_cccd_nguoi_nop_lay_so_dinh_danh_chu_ho_so():
    vals = {k: v for k, v in _TU_NOP.items() if k != "NguoiNop_SoDinhDanh"}
    out, _ = _map(vals)
    assert out["data[identityNumber]"] == "001080001234"


def test_chu_ho_so_trung_chu_dau_tu_bi_bo():
    vals = {**_TU_NOP, "ChuHoSo_LoaiChuThe": "Tổ chức",
            "ChuHoSo_HoTen": "Công ty Cổ phần Đầu tư Bất động sản Mẫu", "ChuHoSo_SoDinhDanh": "0400000001"}
    out, warnings = _map(vals)
    assert "data[ownerFullname]" not in out and "data[organization]" not in out
    assert "data[taxCode]" not in out and "data[email]" not in out
    assert any("chủ đầu tư" in w for w in warnings)


def test_uy_quyen_bo_tich_dien_nguoi_duoc_uy_quyen():
    vals = {**_TU_NOP, "NguoiNop_HoTen": "PHẠM VĂN CƯỜNG", "NguoiNop_SoDinhDanh": "048085005678",
            "NguoiNop_NgaySinh": "01/01/1985", "NguoiNop_NgayCap": "02/02/2021"}
    out, _ = _map(vals)
    assert out["data[isOwnerDossier]"] is False
    assert out["data[ownerFullname]"] == "TRẦN VĂN BÌNH"
    assert out["data[fullname]"] == "PHẠM VĂN CƯỜNG"
    assert out["data[identityNumber]"] == "048085005678"
    assert out["data[birthday]"] == "01/01/1985"


def test_so_dien_thoai_cac_dang():
    for raw, want in (("0905 123 456", "0905123456"), ("+84 905 123 456", "0905123456"),
                      ("+420 111 222 333", "00420111222333"), ("18006636 (1)", None)):
        out, _ = _map({**_TU_NOP, "ChuHoSo_DienThoai": raw})
        assert out.get("data[phoneNumber]") == want, raw


def test_dia_chi_dang_chuoi_bo_viet_nam():
    out, _ = _map({**_TU_NOP, "ChuHoSo_DiaChi": "Tổ dân phố 5, Phường Mẫu Sơn, Thành phố Hà Nội, Việt Nam"})
    assert out["data[province]"] == "Thành phố Hà Nội"
    assert out["data[district]"] == "Phường Mẫu Sơn"
    assert out["data[address]"] == "Tổ dân phố 5"


# --------------------------------------------------------------------------------------
# PLANNER
# --------------------------------------------------------------------------------------
def _seg(fi, a, b, t, name=""):
    return {"fileIndex": fi, "pageFrom": a, "pageTo": b, "type": t, "documentName": name}


def _plan(segments, page_counts, page_texts=None):
    raw_files = [{"name": f"file{i}.pdf", "type": "application/pdf"} for i in range(len(page_counts))]
    meta = {i: {"pageCount": n, "pageBoundariesAvailable": True} for i, n in enumerate(page_counts)}
    return P.build_attachments(segments, raw_files, meta, page_texts or {}, {})


def _bo_ho_so_mau():
    """6 file như bộ hồ sơ mẫu: Đơn (2 bản xen trang trắng), HĐMB, VB sửa đổi, BBBG, GCN, tệp chứng từ."""
    segments = [
        _seg(0, 1, 1, "don_mau_18"), _seg(0, 2, 2, "trang_trang"), _seg(0, 3, 3, "don_mau_18"),
        _seg(0, 4, 4, "trang_trang"),
        _seg(1, 1, 52, "hop_dong_chuyen_nhuong", "Hợp đồng mua bán nhà ở riêng lẻ"),
        _seg(2, 1, 5, "hop_dong_chuyen_nhuong"), _seg(2, 6, 6, "trang_trang"),
        _seg(2, 7, 14, "hop_dong_chuyen_nhuong"),
        _seg(3, 1, 5, "bien_ban_ban_giao"), _seg(3, 6, 6, "trang_trang"), _seg(3, 7, 10, "bien_ban_ban_giao"),
        _seg(4, 1, 2, "gcn_chu_dau_tu", "Giấy chứng nhận quyền sử dụng đất"),
        _seg(5, 1, 1, "giay_to_nhan_than"), _seg(5, 2, 2, "trang_trang"), _seg(5, 3, 5, "giay_to_nhan_than"),
        _seg(5, 6, 26, "chung_tu_tai_chinh"), _seg(5, 27, 28, "giay_dkdn"), _seg(5, 29, 34, "chung_tu_tai_chinh"),
    ]
    return _plan(segments, [4, 52, 14, 10, 2, 34])


def test_bo_ho_so_mau_dung_anh_anh_xa():
    attachments, classified, errors = _bo_ho_so_mau()
    by_row = {a["componentIndex"]: a for a in attachments}
    assert sorted(by_row) == [2, 3, 4, 5, 7, 8, 11]  # dòng 1, 6, 9, 10 để trống
    assert len(attachments) == 7  # mỗi dòng đúng MỘT tệp

    assert by_row[2]["fileIndex"] == 0 and "sourceSegments" not in by_row[2]  # nguyên file Đơn (cả trang trắng)
    assert by_row[3]["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": None},
                                           {"fileIndex": 2, "pageIndexes": None}]  # ghép HĐMB + VB sửa đổi
    assert by_row[4]["fileIndex"] == 3 and "sourceSegments" not in by_row[4]
    assert by_row[5]["fileIndex"] == 4 and by_row[5]["loaiBan"] == "Bản sao"
    assert by_row[7]["fileIndex"] == 5 and "sourceSegments" not in by_row[7] and by_row[7]["loaiBan"] == "Bản sao"

    # Dòng 8 / 11 đính LẠI đúng tệp của dòng 4 / 7.
    for src, dup, loai in ((4, 8, "Bản chính"), (7, 11, "Bản sao")):
        assert by_row[dup]["fileIndex"] == by_row[src]["fileIndex"]
        assert by_row[dup].get("sourceSegments") == by_row[src].get("sourceSegments")
        assert by_row[dup]["documentName"] == by_row[src]["documentName"]
        assert by_row[dup]["loaiBan"] == loai
    for row in (2, 3, 4, 8):
        assert by_row[row]["loaiBan"] == "Bản chính"
    assert all(a["target"] == "attp-row" for a in attachments)
    assert errors == []
    assert sum(c["pageTo"] - c["pageFrom"] + 1 for c in classified) == 4 + 52 + 14 + 10 + 2 + 34


def test_component_name_khac_nhau_de_fe_khong_gom_nham_dong():
    attachments, _, _ = _bo_ho_so_mau()
    keys = [_fold(a["componentName"]) for a in attachments]
    assert len(keys) == len(set(keys))


def test_file_gop_mot_pdf_tach_trang_dung_dong():
    segments = [
        _seg(0, 1, 1, "don_mau_18"), _seg(0, 2, 6, "hop_dong_chuyen_nhuong"), _seg(0, 7, 8, "bien_ban_ban_giao"),
        _seg(0, 9, 10, "gcn_chu_dau_tu"), _seg(0, 11, 11, "giay_to_nhan_than"), _seg(0, 12, 12, "trang_trang"),
        _seg(0, 13, 14, "uy_quyen"),
    ]
    attachments, _, errors = _plan(segments, [14])
    by_row = {a["componentIndex"]: a for a in attachments}
    assert by_row[2]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert by_row[3]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1, 2, 3, 4, 5]}]
    assert by_row[5]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [8, 9]}]
    # CCCD + trang trắng + ủy quyền: không có dòng riêng → đính chung dòng 7, KHÔNG mất trang.
    assert by_row[7]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [10, 11, 12, 13]}]
    assert 11 not in by_row  # dòng 7 không có chứng từ tài chính → không đính lại dòng 11
    assert 8 in by_row
    assert any("chứng từ nghĩa vụ tài chính" in e for e in errors)


def test_thieu_giay_to_chinh_canh_bao():
    _, _, errors = _plan([_seg(0, 1, 1, "don_mau_18")], [1])
    assert any("Hợp đồng chuyển nhượng" in e and "Giấy chứng nhận" in e for e in errors)


def test_llm_loi_rule_ocr_theo_tieu_de_dau_trang():
    texts = {
        0: {1: "BIÊN BẢN BÀN GIAO NHÀ Ở số 01/BBBG. Căn cứ Hợp đồng mua bán nhà ở và các văn bản sửa đổi, "
               "bổ sung số 01 đã ký giữa hai bên"},
        1: {1: "VĂN BẢN SỬA ĐỔI, BỔ SUNG SỐ 02 (V.v: Sửa đổi Hợp đồng mua bán nhà ở) căn cứ Biên bản bàn giao"},
        2: {1: "TỜ KHAI LỆ PHÍ TRƯỚC BẠ NHÀ, ĐẤT [01] Người nộp thuế số căn cước công dân 001080001234"},
        3: {1: "  . , "},
    }
    segments = [P._fallback_segment(i, 1, 1) for i in range(4)]
    _, classified, _ = _plan(segments, [1, 1, 1, 1], texts)
    assert [c["type"] for c in classified] == [
        "bien_ban_ban_giao", "hop_dong_chuyen_nhuong", "chung_tu_tai_chinh", "trang_trang"]


def test_nhan_la_cua_llm_khong_do_chuoi_con():
    assert P._normalize_type("chung_tu_tai_chinh") == "chung_tu_tai_chinh"
    assert P._normalize_type("CCCD") == "giay_to_nhan_than"
    assert P._normalize_type("gcn_dang_ky_doanh_nghiep") == "other"


# Tên dòng trên cổng theo file mapping (Phần IV, STT 23–33); dòng 10 rỗng.
_PORTAL_ROWS = [
    "Văn bản về việc nhà ở, công trình xây dựng đã được nghiệm thu đưa vào khai thác, sử dụng theo quy định của "
    "pháp luật về xây dựng đối với trường hợp có nhận chuyển nhượng nhà ở, công trình xây dựng",
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18 (Click chuột vào đây để mở biểu mẫu "
    "giấy tờ)",
    "Hợp đồng chuyển nhượng quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng, hạng mục công trình xây "
    "dựng theo quy định của pháp luật.",
    "Biên bản bàn giao nhà, đất, công trình xây dựng, hạng mục công trình xây dựng",
    "Giấy chứng nhận đã cấp cho chủ đầu tư dự án.",
    "Văn bản về việc đủ điều kiện được chuyển nhượng cho cá nhân tự xây dựng nhà ở đối với trường hợp chuyển "
    "nhượng quyền sử dụng đất đã có hạ tầng kỹ thuật theo quy định của pháp luật về kinh doanh bất động sản",
    "Chứng từ chứng minh việc hoàn thành nghĩa vụ tài chính đối với trường hợp Văn phòng đăng ký đất đai nhận "
    "được văn bản của cơ quan có thẩm quyền về việc dự án được điều chỉnh quy hoạch xây dựng chi tiết mà làm "
    "phát sinh nghĩa vụ tài chính theo quy định của pháp luật.",
    "Biên bản bàn giao nhà, đất, công trình xây dựng, hạng mục công trình xây dựng.",
    "Văn bản về việc nhà ở, công trình xây dựng đã được nghiệm thu đưa vào khai thác, sử dụng theo quy định của "
    "pháp luật về xây dựng đối với trường hợp có nhận chuyển nhượng nhà ở, công trình xây dựng (nếu có).",
    "",
    "Chứng từ chứng minh việc hoàn thành nghĩa vụ tài chính đối với trường hợp Văn phòng đăng ký đất đai nhận "
    "được văn bản của cơ quan có thẩm quyền về việc dự án được điều chỉnh quy hoạch xây dựng chi tiết mà làm "
    "phát sinh nghĩa vụ tài chính theo quy định của pháp luật (nếu có).",
]


def _fe_fold(text: str) -> str:
    """foldChoiceText của content.js: bỏ dấu, đ→d, gạch → khoảng trắng, lowercase; GIỮ dấu câu."""
    text = str(text or "").replace("Đ", "D").replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s*[-–—‐‑]+\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _fe_find_row(rows: list[str], name: str, index: int) -> str | None:
    """findAttachmentRowByComponent: thử dòng theo index trước, không khớp thì dòng ĐẦU TIÊN khớp tên."""
    def match(row: str) -> bool:
        r, w = _fe_fold(row), _fe_fold(name)
        return bool(r and w) and (r == w or w in r or r in w)
    if 0 < index <= len(rows) and match(rows[index - 1]):
        return rows[index - 1]
    return next((r for r in rows if match(r)), None)


def test_component_tro_dung_dong_ke_ca_khi_fe_loai_dong_10_khong_ten():
    named = [r for r in _PORTAL_ROWS if r]  # FE bỏ dòng không tên → index các dòng sau bị lệch 1
    for rows in (_PORTAL_ROWS, named):
        for row_no, spec in P._ROWS.items():
            found = _fe_find_row(rows, spec["componentName"], spec["componentIndex"])
            assert found == _PORTAL_ROWS[row_no - 1], (row_no, len(rows))


# --------------------------------------------------------------------------------------
# plan() đầu-cuối (OCR + LLM giả lập)
# --------------------------------------------------------------------------------------
def _pdf_file(name: str, pages: int):
    import base64

    import fitz

    from app.process.schemas import FileItem

    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    return FileItem(name=name, type="application/pdf", dataUrl=f"data:application/pdf;base64,{data}",
                    role="attachment")


@pytest.mark.asyncio
async def test_plan_dau_cuoi_hai_file_khong_mat_trang(monkeypatch):
    texts = {
        "don.pdf": ["ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI", ""],
        "hoso.pdf": ["HỢP ĐỒNG MUA BÁN NHÀ Ở", "Điều 2 giá bán", "BIÊN BẢN BÀN GIAO NHÀ Ở",
                     "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT", "TỜ KHAI LỆ PHÍ TRƯỚC BẠ NHÀ, ĐẤT"],
    }

    async def fake_ocr(files):
        out = []
        for f in files:
            pages = texts[f["name"]]
            out.append({"name": f["name"], "text": "\n".join(
                f"───── Trang {i}/{len(pages)} ─────\n{t}" for i, t in enumerate(pages, 1))})
        return out

    async def fake_classify(documents):
        return [  # LLM chỉ xếp được Đơn và Hợp đồng; phần còn lại để rule OCR vá.
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_mau_18", "documentName": "Đơn (Mẫu 18)"},
            {"fileIndex": 1, "pageFrom": 1, "pageTo": 2, "type": "hop_dong_chuyen_nhuong", "documentName": "HĐMB"},
        ]

    monkeypatch.setattr(P.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(P, "_classify_with_llm", fake_classify)
    res = await P.plan([_pdf_file("don.pdf", 2), _pdf_file("hoso.pdf", 5)], {}, None)
    by_row = {a["componentIndex"]: a for a in res["attachments"]}
    assert sorted(by_row) == [2, 3, 4, 5, 7, 8, 11]
    assert by_row[2]["fileIndex"] == 0 and "sourceSegments" not in by_row[2]  # trang trắng theo Đơn
    assert by_row[2]["documentName"] == "Đơn Mẫu 18"
    assert by_row[3]["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": [0, 1]}]
    assert by_row[4]["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": [2]}]
    assert by_row[5]["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": [3]}]
    assert by_row[7]["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": [4]}]
    assert res["errors"] == []


def test_llm_loi_trang_tiep_theo_khong_tieu_de_theo_giay_to_truoc():
    texts = {0: {1: "HỢP ĐỒNG MUA BÁN NHÀ Ở RIÊNG LẺ số 01/HĐMB giữa bên bán và bên mua",
                 2: "Điều 3. Phương thức và thời hạn thanh toán, hai bên thống nhất các khoản thanh toán",
                 3: "", 4: "BIÊN BẢN BÀN GIAO NHÀ Ở, căn cứ hợp đồng mua bán nhà ở đã ký",
                 5: "Bên nhận bàn giao đã kiểm tra hiện trạng nhà ở và ký xác nhận dưới đây"}}
    segments = [P._fallback_segment(0, p, p) for p in range(1, 6)]
    attachments, _, _ = _plan(segments, [5], texts)
    by_row = {a["componentIndex"]: a for a in attachments}
    assert by_row[3]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0, 1, 2]}]
    assert by_row[4]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [3, 4]}]
    assert sorted(by_row) == [3, 4, 8]
