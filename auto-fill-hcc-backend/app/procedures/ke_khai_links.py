"""Link trang kê khai của từng thủ tục trên Cổng DVC quốc gia.

Nguồn dữ liệu: `data/ke_khai_links.json` (trước đây nằm ở auto-fill-hcc-extension/data/
procedure-links.js — đã dồn về backend để extension không phải đóng gói dữ liệu riêng).
`key` trùng key thủ tục trong registry nên chọn link nào là chọn luôn đúng pipeline điền tự động.

Đọc một lần lúc process khởi động, giống app/locations/catalog.py.
"""
import json
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "data" / "ke_khai_links.json"


def _load() -> list[dict]:
    raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    return list(raw["links"])


KE_KHAI_LINKS: list[dict] = _load()
