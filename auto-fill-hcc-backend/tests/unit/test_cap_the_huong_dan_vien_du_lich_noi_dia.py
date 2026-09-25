"""[Bộ VHTTDL] Thủ tục cấp thẻ hướng dẫn viên du lịch nội địa (1.004623).

Khoá: người đề nghị vào đúng khối (tự nộp → Phần II, nộp thay → Phần III) theo tài khoản đăng nhập;
số liệu bị che trên bản scan không được điền nửa vời; bảng đính kèm 3 dòng theo thứ tự DOM, văn bằng +
chứng chỉ chung một dòng, ảnh chân dung (không có chữ) nhận tất định.
"""

import asyncio

from app.pipelines.cap_the_huong_dan_vien_du_lich_noi_dia.attach import planner
from app.pipelines.cap_the_huong_dan_vien_du_lich_noi_dia.process import mapper
from app.pipelines.cap_the_huong_dan_vien_du_lich_noi_dia.process.schema import (
    S_NOP,
    S_THE,
    S_UQ,
    UI_FIELDS,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, public_list

_KEY = "cap-the-huong-dan-vien-du-lich-noi-dia"

_DON = [
    {"name": "NguoiDeNghi_HoTen", "value": "TRẦN THỊ LAN"},
    {"name": "NguoiDeNghi_NgaySinh", "value": "05/03/2003"},
    {"name": "NguoiDeNghi_GioiTinh", "value": "Nữ"},
    {"name": "NguoiDeNghi_SoDinhDanh", "value": "001303012345"},
    {"name": "NguoiDeNghi_NgayCap", "value": "10/09/2024"},
    {"name": "NguoiDeNghi_NoiCap", "value": "BỘ CÔNG AN"},
    {"name": "NguoiDeNghi_DienThoai", "value": "0912 345 678"},
    {"name": "NguoiDeNghi_Email", "value": "tranthilan@example.com"},
    {"name": "NguoiDeNghi_DiaChi", "value": {"tinh": "Quảng Trị", "xa": "Xã Bố Trạch", "diaChi": "Thôn 3"}},
    {"name": "NguoiDeNghi_TrinhDoChuyenMon", "value": "Đại học"},
    {"name": "Don_LoaiThe", "value": "nội địa"},
]


def _ui(fields):
    return {(f["section"], f["name"]): f["value"] for f in fields}


def _files(specs):
    return [{"name": n, "type": t} for n, t in specs]


def test_registry_dang_ky_du_process_attach_va_link_ke_khai():
    entry = next(p for p in public_list() if p["key"] == _KEY)
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert "matthc=1.004623" in entry["detect"]["urlIncludes"]
    assert get_pipeline(_KEY) is not None
    assert get_attach_pipeline(_KEY) is not None
    assert any(link["key"] == _KEY and link["code"] == "1.004623" for link in KE_KHAI_LINKS)


def test_khong_khai_o_bi_cong_khoa_o_khoi_nguoi_nop():
    """Tên + CMND của Phần II là disabled (cổng tự điền từ tài khoản định danh)."""
    khai_nop = {label for section, label, _c, _a in UI_FIELDS if section == S_NOP}
    assert not any(label.startswith(("Tên người", "CMND")) for label in khai_nop)


def test_tu_nop_dien_khoi_nguoi_nop_va_khong_dung_khoi_uy_quyen():
    fields, warnings = mapper.enrich(_DON, {"formContext": {
        "applicantFullname": "Trần Thị Lan", "applicantIdentityNumber": "001303012345",
    }})
    ui = _ui(fields)

    assert ui[(S_NOP, "Ngày sinh")] == "05/03/2003"
    assert ui[(S_NOP, "Ngày cấp")] == "10/09/2024"
    assert ui[(S_NOP, "Nơi cấp")] == "Bộ Công an"
    assert ui[(S_NOP, "Số điện thoại")] == "0912345678"
    assert ui[(S_NOP, "Email")] == "tranthilan@example.com"
    assert ui[(S_NOP, "Địa chỉ chi tiết")] == "Thôn 3"
    assert "Bố Trạch" in ui[(S_NOP, "Địa chỉ hành chính")]
    assert not any(section == S_UQ for section, _ in ui)
    assert ui[(S_THE, "Giới tính")] == "Nữ"
    assert ui[(S_THE, "Trình độ chuyên môn nghiệp vụ")] == "Đại học"
    assert ui[(S_THE, "Email")] == "tranthilan@example.com"
    assert warnings == []


def test_select_dia_chi_kem_goi_y_tinh_va_aliases_nhan():
    fields, _ = mapper.enrich(_DON)
    by_label = {(f["section"], f["name"]): f for f in fields}
    select = by_label[(S_NOP, "Địa chỉ hành chính")]
    assert select["comp"] == "liz-select"
    assert select["hint"] == "Tỉnh Quảng Trị"
    assert "Địa chỉ" in by_label[(S_NOP, "Địa chỉ chi tiết")]["aliases"]


def test_nop_thay_dua_nguoi_de_nghi_sang_khoi_uy_quyen():
    fields, warnings = mapper.enrich(_DON, {"formContext": {
        "applicantFullname": "NGUYỄN VĂN BÌNH", "applicantIdentityNumber": "038090001111",
    }})
    ui = _ui(fields)

    assert ui[(S_UQ, "Tên người / Tên đơn vị ủy quyền")] == "TRẦN THỊ LAN"
    assert ui[(S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp")] == "001303012345"
    assert ui[(S_UQ, "Ngày sinh")] == "05/03/2003"
    assert not any(section == S_NOP for section, _ in ui)
    assert any("Thông tin ủy quyền" in w for w in warnings)


def test_ten_va_so_bi_che_van_coi_la_tu_nop_nhung_khong_dien_so_cut():
    """Bản scan che phần tên + đuôi số: đầu khớp tài khoản thì vẫn là tự nộp; số cụt không được điền."""
    masked = [
        {"name": "NguoiDeNghi_HoTen", "value": "TRẦN THỊ"},
        {"name": "NguoiDeNghi_SoDinhDanh", "value": "0013"},
        {"name": "NguoiDeNghi_DienThoai", "value": "091"},
        {"name": "NguoiDeNghi_Email", "value": "@gmail.com"},
    ]
    fields, warnings = mapper.enrich(masked, {"formContext": {
        "applicantFullname": "TRẦN THỊ LAN", "applicantIdentityNumber": "001303012345",
    }})
    ui = _ui(fields)

    assert not any(section == S_UQ for section, _ in ui)
    assert (S_NOP, "Số điện thoại") not in ui
    assert (S_NOP, "Email") not in ui
    assert any("0013" in w for w in warnings)
    assert any("Số điện thoại" in w and "E-mail" in w for w in warnings)


def test_gioi_tinh_suy_tu_cccd_khi_don_khong_danh_dau():
    fields, _ = mapper.enrich([{"name": "NguoiDeNghi_SoDinhDanh", "value": "001203012345"}])
    assert _ui(fields)[(S_THE, "Giới tính")] == "Nam"


def test_khong_bia_ngay_khi_thieu_nam():
    fields, _ = mapper.enrich([{"name": "NguoiDeNghi_NgaySinh", "value": "16/11"}])
    assert (S_NOP, "Ngày sinh") not in _ui(fields)


def test_canh_bao_bang_khac_chuyen_nganh_thieu_chung_chi_va_sai_loai_the():
    _, warnings = mapper.enrich([
        {"name": "VanBang_ChuyenNganh", "value": "Kế toán"},
        {"name": "Don_LoaiThe", "value": "quốc tế"},
    ])
    assert any("Chứng chỉ nghiệp vụ" in w for w in warnings)
    assert any("quốc tế" in w for w in warnings)

    _, warnings = mapper.enrich([
        {"name": "VanBang_ChuyenNganh", "value": "Quản trị dịch vụ du lịch và lữ hành"},
    ])
    assert not any("Chứng chỉ nghiệp vụ" in w for w in warnings)


def test_bo_ho_so_mau_len_dung_ba_dong():
    items, warnings, _ = planner.build_plan_items(
        _files([("anh.pdf", "application/pdf"), ("don.pdf", "application/pdf"),
                ("bang.pdf", "application/pdf"), ("chung_chi.pdf", "application/pdf")]),
        {0: ("anh_chan_dung", []), 1: ("don_de_nghi", []), 2: ("van_bang", []),
         3: ("chung_chi_nghiep_vu", [])},
    )
    by_file = {i["fileName"]: i for i in items}

    assert by_file["anh.pdf"]["slotIndex"] == 0
    assert by_file["don.pdf"]["slotIndex"] == 1
    assert by_file["bang.pdf"]["slotIndex"] == by_file["chung_chi.pdf"]["slotIndex"] == 2
    # Chung slotKey → engine gom hai tệp vào MỘT lần gán input multiple của dòng (2).
    assert by_file["bang.pdf"]["slotKey"] == by_file["chung_chi.pdf"]["slotKey"]
    assert by_file["bang.pdf"]["loaiBan"] == "Bản sao"
    assert by_file["don.pdf"]["loaiBan"] == "Bản chính"
    assert all(i["target"] == "fixed-slot" for i in items)
    assert warnings == []


def test_tep_la_vao_dong_don_va_canh_bao_thieu():
    items, warnings, _ = planner.build_plan_items(
        _files([("don.pdf", "application/pdf"), ("cccd.jpg", "image/jpeg"), ("bang.pdf", "application/pdf")]),
        {0: ("don_de_nghi", []), 1: ("other", []), 2: ("van_bang", [])},
    )
    assert {i["fileName"]: i["slotIndex"] for i in items}["cccd.jpg"] == 1
    assert len(items) == 3
    assert any("cccd.jpg" in w for w in warnings)
    assert any("ẢNH CHÂN DUNG" in w for w in warnings)
    assert any("chứng chỉ nghiệp vụ" in w for w in warnings)


def test_plan_nhan_anh_chan_dung_khi_ocr_khong_co_chu(monkeypatch):
    from app.process.schemas import FileItem
    from app.services import ocr

    async def fake_ocr(files):
        texts = {"anh.pdf": "", "don.pdf": "ĐƠN ĐỀ NGHỊ Cấp thẻ hướng dẫn viên du lịch nội địa " * 3}
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    async def fake_classify(documents, errors=None):
        return {d["index"]: ("don_de_nghi", []) for d in documents}

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_classify_with_llm", fake_classify)
    files = [
        FileItem(role="doc", name="anh.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AA=="),
        FileItem(role="doc", name="don.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AA=="),
    ]
    result = asyncio.run(planner.plan(files))
    slots = {a["fileName"]: a["slotIndex"] for a in result["attachments"]}

    assert slots == {"anh.pdf": 0, "don.pdf": 1}
    assert result["extracted"]["llmDocuments"] == ["don.pdf"]
