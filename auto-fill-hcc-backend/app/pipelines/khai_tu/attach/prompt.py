import json
from typing import Any


SYSTEM_PROMPT = (
    "Bạn là agent phân loại tài liệu đính kèm cho thủ tục đăng ký khai tử. "
    "Trả về JSON object duy nhất, không giải thích. "
    "Dựa vào OCR là nguồn chính; dùng tên file chỉ khi OCR không đủ thông tin. "
    "Mỗi tài liệu phải trả type thuộc đúng một trong các giá trị sau: "
    "requester_identity, paper_declaration, death_notice, death_event_proof, "
    "death_place_proof, other. "
    "requester_identity = CCCD/CMND/hộ chiếu/giấy tờ tùy thân của người yêu cầu. "
    "Bao gồm CẢ MẶT SAU thẻ CCCD/căn cước (chỉ có 'Đặc điểm nhận dạng', vân tay, "
    "'CỤC TRƯỞNG CỤC CẢNH SÁT', dòng MRZ 'IDVNM...', KHÔNG có tiêu đề 'Căn cước công dân') "
    "— VẪN thuộc loại giấy tùy thân này. "
    "paper_declaration = tờ khai đăng ký khai tử bản giấy, có các trường tương tự mẫu form web. "
    "death_notice = giấy báo tử, giấy chứng tử, hoặc giấy tờ thay Giấy báo tử do cơ quan có thẩm quyền cấp. "
    "death_event_proof = giấy tờ/tài liệu/chứng cứ chứng minh sự kiện chết khi người chết đã lâu, "
    "không có giấy báo tử, hoặc văn bản ủy quyền liên quan đăng ký khai tử. "
    "death_place_proof = giấy tờ chứng minh nơi người chết chết hoặc nơi phát hiện thi thể khi không xác định "
    "được nơi cư trú cuối cùng. "
    "title là tên tài liệu tiếng Việt ngắn để hiển thị; nếu type requester_identity thì title là "
    "'Căn cước công dân người yêu cầu'; nếu type paper_declaration thì title là "
    "'Tờ khai đăng ký khai tử bản giấy'. "
    "documentName là tên ngắn gọn, CỤ THỂ theo NỘI DUNG file (dùng làm tên thành phần hồ sơ): "
    "TUYỆT ĐỐI không đặt chung chung 'Tài liệu khác'/'Tài liệu'; nêu đúng loại giấy tờ đọc được. "
    "Nhiều tài liệu cùng loại thì documentName phải KHÁC nhau (thêm tên người/số/đặc điểm). "
    "Chỉ dùng chữ, số, khoảng trắng, gạch dưới, gạch ngang; tối đa ~50 ký tự. "
    "Nếu OCR quá thiếu để biết loại giấy tờ thì để documentName rỗng."
)


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    return (
        "DANH SÁCH OCR:\n"
        f"{json.dumps(documents, ensure_ascii=False)}\n\n"
        'Schema bắt buộc: {"documents":[{"index":0,"type":"death_notice","title":"Giấy báo tử","documentName":"Giấy báo tử"}]}'
    )
