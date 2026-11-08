"""Điền lại sau khi điều chỉnh giấy tờ: dọn dữ liệu CHÍNH trợ lý đã điền ở lượt trước mà bộ giấy mới không còn.

Lỗi gốc (phù hiệu xe, cổng Bộ Xây dựng): xoá giấy cũ, scan giấy mới, điền lại → xe của bộ giấy cũ vẫn ở dòng 1 danh
sách phương tiện, ô bộ giấy mới không có vẫn giữ giá trị cũ.
"""
from app.channels.handfree.chat import flow

_PANEL = "data[ThamDinh][ThemPhuongTienRaw]"


def _click(plate: str) -> dict:
    return {"name": "data[ThamDinh][themPhuongTien]", "comp": "dom-click", "value": True,
            "waitName": f"{_PANEL}[BienDangKy]", "skipIfListed": plate}


def _set_a() -> list[dict]:
    return [
        {"name": "data[ThamDinh][TenDonVi]", "comp": "dom-input", "value": "Đơn vị A"},
        {"name": "data[ThamDinh][DiaChi]", "comp": "dom-input", "value": "Địa chỉ A"},
        {"name": "data[ThamDinh][NgayCap]", "comp": "dom-date", "value": "01/01/2020"},
        {"name": "data[ThamDinh][LoaiHinh]", "comp": "dom-select", "value": "Tuyến cố định"},
        _click("XE-A"),
        {"name": f"{_PANEL}[SoKhung]", "comp": "dom-input", "value": "KHUNG-A"},
        {"name": "data[ThamDinh][GhiChu]", "comp": "dom-input", "value": "", "clear": True},
    ]


def test_lan_dien_dau_giu_nguyen_lenh_dien():
    conv = {"procedure_key": "p"}
    fields = _set_a()
    assert flow._with_refill_cleanup(conv, fields) == fields


def test_dien_lai_bo_giay_moi_xoa_xe_cu_va_o_khong_con():
    conv = {"procedure_key": "p"}
    flow._with_refill_cleanup(conv, _set_a())
    out = flow._with_refill_cleanup(conv, [
        {"name": "data[ThamDinh][TenDonVi]", "comp": "dom-input", "value": "Đơn vị B"},
        _click("XE-B"),
        {"name": f"{_PANEL}[SoKhung]", "comp": "dom-input", "value": "KHUNG-B"},
    ])
    click = next(f for f in out if f["comp"] == "dom-click")
    assert click["skipIfListed"] == "XE-B" and click["removeListed"] == ["XE-A"]
    cleared = {f["name"] for f in out if f.get("clear")}
    # Ô gõ / ô ngày lượt trước có mà lượt này không có → xoá; ô chọn không có đường xoá; ô trong panel thêm xe (đã
    # đóng sau khi thêm) không đụng; ô mapper đã tự xoá ở lượt trước không tính là trợ lý đã điền.
    assert cleared == {"data[ThamDinh][DiaChi]", "data[ThamDinh][NgayCap]"}


def test_dien_lai_cung_bo_giay_khong_xoa_gi():
    conv = {"procedure_key": "p"}
    flow._with_refill_cleanup(conv, _set_a())
    out = flow._with_refill_cleanup(conv, _set_a())
    assert not any(f.get("clear") and f["name"] != "data[ThamDinh][GhiChu]" for f in out)
    assert "removeListed" not in next(f for f in out if f["comp"] == "dom-click")


def test_doi_thu_tuc_khong_dung_ghi_nho_cua_thu_tuc_truoc():
    conv = {"procedure_key": "p"}
    flow._with_refill_cleanup(conv, _set_a())
    conv["procedure_key"] = "q"
    fields = [{"name": "data[Khac]", "comp": "dom-input", "value": "x"}, _click("XE-C")]
    assert flow._with_refill_cleanup(conv, fields) == fields


def test_lenh_dien_cua_reply_mang_lenh_don():
    conv = {"procedure_key": "", "fields": _set_a()}
    flow._fill_fields_reply(conv)
    conv["fields"] = [_click("XE-B")]
    r = flow._fill_fields_reply(conv)
    sent = r.actions[0]["fields"]
    assert next(f for f in sent if f["comp"] == "dom-click")["removeListed"] == ["XE-A"]
    assert conv["fields"] == [_click("XE-B")], "không ghi lệnh dọn vào conv['fields']"
