# -*- coding: utf-8 -*-
"""Phần dùng chung cho hai chế độ đọc: gọi máy chủ Qwen, cộng token, cảnh báo, kết quả trả về."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from . import chuan_bi_anh as cb
from . import goi_qwen as gq
from .prompt import system_prompt

NOI_TRANG = "\n\n---\n\n"           # kết quả các trang nối với nhau bằng dòng kẻ ---


class MayChuQwen:
    """Gọi model trên máy chủ chuẩn OpenAI theo cấu hình (như Runner của web với nguồn "máy chủ riêng")."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.label = f"{cfg['model']} (máy chủ riêng)"
        self.spec = cb.openai_spec(cfg["image_mp"], cfg["long_edge"], self.label)   # giới hạn kích thước mỗi ảnh
        self.max_images = max(1, int(cfg["max_images"]))
        self.system = system_prompt(cfg["prompt_he_thong"], cfg.get("mau_trinh_bay", ""))

    def stream(self, content: list, max_tokens: int | None = None):
        """Gửi một yêu cầu; sinh các sự kiện {"type": "status" | "text" | "usage", ...}.
        Dừng ngay khi model bắt đầu lặp vô hạn (detect_loop)."""
        c = self.cfg
        cap = c["max_tokens"] if max_tokens is None else min(max_tokens, c["max_tokens"])
        return gq.stream_openai(c["base_url"], c.get("api_key", ""), c["model"], self.system, content,
                                c["temperature"], cap, c.get("disable_thinking", True),
                                c.get("repetition_penalty", 1.0), stop_check=gq.detect_loop)

    def doc(self, content: list, max_tokens: int | None = None, bao=None) -> tuple[str, dict]:
        """Gửi một yêu cầu, trả (toàn bộ chữ model viết, sự kiện usage). bao(su_kien) nhận từng đoạn chữ nếu cần."""
        text, usage = "", {}
        for ev in self.stream(content, max_tokens):
            if ev["type"] == "text":
                text += ev["text"]
            elif ev["type"] == "usage":
                usage = ev
            if bao:
                bao(ev)
        return text, usage


@dataclass
class KetQua:
    markdown: str = ""                    # kết quả Markdown của cả tệp, các trang nối bằng dòng ---
    so_trang: int = 0
    giay: float = 0.0                     # thời gian đọc (giây), gồm cả tiền xử lý
    input_tokens: int = 0
    output_tokens: int = 0
    che_do: str = ""                      # "tach_4_phan" | "khong_tach"
    so_trang_da_cat: int = 0              # số trang thật sự được cắt 4 phần (trang không phải A4 dọc thì đọc cả trang)
    canh_bao: list = field(default_factory=list)
    trang: list = field(default_factory=list)   # mỗi trang: {"trang", "cach_doc", "buoc", "chieu_chu", "so_anh", ...}


class TongHop:
    """Cộng token của các yêu cầu (an toàn khi chạy song song) và ghi cảnh báo giống web."""

    def __init__(self, ket_qua: KetQua):
        self.kq = ket_qua
        self._lock = threading.Lock()

    def them(self, usage: dict, noi: str = "") -> None:
        with self._lock:
            self.kq.input_tokens += usage.get("input_tokens") or 0
            self.kq.output_tokens += usage.get("output_tokens") or 0
            warn = canh_bao(usage)
            if warn:
                self.kq.canh_bao.append(f"{noi}: {warn}" if noi else warn)


def canh_bao(usage: dict) -> str | None:
    """Cảnh báo theo lý do dừng của model (như add_usage của web)."""
    r = usage.get("stop_reason")
    if r == "max_tokens":
        return "Kết quả bị cắt vì chạm giới hạn độ dài. Tăng max_tokens rồi đọc lại."
    if r == "refusal":
        return "Model từ chối xử lý ảnh này."
    if r == "loop":
        return "Model bị kẹt lặp lại cùng một nội dung nên đã được dừng sớm và bỏ phần lặp; nên xem lại chỗ này."
    return None


def bao_su_kien(bao, su_kien: dict) -> None:
    if bao:
        bao(su_kien)
