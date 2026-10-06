"""Unit test "Xóa đăng ký thuê, cho thuê lại QSDĐ trong dự án xây dựng kinh doanh kết cấu hạ tầng" — cổng DVC Đà
Nẵng (1.012766).

Kiểm: registry + ke_khai_links (tích Sở), nhận diện trang, mapper hai vai + nội dung yêu cầu, planner đính NGUYÊN
file (không tách trang) và chỉ chuyển tệp lẻ sang dòng riêng."""

import re
import unicodedata

from app.pipelines.xoa_dang_ky_thue_cho_thue_lai_qsdd_du_an_ket_cau_ha_tang.attach import planner as P
from app.pipelines.xoa_dang_ky_thue_cho_thue_lai_qsdd_du_an_ket_cau_ha_tang.process.mapper import enrich
from app.pipelines.xoa_dang_ky_thue_cho_thue_lai_qsdd_du_an_ket_cau_ha_tang.process.schema import (
    ALLOWED,
    UI_COMP_BY_NAME,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "xoa-dang-ky-thue-cho-thue-lai-qsdd-du-an-ket-cau-ha-tang"


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


# --------------------------------------------------------------------------------------
# REGISTRY + DETECT
# --------------------------------------------------------------------------------------
def test_registry_khop_ke_khai_links_va_tich_so():
    procedure = get_procedure(_KEY)
    assert procedure
    assert procedure["hasAttachmentStep"] is True
    assert procedure["detect"]["urlScope"] == ["dichvucong.danang.gov.vn"]
    assert procedure["detect"]["textPriority"] is True
    assert callable(get_pipeline(_KEY))
    assert callable(get_attach_pipeline(_KEY))
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.012766"
    assert link["selectSo"] is True


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


def test_trang_da_nang_nhan_dung_thu_tuc():
    body = _fold(
        "Xóa đăng ký thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ tầng "
        "Văn phòng Đăng ký đất đai Thành phần hồ sơ (1) Đơn đăng ký biến động đất đai, tài sản gắn liền với đất "
        "theo Mẫu số 18 (2) Giấy chứng nhận đã cấp; (4) Văn bản về việc đại diện theo quy định của pháp luật về "
        "dân sự (3) Văn bản về việc xóa cho thuê, xóa cho thuê lại quyền sử dụng đất"
    )
    assert _popup_priority_pick(body, "https://dichvucong.danang.gov.vn/vi/padsvc/apply-online/abc") == _KEY
    assert _popup_priority_pick(body, "https://dichvucong.quangngai.gov.vn/vi/padsvc/apply-online/abc") == ""


def test_schema_ui_key_theo_file_mapping():
    for key in ("data[ownerFullname]", "data[isOwnerDossier]", "data[organization]", "data[fullname]",
                "data[birthday]", "data[gender]", "data[email]", "data[phoneNumber]", "data[identityNumber]",
                "data[identityDate]", "data[identityAgency]", "data[noidungyeucaugiaiquyet]", "data[taxCode]",
                "data[chonDoiTuong]", "data[province]", "data[district]", "data[address]"):
        assert key in UI_COMP_BY_NAME
    assert not any(name.startswith("data[") for name in ALLOWED)


# --------------------------------------------------------------------------------------
# MAPPER
# --------------------------------------------------------------------------------------
def _map(vals: dict) -> tuple[dict, list[str]]:
    fields, warnings = enrich([{"name": k, "value": v} for k, v in vals.items()], {})
    return {f["name"]: f["value"] for f in fields}, warnings


_TU_NOP = {
    "ChuHoSo_LoaiChuThe": "Cá nhân",
    "ChuHoSo_HoTen": "LÊ THỊ HOA",
    "ChuHoSo_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường An Hải Bắc", "diaChi": "12 Nguyễn Văn Thoại"},
    "VanBanXoaThue": "Hợp đồng chấm dứt Hợp đồng thuê quyền sử dụng đất số công chứng 1111/2026/CCGD ngày "
                     "05/3/2026 tại Văn phòng công chứng Hòa Bình",
    "NguoiNop_HoTen": "LÊ THỊ HOA",
    "NguoiNop_NgaySinh": "20/05/1962",
    "NguoiNop_SoDinhDanh": "048162001234",
    "NguoiNop_NgayCap": "22/4/2021",
    "NguoiNop_DienThoai": "0905.123.456",
}


def test_tu_nop_dien_du_nguoi_nop_va_noi_dung():
    out, warnings = _map(_TU_NOP)
    assert out["data[ownerFullname]"] == "LÊ THỊ HOA"
    assert out["data[isOwnerDossier]"] is True
    assert out["data[fullname]"] == "LÊ THỊ HOA"
    assert out["data[birthday]"] == "20/05/1962"
    assert out["data[gender]"] == "Nữ"                      # suy từ chữ số thứ 4 của số định danh.
    assert out["data[identityNumber]"] == "048162001234"
    assert out["data[identityDate]"] == "22/04/2021"
    assert out["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert out["data[phoneNumber]"] == "0905123456"
    assert out["data[chonDoiTuong]"] == "Cá nhân"
    assert out["data[province]"] == "Thành phố Đà Nẵng"
    assert out["data[district]"] == "Phường An Hải"             # địa danh cũ trước sáp nhập → phường mới.
    assert out["data[address]"] == "12 Nguyễn Văn Thoại"
    noi_dung = out["data[noidungyeucaugiaiquyet]"]
    assert noi_dung.startswith("ÔNG/BÀ: LÊ THỊ HOA (chủ hồ sơ) ĐỀ NGHỊ GIẢI QUYẾT Xóa đăng ký thuê")
    assert "theo Hợp đồng chấm dứt Hợp đồng thuê quyền sử dụng đất số công chứng 1111/2026/CCGD" in noi_dung
    assert "data[organization]" not in out and "data[taxCode]" not in out and "data[note]" not in out
    assert warnings == []


def test_don_co_muc_ii_thi_chep_muc_ii():
    out, _ = _map({**_TU_NOP, "NoiDungYeuCau": "Xóa đăng ký cho thuê quyền sử dụng đất ....."})
    assert out["data[noidungyeucaugiaiquyet]"].endswith("\nXóa đăng ký cho thuê quyền sử dụng đất")


def test_cmnd_9_so_khong_dien_va_canh_bao():
    out, warnings = _map({**_TU_NOP, "NguoiNop_SoDinhDanh": "201234567"})
    assert "data[identityNumber]" not in out
    assert "data[identityAgency]" not in out
    assert any("CMND 9 số" in w for w in warnings)


def test_thieu_ngay_sinh_va_dien_thoai_canh_bao():
    vals = {k: v for k, v in _TU_NOP.items() if k not in ("NguoiNop_NgaySinh", "NguoiNop_DienThoai")}
    out, warnings = _map({**vals, "NguoiNop_NgaySinh": "1962"})
    assert "data[birthday]" not in out
    assert any("Ngày sinh" in w for w in warnings)
    assert any("Số điện thoại" in w for w in warnings)


def test_uy_quyen_bo_tich_dien_nguoi_duoc_uy_quyen():
    out, _ = _map({
        **_TU_NOP,
        "NguoiNop_HoTen": "TRẦN VĂN BÌNH",
        "NguoiNop_SoDinhDanh": "048090004321",
        "NguoiNop_NgaySinh": "01/02/1990",
        "NguoiNop_GioiTinh": "Nam",
        "NguoiNop_DiaChi": {"tinh": "Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "5 Lê Lợi"},
    })
    assert out["data[ownerFullname]"] == "LÊ THỊ HOA"
    assert out["data[isOwnerDossier]"] is False
    assert out["data[fullname]"] == "TRẦN VĂN BÌNH"
    assert out["data[gender]"] == "Nam"
    assert out["data[district]"] == "Phường Hải Châu"
    assert out["data[address]"] == "5 Lê Lợi"


def test_chu_ho_so_to_chuc():
    out, _ = _map({
        "ChuHoSo_LoaiChuThe": "Tổ chức",
        "ChuHoSo_HoTen": "CÔNG TY TNHH MTV DỊCH VỤ BIỂN XANH",
        "ChuHoSo_MaSoThue": "0400000001",
        "ChuHoSo_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường An Hải", "diaChi": "20 Võ Văn Kiệt"},
        "NguoiNop_DienThoai": "0236123456",
    })
    assert out["data[organization]"] == "CÔNG TY TNHH MTV DỊCH VỤ BIỂN XANH"
    assert out["data[chonDoiTuong]"] == "Tổ chức"
    assert out["data[taxCode]"] == "0400000001"
    assert out["data[identityNumber]"] == "0400000001"
    assert out["data[noidungyeucaugiaiquyet]"].startswith("CÔNG TY TNHH MTV DỊCH VỤ BIỂN XANH (chủ hồ sơ)")


def test_thieu_chu_ho_so_canh_bao():
    _, warnings = _map({"NguoiNop_DienThoai": "0905123456"})
    assert any("Thiếu tên chủ hồ sơ" in w for w in warnings)


# --------------------------------------------------------------------------------------
# PLANNER
# --------------------------------------------------------------------------------------
def _files(*names: str) -> list[dict]:
    return [{"name": n, "type": "application/pdf", "dataUrl": "data:application/pdf;base64,"} for n in names]


_OCR_DON = "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT Kính gửi: Văn phòng đăng ký đất đai"
_OCR_HD = (
    "HỢP ĐỒNG CHẤM DỨT HỢP ĐỒNG THUÊ QUYỀN SỬ DỤNG ĐẤT Bên cho thuê … Bên thuê … (Theo Giấy ủy quyền số "
    "01/2026/GUQ) Giấy chứng nhận quyền sử dụng đất số AB 000001 LỜI CHỨNG CỦA CÔNG CHỨNG VIÊN"
)
_OCR_GCN = "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT Số vào sổ cấp giấy chứng nhận CS 0001 Những thay đổi sau khi cấp"


def test_ho_so_mau_mot_file_gop_dinh_nguyen_vao_dong_1():
    files = _files("ho_so.pdf")
    llm = {0: {"docType": P._XOA_THUE, "containsTypes": {P._XOA_THUE, P._DON}}}
    items, messages, classified = P.build_plan_items(files, {0: _OCR_HD + " " + _OCR_DON}, llm)
    assert len(items) == 1
    item = items[0]
    assert item["componentIndex"] == 1 and item["loaiBan"] == "Bản chính" and item["target"] == "attp-row"
    assert "sourceSegments" not in item                          # không tách, không ghép.
    assert classified[0]["componentIndex"] == 1
    assert any("dòng 4 không đính lại" in m for m in messages)
    assert any("chưa có bản scan Giấy chứng nhận" in m for m in messages)


def test_file_rieng_le_vao_dung_dong():
    files = _files("don.pdf", "gcn.pdf", "hd.pdf", "uq.pdf")
    llm = {
        0: {"docType": P._DON, "containsTypes": {P._DON}},
        1: {"docType": P._GCN, "containsTypes": {P._GCN}},
        2: {"docType": P._XOA_THUE, "containsTypes": {P._XOA_THUE}},
        3: {"docType": P._DAI_DIEN, "containsTypes": {P._DAI_DIEN}},
    }
    items, messages, _ = P.build_plan_items(files, {}, llm)
    by_row = {i["componentIndex"]: i for i in items}
    assert by_row[1]["fileName"] == "don.pdf"
    assert by_row[2]["fileName"] == "gcn.pdf" and by_row[2]["loaiBan"] == "Bản chính"
    assert by_row[3]["fileName"] == "uq.pdf" and by_row[3]["loaiBan"] == "Bản sao"
    assert by_row[4]["fileName"] == "hd.pdf" and by_row[4]["loaiBan"] == "Bản sao"
    assert messages == []


def test_cccd_le_ghep_nguyen_file_sau_don_o_dong_1():
    files = _files("cccd.pdf", "don.pdf")
    llm = {0: {"docType": P._CCCD, "containsTypes": {P._CCCD}}, 1: {"docType": P._DON, "containsTypes": {P._DON}}}
    items, messages, _ = P.build_plan_items(files, {}, llm)
    row1 = [i for i in items if i["componentIndex"] == 1]
    assert len(row1) == 1
    assert row1[0]["fileIndex"] == 1
    assert row1[0]["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": None}, {"fileIndex": 0, "pageIndexes": None}]
    assert any("cccd.pdf" in m and "đính chung ở dòng 1" in m for m in messages)


def test_llm_loi_rule_ocr_hop_dong_nhac_uy_quyen_van_vao_dong_4():
    files = _files("hd.pdf", "gcn.pdf")
    items, _, classified = P.build_plan_items(files, {0: _OCR_HD, 1: _OCR_GCN}, {})
    by_file = {c["fileName"]: c for c in classified}
    assert by_file["hd.pdf"]["docType"] == P._XOA_THUE and by_file["hd.pdf"]["componentIndex"] == 4
    assert by_file["gcn.pdf"]["docType"] == P._GCN and by_file["gcn.pdf"]["componentIndex"] == 2
    assert all(c["source"] == "rule" for c in classified)


def test_ocr_thay_don_ma_llm_bo_sot_van_vao_dong_1():
    files = _files("ho_so.pdf")
    llm = {0: {"docType": P._XOA_THUE, "containsTypes": {P._XOA_THUE}}}
    items, _, _ = P.build_plan_items(files, {0: _OCR_HD + " " + _OCR_DON}, llm)
    assert [i["componentIndex"] for i in items] == [1]


def test_normalize_type():
    assert P._normalize_type("hop_dong_cham_dut_thue") == P._XOA_THUE
    assert P._normalize_type("van ban uy quyen") == P._DAI_DIEN
    assert P._normalize_type("don_mau_18") == P._DON
    assert P._normalize_type("giay_chung_nhan") == P._GCN
    assert P._normalize_type("") == P._OTHER
