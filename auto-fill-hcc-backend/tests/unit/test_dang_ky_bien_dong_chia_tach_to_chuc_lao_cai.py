"""[Lào Cai] Đăng ký biến động do chia/tách/hợp nhất/sáp nhập tổ chức (1.115670).

Khoá 3 điều dễ vỡ: thứ tự 8 dòng thành phần hồ sơ (FE đi bằng slotIndex); một tệp scan GỘP phải được
đính vào nhiều dòng; chủ hồ sơ là tổ chức thì 7 ô cá nhân bị cổng ẩn nên không được phát.
"""

import re
from pathlib import Path

from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.attach import planner
from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.process import mapper
from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.process.schema import (
    UI_CHU_HO_SO_CA_NHAN,
    UI_COMP_BY_NAME,
)
from app.procedures.registry import public_list

_KEY = "dang-ky-bien-dong-chia-tach-to-chuc-lao-cai"
_THONGTIN = Path(__file__).resolve().parents[2].parent / "thongtin"


def _dir():
    for d in _THONGTIN.glob("154-*"):
        return d
    return None


def _visible_text(path: Path) -> str:
    html = path.read_text(encoding="utf-8", errors="replace")
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", html)).lower()


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _entry():
    return next(p for p in public_list() if p["key"] == _KEY)


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_registry_co_buoc_dinh_kem_va_khoa_dung_ma_thu_tuc():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["laocai.gov.vn"]
    assert entry["detect"]["urlIncludes"] == ["1.115670"]
    assert "1.115670" in entry["detect"]["textIncludes"]
    assert entry["label"].startswith("[Tỉnh Lào Cai]")


def test_moi_cum_detect_co_that_trong_van_ban_hien_thi_cua_snapshot():
    """textIncludes khớp ĐỦ (AND) — cụm nào không hiện trên trang là hỏng detect."""
    snapshot_dir = _dir()
    if snapshot_dir is None:
        return
    for html_file in snapshot_dir.glob("*.html"):
        text = _visible_text(html_file)
        for phrase in _entry()["detect"]["textIncludes"]:
            assert phrase.lower() in text, (html_file.name, phrase)


def test_slot_index_dung_thu_tu_dom_cua_12_o_upload():
    snapshot_dir = _dir()
    if snapshot_dir is None:
        return
    html_files = list(snapshot_dir.glob("*ính*.html"))
    if not html_files:
        return
    html = html_files[0].read_text(encoding="utf-8", errors="replace")
    postnames = re.findall(r'<input[^>]*type="file"[^>]*postname="([^"]*)"', html)
    if not postnames:
        return
    # Thứ tự DOM thật của cổng — id thành phần hồ sơ do cổng sinh, chỉ thứ tự là ổn định.
    assert postnames[0].endswith("50001_fileGiayTo")   # QĐ phê duyệt điều chỉnh quy hoạch
    assert postnames[1].endswith("49996_fileGiayTo")   # ĐKDN / văn bản thành lập tổ chức
    assert postnames[2].endswith("49999_fileGiayTo")   # Mảnh trích đo
    assert postnames[3].endswith("49987_fileGiayTo")   # QĐ chia/tách/sáp nhập
    assert postnames[4].endswith("50000_fileGiayTo")   # Văn bản đại diện
    assert postnames[5].endswith("49986_fileGiayTo")   # Giấy chứng nhận đã cấp
    assert postnames[6].endswith("49995_fileGiayTo")   # Đơn Mẫu 24
    assert postnames[7].endswith("49998_fileGiayTo")   # Bản vẽ tách/hợp thửa Mẫu 28
    assert postnames[8] == "HoSoOnline_giayToKhac_file_1"


def test_ho_so_mau_cua_ba_len_dung_dong():
    """Hồ sơ thật (trace req_5197677a56d9): 1 tệp Đơn 1 trang + 2 bản scan gộp 16 trang TRÙNG NỘI DUNG.

    LLM trả docType chính = don_mau_24 cho cả ba vì tệp gộp cũng mở đầu bằng Đơn. Phân bổ phủ dòng
    phải ra đúng ánh xạ tay của cán bộ: Đơn → QĐ chia/tách → Giấy chứng nhận.
    """
    items, warnings, classified = planner.build_plan_items(
        _files(["don_ms24.pdf", "scan_gop_a.pdf", "scan_gop_b.pdf"]),
        {
            0: ("don_mau_24", []),
            1: ("don_mau_24", ["qd_chia_tach_sap_nhap", "gcn_da_cap"]),
            2: ("don_mau_24", ["qd_chia_tach_sap_nhap", "van_ban_thanh_lap_to_chuc", "gcn_da_cap"]),
        },
    )

    assert len(items) == 3, "mỗi tệp chỉ được đính vào MỘT dòng"
    assert [i["slotIndex"] for i in items] == [6, 3, 5]
    assert [c["assignedType"] for c in classified] == [
        "don_mau_24", "qd_chia_tach_sap_nhap", "gcn_da_cap",
    ]
    # Dòng "văn bản thành lập tổ chức" còn trống nhưng nằm trong bản scan gộp → chỉ gợi ý.
    assert any("chưa có tệp" in w and "thành lập tổ chức" in w for w in warnings)


def test_mot_tep_khong_bi_nhan_ban_ra_moi_dong_no_chua():
    """Lỗi cũ: alsoTypes sinh thêm dòng → 3 tệp thành 13 lượt đính."""
    items, _, _ = planner.build_plan_items(
        _files(["scan_gop.pdf"]),
        {0: ("don_mau_24", ["qd_chia_tach_sap_nhap", "gcn_da_cap", "van_ban_thanh_lap_to_chuc"])},
    )

    assert len(items) == 1
    assert items[0]["slotIndex"] == 6
    assert items[0]["slotKey"] == "laocai_bdtc_don_mau_24"


def test_het_dong_trong_thi_ve_lai_dong_cua_doc_type_chinh():
    items, warnings, _ = planner.build_plan_items(
        _files(["a.pdf", "b.pdf"]), {0: ("gcn_da_cap", []), 1: ("gcn_da_cap", [])}
    )

    assert [i["slotIndex"] for i in items] == [5, 5]
    assert any("2 tệp" in w for w in warnings)


def test_also_types_bo_loai_trung_va_loai_khong_hop_le():
    items, _, classified = planner.build_plan_items(
        _files(["scan.pdf"]), {0: ("gcn_da_cap", ["gcn_da_cap", "other", "khong_ton_tai"])}
    )

    assert len(items) == 1
    assert classified[0]["alsoTypes"] == []


def test_giay_to_la_di_duong_giay_to_khac_co_ten_tai_lieu():
    """Đính ở 'giấy tờ khác' phải có tên tài liệu → target 'new' cho engine otherListFile."""
    items, warnings, _ = planner.build_plan_items(_files(["Ban_do_dia_chinh.pdf"]), {0: ("other", [])})

    item = items[0]
    assert item["target"] == "new"
    assert item["needsAddComponent"] is True
    assert "slotIndex" not in item
    assert item["componentName"] == "Ban do dia chinh"
    assert any("không bỏ sót" in w for w in warnings)


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {})

    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(i["target"] == "new" for i in items)
    assert all(c["source"] == "default" for c in classified)
    assert warnings


def test_slot_key_khong_trung_keyword_cua_extension():
    content = (
        Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "content.js"
    )
    if not content.exists():
        return
    block = content.read_text(encoding="utf-8").split("FIXED_SLOT_KEYWORDS = {", 1)[1].split("};", 1)[0]
    assert "laocai_bdtc_" not in block


def test_chu_ho_so_to_chuc_khong_phat_7_o_ca_nhan():
    """Chọn đối tượng 'Tổ chức' là cổng display:none 7 ô cá nhân của khối chủ hồ sơ."""
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "Trung tâm Dịch vụ tổng hợp xã Yên Bình"},
        {"name": "ChuHoSo_HoTen", "value": "KIỀU THỊ MƯỜI"},
        {"name": "ChuHoSo_NgaySinh", "value": "10/02/1980"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "001180000000"},
    ])
    values = _values(fields)

    assert values["ChuHoSo_maDoiTuongNopHS"] == "Tổ chức"
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "Trung tâm Dịch vụ tổng hợp xã Yên Bình"
    for name in UI_CHU_HO_SO_CA_NHAN:
        assert name not in values, name


def test_chu_ho_so_ca_nhan_van_phat_du_o_ca_nhan():
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_LaToChuc", "value": False},
        {"name": "ChuHoSo_HoTen", "value": "NGÔ HỒNG HẢI"},
        {"name": "ChuHoSo_NgaySinh", "value": "12/03/1970"},
    ])
    values = _values(fields)

    assert values["ChuHoSo_maDoiTuongNopHS"] == "Cá nhân"
    assert values["ChuHoSo_tenChuHoSo"] == "NGÔ HỒNG HẢI"
    assert values["ChuHoSo_ngaySinhChuHoSo"] == "12/03/1970"


def test_to_chuc_thieu_ten_thi_canh_bao_chu_khong_lay_ten_tren_gcn():
    _, warnings = mapper.enrich([
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ToChucCu_Ten", "value": "Đài Truyền thanh huyện Yên Bình"},
    ])

    assert any("Tên cơ quan/tổ chức" in w for w in warnings)


def test_ve_viec_ghi_de_bang_noi_dung_that_cua_don():
    fields, _ = mapper.enrich([
        {"name": "Don_NoiDungBienDong", "value": "sáp nhập tổ chức, thay đổi người sử dụng đất"},
        {"name": "ThuaDat_SoThua", "value": "1"},
        {"name": "ThuaDat_ToBanDo", "value": "32"},
        {"name": "ThuaDat_DiaChi", "value": {"tinh": "Lào Cai", "xa": "Xã Yên Bình", "diaChi": "Tổ 10"}},
    ])
    ve_viec = _values(fields)["HoSoOnline_veViec"]

    assert "sáp nhập tổ chức" in ve_viec
    assert "thửa 1" in ve_viec and "tờ bản đồ 32" in ve_viec
    assert "Xã Yên Bình" in ve_viec


def test_ve_viec_khong_bia_khi_thieu_so_thua():
    fields, _ = mapper.enrich([{"name": "ChuHoSo_TenToChuc", "value": "Trung tâm A"}])
    assert "HoSoOnline_veViec" not in _values(fields)


def test_o_ve_viec_ghi_chu_co_that_tren_trang():
    for name in ("HoSoOnline_veViec", "HoSoOnline_ghiChu"):
        assert name in UI_COMP_BY_NAME, name
    snapshot_dir = _dir()
    if snapshot_dir is None:
        return
    html_files = list(snapshot_dir.glob("*ính*.html"))
    if not html_files:
        return
    html = html_files[0].read_text(encoding="utf-8", errors="replace")
    for name in ("HoSoOnline_veViec", "HoSoOnline_ghiChu"):
        assert f'name="{name}"' in html, name


def test_o_fill_khai_trong_schema_deu_co_that_tren_trang_fill():
    snapshot_dir = _dir()
    if snapshot_dir is None:
        return
    html_files = [f for f in snapshot_dir.glob("*.html") if "ính" not in f.name]
    if not html_files:
        return
    html = html_files[0].read_text(encoding="utf-8", errors="replace")
    for name in UI_COMP_BY_NAME:
        if name.startswith("HoSoOnline_"):
            continue  # 2 textarea nằm ở trang đính kèm.
        assert f'name="{name}"' in html, name


def test_prompt_chan_also_types_cho_giay_to_chi_duoc_nhac_toi():
    """Tệp Đơn 1 trang từng bị gán 3 alsoTypes vì mục 3 của Đơn liệt kê giấy tờ nộp kèm."""
    from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.attach.prompt import SYSTEM_PROMPT

    assert "CHỈ RA ĐƯỢC TRANG" in SYSTEM_PROMPT
    assert "MỘT TỜ/MỘT TRANG" in SYSTEM_PROMPT
    assert "Đó là DANH MỤC, không phải nội dung tệp" in SYSTEM_PROMPT


def test_prompt_co_bay_tep_gop_va_don_vi_su_nghiep():
    from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.attach.prompt import SYSTEM_PROMPT

    assert "alsoTypes" in SYSTEM_PROMPT
    assert "ĐƠN VỊ SỰ NGHIỆP CÔNG LẬP KHÔNG CÓ GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP" in SYSTEM_PROMPT
    assert "BẢN ĐỒ ĐỊA CHÍNH KHU ĐẤT ≠ MẢNH TRÍCH ĐO" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG BỎ SÓT" in SYSTEM_PROMPT
