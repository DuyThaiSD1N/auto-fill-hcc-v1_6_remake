"""Trích xuất thông tin người nộp từ giấy đề nghị đăng ký hộ kinh doanh bằng Python.

KHÔNG DÙNG NỮA - Declaration.py bị vô hiệu hóa.
Logic mới: Mapper trực tiếp xử lý dựa trên so sánh loginName với ChuHo_HoTen.
"""


def fill_missing(fields: list[dict], ocr_text: str, comp_by_name: dict[str, str], login_name: str = None) -> list[dict]:
    """Không làm gì cả - bị vô hiệu hóa."""
    return fields
