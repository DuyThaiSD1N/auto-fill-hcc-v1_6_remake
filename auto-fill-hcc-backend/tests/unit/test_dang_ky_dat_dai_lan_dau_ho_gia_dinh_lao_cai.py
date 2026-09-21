"""[Lào Cai] Đăng ký đất đai, cấp GCN lần đầu — hộ gia đình, cá nhân (1.115689).

Khoá 4 điều dễ vỡ: thứ tự DOM 33 ô upload (3 dòng "Đơn Mẫu 21" trùng tên → phải đi slotIndex);
ba nhóm a/b/c loại trừ nhau; bản mô tả ranh giới đính THAY THẾ vào dòng mảnh trích đo + bắt buộc ghi
chú; ô "Về việc" phải GIỮ NGUYÊN nội dung cổng điền sẵn.
"""

import re
from pathlib import Path

from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai.attach import planner
from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai.process import mapper
from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import public_list

_KEY = "dang-ky-dat-dai-lan-dau-ho-gia-dinh-lao-cai"
_THONGTIN = Path(__file__).resolve().parents[2].parent / "thongtin"


def _dir():
    for d in _THONGTIN.glob("160-*"):
        return d
    return None


def _attach_html():
    snapshot_dir = _dir()
    if snapshot_dir is None:
        return None
    for f in snapshot_dir.glob("*ính kèm*.html"):
        return f
    return None


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _entry():
    return next(p for p in public_list() if p["key"] == _KEY)


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_registry_khoa_bang_ma_va_cum_doi_tuong():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["laocai.gov.vn"]
    assert "1.115689" in entry["detect"]["textIncludes"]


def test_detect_khong_lan_voi_ban_danh_cho_to_chuc():
    """Cùng tên thủ tục, khác đối tượng: bản tổ chức không có cụm 'hộ gia đình, cá nhân'."""
    cum = next(t for t in _entry()["detect"]["textIncludes"] if "hộ gia đình" in t).lower()
    ban_to_chuc = (
        "đăng ký đất đai, tài sản gắn liền với đất, cấp giấy chứng nhận quyền sử dụng đất, quyền sở "
        "hữu tài sản gắn liền với đất lần đầu đối với tổ chức đang sử dụng đất"
    )
    assert cum not in ban_to_chuc


def test_detect_khong_lan_voi_thu_tuc_lan_dau_tinh_khac():
    """Mã thủ tục là thứ phân biệt Lào Cai với Lâm Đồng/Ninh Bình/Đà Nẵng (tên gần như trùng)."""
    entry = _entry()
    khac_tinh = [p for p in public_list()
                 if p["key"] != _KEY and "lan-dau" in p["key"] and "dang-ky-dat-dai" in p["key"]]
    assert khac_tinh, "phải còn các thủ tục lần đầu của tỉnh khác để đối chiếu"
    for other in khac_tinh:
        assert "1.115689" not in str(other.get("detect")), other["key"]
    assert entry["detect"]["urlIncludes"] == ["1.115689"]


def test_slot_index_dung_thu_tu_dom_cua_33_o_upload():
    html_file = _attach_html()
    if html_file is None:
        return
    html = html_file.read_text(encoding="utf-8", errors="replace")
    postnames = []
    for tag in re.findall(r"<input\b[^>]*>", html):
        if 'type="file"' not in tag:
            continue
        found = re.search(r'postname="([^"]*)"', tag)
        postnames.append(found.group(1) if found else "")
    if not postnames:
        return

    assert len(postnames) == 33
    # Thứ tự DOM thật của cổng (id thành phần do cổng sinh, chỉ thứ tự là ổn định).
    assert postnames[1].endswith("49826_fileGiayTo")   # Đơn Mẫu 21 — nhóm a
    assert postnames[9].endswith("49852_fileGiayTo")   # Mảnh trích đo — nhóm a
    assert postnames[18].endswith("49850_fileGiayTo")  # Đơn Mẫu 21 — nhóm b
    assert postnames[27].endswith("49872_fileGiayTo")  # Đơn Mẫu 21 — nhóm c
    assert postnames[28].endswith("49870_fileGiayTo")  # Thông báo xác nhận kết quả
    assert postnames[29] == "HoSoOnline_giayToKhac_file_1"


def test_ba_dong_don_mau_21_trung_ten_nen_phai_di_bang_slot_index():
    assert planner._ROUTES["don_mau_21"] == {"a": 1, "b": 18, "c": 27}
    for slot in (1, 18, 27):
        assert "Mẫu số 21" in planner._SLOT_NAMES[slot]
    items, _, _ = planner.build_plan_items(_files(["don.pdf"]), {0: ("don_mau_21", [])})
    assert items[0]["slotIndex"] == 1


def test_ho_so_mau_hs1_len_dung_dong():
    """HS1 Bùi Thị Hải: đơn + mảnh trích đo thật."""
    items, warnings, _ = planner.build_plan_items(
        _files(["don_bui_thi_hai.pdf", "trich_luc_bui_thi_hai.pdf"]),
        {0: ("don_mau_21", []), 1: ("manh_trich_do", [])},
    )

    assert [i["slotIndex"] for i in items] == [1, 9]
    assert any("NHÓM A)" in w for w in warnings)
    assert not any("ĐÍNH KÈM THAY THẾ" in w for w in warnings)


def test_ho_so_mau_hs2_ban_mo_ta_ranh_gioi_dinh_thay_the_va_bat_buoc_ghi_chu():
    """HS2 Nguyễn Công Hoan: tệp tên 'trich_luc_…' thực chất là Bản mô tả ranh giới (Phụ lục 12)."""
    items, warnings, classified = planner.build_plan_items(
        _files(["don_nguyen_cong_hoan.pdf", "trich_luc_nguyen_cong_hoan.pdf"]),
        {0: ("don_mau_21", []), 1: ("ban_mo_ta_ranh_gioi", [])},
    )

    assert [i["slotIndex"] for i in items] == [1, 9]
    # Giữ TÊN THẬT của giấy tờ để cán bộ biết dòng đó là tệp thay thế.
    assert items[1]["documentName"] == "Bản mô tả ranh giới, mốc giới thửa đất"
    assert classified[1]["assignedType"] == "ban_mo_ta_ranh_gioi"
    assert any("ĐÍNH KÈM THAY THẾ" in w and "Ghi chú" in w for w in warnings)


def test_co_thong_bao_ket_qua_thi_xep_nhom_c():
    items, warnings, classified = planner.build_plan_items(
        _files(["don.pdf", "thong_bao.pdf"]),
        {0: ("don_mau_21", []), 1: ("thong_bao_ket_qua_dang_ky", [])},
    )

    assert [i["slotIndex"] for i in items] == [27, 28]
    assert all(c["nhom"] == "c" for c in classified)
    assert any("NHÓM C)" in w for w in warnings)


def test_khong_tu_chon_nhom_b_nhung_luon_nhac_can_bo():
    """Không giấy tờ nào chứng minh 'người gốc Việt định cư ở nước ngoài' → không đoán, chỉ cảnh báo."""
    _, warnings, classified = planner.build_plan_items(_files(["don.pdf"]), {0: ("don_mau_21", [])})

    assert classified[0]["nhom"] == "a"
    assert any("NGƯỜI GỐC VIỆT NAM ĐỊNH CƯ Ở NƯỚC NGOÀI" in w for w in warnings)


def test_loai_giay_to_khong_co_dong_trong_nhom_dang_chon_van_duoc_dinh():
    """Nhóm c chỉ có 2 dòng — giấy tờ khác vẫn phải lên hồ sơ qua 'Giấy tờ khác'."""
    items, warnings, _ = planner.build_plan_items(
        _files(["thong_bao.pdf", "trich_do.pdf"]),
        {0: ("thong_bao_ket_qua_dang_ky", []), 1: ("manh_trich_do", [])},
    )

    assert items[0]["slotIndex"] == 28
    assert items[1]["target"] == "new"
    assert items[1]["needsAddComponent"] is True
    assert any("không bỏ sót" in w for w in warnings)


def test_moi_tep_chi_mot_dong_va_uu_tien_don_mau_21():
    items, _, classified = planner.build_plan_items(
        _files(["gop.pdf"]), {0: ("manh_trich_do", ["don_mau_21", "giay_to_dieu_137"])}
    )

    assert len(items) == 1
    assert items[0]["slotIndex"] == 1
    assert classified[0]["assignedType"] == "don_mau_21"


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {})

    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(i["target"] == "new" for i in items)
    assert all(c["source"] == "default" for c in classified)
    assert warnings


def test_slot_key_khong_trung_keyword_cua_extension():
    content = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "content.js"
    if not content.exists():
        return
    block = content.read_text(encoding="utf-8").split("FIXED_SLOT_KEYWORDS = {", 1)[1].split("};", 1)[0]
    assert "laocai_lda_" not in block


def test_khong_ghi_de_o_ve_viec():
    """Nghiệp vụ chốt GIỮ NGUYÊN nội dung cổng điền sẵn — khác 3 thủ tục Lào Cai trước."""
    assert "HoSoOnline_veViec" not in UI_COMP_BY_NAME
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "BÙI THỊ HẢI"},
        {"name": "ThuaDat_SoThua", "value": "401"},
    ])
    assert "HoSoOnline_veViec" not in _values(fields)


def test_ghi_chu_mo_ta_ho_so_tu_don_va_thua_dat():
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "BÙI THỊ HẢI"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "015174011059"},
        {"name": "ThuaDat_SoThua", "value": "401"},
        {"name": "ThuaDat_ToBanDo", "value": "27"},
        {"name": "ThuaDat_DienTich", "value": "250,0 m²"},
        {"name": "ThuaDat_DiaChi",
         "value": {"tinh": "Lào Cai", "xa": "Xã Yên Bình", "diaChi": "Thôn Đào Kiều"}},
    ])
    ghi_chu = _values(fields)["HoSoOnline_ghiChu"]

    assert "BÙI THỊ HẢI" in ghi_chu
    assert "thửa đất số 401" in ghi_chu and "tờ bản đồ 27" in ghi_chu
    assert "Xã Yên Bình" in ghi_chu


def test_ghi_chu_khong_bia_khi_thieu_thua_dat():
    fields, _ = mapper.enrich([{"name": "ChuHoSo_HoTen", "value": "BÙI THỊ HẢI"}])
    assert "HoSoOnline_ghiChu" not in _values(fields)


def test_khong_bia_ngay_sinh_khi_don_chi_ghi_nam():
    """Đơn Mẫu 21 chỉ ghi 'năm sinh 1974' — không được thành 01/01/1974."""
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "BÙI THỊ HẢI"},
        {"name": "ChuHoSo_NgaySinh", "value": "1974"},
    ])
    assert "ChuHoSo_ngaySinhChuHoSo" not in _values(fields)


def test_o_ghi_chu_co_that_tren_trang_dinh_kem():
    html_file = _attach_html()
    if html_file is None:
        return
    html = html_file.read_text(encoding="utf-8", errors="replace")
    assert 'name="HoSoOnline_ghiChu"' in html
    assert 'name="HoSoOnline_veViec"' in html  # có thật nhưng cố ý không điền


def test_prompt_phan_biet_ban_mo_ta_ranh_gioi_voi_manh_trich_do():
    from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai.attach.prompt import SYSTEM_PROMPT

    assert "BẢN MÔ TẢ RANH GIỚI ≠ MẢNH TRÍCH ĐO" in SYSTEM_PROMPT
    assert "VN-2000" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG BỎ SÓT" in SYSTEM_PROMPT
