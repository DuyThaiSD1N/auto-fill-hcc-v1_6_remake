# -*- coding: utf-8 -*-
"""Các lời nhắc (prompt) gửi cho model.

Mỗi yêu cầu gồm:
  - system: PROMPT_HE_THONG (nguyên tắc đọc và quy ước định dạng Markdown, trong tệp prompt_he_thong.md),
    nối thêm mẫu trình bày tham khảo nếu có (system_prompt).
  - user: lần lượt [chú thích ảnh 1, ảnh 1, chú thích ảnh 2, ảnh 2, ...] rồi một lời kết cho biết đây là trang nào
    (loi_ket_trang, khi đọc cả trang) hoặc phần nào của trang (loi_ket_phan, khi tự cắt 4 phần),
    cộng ghi chú của người dùng nếu có (ghi_chu_nguoi_dung).

Câu chữ giống hệt web Bàn đọc giấy tờ (app.py: page_closing, part_closing, hint_text; ocr_engine.py: system_prompt).
"""
from __future__ import annotations

from pathlib import Path

# Prompt hệ thống đang dùng trên web 1 (qwen3.6-35b). Sửa trực tiếp trong prompt_he_thong.md.
PROMPT_HE_THONG = (Path(__file__).parent / "prompt_he_thong.md").read_text(encoding="utf-8")


def system_prompt(base: str, template: str) -> str:
    template = (template or "").strip()
    if not template:
        return base
    return (
        base
        + "\n\nMẪU ĐỊNH DẠNG THAM KHẢO\n"
        + "Chỉ dùng mẫu dưới đây để tham khảo cách trình bày. Tuyệt đối không lấy dữ liệu, tên, số liệu từ mẫu.\n"
        + "<mau_tham_khao>\n" + template + "\n</mau_tham_khao>"
    )


def ghi_chu_nguoi_dung(ghi_chu: str) -> str:
    """Ghi chú ngữ cảnh của người dùng, ví dụ "căn cước 2 mặt". Model chỉ dùng để hiểu, không chép vào kết quả."""
    ghi_chu = (ghi_chu or "").strip()
    return (f"\nThông tin thêm từ người dùng (chỉ để hiểu ngữ cảnh, không phải dữ liệu để chép): {ghi_chu}"
            if ghi_chu else "")


def loi_ket_trang(i: int, so_trang: int, ten_tep: str) -> str:
    """Lời kết khi đọc cả trang i (đếm từ 0)."""
    return (f"Đây là trang {i + 1} trong tổng số {so_trang} trang của tệp \"{ten_tep}\". "
            f"Chỉ chép trang này, tiêu đề ghi TRANG {i + 1}.")


def loi_ket_phan(i: int, k: int, n: int, so_trang: int, ten_tep: str) -> str:
    """Lời kết khi đọc phần k/n (đếm từ 0) của trang i đã được cắt ngang."""
    t = (f"Ảnh này là phần {k + 1}/{n} của trang {i + 1}/{so_trang} trong tệp \"{ten_tep}\". Trang đã được cắt "
         f"ngang thành {n} phần theo thứ tự từ trên xuống và phóng to; mỗi phần được chép riêng rồi ghép lại theo "
         "đúng thứ tự. Chỉ chép nội dung có trong ảnh này, từ trên xuống, theo đúng nguyên tắc và quy ước định dạng.")
    if k == 0:
        t += f" Đây là phần đầu trang: bắt đầu bằng tiêu đề TRANG {i + 1} như quy ước."
    else:
        t += (" Đây là phần tiếp theo của trang: không thêm tiêu đề trang. Nếu đầu ảnh là các hàng tiếp theo của một "
              "bảng ở phần trước (không có hàng tiêu đề cột), vẫn chép thành bảng với đúng số cột như trên giấy.")
    if k < n - 1:
        t += " Không thêm dòng kẻ --- ở cuối."
    t += (" Với bảng: chỉ chép các hàng có chữ, bỏ qua các hàng trống, không lặp lại hàng tiêu đề bảng, dòng kẻ |---| "
          "có đúng số cột của bảng. Chép hết chữ trong ảnh thì dừng.")
    return t
