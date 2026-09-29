"""[Đà Nẵng · Bộ VHTTDL] Cấp lại thẻ hướng dẫn viên du lịch (1.004614, QT-122).

Khoá các điều dễ vỡ: nhận diện không lẫn với cấp đổi/thẻ nội địa/tại điểm cùng cổng; khối người nộp chỉ
điền khi CCCD tài khoản trùng CCCD người đề nghị; "Ngày cấp/Nơi cấp" của khối cấp lại là của THẺ HDV cũ;
loại thẻ đã được cấp tích đúng MỘT ô; hồ sơ nộp nhầm bộ cấp mới gộp trong một PDF được tách theo trang
như ảnh ánh xạ (tr.1–2 Đơn → dòng 2, tr.3–5 chứng chỉ + văn bằng → dòng 1), CCCD không đính.
"""

from pathlib import Path

from app.pipelines.cap_lai_the_huong_dan_vien_du_lich_da_nang.attach import planner
from app.pipelines.cap_lai_the_huong_dan_vien_du_lich_da_nang.process import mapper
from app.pipelines.cap_lai_the_huong_dan_vien_du_lich_da_nang.process.schema import (
    LABEL_LOAI_THE,
    LABEL_LY_DO,
    S_NOP,
    S_THE,
    UI_FIELDS,
)
from app.procedures import registry
from app.procedures.ke_khai_links import with_ke_khai_detect_urls

_KEY = "cap-lai-the-huong-dan-vien-du-lich-da-nang"
_TITLE = "qt-122 - thủ tục cấp lại thẻ hướng dẫn viên du lịch"
_EXTENSION = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension"

# Hồ sơ bịa — không dùng dữ liệu thật.
_CCCD = "048196054321"
_FACTS = {
    "NguoiDeNghi_HoTen": "Trần Thị Lan",
    "NguoiDeNghi_NgaySinh": "9/11/1996",
    "NguoiDeNghi_GioiTinh": "Nữ",
    "NguoiDeNghi_SoDinhDanh": _CCCD,
    "NguoiDeNghi_NgayCap": "02/03/2023",
    "NguoiDeNghi_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "NguoiDeNghi_DienThoai": "0935 222 333",
    "NguoiDeNghi_Email": "lan.tran@example.com",
    "NguoiDeNghi_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Sơn Trà", "diaChi": "12 Ngô Quyền"},
    "TheCu_SoThe": "+ Số thẻ: 248765432",
    "TheCu_NgayCap": "05/08/2022",
    "TheCu_NoiCap": "Sở Du lịch thành phố Đà Nẵng",
    "TheCu_Loai": "Quốc tế",
    "Don_LyDo": "Thẻ bị mất",
    "Don_LoaiDeNghi": "cấp lại",
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


def test_ma_1_004614_duoc_ghep_tu_ke_khai_links():
    public = next(p for p in with_ke_khai_detect_urls(registry.PROCEDURES) if p["key"] == _KEY)
    assert "matthc=1.004614" in public["detect"]["urlIncludes"]


def test_cum_nhan_dien_khong_lan_voi_cac_the_hdv_khac():
    phrase = _entry()["detect"]["textIncludes"][0].lower()
    assert phrase in _TITLE
    for key in (
        "cap-the-huong-dan-vien-du-lich-noi-dia",
        "cap-the-huong-dan-vien-du-lich-tai-diem-da-nang",
        "cap-doi-the-huong-dan-vien-du-lich-da-nang",
    ):
        other = next(p for p in registry.PROCEDURES if p["key"] == key)
        for other_phrase in other["detect"]["textIncludes"]:
            assert other_phrase.lower() not in _TITLE, key
    # Trang cấp đổi có nhãn "Lý do đề nghị cấp đổi/cấp lại thẻ" nhưng không có cụm của cấp lại.
    assert phrase not in (
        "qt-113 - thủ tục cấp đổi thẻ hướng dẫn viên du lịch quốc tế, thẻ hướng dẫn viên du lịch nội địa "
        "lý do đề nghị cấp đổi/cấp lại thẻ"
    )


# ---------------- process mapper ----------------

def test_tu_nop_dien_khoi_nguoi_nop_va_the_da_cap():
    fields, warnings = mapper.enrich(_facts(), {"formContext": {"identityNumber": _CCCD}})
    ui = _ui(fields)

    assert ui[(S_NOP, "Ngày sinh")] == "09/11/1996"
    assert ui[(S_NOP, "Ngày cấp")] == "02/03/2023"
    assert ui[(S_NOP, "Số điện thoại")] == "0935222333"
    assert ui[(S_NOP, "Địa chỉ chi tiết")] == "12 Ngô Quyền"
    assert ui[(S_THE, "Giới tính")] == "Nữ"
    assert ui[(S_THE, "Email")] == "lan.tran@example.com"
    assert ui[(S_THE, "Số thẻ")] == "248765432"
    assert ui[(S_THE, "Ngày cấp")] == "05/08/2022", "ngày cấp THẺ, không phải ngày cấp CCCD"
    assert ui[(S_THE, "Nơi cấp")] == "Sở Du lịch thành phố Đà Nẵng"
    assert ui[(S_THE, LABEL_LY_DO)] == "Thẻ bị mất"
    assert warnings == []


def test_loai_the_tich_dung_mot_o_va_tich_truoc():
    fields, _ = mapper.enrich(_facts(TheCu_Loai="HƯỚNG DẪN VIÊN DU LỊCH TẠI ĐIỂM"), {})
    boxes = [f for f in fields if f["comp"] == "liz-checkbox"]

    assert len(boxes) == 1
    assert boxes[0]["name"] == LABEL_LOAI_THE and boxes[0]["option"] == "Tại điểm"
    assert fields.index(boxes[0]) == 0


def test_cccd_tai_khoan_khac_thi_bo_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_facts(), {"formContext": {"identityNumber": "001088000111"}})

    assert all(f["section"] == S_THE for f in fields)
    assert any("Không điền khối \"Thông tin người nộp hồ sơ\"" in w for w in warnings)


def test_moi_o_emit_deu_khai_trong_schema():
    fields, _ = mapper.enrich(_facts(), {"formContext": {"identityNumber": _CCCD}})
    khai = {(s, l) for s, l, _c, _a in UI_FIELDS}
    assert {(f["section"], f["name"]) for f in fields} <= khai


def test_ho_so_cap_moi_nop_nham_khong_bia_the_cu():
    """Như bản mapping: Đơn Mẫu 04 nội địa + chứng chỉ → không tích loại thẻ, không bịa số thẻ, cảnh báo."""
    fields, warnings = mapper.enrich(
        _facts(
            Don_LoaiDeNghi="cấp mới", Don_LoaiTheDeNghi="nội địa", TheCu_SoThe="CMS./HDDLNĐ-0123",
            TheCu_NgayCap=None, TheCu_NoiCap=None, TheCu_Loai=None, Don_LyDo=None,
        ),
        {},
    )
    ui = _ui(fields)

    assert (S_THE, "Số thẻ") not in ui
    assert not any(f["comp"] == "liz-checkbox" for f in fields)
    assert any("LỆCH THỦ TỤC" in w and "NỘI ĐỊA" in w and "CẤP LẠI" in w for w in warnings)
    assert any("trông như số hiệu chứng chỉ" in w for w in warnings)
    assert any("LOẠI THẺ" in w and "đề nghị loại NỘI ĐỊA" in w for w in warnings)
    assert not any("chưa ghi LÝ DO" in w for w in warnings), "đơn cấp mới không có mục lý do"


def test_don_cap_doi_hoac_the_het_han_canh_bao_nham_thu_tuc():
    for over in ({"Don_LoaiDeNghi": "cấp đổi"}, {"Don_LyDo": "Thẻ hết hạn sử dụng"}):
        _, warnings = mapper.enrich(_facts(**over), {})
        assert any("CẤP ĐỔI" in w and "1.001432" in w for w in warnings), over


def test_tieu_de_cap_doi_cap_lai_khong_gach_la_cap_lai():
    _, warnings = mapper.enrich(_facts(Don_LoaiDeNghi="cấp đổi/cấp lại"), {})
    assert not any("1.001432" in w for w in warnings)


def test_thieu_so_the_va_ly_do_thi_canh_bao():
    fields, warnings = mapper.enrich(_facts(TheCu_SoThe=None, Don_LyDo=None), {})
    assert (S_THE, "Số thẻ") not in _ui(fields)
    assert any("Chưa có SỐ THẺ" in w for w in warnings)
    assert any("chưa ghi LÝ DO" in w for w in warnings)


def test_ngay_cap_noi_cap_the_co_moc_vi_tri_sau_o_so_the():
    fields, _ = mapper.enrich(_facts(), {})
    by_name = {f["name"]: f for f in fields if f["section"] == S_THE}

    for label in ("Ngày cấp", "Nơi cấp"):
        assert by_name[label]["after"][0] == "Số thẻ", label
    assert "Số" in by_name["Số thẻ"]["aliases"], "DOM dịch nhãn thành 'Số'"


def test_don_gui_tinh_khac_thi_canh_bao_noi_tiep_nhan():
    _, warnings = mapper.enrich(_facts(Don_CoQuanNhan="Sở Văn hóa, Thể thao và Du lịch tỉnh Quảng Ngãi"), {})
    assert any("Kiểm tra lại nơi tiếp nhận" in w for w in warnings)


# ---------------- đính kèm ----------------

def test_du_bo_cap_lai_vao_dung_3_dong():
    items, warnings, _ = planner.build_plan_items(
        _files(["giay_to_thay_doi.pdf", "don_mau05.pdf"]) + _files(["anh_3x4.jpg"], "image/jpeg"),
        {0: ("giay_to_thay_doi", []), 1: ("don_cap_lai", []), 2: ("anh_chan_dung", [])},
    )

    assert [i["slotIndex"] for i in items] == [0, 1, 2]
    assert [i["loaiBan"] for i in items] == ["Bản sao", "Bản chính", "Bản chính"]
    assert all("sourceSegments" not in i for i in items)
    assert warnings == []


def test_pdf_gop_cap_moi_tach_theo_trang_nhu_anh_anh_xa():
    """1 PDF 5 trang: tr.1 Đơn Mẫu 04, tr.2 'Hướng dẫn ghi' (None → theo trang trước), tr.3–4 chứng chỉ,
    tr.5 văn bằng → Đơn tr.1–2 lên dòng 2; chứng chỉ + văn bằng tr.3–5 CHUNG một đoạn lên dòng 1."""
    items, warnings, classified = planner.build_plan_items(
        _files(["ho_so_the_hdv.pdf"]), {},
        {0: ["don_cap_moi", None, "chung_chi_nghiep_vu", "chung_chi_nghiep_vu", "van_bang"]},
    )

    assert [i["slotIndex"] for i in items] == [1, 0]
    assert items[0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0, 1]}]
    assert items[1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2, 3, 4]}]
    assert items[1]["documentName"] == "Chứng chỉ nghiệp vụ hướng dẫn du lịch + Bằng tốt nghiệp"
    assert any("SAI MẪU ĐƠN" in w for w in warnings)
    assert any("Chưa thấy ẢNH CHÂN DUNG" in w for w in warnings)
    assert any("ô duy nhất nhận bản sao giấy tờ kèm theo" in w for w in warnings)
    mo_ta = next(w for w in warnings if w.startswith("Dòng 1") and "nút Mô tả" in w)
    assert "trang 3–5" in mo_ta
    assert [c["pages"] for c in classified] == [[1, 2], [3, 4, 5]]


def test_pdf_nhieu_trang_cung_mot_dong_khong_tach():
    items, _, _ = planner.build_plan_items(
        _files(["don_2_trang.pdf"]), {}, {0: ["don_cap_lai", None]}
    )
    assert len(items) == 1 and items[0]["slotIndex"] == 1
    assert "sourceSegments" not in items[0]


def test_cccd_khong_dinh_kem_giay_to_la_vao_dong_1():
    items, warnings, classified = planner.build_plan_items(
        _files(["don.pdf", "CCCD.pdf", "giay_kham.pdf"]),
        {0: ("don_cap_lai", []), 1: ("cccd", []), 2: ("other", [])},
    )

    assert [i["fileIndex"] for i in items] == [0, 2]
    assert items[1]["slotIndex"] == 0 and items[1]["documentName"] == "giay_kham.pdf"
    assert classified[1]["target"] == "skip"
    assert any("Không đính kèm CCCD" in w and "CCCD.pdf" in w for w in warnings)


def test_trang_cccd_trong_pdf_gop_bi_bo_ra():
    items, _, _ = planner.build_plan_items(
        _files(["gop.pdf"]), {}, {0: ["don_cap_lai", "cccd", "chung_chi_nghiep_vu"]}
    )
    assert [(i["slotIndex"], i["sourceSegments"][0]["pageIndexes"]) for i in items] == [(1, [0]), (0, [2])]


def test_mot_tep_gop_khong_header_trang_uu_tien_don():
    items, _, classified = planner.build_plan_items(
        _files(["ho_so_gop.pdf"]), {0: ("chung_chi_nghiep_vu", ["don_cap_lai", "cccd"])}
    )
    assert items[0]["slotIndex"] == 1
    assert classified[0]["assignedType"] == "don_cap_lai"


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {}, {1: [None, None]})

    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(c["source"] == "default" for c in classified)
    assert any("Chưa thấy ĐƠN ĐỀ NGHỊ CẤP LẠI" in w for w in warnings)


def test_tach_trang_theo_header_ocr():
    text = "── Trang 1/3 ──\nĐƠN ĐỀ NGHỊ\n── Trang 2/3 ──\nHướng dẫn ghi: (1) Quốc tế…\n── Trang 3/3 ──\nCHỨNG CHỈ"
    pages = planner._split_pages(text)

    assert pages == ["ĐƠN ĐỀ NGHỊ", "Hướng dẫn ghi: (1) Quốc tế…", "CHỨNG CHỈ"]
    assert planner._split_pages("không có header") is None
    assert planner._page_follows_previous(pages[1])
    assert planner._page_follows_previous("   ")
    assert not planner._page_follows_previous("Kính gửi: Sở Văn hóa … Hướng dẫn ghi … Họ và tên (chữ in hoa)")


def test_hai_tep_cung_la_don_thi_canh_bao():
    _, warnings, _ = planner.build_plan_items(
        _files(["don_1.pdf", "don_2.pdf"]), {0: ("don_cap_lai", []), 1: ("don_cap_lai", [])}
    )
    assert any("2 tệp cùng nhận là Đơn đề nghị" in w for w in warnings)


# ---------------- extension ----------------

def test_slot_key_khong_trung_keyword_cua_extension():
    content = _EXTENSION / "content.js"
    if not content.exists():
        return
    block = content.read_text(encoding="utf-8").split("FIXED_SLOT_KEYWORDS = {", 1)[1].split("};", 1)[0]
    assert "hdvcl_" not in block


def test_extension_gui_moc_tai_khoan_va_bo_qua_luong_cong_tinh():
    popup = _EXTENSION / "popup.js"
    portal = _EXTENSION / "content" / "portal-quangninh.js"
    if not popup.exists() or not portal.exists():
        return
    assert f'cfg.key === "{_KEY}"' in popup.read_text(encoding="utf-8")
    assert '"1.004614"' in portal.read_text(encoding="utf-8").split("NO_FLOW_MA_TTHC = new Set(", 1)[1].split(")", 1)[0]
