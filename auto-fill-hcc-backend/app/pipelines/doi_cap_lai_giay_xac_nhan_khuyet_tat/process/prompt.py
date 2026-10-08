"""Rule prompt cho "Đổi, cấp lại Giấy xác nhận khuyết tật".

Lấy nguyên rule của khuyet_tat (cùng Mẫu số 01), chỉ thay khối <procedure> và <proposal_rules>.
"""

import re

from app.pipelines.khuyet_tat.process.prompt import EXTRA_RULES as _BASE_RULES

_PROCEDURE = """<procedure>
Thủ tục: Đổi, cấp lại Giấy xác nhận khuyết tật.
Đầu vào thường gồm:
1. ĐƠN ĐỀ NGHỊ XÁC ĐỊNH, XÁC ĐỊNH LẠI MỨC ĐỘ KHUYẾT TẬT VÀ CẤP, CẤP ĐỔI, CẤP LẠI GIẤY XÁC NHẬN KHUYẾT TẬT (Mẫu số 01), đã tích ô "Cấp lại" hoặc "Cấp đổi".
2. CCCD/CMND của người đứng đơn/người đại diện hợp pháp hoặc người khuyết tật.
Có thể kèm Giấy xác nhận khuyết tật cũ hoặc giấy tờ khác để đối chiếu thông tin người khuyết tật.
Trường hợp cấp đổi, đơn được phép bỏ trống Mục III (dạng khuyết tật, mức độ): khi đó KHÔNG trả KhuyetTat_* và MucDo_HoatDong.
</procedure>"""

_PROPOSAL = """<proposal_rules>
- DeNghi_NoiDung = "cap_lai" khi ô "Cấp lại Giấy xác nhận khuyết tật" được đánh dấu.
- DeNghi_NoiDung = "cap_doi" khi ô "Cấp đổi Giấy xác nhận khuyết tật" được đánh dấu.
- Chỉ chọn theo ô được đánh dấu rõ (X, ☒, ☑, ✓). Ô "Xác định..."/"Xác định lại..." được tích hoặc không rõ ô nào thì bỏ field.
- DeNghi_LyDo chỉ trả khi OCR có câu ghi rõ lý do; Mẫu số 01 không có mục lý do nên KHÔNG suy lý do từ ô cấp lại/cấp đổi.
  "sai thông tin so với căn cước/CCCD/giấy tờ" -> "sai_thong_tin"; "bị mất", "đánh mất", "hư hỏng", "rách", "nhòe" -> "mat_hu_hong";
  "được cấp khi dưới 6 tuổi, nay đã đủ 6 tuổi" -> "du_6_tuoi".
</proposal_rules>"""


def _replace_block(text: str, tag: str, block: str) -> str:
    pattern = re.compile(rf"<{tag}>.*?</{tag}>", re.S)
    new_text, count = pattern.subn(lambda _m: block, text, count=1)
    if count != 1:
        # Rule gốc đổi cấu trúc thì phải sửa ở đây, không âm thầm giữ rule xác định mức độ.
        raise RuntimeError(f"khuyet_tat EXTRA_RULES thiếu khối <{tag}>")
    return new_text


EXTRA_RULES = _replace_block(
    _replace_block(_BASE_RULES, "procedure", _PROCEDURE),
    "proposal_rules",
    _PROPOSAL,
)
