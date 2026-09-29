"""Quy tắc chung khối người nộp cổng Lào Cai: tài khoản không ghi ô readonly; tờ khai ghi + xoá ô tài khoản."""

from app.pipelines._shared import lao_cai_nguoi_nop as nn

_COMP = {name: "dom-input" for name in (*nn.O_READONLY, *nn.O_NHAN_THAN_XOA_DUOC)}
_COMP.update({"CongDan_gioiTinhCongDan": "dom-select", "CongDan_danTocCongDan": "dom-select",
              "CongDan_maTinhThanh": "dom-select", "ChuHoSo_tenChuHoSo": "dom-input"})


def _f(name, value):
    return {"name": name, "comp": _COMP.get(name, "dom-input"), "value": value}


def test_tai_khoan_bo_hai_o_readonly_va_khong_xoa_gi():
    out = [_f("CongDan_tenCongDan", "A"), _f("CongDan_soCmnd", "1"), _f("CongDan_diDong", "0900000000")]
    ket_qua = nn.chot_khoi_nguoi_nop(out, theo_to_khai=False, comp_by_name=_COMP)
    assert [f["name"] for f in ket_qua] == ["CongDan_diDong"]


def test_to_khai_dua_readonly_len_dau_va_xoa_o_thieu():
    out = [
        _f("CongDan_ngaySinhCongDan", "01/02/1990"),
        _f("CongDan_tenCongDan", "NGƯỜI GIẢ"),
        _f("ChuHoSo_tenChuHoSo", "NGƯỜI GIẢ"),
    ]
    warnings: list[str] = []
    ket_qua = nn.chot_khoi_nguoi_nop(out, theo_to_khai=True, comp_by_name=_COMP, warnings=warnings)
    names = [f["name"] for f in ket_qua]

    assert names[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert ket_qua[1]["value"] == "" and ket_qua[1]["clear"] is True
    cleared = {f["name"] for f in ket_qua if f.get("clear")}
    assert "CongDan_ngaySinhCongDan" not in cleared
    assert {"CongDan_ngayCapCmnd", "CongDan_diaChi", "CongDan_diDong", "CongDan_maTinhThanh"} <= cleared
    # Lệnh xoá nằm trong khối người nộp, trước khối chủ hồ sơ.
    assert names.index("ChuHoSo_tenChuHoSo") > max(names.index(n) for n in cleared)
    assert warnings == [nn.CANH_BAO_GIOI_TINH]


def test_to_khai_chua_xac_dinh_duoc_ai_thi_de_nguyen():
    out = [_f("ChuHoSo_tenChuHoSo", "X")]
    assert nn.chot_khoi_nguoi_nop(out, theo_to_khai=True, comp_by_name=_COMP) == out


def test_bo_qua_o_dang_an():
    out = [_f("CongDan_tenCongDan", "A"), _f("CongDan_soCmnd", "1")]
    ket_qua = nn.chot_khoi_nguoi_nop(
        out, theo_to_khai=True, comp_by_name=_COMP, bo_qua={"CongDan_fax"}
    )
    assert "CongDan_fax" not in {f["name"] for f in ket_qua}


def test_to_khai_co_so_ma_khong_co_ten_thi_khong_ghi_so():
    out = [_f("CongDan_soCmnd", "001099000001"), _f("CongDan_diDong", "0900000000")]
    ket_qua = nn.chot_khoi_nguoi_nop(out, theo_to_khai=True, comp_by_name=_COMP)
    assert [f["name"] for f in ket_qua] == ["CongDan_diDong"]


def test_xoa_ca_o_package_khong_khai_trong_schema():
    """Mọi form Lào Cai có chung bộ ô CongDan_*; package không khai ô vẫn phải xoá được giá trị tài khoản."""
    comp = {"CongDan_tenCongDan": "dom-input", "CongDan_ngaySinhCongDan": "dom-input"}
    out = [{"name": "CongDan_tenCongDan", "comp": "dom-input", "value": "NGƯỜI GIẢ"}]
    ket_qua = nn.chot_khoi_nguoi_nop(out, theo_to_khai=True, comp_by_name=comp)
    by_name = {f["name"]: f for f in ket_qua}
    assert by_name["CongDan_diDong"] == {"name": "CongDan_diDong", "comp": "dom-input", "value": "", "clear": True, "markEmpty": True}
    assert by_name["CongDan_maTinhThanh"]["comp"] == "dom-select"
    assert by_name["CongDan_soCmnd"]["clear"] is True


def test_email_fax_bi_xoa_nhung_khong_to_do():
    out = [_f("CongDan_tenCongDan", "NGƯỜI GIẢ")]
    ket_qua = {f["name"]: f for f in nn.chot_khoi_nguoi_nop(out, theo_to_khai=True, comp_by_name=_COMP)}
    assert ket_qua["CongDan_email"]["clear"] is True and ket_qua["CongDan_email"]["markEmpty"] is False
    assert ket_qua["CongDan_fax"]["markEmpty"] is False
    assert ket_qua["CongDan_ngaySinhCongDan"]["markEmpty"] is True
