"""Ngữ cảnh cho hai agent của trợ lý hộ kinh doanh: bản đồ các khối và mục, mục đang hỏi, hội thoại gần."""
from app.channels.handfree.chat import store

DIALOGUE_TURNS = 10     # cặp lượt (trợ lý + công dân) đưa cho agent điều phối — đủ thấy giá trị vừa đọc lại để sửa
SPECIALIST_TURNS = 10   # agent chuyên môn: đủ xa để lấy lại giá trị công dân "đã nói ở trên"
_STATUS = {"dang_mo": "ĐANG MỞ", "da_luu": "đã lưu", "sap_toi": "chưa tới"}


def with_codes(catalog: list[dict]) -> dict[str, dict]:
    """Mỗi mục một mã ngắn m1, m2… cho agent tham chiếu (mã mục thật dài, dễ chép sai)."""
    out = {}
    for i, item in enumerate(catalog, 1):
        item["code"] = f"m{i}"
        out[item["code"]] = item
    return out


def code_of(catalog: list[dict], key: str) -> str:
    return next((c["code"] for c in catalog if c.get("key") == key), "")


def form_block(catalog: list[dict]) -> str:
    lines, block = [], None
    for item in catalog:
        if item["block"] != block:
            block = item["block"]
            lines.append(f"## Khối {block} ({_STATUS.get(item['status'], item['status'])})")
        lines.append(f"{item['code']} · {item['label']} · {item['format']} · {item['value']}"
                     f"{' · bỏ qua được' if item.get('skip') else ''}")
    return "\n".join(lines) or "(không có)"


def current_block(catalog: list[dict], current: dict) -> str:
    key = current.get("key") or ""
    if current.get("confirm"):
        return (f"Trợ lý vừa đọc bảng tóm tắt khối \"{current.get('block')}\" và hỏi công dân: đúng thì lưu khối này, "
                f"sai chỗ nào thì nói để sửa.")
    item = next((c for c in catalog if c.get("key") == key), None)
    if not item:
        return f"(trợ lý vừa hỏi: {current.get('question') or 'không rõ'})"
    part = f" — đang hỏi phần {current['part']}" if current.get("part") else ""
    return f"{item['code']} · {item['label']} (khối {item['block']}){part}\nCâu trợ lý vừa hỏi: {current.get('question')}"


def thread_block(thread: list[str]) -> str:
    return "\n".join(f'- "{t}"' for t in thread) or "(không có)"


def dialogue_block(conv: dict, turns: int) -> str:
    lines = [("TRỢ LÝ: " if m["role"] == "assistant" else "CÔNG DÂN: ") + m["content"]
             for m in store.recent_dialogue(conv, turns * 2)]
    return "\n".join(lines) or "(chưa có)"
