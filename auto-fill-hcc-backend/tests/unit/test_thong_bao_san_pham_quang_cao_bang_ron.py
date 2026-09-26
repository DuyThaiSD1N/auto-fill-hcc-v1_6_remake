"""[Bộ VHTTDL] Thủ tục tiếp nhận hồ sơ thông báo sản phẩm quảng cáo trên bảng quảng cáo, băng-rôn (1.004650).

Khoá: mọi (section, mat-label) có thật trên trang; không điền khối người nộp; khối ủy quyền = doanh nghiệp
và TÍCH ô "Thông tin người ủy quyền" trước; 7 dòng đính kèm theo BA, không bỏ sót tệp.
"""

import re
from pathlib import Path

from app.pipelines.thong_bao_san_pham_quang_cao_bang_ron.attach import planner
from app.pipelines.thong_bao_san_pham_quang_cao_bang_ron.process import mapper
from app.pipelines.thong_bao_san_pham_quang_cao_bang_ron.process.schema import S_TB, S_UQ, UI_FIELDS
from app.procedures.registry import public_list

_KEY = "thong-bao-san-pham-quang-cao-bang-ron"
_ROOT = Path(__file__).resolve().parents[2].parent


def _snapshot() -> Path | None:
    for d in (_ROOT / "thongtin").glob("179-*"):
        for f in d.glob("*.html"):
            return f
    return None


def _fold(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _facts():
    return {
        "DoanhNghiep_Ten": "CÔNG TY TNHH MẪU A",
        "DoanhNghiep_MaSo": "3100000001",
        "DoanhNghiep_NgayCap": "05/03/2026",
        "DoanhNghiep_NoiCap": "Phòng Đăng ký kinh doanh - Sở Tài chính tỉnh Quảng Trị",
        "DoanhNghiep_DienThoai": "0900000001",
        "DoanhNghiep_TruSo": {"tinh": "Tỉnh Quảng Trị", "xa": "Xã Lệ Thủy", "diaChi": "Thôn Mẫu"},
        "ThongBao_NoiDung": "Khuyến mại mẫu",
        "ThongBao_DiaDiem": "Xã Lệ Thủy, tỉnh Quảng Trị",
        "ThongBao_TuNgay": "03/07/2026",
        "ThongBao_DenNgay": "12/07/2026",
        "ThongBao_SoLuong": "Băng rôn dọc: 30 tấm\nBăng rôn ngang: 10 tấm",
        "ThongBao_PhuongAnThaoDo": "Tháo dỡ khi hết thời gian",
    }


def _run(values):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()])
    return fields, warnings


def _ui(fields):
    return {(f["section"], f["name"]): f["value"] for f in fields}


def test_registry_detect_theo_ma_va_co_buoc_dinh_kem():
    entry = next(p for p in public_list() if p["key"] == _KEY)
    assert entry["detect"] == {"urlScope": ["dichvucong.bvhttdl.gov.vn"], "urlIncludes": ["matthc=1.004650"]}
    assert entry["mode"] == "agent" and entry["hasAttachmentStep"] is True


def test_moi_o_khai_trong_schema_deu_co_that_tren_trang():
    html_file = _snapshot()
    if html_file is None:
        return
    html = html_file.read_text(encoding="utf-8", errors="replace")
    labels = {_fold(re.sub(r"(?s)<[^>]+>", " ", m)) for m in re.findall(r"(?s)<mat-label[^>]*>(.*?)</mat-label>", html)}
    headers = {
        _fold(re.sub(r"(?s)<[^>]+>", " ", m))
        for m in re.findall(r'(?s)<[^>]*class="[^"]*group-header[^"]*"[^>]*>(.*?)</div>', html)
    }
    for section, label, _comp in UI_FIELDS:
        assert _fold(label) in labels, label
        assert any(_fold(section) in h or h in _fold(section) for h in headers), section
    assert "Thông tin người ủy quyền" in html  # nhãn ô tích bật khối ủy quyền


def test_tich_o_uy_quyen_truoc_roi_dien_doanh_nghiep_khong_dien_nguoi_nop():
    fields, _ = _run(_facts())
    assert fields[0] == {"name": "Thông tin người ủy quyền", "comp": "liz-checkbox", "value": True, "section": ""}
    ui = _ui(fields)
    assert ui[(S_UQ, "Tên người / Tên đơn vị ủy quyền")] == "CÔNG TY TNHH MẪU A"
    assert ui[(S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp")] == "3100000001"
    assert ui[(S_UQ, "Địa chỉ hành chính")] == "Xã Lệ Thủy, Tỉnh Quảng Trị"
    assert ui[(S_UQ, "Địa chỉ chi tiết")] == "Thôn Mẫu"
    assert not any("người nộp" in f["section"].lower() for f in fields)


def test_khoi_thong_bao_va_so_luong_noi_thanh_mot_dong():
    ui = _ui(_run(_facts())[0])
    assert ui[(S_TB, "Số GPKD")] == "3100000001"
    assert ui[(S_TB, "Từ ngày thực hiện")] == "03/07/2026"
    assert ui[(S_TB, "Đến ngày thực hiện")] == "12/07/2026"
    assert ui[(S_TB, "Số lượng")] == "Băng rôn dọc: 30 tấm; Băng rôn ngang: 10 tấm"


def test_noi_dung_chi_lay_dong_muc_2_bo_dia_diem_kinh_doanh_ben_duoi():
    values = {**_facts(), "ThongBao_NoiDung": "Khuyến mại mẫu, điện máy mẫu\nĐỊA ĐIỂM KD – CÔNG TY MẪU B\n"
                                              "1 Đường Mẫu, Phường Mẫu, Tỉnh Mẫu"}
    ui = _ui(_run(values)[0])
    assert ui[(S_TB, "Nội dung trên bảng quảng cáo, băng-rôn")] == "Khuyến mại mẫu, điện máy mẫu"


def test_so_bi_che_va_ngay_trong_khong_dien_ma_canh_bao():
    values = {**_facts(), "DoanhNghiep_MaSo": "310", "DoanhNghiep_DienThoai": "09",
              "ThongBao_TuNgay": "  /  /2026", "ThongBao_DenNgay": ""}
    fields, warnings = _run(values)
    ui = _ui(fields)
    assert (S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp") not in ui and (S_TB, "Số GPKD") not in ui
    assert (S_UQ, "Số điện thoại") not in ui and (S_TB, "Từ ngày thực hiện") not in ui
    assert any("Mã số doanh nghiệp" in w for w in warnings)
    assert any("thời gian thực hiện" in w for w in warnings)


def test_khong_co_ten_doanh_nghiep_thi_khong_tich_o_uy_quyen():
    values = {k: v for k, v in _facts().items() if k != "DoanhNghiep_Ten"}
    fields, warnings = _run(values)
    assert not any(f["comp"] == "liz-checkbox" for f in fields)
    assert not any(f["section"] == S_UQ for f in fields)
    assert any("Không tích" in w and "Tên đơn vị ủy quyền" in w for w in warnings)


def test_thieu_o_bat_buoc_cua_khoi_uy_quyen_thi_khong_tich():
    """Trace req_04699ba09c29: MST "310" và điện thoại "09" bị che → tích vào là cổng khoá nút nộp."""
    values = {**_facts(), "DoanhNghiep_MaSo": "310", "DoanhNghiep_DienThoai": "09"}
    fields, warnings = _run(values)
    assert not any(f["comp"] == "liz-checkbox" for f in fields)
    assert not any(f["section"] == S_UQ for f in fields)
    assert any("Mã số doanh nghiệp" in w and "Số điện thoại" in w and "Không tích" in w for w in warnings)


def test_bay_dong_dinh_kem_dung_thu_tu_dom_va_theo_ba():
    html_file = _snapshot()
    if html_file is not None:
        html = html_file.read_text(encoding="utf-8", errors="replace")
        assert len(re.findall(r"<app-upload-flie-multi", html)) == 7
    names = ["hopquy.pdf", "dkkd.pdf", "km.pdf", "maket.pdf", "phoicanh.pdf", "tokhai.pdf", "la.pdf"]
    types = {0: "hop_chuan_hop_quy", 1: "gcn_dang_ky_doanh_nghiep", 2: "thong_bao_khuyen_mai",
             3: "maket", 4: "phoi_canh", 5: "thong_bao_mau_01", 6: "other"}
    items, warnings, _ = planner.build_plan_items([{"name": n} for n in names], types)
    assert [i["slotIndex"] for i in items] == [0, 0, 0, 2, 4, 6, 6]
    assert all(i["target"] == "fixed-slot" for i in items)
    assert warnings and "la.pdf" in warnings[0]


def test_khong_bo_sot_file_khi_llm_chet():
    items, _, _ = planner.build_plan_items([{"name": "a.pdf"}, {"name": "b.pdf"}], {})
    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(i["slotIndex"] == 6 for i in items)


def test_slot_key_khong_trung_keyword_cua_extension():
    content = _ROOT / "auto-fill-hcc-extension" / "content.js"
    if not content.exists():
        return
    block = content.read_text(encoding="utf-8").split("FIXED_SLOT_KEYWORDS = {", 1)[1].split("};", 1)[0]
    assert "spqc_" not in block


def test_engine_liz_tich_duoc_o_checkbox():
    fill_liz = _ROOT / "auto-fill-hcc-extension" / "content" / "fill-liz.js"
    if not fill_liz.exists():
        return
    src = fill_liz.read_text(encoding="utf-8")
    assert 'f.comp === "liz-checkbox"' in src
    assert "input.checked !== want" in src, "chỉ bấm khi trạng thái khác — chạy lại không được bỏ tích"
    assert "index = buildIndex()" in src, "tích xong phải dựng lại chỉ mục cho khối vừa hiện"
    assert "if (sec) return null;" in src, "có section mà không thấy ô đúng khối thì KHÔNG khớp nhãn trần"
    click = src.index("input.click();")
    assert src.rindex("const before = visibleFields();", 0, click) < click, "đếm ô hiển thị TRƯỚC khi bấm"


def _fe_fold(text: str) -> str:
    """Bản Python của foldChoiceText (content.js): bỏ dấu, đ→d, mọi dấu gạch → khoảng trắng, gọn khoảng trắng."""
    import unicodedata

    text = str(text or "").replace("Đ", "D").replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s*[-‐-―]\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def test_moi_dong_dinh_kem_do_theo_chu_khop_dung_mot_dong_co_o_upload():
    """Engine dò ô theo (sectionHeader, slotKeywords) — keyword phải khớp ĐÚNG một dòng có ô upload."""
    html_file = _snapshot()
    if html_file is None:
        return
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_file.read_text(encoding="utf-8", errors="replace"), "html.parser")
    rows = soup.select("tr")
    header = _fe_fold(planner._BANG_HEADER)
    assert any(header in _fe_fold(r.get_text(" ")) for r in rows)
    upload_rows = [_fe_fold(r.get_text(" ")) for r in rows if r.select("app-upload-flie-multi")]
    assert len(upload_rows) == 7
    for slot, keywords in planner._SLOT_KEYWORDS.items():
        hits = [i for i, text in enumerate(upload_rows) if any(_fe_fold(k) in text for k in keywords)]
        assert hits == [slot], (slot, keywords, hits)


def test_cac_tep_cung_dong_chung_slot_key_de_engine_gom_mot_o():
    types = {0: "hop_chuan_hop_quy", 1: "gcn_dang_ky_doanh_nghiep", 2: "thong_bao_khuyen_mai"}
    items, _, _ = planner.build_plan_items([{"name": f"{i}.pdf"} for i in range(3)], types)
    assert {i["slotKey"] for i in items} == {"spqc_row_0"}
    assert all(i["sectionHeader"] == "Thành phần hồ sơ" and i["slotKeywords"] == ["hop chuan"] for i in items)
