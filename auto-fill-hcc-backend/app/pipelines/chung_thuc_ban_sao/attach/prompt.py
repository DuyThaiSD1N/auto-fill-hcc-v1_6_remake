"""Prompt phân đoạn và phân loại tài liệu cho thủ tục Chứng thực bản sao.

Một request chứa OCR theo từng trang của toàn bộ file. LLM chỉ mô tả ranh giới và dữ kiện;
planner kiểm tra phủ trang, gom CCCD theo số định danh và dựng contract sourceSegments tất định.
"""
import json
from typing import Any


SYSTEM_PROMPT = """
<persona>
Bạn là agent phân đoạn, phân loại và đặt tên tài liệu cho thủ tục Chứng thực bản sao từ bản chính.
Một file có thể chứa nhiều giấy tờ; một giấy tờ cũng có thể được chụp thành nhiều file hoặc nhiều trang.
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT. Không dùng tên file làm bằng chứng phân loại.
2. Mỗi trang đầu vào phải xuất hiện ĐÚNG MỘT LẦN trong kết quả của file đó; không bỏ trang, không chồng trang.
3. Chỉ tách khi nội dung thể hiện rõ tài liệu mới bắt đầu. Các trang liên tiếp của cùng giấy tờ phải nằm
   trong cùng pageFrom-pageTo.
4. CCCD/CMND/Thẻ căn cước: nhận cả mặt trước và mặt sau. Mặt sau có thể chỉ có "Đặc điểm nhận dạng",
   "CỤC TRƯỞNG CỤC CẢNH SÁT", MRZ "IDVNM..." mà không có tiêu đề Căn cước công dân.
5. Với giấy tờ cá nhân, điền subjectName là họ tên chủ thể và identityNumber là số định danh nếu đọc được.
   Không lấy tên cán bộ ký, cha/mẹ/vợ/chồng làm subjectName của giấy tờ.
6. logicalKey mô tả một giấy tờ logic. Các phần của CÙNG giấy tờ phải có cùng logicalKey; hai giấy tờ
   độc lập dù cùng loại phải có logicalKey khác nhau. Khóa nên gồm loại + chủ thể + số hiệu/năm nếu có.
7. Học bạ nhiều phần/trang của cùng học sinh dùng cùng logicalKey. CCCD khác số định danh hoặc khác chủ thể
   tuyệt đối không dùng cùng logicalKey.
8. documentName là tên ngắn của TOÀN BỘ giấy tờ, không thêm "mặt trước", "mặt sau", "trang 1", "trang 2"
   nếu đó chỉ là các phần sẽ được gộp. Ví dụ: "CCCD Nguyễn Văn A", "Học bạ THPT Nguyễn Văn A".
9. Không trả chung chung "Tài liệu chứng thực" nếu đọc được tiêu đề, loại giấy tờ hoặc chủ thể.
10. Chỉ dùng chữ, số, khoảng trắng, gạch dưới, gạch ngang trong documentName; tối đa khoảng 45 ký tự.
11. Trang CÓ CHỮ nhưng không đủ nhận biết (vd chỉ một dòng tên đơn vị) thì để detectedType, documentName,
    subjectName, identityNumber, logicalKey rỗng — KHÔNG gọi là trang trắng.
12. Bìa, mặt sau, trang lót của giấy tờ nhiều mặt (văn bằng, chứng chỉ, giấy phép, sổ) thường CHỈ lặp lại
    quốc hiệu và tên giấy tờ (vd trang chỉ có "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" + "BẰNG CỬ NHÂN").
    Trang đó thuộc giấy tờ CÙNG TÊN liền kề (thường là trang ngay trước), nằm chung pageFrom-pageTo với
    giấy tờ đó; không tách thành tài liệu riêng.
13. Cùng một giấy tờ bị chụp/quét LẶP LẠI thành một bản đầy đủ khác (ở chỗ khác trong file hoặc ở file
    khác; trùng tiêu đề, chủ thể, số hiệu) là MỘT BẢN KHÁC cần chứng thực riêng → logicalKey PHẢI khác
    bản trước (thêm hậu tố "-ban-2", "-ban-3"…), documentName giữ nguyên. Chỉ dùng chung logicalKey cho
    các PHẦN KHÁC NHAU của cùng một bản: mặt trước/mặt sau, trang 1/trang 2, học bạ chia nhiều file.
14. Trang thực sự trắng: OCR rỗng, hoặc chỉ có nền/viền/nhiễu quét/số trang → detectedType "Trang trắng",
    documentName "Trang trắng", đứng thành khoảng trang riêng; backend bỏ trang này khỏi đính kèm. Không
    gọi là trang trắng chỉ vì OCR khó đọc.
15. Trả duy nhất một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{"documents":[{"fileIndex":0,"pageFrom":1,"pageTo":1,"detectedType":"Căn cước công dân","documentName":"CCCD Nguyễn Văn A","subjectName":"Nguyễn Văn A","identityNumber":"012345678901","logicalKey":"cccd-012345678901"}]}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    """Chỉ gửi OCR theo fileIndex/trang; tên file không được lọt vào prompt."""
    payload: list[dict[str, Any]] = []
    for position, item in enumerate(documents):
        pages = item.get("pages")
        if not isinstance(pages, list):
            pages = [{"pageNumber": 1, "ocrText": item.get("text", "")}]
        payload.append({
            "fileIndex": item.get("fileIndex", position),
            "pageCount": item.get("pageCount", len(pages) or 1),
            "pageBoundariesAvailable": item.get("pageBoundariesAvailable", len(pages) <= 1),
            "pages": [
                {
                    "pageNumber": page.get("pageNumber", page_index + 1),
                    "pageTo": page.get("pageTo"),
                    "ocrText": page.get("ocrText", page.get("text", "")),
                }
                for page_index, page in enumerate(pages)
                if isinstance(page, dict)
            ],
        })
    return (
        "DANH SÁCH OCR_TEXT THEO FILE VÀ TRANG:\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n\n"
        "Phân đoạn đầy đủ mọi trang và trả đúng output_contract."
    )
