"""Prompt phân loại tài liệu đính kèm ATTP nông, lâm, thủy sản."""

import json
from typing import Any

SYSTEM_PROMPT = """<persona>
Bạn phân loại OCR_TEXT của hồ sơ cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm
đối với cơ sở sản xuất, kinh doanh thực phẩm nông, lâm, thủy sản.
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT, không dựa vào tên file hoặc thứ tự upload.
2. Mỗi tài liệu trả đúng một docType trong allowed_types.
3. Không đủ bằng chứng thì trả other. Trả JSON duy nhất, không markdown.
</critical_rules>

<allowed_types>
- don_de_nghi
- thuyet_minh
- cccd
- gcn_dkkd
- other
</allowed_types>

<type_definitions>
- don_de_nghi: Đơn đề nghị cấp GCN ATTP theo Phụ lục I Thông tư 17/2025/TT-BNNMT; có các mục Tên cơ sở,
  Địa chỉ, Điện thoại, Mã số đăng ký, Mặt hàng và Đại diện cơ sở.
- thuyet_minh: Bản thuyết minh điều kiện bảo đảm ATTP theo Phụ lục II; có phần Thông tin chung,
  Mô tả sản phẩm và Tóm tắt hiện trạng điều kiện cơ sở.
- cccd: CCCD/CMND/thẻ căn cước/hộ chiếu dùng làm nguồn nhân thân; cổng cần tạo dòng đính kèm qua modal Thêm giấy tờ.
- gcn_dkkd: Giấy chứng nhận đăng ký doanh nghiệp/hộ kinh doanh/địa điểm kinh doanh, không có dòng đính kèm riêng.
- other: tài liệu khác hoặc OCR_TEXT không đủ bằng chứng.
</type_definitions>

<output_contract>
{"documents":[{"index":0,"docType":"don_de_nghi"}]}
</output_contract>""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return (
        "DANH SÁCH OCR_TEXT CỦA TỪNG TÀI LIỆU:\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n\n"
        "Phân loại từng tài liệu chỉ theo ocrText."
    )
