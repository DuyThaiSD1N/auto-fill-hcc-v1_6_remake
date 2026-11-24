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
    assert D.to_fields(rows) == {"KhuyetTat_DanhMuc": ["kt1"], "KhuyetTat_ChiTiet": ["kt1_4"], "KhuyetTat_KhongNhom": []}


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


def test_stt_dinh_dau_nhay_ocr_van_doc_duoc_dong_nhom():
    """OCR đọc STT dòng nhóm thành "6’" — trước đây cả dòng bị bỏ, nhóm duy nhất "Có" mất nên không tích ô nào."""
    from app.pipelines.khuyet_tat.process import dang_khuyet_tat as dkt

    ocr = ("| 5’ | Khuyết tật trí tuệ | | X |\n| 6’ | Khuyết tật khác | X | |\n"
           "| 6.1 | Có kết luận của cơ sở y tế | | |")
    rows = dkt.rows_from({"dong": [{"so": "5’", "dong_ocr": ""}, {"so": "6", "dong_ocr": ""},
                                   {"so": "6.1", "dong_ocr": ""}]}, ocr)
    assert rows == {"5": "khong", "6": "co", "6.1": "trong"}
    assert dkt.to_fields(rows)["KhuyetTat_DanhMuc"] == ["kt6"]


def test_bang_toan_khong_thi_tich_khong_o_nhom_co_dau():
    """Đơn đánh dấu toàn cột "Không": nhóm có dấu "Không" (dòng nhóm hoặc dòng con) tích "Không", nhóm OCR mất dấu để trống."""
    from app.pipelines.khuyet_tat.process import mapper
    rows = {"1": "khong", "1.1": "khong", "2": "trong", "2.1": "khong", "3": "trong", "3.1": "trong"}
    fields = D.to_fields(rows)
    assert fields["KhuyetTat_KhongNhom"] == ["kt1", "kt2"] and not fields["KhuyetTat_DanhMuc"]
    res = {"fields": []}
    D.apply(res, rows)
    ui = {f["name"]: f["value"] for f in mapper.enrich(res["fields"], {})}
    radios = {k: v for k, v in ui.items() if "khuyetTat" in k}
    assert radios == {"data[khuyetTat1Obj][khuyetTatRadio]": "khong", "data[khuyetTat2Obj][khuyetTatRadio]": "khong"}
