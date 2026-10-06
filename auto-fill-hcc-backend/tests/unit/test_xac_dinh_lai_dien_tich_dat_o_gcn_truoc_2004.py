"""Unit test "Xác định lại diện tích đất ở (GCN cấp trước 01/7/2004)" — cổng DVC Đà Nẵng (1.012817).

Kiểm: registry + tách detect với hai bản cùng tên (Quảng Ngãi, Lào Cai), mapper hai vai + panel thửa đất +
ghi chú, planner đính CHUNG ở dòng Đơn và chỉ tách trang GCN / văn bản đại diện."""

import re
import unicodedata

from app.pipelines.xac_dinh_lai_dien_tich_dat_o_gcn_truoc_2004.attach import planner as P
from app.pipelines.xac_dinh_lai_dien_tich_dat_o_gcn_truoc_2004.process.mapper import enrich
from app.pipelines.xac_dinh_lai_dien_tich_dat_o_gcn_truoc_2004.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import (
    PROCEDURES,
    get_attach_pipeline,
    get_pipeline,
    get_procedure,
)

_KEY = "xac-dinh-lai-dien-tich-dat-o-gcn-truoc-2004"


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


# --------------------------------------------------------------------------------------
# REGISTRY + DETECT
# --------------------------------------------------------------------------------------
def test_registry_khop_ke_khai_links():
    procedure = get_procedure(_KEY)
    assert procedure
    assert procedure["hasAttachmentStep"] is True
    assert procedure["detect"]["urlScope"] == ["dichvucong.danang.gov.vn"]
    assert procedure["detect"]["textPriority"] is True
    assert callable(get_pipeline(_KEY))
    assert callable(get_attach_pipeline(_KEY))
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.012817"


def test_ba_ban_cung_ten_chi_tach_bang_url_scope():
    phrase = _fold(" ".join(get_procedure(_KEY)["detect"]["textIncludes"]))
    scopes = {}
    for key in (_KEY, "xac-dinh-lai-dien-tich-dat-o-quang-ngai", "xac-dinh-lai-dien-tich-dat-o-truoc-01-7-2004"):
        detect = get_procedure(key)["detect"]
        assert phrase in _fold(" ".join(detect["textIncludes"]))
        scopes[key] = tuple(detect["urlScope"])
    assert len(set(scopes.values())) == 3


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


def test_trang_da_nang_nhan_dung_thu_tuc_khong_bi_thu_tuc_dat_dai_khac_cuop():
    body = _fold(
        "Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp Giấy chứng nhận trước ngày 01 "
        "tháng 7 năm 2004 1. Bản gốc Giấy chứng nhận đã cấp. 2. Văn bản về việc đại diện theo quy định của "
        "pháp luật về dân sự đối với trường hợp thực hiện thủ tục đăng ký đất đai, tài sản gắn liền với đất "
        "thông qua người đại diện. 3. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18"
    )
    assert _popup_priority_pick(body, "https://dichvucong.danang.gov.vn/vi/padsvc/apply-online/abc") == _KEY
    assert _popup_priority_pick(body, "https://dichvucong.quangngai.gov.vn/vi/padsvc/apply-online/abc") == (
        "xac-dinh-lai-dien-tich-dat-o-quang-ngai"
    )


def test_schema_ui_key_theo_file_mapping():
    for key in ("data[ownerFullname]", "data[isOwnerDossier]", "data[fullname]", "data[birthday]",
                "data[gender]", "data[phoneNumber]", "data[identityNumber]", "data[note]",
                "data[noidungyeucaugiaiquyet]", "data[chonDoiTuong]", "data[province]", "data[district]",
                "data[address]", "data[diaChiThuaDat]", "data[SoToBanDo]", "data[SoThuaDat]",
                "data[province2]", "data[district2]", "data[nation2]"):
        assert key in UI_COMP_BY_NAME
    assert not any(name.startswith("data[") for name in ALLOWED)


# --------------------------------------------------------------------------------------
# MAPPER
# --------------------------------------------------------------------------------------
def _map(vals: dict) -> tuple[dict, list[str]]:
    fields, warnings = enrich([{"name": k, "value": v} for k, v in vals.items()], {})
    return {f["name"]: f["value"] for f in fields}, warnings


_HO_SO_KHONG_CCCD = {
    "ChuHoSo_LoaiChuThe": "Cá nhân",
    "ChuHoSo_HoTen": "LÊ VĂN AN",
    "ChuHoSo_DiaChi": "Tổ dân phố An Bình 3, Phường Liên Chiểu, TP Đà Nẵng",
    "NguoiNop_HoTen": "LÊ VĂN AN",
    "NguoiNop_SoDinhDanh": "CCCD 048060001234",
    "NguoiNop_DienThoai": "0905 123 456",
    "NoiDungYeuCau": "Xác định lại diện tích đất ở",
    "ThuaDat_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Liên Chiểu", "diaChi": "Tổ An Bình 3"},
    "ThuaDat_SoThua": "thửa đất số 101, 102 và 103",
    "ThuaDat_SoTo": "45, 45, 45",
}


def test_tu_nop_khong_cccd():
    out, warnings = _map(_HO_SO_KHONG_CCCD)
    assert out["data[ownerFullname]"] == "LÊ VĂN AN"
    assert out["data[isOwnerDossier]"] is True
    assert out["data[fullname]"] == "LÊ VĂN AN"
    assert out["data[identityNumber]"] == "048060001234"
    assert out["data[gender]"] == "Nam"  # chữ số thứ 4 của số định danh là 0
    assert out["data[phoneNumber]"] == "0905123456"
    assert out["data[chonDoiTuong]"] == "Cá nhân"
    assert out["data[province]"] == "Thành phố Đà Nẵng"
    assert out["data[district]"] == "Phường Liên Chiểu"
    assert out["data[address]"] == "Tổ dân phố An Bình 3"
    assert out["data[noidungyeucaugiaiquyet]"] == "Xác định lại diện tích đất ở"
    assert "data[birthday]" not in out
    assert any("Ngày sinh" in w for w in warnings)


def test_panel_thua_dat_nhieu_thua_mot_to():
    out, _ = _map(_HO_SO_KHONG_CCCD)
    assert out["data[SoThuaDat]"] == "101, 102, 103"
    assert out["data[SoToBanDo]"] == "45"
    assert out["data[province2]"] == "Thành phố Đà Nẵng"
    assert out["data[district2]"] == "Phường Liên Chiểu"
    assert out["data[nation2]"] == "Việt Nam"
    assert out["data[diaChiThuaDat]"] == "Tổ An Bình 3, Phường Liên Chiểu, Thành phố Đà Nẵng"


def test_gioi_tinh_nu_suy_tu_so_dinh_danh():
    out, _ = _map({**_HO_SO_KHONG_CCCD, "NguoiNop_SoDinhDanh": "048165001234"})
    assert out["data[gender]"] == "Nữ"


def test_gioi_tinh_tu_giay_to_thang_so_dinh_danh():
    out, _ = _map({**_HO_SO_KHONG_CCCD, "NguoiNop_GioiTinh": "Nữ"})
    assert out["data[gender]"] == "Nữ"


def test_co_cccd_day_du_khong_canh_bao_ngay_sinh():
    out, warnings = _map({
        **_HO_SO_KHONG_CCCD,
        "NguoiNop_NgaySinh": "05/04/1960",
        "NguoiNop_NgayCap": "10/8/2021",
        "NguoiNop_NoiCap": "CCS QLHC về TTXH",
    })
    assert out["data[birthday]"] == "05/04/1960"
    assert out["data[identityDate]"] == "10/08/2021"
    assert out["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert not any("Ngày sinh" in w for w in warnings)


def test_chi_co_nam_sinh_thi_bo_trong():
    out, _ = _map({**_HO_SO_KHONG_CCCD, "NguoiNop_NgaySinh": "1960"})
    assert "data[birthday]" not in out


def test_ghi_chu_van_ban_co_quan_va_giay_to_dinh_chung():
    out, _ = _map({
        **_HO_SO_KHONG_CCCD,
        "VanBanCoQuan": "Công văn số 1234/CNKV-KTĐC ngày 15/3/2026 của Chi nhánh Văn phòng Đăng ký đất đai Khu vực II",
        "GiayToTrongHoSo": [
            "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 25) ký ngày 05/3/2026",
            "Bản mô tả ranh giới, mốc giới thửa đất lập ngày 10/01/2026",
        ],
    })
    note = out["data[note]"]
    assert note.startswith("Hồ sơ nộp theo Công văn số 1234/CNKV-KTĐC")
    assert "Tệp đính kèm gồm: Đơn đăng ký biến động" in note
    assert "Bản mô tả ranh giới" in note


def test_ghi_chu_chuoi_ngan_cach_cham_phay():
    out, _ = _map({**_HO_SO_KHONG_CCCD, "GiayToTrongHoSo": "Đơn đăng ký biến động; Bản mô tả ranh giới"})
    assert out["data[note]"] == "Tệp đính kèm gồm: Đơn đăng ký biến động; Bản mô tả ranh giới."


def test_noi_dung_trong_dung_ten_viec_cua_thu_tuc():
    vals = dict(_HO_SO_KHONG_CCCD)
    vals.pop("NoiDungYeuCau")
    out, _ = _map(vals)
    assert out["data[noidungyeucaugiaiquyet]"] == "Xác định lại diện tích đất ở"


def test_nguoi_cung_su_dung_canh_bao():
    _, warnings = _map({**_HO_SO_KHONG_CCCD, "NguoiCungSuDung": ["LÊ VĂN AN", "Trần Thị Bình", "Lê Văn Cường"]})
    msg = next(w for w in warnings if "cùng sử dụng" in w)
    assert "thêm 2 người" in msg
    assert "LÊ VĂN AN" not in msg


def test_uy_quyen_bo_tich_dien_nguoi_duoc_uy_quyen():
    out, _ = _map({
        **_HO_SO_KHONG_CCCD,
        "NguoiNop_HoTen": "PHẠM THỊ DUNG",
        "NguoiNop_SoDinhDanh": "048185009999",
        "NguoiNop_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "12 Lê Lợi"},
    })
    assert out["data[isOwnerDossier]"] is False
    assert out["data[ownerFullname]"] == "LÊ VĂN AN"
    assert out["data[fullname]"] == "PHẠM THỊ DUNG"
    assert out["data[identityNumber]"] == "048185009999"
    assert out["data[district]"] == "Phường Hải Châu"
    assert out["data[address]"] == "12 Lê Lợi"


def test_thieu_chu_ho_so_canh_bao():
    _, warnings = _map({"NguoiNop_HoTen": "LÊ VĂN AN"})
    assert any("chủ hồ sơ" in w for w in warnings)


# --------------------------------------------------------------------------------------
# ATTACH PLANNER
# --------------------------------------------------------------------------------------
def _seg(file_index, page_from, page_to, doc_type, name=""):
    return {"fileIndex": file_index, "pageFrom": page_from, "pageTo": page_to, "type": doc_type, "documentName": name}


def _build(segments, page_counts, texts=None):
    raw_files = [{"name": f"hoso{i}.pdf", "type": "application/pdf"} for i in range(len(page_counts))]
    meta = {i: {"pageCount": n, "pageBoundariesAvailable": True} for i, n in enumerate(page_counts)}
    pages = {i: (texts or {}).get(i, {}) for i in range(len(page_counts))}
    full = {i: "\n".join((texts or {}).get(i, {}).values()) for i in range(len(page_counts))}
    return P.build_attachments(segments, raw_files, meta, pages, full)


def test_bo_ho_so_mau_dinh_chung_nguyen_file_vao_dong_don():
    # Đơn + trang trắng + bản mô tả ranh giới (2 trang) + công văn (3 trang) + trang trắng, KHÔNG có GCN.
    atts, classified, errors = _build([
        _seg(0, 1, 1, "don_bien_dong"),
        _seg(0, 2, 2, "trang_trang"),
        _seg(0, 3, 4, "ban_mo_ta_ranh_gioi"),
        _seg(0, 5, 7, "van_ban_co_quan"),
        _seg(0, 8, 8, "trang_trang"),
    ], [8])
    assert len(atts) == 1
    item = atts[0]
    assert item["componentIndex"] == 3
    assert item["componentName"] == "Đơn đăng ký biến động đất đai"
    assert item["loaiBan"] == "Bản chính"
    assert item["target"] == "attp-row"
    assert "sourceSegments" not in item  # đính nguyên file, giữ cả trang trắng
    assert item["documentName"] == "Đơn đăng ký biến động và giấy tờ kèm theo"
    assert {c["componentIndex"] for c in classified} == {3}
    assert any("Giấy chứng nhận đã cấp" in e for e in errors)


def test_file_gop_co_gcn_tach_trang_gcn_sang_dong_1():
    atts, _, errors = _build([
        _seg(0, 1, 1, "don_bien_dong"),
        _seg(0, 2, 3, "gcn_da_cap"),
        _seg(0, 4, 4, "trang_trang"),  # mặt sau trắng của GCN → theo GCN
        _seg(0, 5, 6, "ban_mo_ta_ranh_gioi"),
    ], [6])
    by_row = {a["componentIndex"]: a for a in atts}
    assert set(by_row) == {1, 3}
    assert by_row[1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1, 2, 3]}]
    assert by_row[3]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0, 4, 5]}]
    assert not any("Giấy chứng nhận đã cấp" in e for e in errors)


def test_van_ban_uy_quyen_sang_dong_2():
    atts, _, _ = _build([
        _seg(0, 1, 1, "don_bien_dong"),
        _seg(0, 2, 2, "van_ban_dai_dien"),
    ], [2])
    rows = {a["componentIndex"]: a for a in atts}
    assert rows[2]["componentName"] == "Văn bản về việc đại diện"
    assert rows[2]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1]}]


def test_nhieu_file_rieng_le():
    atts, _, errors = _build([
        _seg(0, 1, 1, "don_bien_dong"),
        _seg(1, 1, 2, "gcn_da_cap"),
        _seg(2, 1, 1, "cccd"),
    ], [1, 2, 1])
    rows = [(a["fileIndex"], a["componentIndex"], "sourceSegments" in a) for a in atts]
    assert rows == [(0, 3, False), (1, 1, False), (2, 3, False)]
    names = [a["documentName"] for a in atts]
    assert len(set(names)) == len(names)
    assert errors == []


def test_trang_trang_dau_file_theo_doan_sau():
    atts, _, _ = _build([
        _seg(0, 1, 1, "trang_trang"),
        _seg(0, 2, 3, "gcn_da_cap"),
        _seg(0, 4, 4, "don_bien_dong"),
    ], [4])
    rows = {a["componentIndex"]: a for a in atts}
    assert rows[1]["sourceSegments"][0]["pageIndexes"] == [0, 1, 2]
    assert rows[3]["sourceSegments"][0]["pageIndexes"] == [3]


def test_llm_loi_rule_ocr_khong_nham_cong_van_thanh_gcn():
    # LLM hỏng → mỗi file một đoạn 'other'; rule OCR phải nhận công văn (có nhắc "Giấy chứng nhận") là
    # văn bản cơ quan, GCN thật (có "số vào sổ cấp giấy chứng nhận") mới lên dòng 1.
    texts = {
        0: {1: "CHI NHÁNH VĂN PHÒNG ĐĂNG KÝ ĐẤT ĐAI Số: 1234/CNKV V/v hồ sơ. Hộ ông A đã được cấp Giấy "
               "chứng nhận quyền sử dụng đất số X 000001, thửa đất số 1, tờ bản đồ số 2. Nơi nhận: - Như trên"},
        1: {1: "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT ... Số vào sổ cấp giấy chứng nhận quyền sử dụng đất: 00123"},
    }
    atts, classified, _ = _build([_seg(0, 1, 1, "other"), _seg(1, 1, 1, "other")], [1, 1], texts)
    assert [c["type"] for c in classified] == ["van_ban_co_quan", "gcn_da_cap"]
    assert [a["componentIndex"] for a in atts] == [3, 1]


def test_normalize_type_ho_so_do_dac_khong_thanh_gcn():
    assert P._normalize_type("ho_so_do_dac") == "phieu_do_dac"
    assert P._normalize_type("giay chung nhan") == "gcn_da_cap"
    assert P._normalize_type("don_mau_25") == "don_bien_dong"
