import json
from typing import Any


SYSTEM_PROMPT = (
    "Bạn là agent phân loại tài liệu đính kèm cho thủ tục thay đổi/cải chính/bổ sung thông tin "
    "hộ tịch, xác định lại dân tộc. Trả về JSON object duy nhất, không giải thích. "
    "Dựa vào OCR là nguồn chính; dùng tên file chỉ khi OCR không đủ. "
    "Mỗi tài liệu trả type thuộc đúng một trong: ho_tich_doc, authorization, identity, other. "
    "ho_tich_doc = giấy tờ hộ tịch làm căn cứ: GIẤY KHAI SINH, GIẤY ĐĂNG KÝ KẾT HÔN / TRÍCH LỤC "
    "KẾT HÔN, giấy lịch sử có tên HÔN THÚ / GIẤY CHỨNG NHẬN TẠM THAY HÔN THÚ, "
    "GIẤY KHAI TỬ / TRÍCH LỤC KHAI TỬ. "
    "authorization = văn bản ủy quyền. "
    "identity = CCCD/CMND/căn cước/hộ chiếu. "
    "Bao gồm CẢ MẶT SAU thẻ CCCD/căn cước (chỉ có 'Đặc điểm nhận dạng', vân tay, "
    "'CỤC TRƯỞNG CỤC CẢNH SÁT', dòng MRZ 'IDVNM...', KHÔNG có tiêu đề 'Căn cước công dân') "
    "— VẪN là identity. "
    "other = giấy tờ khác. "
    "documentName là tên ngắn gọn, CỤ THỂ theo NỘI DUNG file (dùng làm tên thành phần hồ sơ): "
    "TUYỆT ĐỐI không đặt chung chung 'Tài liệu'/'Tài liệu khác'; nêu đúng loại giấy tờ đọc được "
    "(vd 'Trích lục kết hôn', 'Giấy khai sinh', 'Căn cước công dân'). "
    "Nhiều tài liệu cùng loại thì documentName phải KHÁC nhau (thêm tên người/số/đặc điểm). "
    "Chỉ dùng chữ, số, khoảng trắng, gạch dưới, gạch ngang; tối đa ~50 ký tự. "
    "Nếu OCR quá thiếu để biết loại giấy tờ thì để documentName rỗng."
)


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    return (
        "DANH SÁCH OCR:\n"
        f"{json.dumps(documents, ensure_ascii=False)}\n\n"
        'Schema bắt buộc: {"documents":[{"index":0,"type":"ho_tich_doc","documentName":"Trích lục kết hôn"}]}'
    )
