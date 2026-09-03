import json
from typing import Any

from .catalog import llm_options


SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại tài liệu cho thủ tục "Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền
với đất" trên cổng DVC tỉnh Bắc Ninh. Đọc OCR của từng FILE; một file có thể là PDF gộp nhiều giấy tờ.
</persona>

<danh_muc_nhan>
{llm_options()}
</danh_muc_nhan>

<critical_rules>
1. Chỉ dựa trên OCR_TEXT, không dùng tên hay thứ tự file.
2. Trả labels là MẢNG gồm mọi nhãn chắc chắn có trong file (PDF gộp có thể chứa nhiều loại).
3. "phieu_01a" là Phiếu yêu cầu đăng ký biện pháp bảo đảm theo Mẫu số 01a.
4. "hop_dong_bao_dam" là hợp đồng thế chấp/bảo đảm (kể cả có lời chứng công chứng).
5. "gcn_qsdd" là Giấy chứng nhận quyền sử dụng đất; "gcn_dkdn" là GCN đăng ký doanh nghiệp/hộ kinh doanh.
6. Chỉ trả "khac" khi không xác định được nhãn cụ thể nào.
7. documentName phải là tên tiếng Việt cụ thể theo nội dung; không dùng "Tài liệu bổ sung".
8. Trả duy nhất JSON, không markdown và không giải thích.
</critical_rules>

<output_contract>
{{"documents":[{{"index":0,"labels":["phieu_01a","hop_dong_bao_dam","gcn_qsdd"],"documentName":"Hồ sơ đăng ký thế chấp"}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "OCR_TEXT TỪNG FILE:\n" + json.dumps(payload, ensure_ascii=False)
