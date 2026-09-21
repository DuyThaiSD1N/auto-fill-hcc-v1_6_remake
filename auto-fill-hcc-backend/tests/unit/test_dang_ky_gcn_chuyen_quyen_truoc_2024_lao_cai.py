"""[Lào Cai] Đăng ký, cấp GCN khi đã chuyển quyền SDĐ trước 01/8/2024 (1.115666).

Khoá 3 điều dễ vỡ: 2 dòng "Đơn Mẫu 24" trùng tên nên phải đi bằng slotIndex; hai trường hợp a)/b) loại
trừ nhau; giấy tờ lạ phải đi đường "Giấy tờ khác" để engine điền TÊN tài liệu.
"""

import re
from pathlib import Path

from app.pipelines.dang_ky_gcn_chuyen_quyen_truoc_2024_lao_cai.attach import planner
from app.pipelines.dang_ky_gcn_chuyen_quyen_truoc_2024_lao_cai.process import mapper
from app.pipelines.dang_ky_gcn_chuyen_quyen_truoc_2024_lao_cai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import public_list

_KEY = "dang-ky-gcn-chuyen-quyen-truoc-2024-lao-cai"
_THONGTIN = Path(__file__).resolve().parents[2].parent / "thongtin"


def _dir():
    for d in _THONGTIN.glob("153-*"):
        return d
    return None


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _entry():
    return next(p for p in public_list() if p["key"] == _KEY)


def test_registry_co_buoc_dinh_kem_va_khoa_dung_ma_thu_tuc():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["laocai.gov.vn"]
    assert entry["detect"]["urlIncludes"] == ["1.115666"]
    assert entry["label"].startswith("[Tỉnh Lào Cai]")


def test_detect_khoa_bang_ma_thu_tuc_trong_van_ban_trang():
    """Mã nằm ở TIÊU ĐỀ trang chứ không có trong URL → phải khoá ở textIncludes."""
    assert "1.115666" in _entry()["detect"]["textIncludes"]


def test_duong_dan_cong_lao_cai_chi_gioi_han_pham_vi_khong_tu_nhan_dien():
    """URL bước nộp dùng chung cho mọi thủ tục Lào Cai → để trong urlIncludes là cướp trang."""
    detect = _entry()["detect"]
    url_buoc_nop = "dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so"
    assert any(url_buoc_nop.startswith(scope) or scope in url_buoc_nop for scope in detect["urlScope"])
    assert all(u not in url_buoc_nop for u in detect["urlIncludes"])


def test_detect_khong_lan_voi_thu_tuc_1_115667():
    """1.115667 cũng là 'đăng ký, cấp GCN cho người nhận chuyển nhượng' — cụm phải tách được."""
    cum = next(t for t in _entry()["detect"]["textIncludes"] if "chuyển quyền" in t).lower()
    body_1115667 = (
        "đăng ký, cấp giấy chứng nhận quyền sử dụng đất … cho người nhận chuyển nhượng quyền sử dụng "
        "đất, quyền sở hữu nhà ở, công trình xây dựng trong dự án bất động sản"
    )
    assert cum not in body_1115667


def test_moi_cum_detect_co_that_trong_van_ban_hien_thi_cua_snapshot():
    """textIncludes phải khớp ĐỦ (AND) — cụm nào không hiện trên trang là hỏng detect."""
    snapshot_dir = _dir()
    if snapshot_dir is None:
        return
    for html_file in snapshot_dir.glob("*.html"):
        html = html_file.read_text(encoding="utf-8", errors="replace")
        html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
        text = re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", html)).lower()
        for phrase in _entry()["detect"]["textIncludes"]:
            assert phrase.lower() in text, (html_file.name, phrase)


def test_slot_index_dung_thu_tu_dom_cua_11_o_upload():
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
    # Thứ tự DOM thật của cổng.
    assert postnames[1].endswith("50012_fileGiayTo")   # Đơn Mẫu 24 nhánh a
    assert postnames[2].endswith("50005_fileGiayTo")   # Hợp đồng/văn bản chuyển quyền
    assert postnames[4].endswith("50014_fileGiayTo")   # Đơn Mẫu 24 nhánh b
    assert postnames[5].endswith("50006_fileGiayTo")   # Bản gốc GCN
    assert postnames[6].endswith("50007_fileGiayTo")   # Giấy tờ chuyển quyền có chữ ký
    assert postnames[7] == "HoSoOnline_giayToKhac_file_1"


def test_hai_dong_don_mau_24_trung_ten_nen_phai_di_bang_slot_index():
    """slot 1 và slot 4 cùng tên 'Đơn đăng ký biến động … Mẫu số 24' → khớp text là không thể."""
    assert planner._ROUTES["don_mau_24"] == {"a": 1, "b": 4}
    assert "Mẫu số 24" in planner._SLOT_NAMES[1]
    assert "Mẫu số 24" in planner._SLOT_NAMES[4]
    items, _, _ = planner.build_plan_items(_files(["don.pdf"]), {0: "don_mau_24"})
    assert items[0]["slotIndex"] is not None


def test_co_van_ban_chuyen_quyen_thi_xep_nhanh_a():
    """Hồ sơ mẫu của BA: có giấy bán nhượng → trường hợp a)."""
    items, warnings, classified = planner.build_plan_items(
        _files(["don.pdf", "giay_ban.pdf", "gcn.pdf"]),
        {0: "don_mau_24", 1: "van_ban_chuyen_quyen", 2: "gcn_ban_goc"},
    )

    by_file = {i["fileName"]: i["slotIndex"] for i in items}
    assert by_file == {"don.pdf": 1, "giay_ban.pdf": 2, "gcn.pdf": 5}
    assert all(c["nhanh"] == "a" for c in classified)
    assert any("TRƯỜNG HỢP A)" in w and "LOẠI TRỪ NHAU" in w for w in warnings)


def test_khong_co_van_ban_chuyen_quyen_thi_xep_nhanh_b():
    items, warnings, _ = planner.build_plan_items(
        _files(["don.pdf", "gcn.pdf"]), {0: "don_mau_24", 1: "gcn_ban_goc"}
    )

    by_file = {i["fileName"]: i["slotIndex"] for i in items}
    assert by_file == {"don.pdf": 4, "gcn.pdf": 5}
    assert any("TRƯỜNG HỢP B)" in w for w in warnings)


def test_giay_to_la_di_duong_giay_to_khac_co_ten_tai_lieu():
    """Yêu cầu nghiệp vụ: đính ở 'giấy tờ khác' PHẢI có tên tài liệu → target 'new'."""
    items, warnings, _ = planner.build_plan_items(
        _files(["To_khai_thue_TNCN.pdf"]), {0: "other"}
    )

    item = items[0]
    assert item["target"] == "new"
    assert item["needsAddComponent"] is True
    assert "slotIndex" not in item
    assert item["componentName"] == "To khai thue TNCN"
    assert item["documentName"] == item["componentName"]
    assert any("không bỏ sót" in w for w in warnings)


def test_nhieu_tep_cung_mot_dong_thi_canh_bao_kiem_trung():
    """Hồ sơ mẫu có 2 tệp giấy bán nhượng TRÙNG NỘI DUNG 100%."""
    items, warnings, _ = planner.build_plan_items(
        _files(["ban_1.pdf", "ban_2.pdf"]),
        {0: "van_ban_chuyen_quyen", 1: "van_ban_chuyen_quyen"},
    )

    assert [i["slotIndex"] for i in items] == [2, 2]
    assert any("trùng nội dung" in w for w in warnings)


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
    assert "laocai_cq2024_" not in block


def test_ve_viec_ghi_de_bang_noi_dung_that_cua_don():
    fields, _ = mapper.enrich([
        {"name": "ThuaDat_SoThua", "value": "43"},
        {"name": "ThuaDat_ToBanDo", "value": "10-21"},
        {"name": "ThuaDat_DiaChi",
         "value": {"tinh": "Lào Cai", "xa": "Xã Gia Phú", "diaChi": "Thôn Hùng Thắng"}},
    ])
    ve_viec = {f["name"]: f["value"] for f in fields}["HoSoOnline_veViec"]

    assert "thửa 43" in ve_viec and "tờ bản đồ 10-21" in ve_viec
    assert "Xã Gia Phú" in ve_viec


def test_ve_viec_khong_bia_khi_thieu_so_thua():
    fields, _ = mapper.enrich([{"name": "ChuHoSo_HoTen", "value": "NGÔ HỒNG HẢI"}])
    assert "HoSoOnline_veViec" not in {f["name"] for f in fields}


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


def test_prompt_co_bay_gcn_mang_ten_ben_chuyen_quyen():
    from app.pipelines.dang_ky_gcn_chuyen_quyen_truoc_2024_lao_cai.attach.prompt import SYSTEM_PROMPT

    assert "GIẤY CHỨNG NHẬN MANG TÊN NGƯỜI KHÁC LÀ BÌNH THƯỜNG" in SYSTEM_PROMPT
    assert "GIẤY TỜ CHUYỂN QUYỀN VIẾT TAY VẪN LÀ" in SYSTEM_PROMPT
    assert "Mẫu số 39" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG BỎ SÓT" in SYSTEM_PROMPT


def test_prompt_uu_tien_mau_24_o_bat_ky_trang_nao_cua_tep_gop():
    """Tệp Đơn của hồ sơ thật có Mẫu 39 ở TRANG ĐẦU, Mẫu 24 ở trang 2 — phân theo trang đầu là
    đẩy Đơn bắt buộc sang 'Giấy tờ khác'."""
    from app.pipelines.dang_ky_gcn_chuyen_quyen_truoc_2024_lao_cai.attach.prompt import SYSTEM_PROMPT

    assert "BẤT KỲ trang nào" in SYSTEM_PROMPT
    assert "chỉ trả \"other\"\nkhi tệp CHỈ có Mẫu 39" in SYSTEM_PROMPT
