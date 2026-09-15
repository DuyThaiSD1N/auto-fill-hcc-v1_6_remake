"""Unit test "Cấp, cấp lại, chuyển đổi GCNKNCM, CCCM" (dvc.moc — process contact-block + attach attp-row)."""

from app.pipelines.cap_gcnkncm_cccm.attach import planner
from app.pipelines.cap_gcnkncm_cccm.process import mapper
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _map(vals: dict) -> dict:
    fields = [{"name": k, "value": v} for k, v in vals.items()]
    out, _ = mapper.enrich(fields)
    return {f["name"]: f["value"] for f in out}


_BASE = {
    "NguoiNop_HoTen": "NGUYỄN VĂN A",
    "NguoiNop_NgaySinh": "10/08/1986",
    "NguoiNop_GioiTinh": "Nam",
    "NguoiNop_SoDinhDanh": "049086009139",
    "NguoiNop_QuocTich": "Việt Nam",
    "NguoiNop_ThuongTru": {"tinh": "Thành phố Đà Nẵng", "xa": "Xã Thu Bồn", "diaChi": "Thôn 1"},
    "NguoiNop_DienThoai": "0786348870",
}


def test_ca_nhan_contact_block_va_khoi_b():
    d = _map({**_BASE, "DoiTuong": "Cá nhân", "DoiTuong_Ten": "NGUYỄN VĂN A"})
    assert d["data[chonDoiTuong]"] == "Cá nhân"
    assert d["data[fullname]"] == "NGUYỄN VĂN A"
    assert d["data[birthday]"] == "10/08/1986"
    assert d["data[identityNumber]"] == "049086009139"
    # SĐT vào ô "Số điện thoại" = data[phoneNumber] (KHÔNG phải ô "SĐT người được ủy quyền").
    assert d["data[phoneNumber]"] == "0786348870"
    assert "data[AuthorityApplicantPhoneNumber]" not in d
    assert d["data[nation]"] == "Việt Nam"
    assert d["data[province]"] == "Thành phố Đà Nẵng"
    assert d["data[district]"] == "Xã Thu Bồn"
    # Khối B cá nhân: tên + địa chỉ; KHÔNG có ô tổ chức.
    assert d["data[fullName]"] == "NGUYỄN VĂN A"
    assert "data[diachicanhan]" in d
    assert "data[ownerFullname]" not in d


def test_ca_nhan_thuan_khong_co_dangky():
    """Cá nhân thuần không có giấy ĐKKD → các ô đăng ký để trống."""
    d = _map({**_BASE, "DoiTuong": "Cá nhân"})
    assert "data[dangkyhogiadinh]" not in d
    assert "data[captaicaNhan]" not in d


def test_to_chuc_dien_khoi_doanh_nghiep():
    d = _map({
        **_BASE, "DoiTuong": "Tổ chức", "DoiTuong_Ten": "CÔNG TY TNHH X",
        "DoiTuong_SoDangKy": "0401234567", "DoiTuong_NgayCapDangKy": "01/02/2020",
        "DoiTuong_NoiCapDangKy": "Sở KH&ĐT Đà Nẵng", "DoiTuong_DiaChi": "12 Lê Lợi, Đà Nẵng",
        "DoiTuong_DienThoai": "02363888888",
    })
    assert d["data[chonDoiTuong]"] == "Tổ chức"
    assert d["data[ownerFullname]"] == "CÔNG TY TNHH X"
    assert d["data[dangkydoanhnghiep]"] == "0401234567"
    assert d["data[ngaythangnamdoanhnghiep]"] == "01/02/2020"
    assert d["data[diaChitoChuc]"] == "12 Lê Lợi, Đà Nẵng"
    assert d["data[phoneNumberTC]"] == "02363888888"
    # KHÔNG lẫn field cá nhân.
    assert "data[fullName]" not in d


def test_remap_tinh_cu_sang_moi():
    d = _map({**_BASE, "NguoiNop_ThuongTru": {"tinh": "Quảng Nam", "xa": "Xã Thu Bồn", "diaChi": "Thôn 1"},
              "DoiTuong": "Cá nhân"})
    # Quảng Nam (cũ) → Thành phố Đà Nẵng (sau sáp nhập) để khớp SELECT.
    assert d["data[province]"] == "Thành phố Đà Nẵng"


def test_attach_llm_first_routes_va_component_index():
    """LLM-PRIMARY (không rule). Thứ tự dòng THẬT: Sức khỏe(1) · GCNKNCM(2) · Ảnh(3) · Đơn(4)."""
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "gcnkncm.pdf", "type": "application/pdf"},
        {"name": "suckhoe.pdf", "type": "application/pdf"},
    ]
    # llm_types = kết quả phân loại của LLM (build_plan_items HOÀN TOÀN dựa LLM, không dùng OCR/rule).
    llm_types = {0: "don_de_nghi", 1: "gcnkncm", 2: "giay_kham_suc_khoe"}
    attachments, warnings, classified = planner.build_plan_items(files, [], llm_types)
    by = {a["fileName"]: a for a in attachments}
    assert by["don.pdf"]["detectedType"] == "don_de_nghi"
    assert by["don.pdf"]["componentIndex"] == 4
    assert by["don.pdf"]["componentName"] == "Đơn đề nghị theo quy định"
    assert by["gcnkncm.pdf"]["detectedType"] == "gcnkncm"
    assert by["gcnkncm.pdf"]["componentIndex"] == 2
    assert by["gcnkncm.pdf"]["componentName"] == "thuyền trưởng hoặc máy trưởng"
    assert by["suckhoe.pdf"]["detectedType"] == "giay_kham_suc_khoe"
    assert by["suckhoe.pdf"]["componentIndex"] == 1
    assert all(a["source"] == "llm" for a in classified if not a.get("skipped"))
    assert all(a["target"] == "attp-row" for a in attachments)


def test_attach_cccd_skip_va_other_warn():
    """LLM nói cccd → skip (nguồn điền); LLM không nhận ra (other) → cảnh báo, không đính."""
    files = [{"name": "cccd.jpg", "type": "image/jpeg"}, {"name": "la.pdf", "type": "application/pdf"}]
    llm_types = {0: "cccd", 1: "other"}
    attachments, warnings, classified = planner.build_plan_items(files, [], llm_types)
    assert attachments == []
    assert any(c.get("skipped") for c in classified if c["fileName"] == "cccd.jpg")
    assert warnings and "la.pdf" in warnings[0]


def test_registry_process_and_attach():
    proc = get_procedure("cap-gcnkncm-cccm")
    assert proc is not None and proc["mode"] == "agent" and proc["hasAttachmentStep"] is True
    assert get_pipeline("cap-gcnkncm-cccm") is not None
    assert get_attach_pipeline("cap-gcnkncm-cccm") is not None
