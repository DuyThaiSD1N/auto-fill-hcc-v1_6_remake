"""Cấp bản sao văn bằng từ sổ gốc: tên dòng kế hoạch đính phải khớp bảng thành phần hồ sơ của MỌI Sở.

Mỗi Sở cấu hình bảng riêng trên dvc.moet.gov.vn: mẫu cũ ("Đơn đề nghị…") và mẫu Thông tư 10/2026 của Sở Quảng Trị
("Phiếu đề nghị…", ủy quyền và chứng minh quan hệ tách hai dòng). Khớp như FE (attach-core.componentTextMatches):
bỏ dấu, chữ thường, chuỗi con hai chiều.
"""
import re
import unicodedata

from app.pipelines.cap_ban_sao_van_bang_so_goc.attach import planner

_OLD_ROWS = [
    "Đơn đề nghị cấp bản sao văn bằng, chứng chỉ, trong đó cung cấp các thông tin về văn bằng, chứng chỉ đã được cấp.",
    "Trường hợp người yêu cầu cấp bản sao văn bằng, chứng chỉ từ sổ gốc là người đại diện theo pháp luật, người đại "
    "diện theo ủy quyền của người được cấp bản chính văn bằng, chứng chỉ; cha, mẹ, con; vợ, chồng; anh, chị, em ruột; "
    "người thừa kế khác … thì phải xuất trình giấy ủy quyền (đối với người được ủy quyền) hoặc giấy tờ chứng minh quan hệ",
    "Trường hợp người yêu cầu cấp bản sao văn bằng, chứng chỉ từ sổ gốc gửi yêu cầu qua bưu điện thì phải gửi bản sao "
    "có chứng thực giấy tờ quy định tại điểm a, b, c nêu trên kèm theo 01 (một) phong bì dán tem",
]
_QUANG_TRI_ROWS = [
    "Phiếu đề nghị cấp bản sao từ sổ gốc (theo Mẫu tại Phụ lục VI Thông tư số 10/2026/TT-BGDĐT, đính kèm theo Quyết "
    "định này) (Click chuột vào đây để mở Biểu mẫu giấy tờ)",
    "Trường hợp người yêu cầu cấp bản sao văn bằng, chứng chỉ từ sổ gốc là người đại diện theo pháp luật, người đại "
    "diện theo ủy quyền của người được cấp bản chính văn bằng, chứng chỉ thì phải có giấy ủy quyền (đối với người được "
    "ủy quyền);",
    "Trường hợp người yêu cầu cấp bản sao văn bằng, chứng chỉ từ sổ gốc là cha, mẹ, con; vợ/chồng; anh, chị, em ruột; "
    "người thừa kế khác của người được cấp văn bằng, chứng chỉ … thì phải có giấy tờ … chứng minh quan hệ với người "
    "được cấp văn bằng, chứng chỉ.",
]


def _fe_fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.replace("Đ", "D").replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").lower()
    return " ".join(re.sub(r"[‐-―-]", " ", text).split())


def _matching_rows(component: str, rows: list[str]) -> list[int]:
    want = _fe_fold(component)
    return [i for i, row in enumerate(rows, 1) if want in _fe_fold(row) or _fe_fold(row) in want]


def test_each_planned_row_matches_exactly_one_row_on_both_templates():
    expected = {"don_bm04": 1, "van_bang": 1, "cccd": 1, "uy_quyen": 2}
    for doc_type, row in expected.items():
        component = planner._ROWS[doc_type]["componentName"]
        assert _matching_rows(component, _OLD_ROWS) == [row], (doc_type, "mẫu cũ")
        assert _matching_rows(component, _QUANG_TRI_ROWS) == [row], (doc_type, "Quảng Trị")


def test_plan_items_carry_the_shared_component_names():
    items, _warnings, _classified = planner.build_plan_items(
        [{"name": "phieu.pdf"}, {"name": "uq.pdf"}], [], {0: "don_bm04", 1: "uy_quyen"})
    assert [item["componentName"] for item in items] == ["đề nghị cấp bản sao", "người đại diện theo ủy quyền"]
    assert all(item["target"] == "attp-row" for item in items)
