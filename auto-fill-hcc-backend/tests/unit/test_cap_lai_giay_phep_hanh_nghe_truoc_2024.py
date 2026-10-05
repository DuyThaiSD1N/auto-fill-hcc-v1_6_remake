"""[Bộ Y tế] Cấp lại giấy phép hành nghề (cấp trước 01/01/2024) — 2 chế độ người nộp + đính kèm không bỏ tệp."""

import re
from pathlib import Path

from app.pipelines.cap_lai_giay_phep_hanh_nghe_truoc_2024.attach import planner
from app.pipelines.cap_lai_giay_phep_hanh_nghe_truoc_2024.process import mapper
from app.procedures.registry import public_list

_KEY = "cap-lai-giay-phep-hanh-nghe-truoc-2024"
_ROOT = Path(__file__).resolve().parents[2].parent

_OWNER = {
    "NguoiHanhNghe_HoTen": "NGUYEN VAN A",
    "NguoiHanhNghe_SoDinhDanh": "001000000001",
    "NguoiHanhNghe_NgaySinh": "01/02/1990",
    "NguoiHanhNghe_GioiTinh": "Nam",
    "NguoiHanhNghe_NgayCap": "03/04/2021",
    "NguoiHanhNghe_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "NguoiHanhNghe_ThuongTru": {"tinh": "Thành phố Đà Nẵng", "xa": "Hải Châu", "diaChi": "Tổ 1"},
    "NguoiHanhNghe_DienThoai": "0900000001",
}
_SUBMITTER = {
    "NguoiNop_HoTen": "TRAN THI B",
    "NguoiNop_SoDinhDanh": "001000000002",
    "NguoiNop_NgaySinh": "05/06/1992",
    "NguoiNop_GioiTinh": "Nữ",
}


def _run(values, options=None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    return {f["name"]: f["value"] for f in fields}, [f["name"] for f in fields], warnings


def _account(name, identity):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": identity}}


def test_registry_detect_va_co_buoc_dinh_kem():
    entry = next(p for p in public_list() if p["key"] == _KEY)
    assert entry["mode"] == "agent" and entry["hasAttachmentStep"] is True
    assert any("cấp lại giấy phép hành nghề" in t for t in entry["detect"]["textIncludes"])


def test_khong_mo_chong_detect_voi_thu_tuc_cap_moi():
    cap_moi = next(p for p in public_list() if p["key"] == "cap-moi-giay-phep-hanh-nghe-chuyen-tiep")
    assert not any("cấp lại giấy phép hành nghề" in t for t in cap_moi["detect"]["textIncludes"])


def test_khong_co_moc_tai_khoan_thi_tu_nop_giu_tich():
    ui, order, _ = _run(_OWNER)
    assert ui["data[isOwnerDossierCheck]"] is True
    assert ui["data[fullname]"] == "NGUYEN VAN A" and ui["data[identityNumber]"] == "001000000001"
    assert order.index("data[isOwnerDossierCheck]") < order.index("data[fullname]")
    assert not any(k.startswith("data[owner") for k in ui)


def test_che_do_theo_tai_khoan_khop_nguoi_hanh_nghe_la_tu_nop_khong_de_o_cong_da_dien():
    ui, _, _ = _run(_OWNER, _account("Nguyễn Văn A", "001000000001"))
    assert ui["data[isOwnerDossierCheck]"] is True
    assert "data[fullname]" not in ui and "data[identityNumber]" not in ui, "cổng đã đổ từ tài khoản"
    assert ui["data[birthday]"] == "01/02/1990"
    assert not any(k.startswith("data[owner") for k in ui)


def test_khop_theo_ten_khong_dau_khi_tai_khoan_khong_co_cccd():
    ui, _, _ = _run(_OWNER, {"formContext": {"applicantFullname": "nguyen van a"}})
    assert ui["data[isOwnerDossierCheck]"] is True


def test_nop_thay_co_cccd_nguoi_nop_bo_tich_dien_ca_hai_phan():
    ui, order, warnings = _run({**_OWNER, **_SUBMITTER}, _account("TRẦN THỊ B", "001000000002"))
    assert ui["data[isOwnerDossierCheck]"] is False
    assert order.index("data[isOwnerDossierCheck]") < order.index("data[ownerFullname]")
    assert ui["data[birthday]"] == "05/06/1992" and ui["data[gender]"] == "Nữ", "Phần I = người nộp"
    assert ui["data[ownerFullname]"] == "NGUYEN VAN A" and ui["data[ownerIdentityNumber]"] == "001000000001"
    assert ui["data[ownerBirthday]"] == "01/02/1990"
    assert not warnings


def test_nop_thay_khong_co_cccd_nguoi_nop_khong_muon_nhan_than_nguoi_hanh_nghe():
    ui, _, warnings = _run(_OWNER, _account("TRẦN THỊ B", "001000000002"))
    assert ui["data[isOwnerDossierCheck]"] is False
    assert "data[birthday]" not in ui and "data[gender]" not in ui
    assert ui["data[ownerFullname]"] == "NGUYEN VAN A"
    assert any("không có CCCD người nộp" in w for w in warnings)


def test_cccd_nguoi_nop_khong_khop_tai_khoan_thi_khong_dien_phan_mot():
    ui, _, warnings = _run({**_OWNER, **_SUBMITTER}, _account("LE VAN C", "001000000003"))
    assert ui["data[isOwnerDossierCheck]"] is False and "data[birthday]" not in ui
    assert any("không khớp tài khoản" in w for w in warnings)


def test_che_do_nguoi_nop_la_chu_ho_so_bo_qua_moc_tai_khoan():
    options = {**_account("TRẦN THỊ B", "001000000002"), "submitterMode": "owner_as_submitter"}
    ui, _, _ = _run({**_OWNER, **_SUBMITTER}, options)
    assert ui["data[isOwnerDossierCheck]"] is True
    assert ui["data[birthday]"] == "01/02/1990"
    # Theo tờ khai người nộp khác tài khoản → ghi đè cả họ tên + CCCD cổng đã đổ, không để khối lai.
    assert ui["data[fullname]"] == "NGUYEN VAN A" and ui["data[identityNumber]"] == "001000000001"
    assert not any(k.startswith("data[owner") for k in ui)


def test_dinh_kem_moi_loai_dung_dong_va_cccd_other_vao_dong_don():
    names = ["don.pdf", "cchn.jpg", "anh.jpg", "cccd.jpg", "la.pdf"]
    types = {0: "don_de_nghi", 1: "giay_phep_cu", 2: "anh_chan_dung", 3: "cccd", 4: "other"}
    items, warnings, _ = planner.build_plan_items([{"name": n} for n in names], types)
    assert [i["fileIndex"] for i in items] == [0, 1, 2, 3, 4], "không bỏ tệp nào"
    comp = [i["componentName"] for i in items]
    assert comp[1] == "hợp lệ giấy phép hành nghề đã được cấp" and comp[2] == "02 ảnh chân dung cỡ 04"
    assert comp[3] == comp[4] == comp[0] == "Đơn theo Mẫu 08 Phụ lục I"
    assert items[3]["documentName"] == "Căn cước công dân" and items[4]["documentName"] == "la.pdf"
    assert warnings and "la.pdf" in warnings[0] and "cccd.jpg" not in warnings[0]


def test_llm_loi_van_dinh_vao_dong_don():
    items, _, _ = planner.build_plan_items([{"name": "a.pdf"}], {})
    assert items[0]["componentName"] == "Đơn theo Mẫu 08 Phụ lục I"


def _fe_fold(text: str) -> str:
    import unicodedata

    text = str(text or "").replace("Đ", "D").replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s*[-‐-―]\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def test_dong_dau_tien_khop_moi_component_la_dong_dung_loai_giay():
    """Engine attp-row lấy dòng ĐẦU TIÊN chứa componentName — dòng đó phải đúng loại giấy (bảng 34 dòng trùng)."""
    # Tên tệp snapshot có dấu (macOS lưu NFD) → chọn theo nội dung: trang có bảng thành phần hồ sơ.
    pages = [f.read_text(encoding="utf-8", errors="replace") for d in (_ROOT / "thongtin").glob("109_*")
             for f in d.glob("*.html")]
    html = next((p for p in pages if "table-tbt" in p and "rdo_File" in p), None)
    if html is None:
        return
    rows = [_fe_fold(re.sub(r"(?s)<[^>]+>", " ", r)) for r in re.findall(r'(?s)<tr[^>]*class="[^"]*item[^"]*"[^>]*>(.*?)</tr>', html)]
    assert len(rows) >= 30
    expect = {
        "don_de_nghi": "don theo mau 08",
        "giay_phep_cu": "giay phep hanh nghe da duoc cap",
        "anh_chan_dung": "02 anh chan dung",
        "so_yeu_ly_lich": "so yeu ly lich",
        "suc_khoe": "giay kham suc khoe",
        "thuc_hanh": "hoan thanh qua trinh thuc hanh",
        "quyet_dinh_thu_hoi": "quyet dinh thu hoi",
        "ket_qua_danh_gia": "kiem tra danh gia nang luc",
    }
    for doc_type, must in expect.items():
        key = _fe_fold(planner._ROWS[doc_type]["componentName"])
        first = next((r for r in rows if key in r), None)
        assert first is not None and must in first, (doc_type, key)


def test_hai_loai_chung_mot_dong_dung_chung_component_de_engine_khong_ghi_de():
    """Engine gom theo componentName rồi set ô upload 1 lần — 2 tên khác nhau cùng trỏ 1 dòng thì ghi đè nhau."""
    assert planner._ROWS["suc_khoe"]["componentName"] == planner._ROWS["ket_qua_danh_gia"]["componentName"]
