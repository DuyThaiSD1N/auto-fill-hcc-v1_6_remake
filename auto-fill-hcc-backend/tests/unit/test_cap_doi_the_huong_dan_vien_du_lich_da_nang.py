"""[Đà Nẵng · Bộ VHTTDL] Cấp đổi thẻ hướng dẫn viên du lịch quốc tế, nội địa (1.001432, QT-113).

Khoá các điều dễ vỡ: nhận diện không lẫn với thẻ nội địa/tại điểm cùng cổng; Phần II chỉ điền khi CCCD tài
khoản trùng CCCD người đề nghị; "Ngày cấp/Nơi cấp" của Phần IV là của THẺ HDV cũ, không phải của CCCD; loại
thẻ đã được cấp tích đúng MỘT ô trong nhóm; hồ sơ nộp nhầm bộ cấp mới (Mẫu 04 + chứng chỉ + văn bằng) vẫn
đính kèm đủ tệp nhưng cảnh báo sai mẫu / thay thế / thiếu thẻ HDV.
"""

from pathlib import Path

from app.pipelines.cap_doi_the_huong_dan_vien_du_lich_da_nang.attach import planner
from app.pipelines.cap_doi_the_huong_dan_vien_du_lich_da_nang.process import mapper
from app.pipelines.cap_doi_the_huong_dan_vien_du_lich_da_nang.process.schema import (
    LABEL_LOAI_THE,
    LABEL_LY_DO,
    S_NOP,
    S_THE,
    UI_FIELDS,
)
from app.procedures import registry
from app.procedures.ke_khai_links import with_ke_khai_detect_urls

_KEY = "cap-doi-the-huong-dan-vien-du-lich-da-nang"
_TITLE = "qt-113 - thủ tục cấp đổi thẻ hướng dẫn viên du lịch quốc tế, thẻ hướng dẫn viên du lịch nội địa"
_EXTENSION = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension"

# Hồ sơ bịa — không dùng dữ liệu thật.
_CCCD = "048095012345"
_FACTS = {
    "NguoiDeNghi_HoTen": "Nguyễn Văn Minh",
    "NguoiDeNghi_NgaySinh": "3/4/1995",
    "NguoiDeNghi_GioiTinh": "Nam",
    "NguoiDeNghi_SoDinhDanh": _CCCD,
    "NguoiDeNghi_NgayCap": "15/06/2022",
    "NguoiDeNghi_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "NguoiDeNghi_DienThoai": "0905 111 222",
    "NguoiDeNghi_Email": "minh.nguyen@example.com",
    "NguoiDeNghi_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "25 Trần Phú"},
    "TheCu_SoThe": "Số/No.: 148123456",
    "TheCu_NgayCap": "20/10/2021",
    "TheCu_NoiCap": "Sở Du lịch thành phố Đà Nẵng",
    "TheCu_Loai": "Nội địa",
    "Don_LyDo": "Thẻ hết hạn sử dụng",
    "Don_LoaiDeNghi": "cấp đổi",
    "Don_CoQuanNhan": "Sở Văn hóa, Thể thao và Du lịch thành phố Đà Nẵng",
}


def _facts(**over):
    data = {**_FACTS, **over}
    return [{"name": k, "value": v} for k, v in data.items() if v is not None]


def _ui(fields):
    return {(f["section"], f["name"]): f["value"] for f in fields}


def _files(names, kind="application/pdf"):
    return [{"name": n, "type": kind} for n in names]


def _entry():
    return next(p for p in registry.PROCEDURES if p["key"] == _KEY)


# ---------------- registry / nhận diện ----------------

def test_registry_co_pipeline_process_va_dinh_kem():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["fillWithAttach"] is True
    assert _KEY in registry._PIPELINE
    assert _KEY in registry._ATTACH_PIPELINE


def test_ma_1_001432_duoc_ghep_tu_ke_khai_links():
    public = next(p for p in with_ke_khai_detect_urls(registry.PROCEDURES) if p["key"] == _KEY)
    assert "matthc=1.001432" in public["detect"]["urlIncludes"]


def test_cum_nhan_dien_khong_lan_voi_the_noi_dia_va_tai_diem():
    phrase = _entry()["detect"]["textIncludes"][0].lower()
    assert phrase in _TITLE
    for key in ("cap-the-huong-dan-vien-du-lich-noi-dia", "cap-the-huong-dan-vien-du-lich-tai-diem-da-nang"):
        other = next(p for p in registry.PROCEDURES if p["key"] == key)
        for other_phrase in other["detect"]["textIncludes"]:
            assert other_phrase.lower() not in _TITLE, key
    assert phrase not in "qt-121 - thủ tục cấp thẻ hướng dẫn viên du lịch nội địa"


# ---------------- process mapper ----------------

def test_tu_nop_dien_phan_nguoi_nop_va_the_da_cap():
    fields, warnings = mapper.enrich(_facts(), {"formContext": {"identityNumber": _CCCD}})
    ui = _ui(fields)

    assert ui[(S_NOP, "Ngày sinh")] == "03/04/1995"
    assert ui[(S_NOP, "Ngày cấp")] == "15/06/2022"
    assert ui[(S_NOP, "Số điện thoại")] == "0905111222"
    assert ui[(S_NOP, "Địa chỉ chi tiết")] == "25 Trần Phú"
    assert ui[(S_THE, "Giới tính")] == "Nam"
    assert ui[(S_THE, "Email")] == "minh.nguyen@example.com"
    assert ui[(S_THE, "Số thẻ")] == "148123456"
    assert ui[(S_THE, "Ngày cấp")] == "20/10/2021", "ngày cấp THẺ, không phải ngày cấp CCCD"
    assert ui[(S_THE, "Nơi cấp")] == "Sở Du lịch thành phố Đà Nẵng"
    assert ui[(S_THE, LABEL_LY_DO)] == "Thẻ hết hạn sử dụng"
    assert warnings == []


def test_loai_the_tich_dung_mot_o_trong_nhom():
    fields, _ = mapper.enrich(_facts(TheCu_Loai="INTERNATIONAL TOUR GUIDE"), {})
    boxes = [f for f in fields if f["comp"] == "liz-checkbox"]

    assert len(boxes) == 1
    assert boxes[0]["name"] == LABEL_LOAI_THE and boxes[0]["value"] is True
    assert boxes[0]["option"] == "Quốc tế"
    assert fields.index(boxes[0]) == 0, "tích trước để ô phụ thuộc kịp hiện"


def test_loai_the_mo_ho_thi_khong_tich_va_canh_bao():
    fields, warnings = mapper.enrich(_facts(TheCu_Loai="Nội địa Quốc tế Tại điểm"), {})
    assert not any(f["comp"] == "liz-checkbox" for f in fields)
    assert any("Chưa xác định được LOẠI THẺ" in w for w in warnings)


def test_cccd_tai_khoan_khac_thi_bo_phan_nguoi_nop():
    fields, warnings = mapper.enrich(_facts(), {"formContext": {"identityNumber": "001088000111"}})

    assert all(f["section"] == S_THE for f in fields)
    assert any("Không điền khối \"Thông tin người nộp hồ sơ\"" in w for w in warnings)


def test_moi_o_emit_deu_khai_trong_schema():
    fields, _ = mapper.enrich(_facts(), {"formContext": {"identityNumber": _CCCD}})
    khai = {(s, l) for s, l, _c, _a in UI_FIELDS}
    assert {(f["section"], f["name"]) for f in fields} <= khai


def test_ho_so_cap_moi_nop_nham_canh_bao_lech_thu_tuc():
    """Bộ cấp mới: Đơn Mẫu 04 + chứng chỉ nghiệp vụ, không có thẻ cũ → không bịa số thẻ/loại thẻ."""
    fields, warnings = mapper.enrich(
        _facts(
            Don_LoaiDeNghi="cấp mới", Don_LoaiTheDeNghi="nội địa", TheCu_SoThe=None, TheCu_NgayCap=None,
            TheCu_NoiCap=None, TheCu_Loai=None, Don_LyDo=None,
        ),
        {},
    )
    ui = _ui(fields)

    assert (S_THE, "Số thẻ") not in ui
    assert not any(f["comp"] == "liz-checkbox" for f in fields)
    assert any("LỆCH THỦ TỤC" in w and "NỘI ĐỊA" in w and "Mẫu số 05" in w for w in warnings)
    assert any("Chưa có SỐ THẺ" in w for w in warnings)


def test_so_hieu_chung_chi_khong_phai_so_the():
    fields, warnings = mapper.enrich(_facts(TheCu_SoThe="CMS./HDDLNĐ-0123"), {})
    assert (S_THE, "Số thẻ") not in _ui(fields)
    assert any("trông như số hiệu chứng chỉ" in w for w in warnings)


def test_don_cap_lai_va_the_tai_diem_deu_canh_bao():
    _, warnings = mapper.enrich(_facts(Don_LoaiDeNghi="cấp lại", TheCu_Loai="tại điểm"), {})
    assert any("CẤP LẠI" in w and "1.004614" in w for w in warnings)
    assert any("TẠI ĐIỂM" in w for w in warnings)


def test_don_gui_tinh_khac_thi_canh_bao_noi_tiep_nhan():
    _, warnings = mapper.enrich(_facts(Don_CoQuanNhan="Sở Văn hóa, Thể thao và Du lịch tỉnh Quảng Nam"), {})
    assert any("Kiểm tra lại nơi tiếp nhận" in w for w in warnings)


def test_ngay_cap_noi_cap_the_co_moc_vi_tri_sau_o_so_the():
    """Nhãn 2 ô này trên cổng chưa khớp được → engine rơi về ô ngày/chữ đầu tiên ngay sau ô Số thẻ."""
    fields, _ = mapper.enrich(_facts(), {})
    by_name = {f["name"]: f for f in fields if f["section"] == S_THE}

    for label in ("Ngày cấp", "Nơi cấp"):
        assert by_name[label]["after"][0] == "Số thẻ", label
    assert by_name["Ngày cấp"]["comp"] == "liz-date" and by_name["Nơi cấp"]["comp"] == "liz-input"
    assert "after" not in by_name["Số thẻ"]


def test_kinh_gui_con_nguyen_dong_in_san_khong_canh_bao_tinh_khac():
    _, warnings = mapper.enrich(
        _facts(Don_CoQuanNhan="Sở Du lịch/Sở Văn hóa, Thể thao và Du lịch tỉnh/thành phố"), {}
    )
    assert not any("Kiểm tra lại nơi tiếp nhận" in w for w in warnings)


def test_so_dinh_danh_bi_che_khong_dien_phan_nguoi_nop():
    fields, warnings = mapper.enrich(
        _facts(NguoiDeNghi_SoDinhDanh="0480", NguoiDeNghi_GioiTinh=None), {"formContext": {"identityNumber": _CCCD}}
    )
    assert (S_THE, "Giới tính") not in _ui(fields)
    assert all(f["section"] == S_THE for f in fields)
    assert any("chỉ đọc được \"0480\"" in w for w in warnings)


# ---------------- đính kèm ----------------

def test_du_bo_cap_doi_vao_dung_4_dong():
    items, warnings, _ = planner.build_plan_items(
        _files(["gcn.pdf", "the_hdv.jpg", "don_mau05.pdf"]) + _files(["anh_3x4.jpg"], "image/jpeg"),
        {0: ("gcn_cap_nhat_kien_thuc", []), 1: ("the_hdv", []), 2: ("don_cap_doi", []), 3: ("anh_chan_dung", [])},
    )

    assert [i["slotIndex"] for i in items] == [0, 1, 2, 3]
    assert [i["loaiBan"] for i in items] == ["Bản sao", "Bản chính", "Bản chính", "Bản chính"]
    assert warnings == []


def test_ho_so_cap_moi_nop_nham_van_dinh_du_tep():
    """Như ảnh ánh xạ: Đơn 04 → dòng (3) sai mẫu; chứng chỉ + văn bằng → CHUNG dòng (1) thay thế."""
    items, warnings, _ = planner.build_plan_items(
        _files(["01_Don.pdf", "02_Chung_chi.pdf", "03_Bang.pdf"]),
        {0: ("don_cap_moi", []), 1: ("chung_chi_nghiep_vu", []), 2: ("van_bang", [])},
    )

    assert [i["slotIndex"] for i in items] == [2, 0, 0]
    assert items[1]["slotKey"] == items[2]["slotKey"], "cùng slotKey để engine gom vào một input multiple"
    assert any("SAI MẪU ĐƠN" in w for w in warnings)
    assert any("THAY THẾ" in w and "khóa cập nhật" in w.lower() for w in warnings)
    assert any("Chưa có tệp THẺ HƯỚNG DẪN VIÊN" in w for w in warnings)
    assert any("Chưa thấy ẢNH CHÂN DUNG" in w for w in warnings)
    mo_ta = next(w for w in warnings if w.startswith("Dòng (1)") and "nút Mô tả" in w)
    assert "02_Chung_chi.pdf" in mo_ta and "03_Bang.pdf" in mo_ta


def test_giay_to_la_vao_dong_don_giu_ten_tep():
    items, warnings, _ = planner.build_plan_items(
        _files(["don.pdf", "CCCD.pdf"]), {0: ("don_cap_doi", []), 1: ("other", [])}
    )
    assert items[1]["slotIndex"] == 2
    assert items[1]["documentName"] == "CCCD.pdf"
    assert any(w.startswith("Dòng (3)") and "CCCD.pdf" in w for w in warnings)


def test_mot_tep_gop_don_va_the_uu_tien_don():
    items, _, classified = planner.build_plan_items(
        _files(["ho_so_gop.pdf"]), {0: ("the_hdv", ["don_cap_doi"])}
    )
    assert items[0]["slotIndex"] == 2
    assert classified[0]["assignedType"] == "don_cap_doi"


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {})

    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(c["source"] == "default" for c in classified)
    assert any("Chưa thấy ĐƠN ĐỀ NGHỊ CẤP ĐỔI" in w for w in warnings)


def test_hai_tep_cung_la_don_thi_canh_bao():
    _, warnings, _ = planner.build_plan_items(
        _files(["don_1.pdf", "don_2.pdf"]), {0: ("don_cap_doi", []), 1: ("don_cap_doi", [])}
    )
    assert any("2 tệp cùng nhận là Đơn đề nghị" in w for w in warnings)


# ---------------- extension ----------------

def test_slot_key_khong_trung_keyword_cua_extension():
    content = _EXTENSION / "content.js"
    if not content.exists():
        return
    block = content.read_text(encoding="utf-8").split("FIXED_SLOT_KEYWORDS = {", 1)[1].split("};", 1)[0]
    assert "hdvcd_" not in block


def test_extension_gui_moc_tai_khoan_va_bo_qua_luong_cong_tinh():
    popup = _EXTENSION / "popup.js"
    portal = _EXTENSION / "content" / "portal-quangninh.js"
    if not popup.exists() or not portal.exists():
        return
    assert f'cfg.key === "{_KEY}"' in popup.read_text(encoding="utf-8")
    assert '"1.001432"' in portal.read_text(encoding="utf-8").split("NO_FLOW_MA_TTHC = new Set(", 1)[1].split(")", 1)[0]


def test_engine_liz_thu_alias_va_tich_option_trong_nhom():
    fill_liz = _EXTENSION / "content" / "fill-liz.js"
    if not fill_liz.exists():
        return
    src = fill_liz.read_text(encoding="utf-8")
    assert "f.aliases" in src.split("async function fillFormLiz", 1)[1]
    assert "fillLizCheckbox(f.name, f.value, f.option, f.aliases)" in src
    assert "function findLizOption" in src
    assert "if (!mf && f.after) mf = findFieldAfter(index, f);" in src
    after = src.split("function findFieldAfter", 1)[1].split("\n  }\n", 1)[0]
    assert "sectionOf(mf) !== sec" in after, "không trượt sang khối khác"
    assert "isDateField(mf) !== wantDate" in after, "ô ngày chỉ nhận datepicker, ô chữ không nhận datepicker"
