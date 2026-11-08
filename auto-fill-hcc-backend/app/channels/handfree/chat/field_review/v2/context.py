"""Dựng ngữ cảnh cho hai agent của vòng bổ sung bản 2: bản đồ tờ khai, ô đang hỏi, nhật ký điền/sửa, hội thoại gần."""
from dataclasses import dataclass, field as dc_field

from app.channels.handfree.chat import store

DIALOGUE_TURNS = 5          # lượt hội thoại (mỗi lượt = câu trợ lý + câu công dân) đưa cho agent điều phối
SPECIALIST_TURNS = 10       # agent chuyên môn: đủ xa để lấy lại giá trị công dân "đã nói ở trên"
LOG_SHOWN = 5
_MAX_FIELDS = 200
_VALUE_CUT = 60
_KIND_VI = {"text": "chữ", "number": "số", "date": "ngày", "select": "chọn trong danh sách", "radio": "tích chọn"}

COMMANDS = """- Điều chỉnh / thêm / chụp lại / scan lại giấy tờ đã gửi
- Điền lại tờ khai từ đầu theo giấy tờ
- Làm thủ tục khác, quay về chọn thủ tục
- Hỏi về hồ sơ, giấy tờ cần nộp, các bước tiếp theo"""


@dataclass
class Context:
    fields: list[dict] = dc_field(default_factory=list)
    by_code: dict[str, dict] = dc_field(default_factory=dict)
    current: dict | None = None
    partial_catalog: bool = True


def kind_vi(field: dict) -> str:
    return _KIND_VI.get(str(field.get("kind") or ""), "")


def _cut(value) -> str:
    text = str(value or "").strip()
    return text if len(text) <= _VALUE_CUT else text[:_VALUE_CUT] + "…"


def build(st: dict) -> Context:
    """Gộp các nguồn biết về ô: danh sách cả tờ khai (extension gửi khi có) → ô đã qua → nhật ký; ô đang hỏi đè bản
    giàu thông tin nhất (có danh sách lựa chọn). Mỗi ô một mã ngắn o1, o2… cho agent tham chiếu."""
    ctx = Context(current=st.get("current"), partial_catalog=not st.get("catalog"))
    seen: dict[str, dict] = {}

    def add(item: dict) -> None:
        key = item.get("key")
        if not key or len(ctx.fields) >= _MAX_FIELDS:
            return
        if key in seen:
            seen[key].update({k: v for k, v in item.items() if v not in (None, "", [])})
            return
        entry = dict(item)
        seen[key] = entry
        ctx.fields.append(entry)

    for item in st.get("catalog") or []:
        add(item)
    for item in st.get("visited") or []:
        add(item)
    for entry in st.get("log") or []:
        add({"key": entry["key"], "label": entry.get("label"), "where": entry.get("where"), "value": entry.get("new")})
    if ctx.current:
        add(dict(ctx.current))
    for i, item in enumerate(ctx.fields, 1):
        item["code"] = f"o{i}"
        ctx.by_code[item["code"]] = item
    if ctx.current:
        ctx.current = seen.get(ctx.current.get("key")) or ctx.current
    return ctx


def code_of(ctx: Context, key: str) -> str:
    return next((f["code"] for f in ctx.fields if f.get("key") == key), "")


def part_of(item: dict) -> str:
    """Phần của tờ khai (Bên nam / Bên nữ…). Ô trong khối địa chỉ có `where` là tên khối ("Nơi cư trú") — giống nhau ở
    hai bên — nên giữ thêm `part` lấy từ tiêu đề phần của trang."""
    return item.get("part") or item.get("where") or "Tờ khai"


def label_of(item: dict) -> str:
    """Nhãn đủ nghĩa: ô trong khối địa chỉ ghép tên khối ("Nơi cư trú – Phường/Xã")."""
    label, where = item.get("label") or "", item.get("where") or ""
    return f"{where} – {label}" if where and item.get("part") and where != item["part"] else label


def form_block(ctx: Context) -> str:
    lines, current_part = [], None
    if ctx.partial_catalog:
        lines.append("(trang chưa gửi đủ tờ khai — dưới đây chỉ có các ô đã đi qua và ô đang hỏi)")
    for item in ctx.fields:
        part = part_of(item)
        if part != current_part:
            current_part = part
            lines.append(f"## {part}")
        value = _cut(item.get("value")) or "trống"
        need = " · bắt buộc" if item.get("required") and not item.get("value") else ""
        kind = kind_vi(item)
        lines.append(f"{item['code']} · {label_of(item)}{' · ' + kind if kind else ''} · {value}{need}")
    return "\n".join(lines) or "(không có)"


def current_block(ctx: Context, st: dict | None = None) -> str:
    f = ctx.current
    if not f:
        return "(không có)"
    options = list(f.get("options") or [])
    choices = f" · lựa chọn: {' / '.join(options[:12])}{' …' if len(options) > 12 else ''}" if options else ""
    if f.get("kind") == "radio" and len(options) == 1:
        choices += " (ô tích một lựa chọn: tích hoặc để trống)"
    line = (f"{f.get('code', '')} · {label_of(f)} · phần {part_of(f)} · loại "
            f"{kind_vi(f) or 'chữ'}{choices}")
    group = (st or {}).get("group") or {}
    if len(group.get("keys") or []) > 1:
        # Công dân hay nói luôn thông tin các ô liền sau cùng cụm (giấy tờ: loại, số, ngày cấp, cơ quan cấp) mà không
        # nêu tên từng ô.
        members = [m for m in (next((x for x in ctx.fields if x.get("key") == k), None) for k in group["keys"]) if m]
        rows = "\n".join(f"{m['code']} · {label_of(m)} · loại {kind_vi(m) or 'chữ'} · "
                         f"{_cut(m.get('value')) or 'trống'}" for m in members)
        line = (f"{line}\nÔ này thuộc CỤM \"{group.get('title') or ''}\" (phần {part_of(f)}); các ô còn trống của cụm "
                f"(công dân có thể nói luôn trong cùng câu, theo thứ tự bất kỳ, không nêu tên ô):\n{rows}")
    if (st or {}).get("thread"):
        # Đang hỏi lại để làm rõ: model hay neo vào ô đang hỏi dở rồi coi câu trả lời làm rõ là "không khớp" → hỏi lặp.
        return ("TRỢ LÝ ĐANG HỎI LẠI ĐỂ LÀM RÕ (xem <dang_lam_ro> và câu trợ lý cuối trong <hoi_thoai>): câu mới là câu "
                "trả lời cho câu hỏi lại đó, KHÔNG phải cho ô dưới đây.\nÔ đang hỏi dở trước khi làm rõ: " + line)
    return line


def log_block(ctx: Context, st: dict) -> str:
    lines = []
    for entry in (st.get("log") or [])[:LOG_SHOWN]:
        code = code_of(ctx, entry["key"])
        lines.append(f"{code} · {entry.get('label') or ''} ({entry.get('where') or 'Tờ khai'}) · "
                     f"{_cut(entry.get('old')) or 'trống'} → {_cut(entry.get('new'))}")
    return "\n".join(lines) or "(chưa điền / sửa ô nào trong vòng này)"


def thread_block(st: dict) -> str:
    """Các câu công dân nói từ khi trợ lý bắt đầu hỏi lại để làm rõ (chưa ra việc) — câu mới thường là câu trả lời cho
    câu hỏi lại đó, phải ghép với các câu này mới trọn ý."""
    thread = list(st.get("thread") or [])
    return "\n".join(f'- "{t}"' for t in thread) or "(không có)"


def dialogue_block(conv: dict, turns: int) -> str:
    lines = [("TRỢ LÝ: " if m["role"] == "assistant" else "CÔNG DÂN: ") + m["content"]
             for m in store.recent_dialogue(conv, turns * 2)]
    return "\n".join(lines) or "(chưa có)"
