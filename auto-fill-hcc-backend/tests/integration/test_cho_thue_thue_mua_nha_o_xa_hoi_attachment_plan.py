"""Đính kèm "Cho thuê, cho thuê mua nhà ở xã hội…" (1.012896, engine attp-row).

Khoá hai điều: không bỏ sót file nào, và dòng "chứng minh đối tượng" phải chốt đúng dòng có cụm
"miễn, giảm tiền thuê" (bảng có hai dòng gần trùng, dòng ngắn là tiền tố của dòng dài).
"""

import inspect
import re
import unicodedata

from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.attach import planner

# Text VERBATIM của các dòng dễ lẫn trên cổng.
_ROW_DOI_TUONG_DAI = (
    "+ Giấy tờ chứng minh đối tượng theo hướng dẫn của Bộ trưởng Bộ Xây dựng, Bộ trưởng Bộ Quốc "
    "phòng, Bộ trưởng Bộ Công an và giấy tờ chứng minh thuộc đối tượng được miễn, giảm tiền thuê "
    "nhà ở xã hội (nếu có)."
)
_ROW_DOI_TUONG_NGAN = (
    "+ Giấy tờ chứng minh đối tượng theo hướng dẫn của Bộ trưởng Bộ Xây dựng, Bộ trưởng Bộ Quốc "
    "phòng, Bộ trưởng Bộ Công an."
)
_ROW_DIEU_KIEN = "+ Giấy tờ chứng minh điều kiện được hưởng chính sách hỗ trợ về nhà ở xã hội theo quy định."
_ROW_DON_THUE = "+ Đơn đăng ký thuê nhà ở xã hội theo mẫu,"
_ROW_DON_THUE_MUA = "+ Đơn đăng ký thuê mua nhà ở xã hội theo mẫu,"
_ROW_TH_THUE = "- Trường hợp thuê nhà ở xã hội:"
_ROW_TH_THUE_MUA = "- Trường hợp thuê mua nhà ở xã hội:"

_ALL_ROWS = [
    _ROW_DIEU_KIEN, _ROW_DOI_TUONG_DAI, _ROW_DOI_TUONG_NGAN, _ROW_DON_THUE_MUA,
    _ROW_DON_THUE, _ROW_TH_THUE_MUA, _ROW_TH_THUE,
]


def _fold(text: str) -> str:
    """Bản rút gọn của foldChoiceText (content.js): bỏ dấu, hạ chữ thường, gom khoảng trắng."""
    stripped = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", stripped.replace("đ", "d").replace("Đ", "D")).strip().lower()


def _matches(row_text: str, component_name: str) -> bool:
    """componentTextMatches của content.js: so substring HAI CHIỀU sau khi fold dấu."""
    row = _fold(row_text)
    want = _fold(component_name)
    if not row or not want:
        return False
    return row == want or want in row or row in want


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _llm(*types):
    return {i: t for i, t in enumerate(types)}


def test_moi_component_name_chi_khop_dung_mot_dong():
    for doc_type, row in planner._ROWS.items():
        hit = [r for r in _ALL_ROWS if _matches(r, row["componentName"])]
        assert len(hit) == 1, (doc_type, row["componentName"], hit)


def test_doi_tuong_chot_dong_co_cum_mien_giam():
    want = planner._ROWS[planner._DOI_TUONG]["componentName"]

    assert _matches(_ROW_DOI_TUONG_DAI, want)
    # Dòng ngắn là TIỀN TỐ của dòng dài → componentName cắt ngắn sẽ khớp cả hai; phải không khớp dòng này.
    assert not _matches(_ROW_DOI_TUONG_NGAN, want)


def test_khong_bo_sot_file_nao_ke_ca_khi_llm_tra_other():
    names = ["don.pdf", "the-hoi-vien.pdf", "ky-niem-chuong.pdf", "huan-chuong.pdf"]
    items, warnings, classified = planner.build_plan_items(
        _files(names), [], _llm("to_don", "other", "doi_tuong", "doi_tuong")
    )

    assert sorted(i["fileIndex"] for i in items) == [0, 1, 2, 3]
    assert all(i["target"] == "attp-row" for i in items)
    # File chưa nhận ra loại về đúng dòng "…miễn, giảm…(nếu có)".
    la = next(i for i in items if i["fileName"] == "the-hoi-vien.pdf")
    assert la["componentName"] == planner._ROWS[planner._DOI_TUONG]["componentName"]
    assert la["detectedType"] == "other"
    assert any("không bỏ sót" in w for w in warnings)
    assert not any(c.get("skipped") for c in classified)


def test_file_khong_co_ocr_van_duoc_dinh():
    """File LLM không nhận được (OCR rỗng) trước đây bị bỏ hẳn khỏi kế hoạch."""
    items, warnings, _ = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), [], {})

    assert sorted(i["fileIndex"] for i in items) == [0, 1]
    assert {i["componentName"] for i in items} == {
        planner._ROWS[planner._DOI_TUONG]["componentName"]
    }
    assert warnings


def test_document_name_trung_duoc_danh_so():
    """attp-row đặt tên tệp tải lên theo documentName và chống trùng bằng chính tên đó."""
    items, _, _ = planner.build_plan_items(
        _files(["a.pdf", "b.pdf", "c.pdf"]), [], _llm("doi_tuong", "doi_tuong", "other")
    )

    names = [i["documentName"] for i in items]
    assert len(set(names)) == 3, names
    assert all(n.endswith((" (1)", " (2)", " (3)")) for n in names), names


def test_document_name_don_le_khong_bi_danh_so():
    items, _, _ = planner.build_plan_items(
        _files(["don.pdf", "cccd.pdf"]), [], _llm("to_don", "cccd")
    )

    assert items[0]["documentName"] == "Đơn đăng ký thuê nhà ở xã hội theo mẫu"
    assert "(1)" not in items[1]["documentName"]


def test_bon_loai_vao_bon_dong_khac_nhau():
    items, _, _ = planner.build_plan_items(
        _files(["don.pdf", "dk.pdf", "dt.pdf", "cccd.pdf"]),
        [],
        _llm("to_don", "dieu_kien", "doi_tuong", "cccd"),
    )

    assert len({i["componentName"] for i in items}) == 4
    for item in items:
        hit = [r for r in _ALL_ROWS if _matches(r, item["componentName"])]
        assert len(hit) == 1, item


def test_khong_con_component_index_va_khong_con_luoi_keyword():
    # Thứ tự dòng trên cổng không ổn định → không gửi componentIndex nữa.
    assert all("componentIndex" not in row for row in planner._ROWS.values())
    items, _, _ = planner.build_plan_items(_files(["a.pdf"]), [], _llm("to_don"))
    assert "componentIndex" not in items[0]
    # Phân loại thuần LLM: planner không được tự đọc OCR để đoán loại.
    assert not hasattr(planner, "_rule_doc_type")
    src = inspect.getsource(planner.build_plan_items)
    assert "_ = ocr_results" in src


def test_prompt_nhan_dien_the_hoi_vien_va_rang_buoc_du_phan_tu():
    from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.attach.prompt import (
        SYSTEM_PROMPT,
        build_user_prompt,
    )

    assert "KỶ NIỆM CHƯƠNG" in SYSTEM_PROMPT
    assert "BỊ ĐỊCH BẮT TÙ, ĐÀY" in SYSTEM_PROMPT
    assert "THẺ HỘI VIÊN" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG BỎ SÓT" in SYSTEM_PROMPT
    assert "KHÔNG BỊA" in SYSTEM_PROMPT
    assert "4 phần tử" in build_user_prompt([{"index": i, "text": ""} for i in range(4)])
