# -*- coding: utf-8 -*-
"""Cấu hình đọc giấy tờ. Giá trị mặc định là đúng cấu hình web 1 đang chạy với qwen3.6-35b.

Dùng: cfg = tao_cau_hinh(base_url="http://may-chu:8010/v1", model="qwen3.6-35b")
Khóa API của máy chủ (nếu có) lấy từ tham số api_key hoặc biến môi trường OCR_SERVER_API_KEY.
"""
from __future__ import annotations

import copy
import os

from . import tien_xu_ly as tx
from .prompt import PROMPT_HE_THONG

CAU_HINH_MAC_DINH = {
    # máy chủ chuẩn OpenAI (vLLM, SGLang...): POST {base_url}/chat/completions
    "base_url": "",                    # đọc từ .env (OCR_QWEN_BASE_URL) qua _chung/may_qwen.py
    "model": "qwen3.6-35b",
    "api_key": "",
    "temperature": 0.1,
    "max_tokens": 8192,               # trần token đầu ra mỗi lần gửi khi đọc cả trang
    "disable_thinking": True,         # chat_template_kwargs.enable_thinking = false
    "repetition_penalty": 1.05,

    # ảnh gửi đi
    "max_images": 5,                  # tối đa số ảnh mỗi lần gửi: 1 ảnh toàn trang + tối đa 4 dải phóng to
    "image_mp": 1.2,                  # mỗi ảnh tối đa khoảng 1,2 triệu điểm ảnh
    "long_edge": 2048,                # cạnh dài tối đa mỗi ảnh
    "zoom": "auto",                   # auto: dải theo dòng chữ | 2x2 | 3x3 | off: chỉ ảnh toàn trang (đọc kém hơn hẳn)
    "image_format": "jpeg",           # jpeg (chất lượng 92) | png

    # chạy song song
    "song_song": 4,                   # số yêu cầu gửi cùng lúc: số trang (không cắt) hoặc số phần (tự cắt 4 phần)

    # tự cắt 4 phần
    "so_phan": 4,                     # số dải ngang khi tự cắt trang dọc khổ A4
    "max_tokens_moi_phan": 1536,      # trần token đầu ra của mỗi phần (một phần bình thường cần dưới 800)

    # tiền xử lý (xem tien_xu_ly.DEFAULT_PREP)
    "prep": {
        "auto_orient": True,          # tự xoay 90°/180°/270° theo chiều chữ
        "deskew": True,               # chỉnh nghiêng nhỏ
        "illum": True,                # cân bằng sáng
        "clahe": False,               # tăng tương phản
        "pattern": False,             # lọc hoa văn nền và dấu đỏ
        "denoise": "zoom",            # off | zoom (chỉ vùng phải phóng to) | on
        "sharpen": "strong",          # off | light | medium | strong
        "binarize": False,            # chuyển đen trắng
    },

    # lời nhắc
    "prompt_he_thong": PROMPT_HE_THONG,
    "mau_trinh_bay": "",              # mẫu trình bày tham khảo (không bắt buộc)
}


def tao_cau_hinh(**ghi_de) -> dict:
    """Cấu hình mặc định, ghi đè các khóa được truyền vào. "prep" được gộp từng khóa, không thay cả khối."""
    cfg = copy.deepcopy(CAU_HINH_MAC_DINH)
    prep = ghi_de.pop("prep", None)
    unknown = set(ghi_de) - set(cfg)
    if unknown:
        raise KeyError(f"Khóa cấu hình không có: {', '.join(sorted(unknown))}")
    cfg.update(ghi_de)
    if prep:
        cfg["prep"].update(prep)
    cfg["prep"] = tx.normalize_prep(cfg["prep"])
    if not cfg["api_key"]:
        cfg["api_key"] = os.environ.get("OCR_SERVER_API_KEY", "")
    return cfg
