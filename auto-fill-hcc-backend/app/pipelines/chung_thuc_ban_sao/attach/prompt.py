"""Prompt phân đoạn và phân loại tài liệu cho thủ tục Chứng thực bản sao.

Một request chứa OCR theo từng trang của toàn bộ file. LLM chỉ mô tả ranh giới và dữ kiện;
planner kiểm tra phủ trang, gom CCCD theo số định danh và dựng contract sourceSegments tất định.
"""
import json
from typing import Any


DOCUMENT_NAME_RULES = """
<document_name_rules>
documentName hiện thành TÊN THÀNH PHẦN HỒ SƠ và TÊN FILE trên cổng. Ô này nhận tối đa 50 ký tự, dài hơn
bị CẮT CỤT giữa chừng. Đặt tên TỐI ĐA 40 ký tự; đọc vào phải biết ngay là giấy gì, bản nào, của ai.
1. Cấu trúc: [Loại giấy] + [Mốc phân biệt] + [Chủ thể].
   · Loại giấy: lấy từ TIÊU ĐỀ in trên giấy; bỏ quốc hiệu, "(Bản dành cho …)", "của cá nhân", phần
     "Về việc …" dài dòng.
   · Mốc phân biệt: năm, năm học, quý, số hiệu văn bản — thứ phân biệt giấy này với giấy CÙNG LOẠI khác.
   · Chủ thể: người đứng tên giấy tờ cá nhân (không phải cán bộ ký).
2. Quá 40 ký tự thì rút gọn LẦN LƯỢT, đủ ngắn thì dừng:
   a. bỏ chữ thừa: "năm", "về việc", "của", "cho";
   b. viết tắt thuật ngữ quen dùng: ĐG (đánh giá), XL (xếp loại), CL (chất lượng), QĐ (quyết định),
      GCN (giấy chứng nhận), QSDĐ, CCCD, HĐ (hợp đồng), UBND, THCS, THPT, CĐ, ĐH;
   c. họ tên chủ thể → chỉ giữ TÊN GỌI (chữ cuối cùng của họ tên);
   d. vẫn dài thì bỏ chủ thể.
   TUYỆT ĐỐI không bỏ loại giấy hoặc mốc phân biệt.
3. Mốc viết liền bằng gạch ngang, KHÔNG dùng "/": "Quý II-2026", "2024-2025", "QĐ 12-QĐ-UBND".
   Không để tên KẾT THÚC bằng một con số đứng riêng (hệ thống hiểu nhầm là số thứ tự): đặt mốc TRƯỚC
   chủ thể, không viết "… năm 2025" ở cuối tên.
4. Chỉ dùng chữ, số, khoảng trắng, gạch dưới, gạch ngang. Không tự thêm số thứ tự "2", "3".
Ví dụ (tiêu đề in trên giấy + chủ thể → documentName):
   · "PHIẾU ĐÁNH GIÁ, XẾP LOẠI CHẤT LƯỢNG VIÊN CHỨC Năm học 2022-2023" + Lê Thị Hoa
     → "Phiếu ĐG XL CL viên chức 2022-2023 Hoa"
   · "BẢN TỰ ĐÁNH GIÁ, XẾP LOẠI CỦA CÁ NHÂN Quý II năm 2026" + Trần Văn Nam → "Bản tự ĐG XL Quý II-2026 Nam"
   · "BẰNG TỐT NGHIỆP TRUNG HỌC PHỔ THÔNG" + Lê Minh Anh → "Bằng tốt nghiệp THPT Lê Minh Anh"
   · "QUYẾT ĐỊNH Số 45/QĐ-UBND Về việc nâng bậc lương thường xuyên…" → "QĐ 45-QĐ-UBND nâng bậc lương"
   · "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU NHÀ Ở…" + Phạm Văn Hùng → "GCN QSDĐ Phạm Văn Hùng"
   · "CĂN CƯỚC CÔNG DÂN" + Nguyễn Văn Bình → "CCCD Nguyễn Văn Bình"
</document_name_rules>
""".strip()


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
8. documentName là tên của TOÀN BỘ giấy tờ, không thêm "mặt trước", "mặt sau", "trang 1", "trang 2"
   nếu đó chỉ là các phần sẽ được gộp. Đặt tên theo document_name_rules.
9. Không trả chung chung "Tài liệu chứng thực" nếu đọc được tiêu đề, loại giấy tờ hoặc chủ thể.
10. Hồ sơ có từ 2 giấy CÙNG LOẠI trở lên (vd nhiều phiếu đánh giá các năm, nhiều quyết định) thì
    documentName của chúng PHẢI khác nhau nhờ mốc phân biệt — trừ bản quét lặp ở quy tắc 13.
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

""" + DOCUMENT_NAME_RULES + """

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
