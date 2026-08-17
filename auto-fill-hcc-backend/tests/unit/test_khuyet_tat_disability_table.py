"""Bảng "dạng khuyết tật": đọc cột Có/Không từ OCR và ánh xạ ra radio Form.io."""

from app.pipelines.khuyet_tat.process import mapper
from app.pipelines.khuyet_tat.process.fallback import apply_ocr_fallback, parse_disability_table


# Trích đúng dạng OCR (tiengnoi) của hồ sơ Nguyễn Ngọc Thái Bảo: trang 2 còn cột, trang 3 bị làm phẳng.
_OCR_TABLE = """| STT | Các dạng khuyết tật | Có | Không |
| :--- | :--- | :--- | :--- |
| 1 | Khuyết tật vận động | | X |
| 1.1 | Mềm nhão hoặc co cứng toàn thân | | X |
| 1.6 | Có kết luận của cơ sở y tế cấp tỉnh trở lên về suy giảm chức năng vận động | | X |
| 2 | Khuyết tật nghe, nói | | X |
| 2.6 | Có kết luận của cơ sở y tế cấp tỉnh trở lên về suy giảm chức năng nghe, nói | | X |
| 3.1 | Mù một hoặc hai mắt | | X |
3.6 Bị dị tật, biến dạng ở vùng mắt X
3.7 Có kết luận của cơ sở y tế cấp tỉnh trở lên về suy giảm chức năng nhìn X
"""


def test_parse_reads_column_not_the_word_co_inside_the_label():
    parsed = parse_disability_table(_OCR_TABLE)

    assert parsed["1"] == "khong"
    assert parsed["1.1"] == "khong"
    # Dòng có chữ "Có kết luận..." trong NỘI DUNG nhưng dấu X nằm ở cột "Không".
    assert parsed["1.6"] == "khong"
    assert parsed["2.6"] == "khong"
    assert parsed["3.1"] == "khong"
    # Dòng OCR làm phẳng: không kết luận được cột -> không trả, để LLM quyết.
    assert "3.6" not in parsed
    assert "3.7" not in parsed


def test_parse_reads_tick_in_co_column():
    parsed = parse_disability_table(
        "| STT | Dạng khuyết tật | Có | Không |\n"
        "| 4 | Khuyết tật thần kinh, tâm thần | X | |\n"
        "| 4.1 | Thường ngồi một mình | X | |\n"
    )
    assert parsed == {"4": "co", "4.1": "co"}


def test_ocr_column_overrides_llm_guess():
    """LLM đoán 1.6 là "co" vì nhãn chứa chữ "Có" — cột OCR thật phải thắng."""
    fields = apply_ocr_fallback(
        {"KhuyetTat_BangDanhDau": {"1.6": "co", "3.6": "co"}},
        [{"name": "don.pdf", "text": _OCR_TABLE}],
    )

    assert fields["KhuyetTat_BangDanhDau"]["1.6"] == "khong"
    assert fields["KhuyetTat_BangDanhDau"]["3.6"] == "co"  # dòng phẳng: giữ nguyên phán đoán LLM


def test_blank_row_read_from_columns_vetoes_llm_guess():
    """Dòng đọc được cột nhưng cả hai ô rỗng ⇒ đơn bỏ trống, không được tick "Có"."""
    parsed = parse_disability_table(
        "| STT | Dạng khuyết tật | Có | Không |\n"
        "| 1.6 | Có kết luận của cơ sở y tế cấp tỉnh trở lên... | | |\n"
    )
    assert parsed == {"1.6": ""}

    out = mapper.enrich([
        {"name": "KhuyetTat_BangDanhDau", "value": parsed},
        {"name": "KhuyetTat_ChiTiet", "value": ["kt1_6"]},
        {"name": "KhuyetTat_DanhMuc", "value": ["kt1"]},
    ])
    d = {item["name"]: item["value"] for item in out}
    assert "data[khuyetTat1Obj][khuyetTatRadio6]" not in d
    # Dòng nhóm "1" không đọc được cột nên phán đoán của LLM cho riêng nhóm vẫn được giữ.
    assert d["data[khuyetTat1Obj][khuyetTatRadio]"] == "co"


def test_mapper_fills_both_co_and_khong_radios():
    out = mapper.enrich([
        {"name": "KhuyetTat_BangDanhDau", "value": {
            "1": "khong", "2": "khong",
            "4": "co", "4.1": "co", "4.2": "khong",
        }},
    ])
    d = {item["name"]: item["value"] for item in out}

    assert d["data[khuyetTat4Obj][khuyetTatRadio]"] == "co"
    assert d["data[khuyetTat4Obj][khuyetTatRadio1]"] == "co"
    assert d["data[khuyetTat4Obj][khuyetTatRadio2]"] == "khong"
    # Nhóm "Không" ⇒ toàn bộ dòng con của nhóm cũng "Không".
    assert d["data[khuyetTat1Obj][khuyetTatRadio]"] == "khong"
    assert d["data[khuyetTat1Obj][khuyetTatRadio6]"] == "khong"
    assert d["data[khuyetTat2Obj][khuyetTatRadio3]"] == "khong"
    # Nhóm chưa có dữ liệu thì KHÔNG tự tick gì.
    assert "data[khuyetTat5Obj][khuyetTatRadio]" not in d


def test_child_marked_co_forces_parent_co():
    out = mapper.enrich([
        {"name": "KhuyetTat_BangDanhDau", "value": {"5": "khong", "5.3": "co"}},
    ])
    d = {item["name"]: item["value"] for item in out}

    assert d["data[khuyetTat5Obj][khuyetTatRadio]"] == "co"
    assert d["data[khuyetTat5Obj][khuyetTatRadio3]"] == "co"
    # Nhóm bị nâng lên "Có" thì không được suy các dòng con còn lại thành "Không".
    assert "data[khuyetTat5Obj][khuyetTatRadio1]" not in d


def test_legacy_list_fields_still_supported():
    out = mapper.enrich([
        {"name": "KhuyetTat_DanhMuc", "value": ["kt5"]},
        {"name": "KhuyetTat_ChiTiet", "value": ["kt5_1", "kt5_3"]},
    ])
    d = {item["name"]: item["value"] for item in out}

    assert d["data[khuyetTat5Obj][khuyetTatRadio]"] == "co"
    assert d["data[khuyetTat5Obj][khuyetTatRadio1]"] == "co"
    assert d["data[khuyetTat5Obj][khuyetTatRadio3]"] == "co"
