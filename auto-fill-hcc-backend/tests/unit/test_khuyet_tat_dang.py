"""Xác định mức độ khuyết tật — lượt đọc riêng bảng dạng khuyết tật (mục III.1). Dữ liệu giả."""

from app.pipelines.khuyet_tat.process import dang_khuyet_tat as D

_OCR = (
    "| STT | Các dạng khuyết tật | Có | Không |\n"
    "| 1 | Khuyết tật vận động | | |\n"
    "| 1.1 | Mềm nhão hoặc co cứng toàn thân | | X |\n"
    "| 1.4 | Yếu, liệt, teo cơ | X | |\n"
    "| 6 | Khuyết tật khác | | x |\n"
    "6.1 Có kết luận của cơ sở y tế cấp tỉnh trở lên về bệnh tê bì\n"
)


def _row(so, line, cells=("", "")):
    return {"so": so, "dong_ocr": line, "o_danh_dau": list(cells)}


def test_o_co_khong_do_ma_tach_tu_dong_ocr_that():
    data = {"dong": [
        _row("1.1", "| 1.1 | Mềm nhão hoặc co cứng toàn thân | | X |", ("X", "")),  # model chép ô sai → mã tách lại
        _row("1.4", "| 1.4 | Yếu, liệt, teo cơ | X | |"),
        _row("6", "| 6 | Khuyết tật khác | | x |"),
        # Dòng chữ thường (trang vỡ bảng) mà model tự dựng thành dòng bảng → không có trong OCR → bỏ.
        _row("6.1", "| 6.1 | Có kết luận của cơ sở y tế cấp tỉnh trở lên về bệnh tê bì | X | |"),
    ]}
    rows = D.rows_from(data, _OCR)
    assert rows == {"1.1": "khong", "1.4": "co", "6": "khong"}
    assert D.to_fields(rows) == {"KhuyetTat_DanhMuc": ["kt1"], "KhuyetTat_ChiTiet": ["kt1_4"]}


def test_bang_khong_co_dau_thi_khong_tich_gi_va_bo_ket_qua_luot_chinh():
    """Lượt chính tự suy dạng khuyết tật từ bệnh án khi bảng không có dấu → bỏ hẳn."""
    res = {"fields": [{"name": "KhuyetTat_DanhMuc", "value": ["kt1"]}, {"name": "KhuyetTat_ChiTiet", "value": ["kt1_4"]},
                      {"name": "Nkt_HoTen", "value": "A"}]}
    D.apply(res, {"1": "trong", "1.1": "trong"})
    assert [f["name"] for f in res["fields"]] == ["Nkt_HoTen"]


def test_khong_doc_duoc_bang_thi_giu_luot_chinh():
    res = {"fields": [{"name": "KhuyetTat_DanhMuc", "value": ["kt2"]}]}
    D.apply(res, None)
    assert res["fields"] == [{"name": "KhuyetTat_DanhMuc", "value": ["kt2"]}]


def test_moi_dong_con_deu_co_la_doc_lech_con_nhieu_nhom_co_that_thi_giu():
    children = [r for r in D.ROWS if "." in r]
    assert D.is_degenerate({r: "co" for r in children})
    res = {"fields": []}
    D.apply(res, {r: "co" for r in children})
    assert res["fields"] == [] and res["errors"] == [D.WARNING]
    nang = {**{r: "co" for r in children if r[0] in "456"}, "1.5": "khong"}
    assert not D.is_degenerate(nang)
    assert "kt4" in D.to_fields(nang)["KhuyetTat_DanhMuc"]
