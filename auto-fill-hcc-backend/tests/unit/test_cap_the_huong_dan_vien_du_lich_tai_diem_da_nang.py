"""[Đà Nẵng · Bộ VHTTDL] Cấp thẻ hướng dẫn viên du lịch tại điểm (1.001440, QT-115).

Khoá các điều dễ vỡ: nhận diện không lẫn với thẻ nội địa cùng cổng; Phần II chỉ điền khi CCCD tài khoản
trùng CCCD người đề nghị; cảnh báo lệch loại thẻ / thiếu tên điểm; bảng đính kèm CHỈ 2 dòng nên chứng
chỉ, văn bằng, giấy tờ lạ đều vào chung dòng Đơn kèm nội dung Mô tả, không bỏ sót tệp nào.
"""

from pathlib import Path

from app.pipelines.cap_the_huong_dan_vien_du_lich_tai_diem_da_nang.attach import planner
from app.pipelines.cap_the_huong_dan_vien_du_lich_tai_diem_da_nang.process import mapper
from app.pipelines.cap_the_huong_dan_vien_du_lich_tai_diem_da_nang.process.schema import (
    S_NOP,
    S_THE,
    UI_FIELDS,
)
from app.procedures import registry
from app.procedures.ke_khai_links import with_ke_khai_detect_urls

_KEY = "cap-the-huong-dan-vien-du-lich-tai-diem-da-nang"
_LABEL_DIEM = "Tên điểm du lịch đối với trường hợp cấp thẻ hướng dẫn viên du lịch tại điểm"
_EXTENSION = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension"

# Hồ sơ bịa — không dùng dữ liệu thật.
_CCCD = "048099012345"
_FACTS = {
    "NguoiDeNghi_HoTen": "Trần Thị Bích",
    "NguoiDeNghi_NgaySinh": "5/3/1999",
    "NguoiDeNghi_GioiTinh": "Nữ",
    "NguoiDeNghi_SoDinhDanh": _CCCD,
    "NguoiDeNghi_NgayCap": "10/08/2021",
    "NguoiDeNghi_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "NguoiDeNghi_DienThoai": "0905 123 456",
    "NguoiDeNghi_Email": "bich.tran@example.com",
    "NguoiDeNghi_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "12 Lê Lợi"},
    "NguoiDeNghi_TrinhDoChuyenMon": "Cao đẳng",
    "NguoiDeNghi_TenDiemDuLich": "Khu du lịch sinh thái Suối Mơ",
    "Don_LoaiThe": "tại điểm",
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


def test_ma_1_001440_duoc_ghep_tu_ke_khai_links():
    public = next(p for p in with_ke_khai_detect_urls(registry.PROCEDURES) if p["key"] == _KEY)
    assert "matthc=1.001440" in public["detect"]["urlIncludes"]


def test_cum_nhan_dien_khong_dinh_nhan_o_ten_diem_cua_trang_noi_dia():
    """Trang thẻ NỘI ĐỊA có ô 'Tên điểm du lịch … cấp thẻ hướng dẫn viên du lịch tại điểm'."""
    phrase = _entry()["detect"]["textIncludes"][0].lower()
    assert phrase not in _LABEL_DIEM.lower()
    assert phrase in "qt-115 - thủ tục cấp thẻ hướng dẫn viên du lịch tại điểm"


# ---------------- process mapper ----------------

def test_tu_nop_dien_ca_phan_nguoi_nop_va_phan_the():
    fields, warnings = mapper.enrich(_facts(), {"formContext": {"identityNumber": _CCCD}})
    ui = _ui(fields)

    assert ui[(S_NOP, "Ngày sinh")] == "05/03/1999"
    assert ui[(S_NOP, "Số điện thoại")] == "0905123456"
    assert ui[(S_NOP, "Địa chỉ chi tiết")] == "12 Lê Lợi"
    assert (S_NOP, "Địa chỉ hành chính") in ui
    assert ui[(S_THE, "Giới tính")] == "Nữ"
    assert ui[(S_THE, "Trình độ chuyên môn nghiệp vụ")] == "Cao đẳng"
    assert ui[(S_THE, "Email")] == "bich.tran@example.com"
    assert ui[(S_THE, _LABEL_DIEM)] == "Khu du lịch sinh thái Suối Mơ"
    assert warnings == []


def test_cccd_tai_khoan_khac_thi_bo_phan_nguoi_nop():
    fields, warnings = mapper.enrich(_facts(), {"formContext": {"identityNumber": "001088000111"}})

    assert all(f["section"] == S_THE for f in fields)
    assert any("Không điền khối \"Thông tin người nộp hồ sơ\"" in w for w in warnings)


def test_moi_o_emit_deu_khai_trong_schema():
    fields, _ = mapper.enrich(_facts(), {"formContext": {"identityNumber": _CCCD}})
    khai = {(s, l) for s, l, _c, _a in UI_FIELDS}
    assert {(f["section"], f["name"]) for f in fields} <= khai


def test_don_the_noi_dia_canh_bao_lech_thu_tuc_va_thieu_ten_diem():
    fields, warnings = mapper.enrich(
        _facts(Don_LoaiThe="nội địa", NguoiDeNghi_TenDiemDuLich=None), {}
    )

    assert (S_THE, _LABEL_DIEM) not in _ui(fields)
    assert any("LỆCH THỦ TỤC" in w and "NỘI ĐỊA" in w for w in warnings)
    assert any("Chưa có TÊN ĐIỂM DU LỊCH" in w for w in warnings)


def test_ten_diem_chep_ca_cau_de_nghi_thi_cat_gon():
    fields, _ = mapper.enrich(
        _facts(NguoiDeNghi_TenDiemDuLich="cấp thẻ hướng dẫn viên du lịch tại điểm Làng đá Non Nước cho tôi"),
        {},
    )
    assert _ui(fields)[(S_THE, _LABEL_DIEM)] == "Làng đá Non Nước"


def test_dong_huong_dan_ghi_in_san_khong_phai_ten_diem():
    fields, warnings = mapper.enrich(
        _facts(NguoiDeNghi_TenDiemDuLich="Tên điểm du lịch đối với trường hợp cấp thẻ hướng dẫn viên du lịch tại điểm"),
        {},
    )
    assert (S_THE, _LABEL_DIEM) not in _ui(fields)
    assert any("Chưa có TÊN ĐIỂM DU LỊCH" in w for w in warnings)


def test_chung_chi_noi_dia_khi_don_khong_ro_loai_the():
    _, warnings = mapper.enrich(
        _facts(Don_LoaiThe=None, ChungChi_Ten="Chứng chỉ nghiệp vụ hướng dẫn du lịch nội địa"), {}
    )
    assert any("chứng chỉ nghiệp vụ hướng dẫn du lịch nội địa" in w for w in warnings)


def test_don_gui_tinh_khac_thi_canh_bao_noi_tiep_nhan():
    _, warnings = mapper.enrich(_facts(Don_CoQuanNhan="Sở Văn hóa, Thể thao và Du lịch tỉnh Quảng Nam"), {})
    assert any("Kiểm tra lại nơi tiếp nhận" in w for w in warnings)


def test_so_dinh_danh_bi_che_khong_dien_va_khong_bia_gioi_tinh():
    fields, warnings = mapper.enrich(
        _facts(NguoiDeNghi_SoDinhDanh="0480", NguoiDeNghi_GioiTinh=None), {"formContext": {"identityNumber": _CCCD}}
    )
    assert (S_THE, "Giới tính") not in _ui(fields)
    assert all(f["section"] == S_THE for f in fields)
    assert any("chỉ đọc được \"0480\"" in w for w in warnings)


# ---------------- đính kèm ----------------

def test_ho_so_mau_don_chung_chi_bang_vao_chung_dong_don():
    """Đơn + chứng chỉ + văn bằng tách 3 tệp, chưa có ảnh: cả 3 lên dòng (1), cảnh báo thiếu ảnh + Mô tả."""
    items, warnings, _ = planner.build_plan_items(
        _files(["01_Don.pdf", "02_Chung_chi.pdf", "03_Bang.pdf"]),
        {0: ("don_de_nghi", []), 1: ("chung_chi_nghiep_vu", []), 2: ("van_bang", [])},
    )

    assert [i["slotIndex"] for i in items] == [0, 0, 0]
    assert len({i["slotKey"] for i in items}) == 1, "cùng slotKey để engine gom vào một input multiple"
    assert all(i["loaiBan"] == "Bản chính" for i in items)
    assert any("Chưa thấy ẢNH CHÂN DUNG" in w for w in warnings)
    mo_ta = next(w for w in warnings if "Mô tả" in w)
    for name in ("01_Don.pdf", "02_Chung_chi.pdf", "03_Bang.pdf"):
        assert name in mo_ta


def test_anh_vao_dong_2():
    items, warnings, _ = planner.build_plan_items(
        _files(["don.pdf"]) + _files(["anh_3x4.jpg"], "image/jpeg"),
        {0: ("don_de_nghi", []), 1: ("anh_chan_dung", [])},
    )

    assert [i["slotIndex"] for i in items] == [0, 1]
    assert warnings == []


def test_mot_tep_gop_don_chung_chi_bang_van_ghi_mo_ta():
    items, warnings, classified = planner.build_plan_items(
        _files(["ho_so_gop.pdf"]), {0: ("chung_chi_nghiep_vu", ["don_de_nghi", "van_bang"])}
    )

    assert len(items) == 1 and items[0]["slotIndex"] == 0
    assert classified[0]["assignedType"] == "don_de_nghi"
    assert any("Mô tả" in w and "ho_so_gop.pdf" in w for w in warnings)


def test_giay_to_la_vao_dong_don_giu_ten_tep():
    items, _, _ = planner.build_plan_items(
        _files(["don.pdf", "CCCD.pdf"]), {0: ("don_de_nghi", []), 1: ("other", [])}
    )
    assert items[1]["slotIndex"] == 0
    assert items[1]["documentName"] == "CCCD.pdf"


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {})

    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(c["source"] == "default" for c in classified)
    assert any("Chưa thấy ĐƠN ĐỀ NGHỊ" in w for w in warnings)


def test_hai_tep_cung_la_don_thi_canh_bao():
    _, warnings, _ = planner.build_plan_items(
        _files(["don_1.pdf", "don_2.pdf"]), {0: ("don_de_nghi", []), 1: ("don_de_nghi", [])}
    )
    assert any("2 tệp cùng nhận là Đơn đề nghị" in w for w in warnings)


def test_slot_key_khong_trung_keyword_cua_extension():
    content = _EXTENSION / "content.js"
    if not content.exists():
        return
    block = content.read_text(encoding="utf-8").split("FIXED_SLOT_KEYWORDS = {", 1)[1].split("};", 1)[0]
    assert "hdvtd_" not in block


def test_extension_gui_moc_tai_khoan_cho_thu_tuc():
    popup = _EXTENSION / "popup.js"
    if not popup.exists():
        return
    assert f'cfg.key === "{_KEY}"' in popup.read_text(encoding="utf-8")
