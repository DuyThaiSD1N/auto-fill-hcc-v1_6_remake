"""Lượt LLM riêng đọc bảng "Mức độ khuyết tật" (mục III.2 Mẫu số 01), chạy song song lượt trích chính.

OCR dựng bảng mức độ lệch cột theo nhiều kiểu: ô chéo tiêu đề tách thành hai cột (dòng dữ liệu ít ô hơn tiêu đề),
cột trống kẻ thêm bên phải (dòng nhiều ô hơn), số thứ tự tách riêng một ô. Model đếm sai khi phải tự tách chuỗi
"| | | X |" nên Python chỉ TRÌNH BÀY lại các dòng bảng với từng ô đánh số; model tự gióng ô có dấu với cột tiêu đề và
ghi ra từng bước. Mức là của model; Python chỉ kiểm đáp án với bảng đã trình bày và bỏ dòng lệch (không tự đổi
mức).
Trả ``None`` khi lỗi/không đọc được để runner giữ kết quả lượt chính.
"""

import asyncio
import logging
import re

from app.services.llm import client

logger = logging.getLogger(__name__)

_LEVELS = ("THD", "CTG", "KTHD", "KXD")
_MAX_TOKENS = 3000
_HEADER = re.compile(r"^(Các hoạt động|Mức độ thực hiện)")
_PAGE_MARK = re.compile(r"^─+.*─+$")
_SEPARATOR = re.compile(r"^\|?[\s:|-]+\|?$")

PROMPT = """<task>
Đọc bảng "2. Thông tin về mức độ khuyết tật" của Đơn đề nghị xác định mức độ khuyết tật (Mẫu số 01): với mỗi hoạt
động 1–10, ô có dấu (X, x, ✓, ☒, +) nằm dưới cột mức độ thứ mấy.
</task>

<input>
Bảng đã được tách sẵn từ OCR: mỗi dòng bảng có mã dòng (L1, L2…) và từng ô đánh số [1], [2]… từ trái sang phải;
ô rỗng ghi (trống). Hàng tiêu đề là dòng chứa "Các hoạt động" / "Mức độ thực hiện". Các dòng của một bảng nằm
liền nhau; hồ sơ quét trùng trang có thể có nhiều bảng — mỗi dòng dữ liệu gióng với hàng tiêu đề GẦN NHẤT phía trên.
</input>

<table_structure>
Mẫu đơn in sẵn 4 cột mức độ theo ĐÚNG thứ tự trái → phải, không bao giờ đổi:
1 = THD (Thực hiện được) · 2 = CTG (Thực hiện được nhưng cần trợ giúp) · 3 = KTHD (Không thực hiện được) ·
4 = KXD (Không xác định được). Trên hàng tiêu đề OCR, 4 cột này là 4 ô CUỐI CÙNG (kể cả ô trống — OCR có thể làm
mất chữ một ô tiêu đề); các ô phía trước ("Các hoạt động", "Mức độ thực hiện", số thứ tự) không phải cột mức độ.
Chữ tiêu đề trong OCR có thể bị đọc sai/đảo — mức xác định theo THỨ TỰ cột, không theo chữ OCR.
Hàng tiêu đề có chữ của một cột mức ("Thực hiện được…", "Không thực hiện…", "Không xác định…") nằm NGOÀI 4 ô cuối
(OCR chèn thêm cột giữa tiêu đề) → không gióng được → trả {"dong":[]}.
Dòng: 1 đi lại; 2 ăn uống; 3 tiểu tiện/đại tiện; 4 vệ sinh cá nhân; 5 mặc/cởi quần áo; 6 nghe và hiểu;
7 diễn đạt ý muốn; 8 làm việc gia đình/lao động/sản xuất; 9 giao tiếp xã hội; 10 đọc, viết, tính toán.
</table_structure>

<alignment>
OCR hay lệch số ô giữa hàng tiêu đề và dòng dữ liệu (tiêu đề dư ô đầu do tách ô chéo; dòng dư ô cuối do OCR kẻ thêm
cột trống bên phải). Gọi H = số ô của hàng tiêu đề, N = số ô của dòng, M = số NHỎ HƠN trong H và N.
Ô [k] của dòng nằm dưới ô tiêu đề [k + H − M] (dòng ít ô hơn thì dịch sang phải cho ô cuối thẳng ô cuối tiêu đề;
dòng đủ hoặc nhiều ô hơn thì gióng thẳng, ô dư cuối dòng bỏ).
</alignment>

<steps>
Làm TỪNG dòng hoạt động, độc lập, ghi kết quả mỗi bước vào JSON:
1. "so": số thứ tự hoạt động IN Ở Ô TÊN của dòng đó ("7. Diễn đạt…" → "7"; số tách riêng ô đầu "[1] 7" → "7") —
   KHÔNG tự đánh số lại khi bỏ qua dòng không có dấu. "dong": mã dòng (L…) đó; "tieu_de": mã hàng tiêu đề để gióng.
2. "H", "N": số ô của hàng tiêu đề và của dòng (= số [k] lớn nhất của dòng đó); "M": số nhỏ hơn trong H và N.
3. "cot_muc": danh sách số [k] của 4 ô cuối hàng tiêu đề (4 cột mức, trái → phải) = [H−3, H−2, H−1, H].
4. "o_ten": số [k] của ô tên/số thứ tự CUỐI CÙNG ở đầu dòng (thường 1; số tách riêng ô thì 2).
   "o_dau": số [k] của ô có dấu nằm sau ô tên. Không ô nào có dấu, hoặc từ 2 ô trở lên có dấu → bỏ dòng (không chọn
   một trong hai).
5. "lech": H − M. "o_muc": 4 ô CỦA DÒNG nằm dưới 4 cột mức = mỗi số trong "cot_muc" trừ đi "lech" (giữ thứ tự).
   Số nhỏ nhất trong "o_muc" ≤ o_ten (dòng thiếu ô — OCR mất cột, không biết dấu thuộc cột nào) → bỏ dòng.
6. "bang": gán 4 số trong "o_muc" THEO THỨ TỰ: số thứ nhất → THD, thứ hai → CTG, thứ ba → KTHD, thứ tư → KXD —
   {"<số ô>": "<mã>", …}. LUÔN theo thứ tự này, KHÔNG nhìn chữ tiêu đề (OCR có thể đọc sai chữ tiêu đề).
7. "muc": bang["<o_dau>"] — đây là ĐÁP ÁN. "o_dau" không có trong "bang" (dấu nằm ngoài 4 cột mức) → bỏ dòng.
</steps>

<examples>
Các ví dụ chỉ minh hoạ HÌNH DẠNG, không phải đáp án của đơn đang đọc.
L1: [1] Các hoạt động | [2] Mức độ thực hiện | [3] Thực hiện được | [4] Thực hiện được nhưng cần trợ giúp | [5] Không thực hiện được | [6] Không xác định được
L2: [1] 2. Ăn, uống | [2] (trống) | [3] (trống) | [4] X | [5] (trống)
→ H=6, N=5, M=5, cot_muc=[3,4,5,6], o_ten=1, o_dau=4, lech=1, o_muc=[2,3,4,5],
  bang={"2":"THD","3":"CTG","4":"KTHD","5":"KXD"} → muc=bang["4"]=KTHD.
L3: [1] 9. Giao tiếp xã hội | [2] (trống) | [3] (trống) | [4] X | [5] (trống) | [6] (trống) | [7] (trống)
→ H=6, N=7, M=6, cot_muc=[3,4,5,6], o_dau=4, lech=0, o_muc=[3,4,5,6],
  bang={"3":"THD","4":"CTG","5":"KTHD","6":"KXD"} → muc=bang["4"]=CTG.
L4: [1] Mức độ thực hiện Các hoạt động | [2] (trống) | [3] Thực hiện được nhưng cần trợ giúp | [4] Không thực hiện được | [5] Không xác định được
L5: [1] 6. Nghe và hiểu | [2] X | [3] (trống) | [4] (trống) | [5] (trống)
→ tiêu đề L4: H=5, N=5, M=5, cot_muc=[2,3,4,5], o_dau=2, lech=0, o_muc=[2,3,4,5],
  bang={"2":"THD","3":"CTG","4":"KTHD","5":"KXD"} → muc=bang["2"]=THD.
L6: [1] 1 | [2] Tự đi lại | [3] (trống) | [4] X | [5] (trống)
→ tiêu đề L4: H=5, N=5, M=5, cot_muc=[2,3,4,5], o_ten=2, lech=0, o_muc=[2,3,4,5], 2 ≤ o_ten → bỏ dòng.
L7: [1] Các hoạt động | [2] Mức độ thực hiện | [3] Thực hiện được nhưng cần trợ giúp | [4] Thực hiện được nhưng không cần trợ giúp | [5] Không thực hiện được | [6] Không xác định được
L8: [1] 3. Tiểu tiện | [2] (trống) | [3] X | [4] (trống) | [5] (trống) | [6] (trống)
→ chữ tiêu đề [3], [4] bị OCR đọc sai — vẫn theo thứ tự: H=6, N=6, M=6, cot_muc=[3,4,5,6], o_dau=3, lech=0,
  o_muc=[3,4,5,6], bang={"3":"THD","4":"CTG","5":"KTHD","6":"KXD"} → muc=bang["3"]=THD.
</examples>

<output_contract>
Trả DUY NHẤT một JSON object, không markdown, không giải thích ngoài JSON:
{"dong":[{"so":"1","dong":"L2","tieu_de":"L1","H":6,"N":5,"M":5,"cot_muc":[3,4,5,6],"o_ten":1,"o_dau":4,"lech":1,"o_muc":[2,3,4,5],"bang":{"2":"THD","3":"CTG","4":"KTHD","5":"KXD"},"muc":"KTHD"}]}
Chỉ liệt kê dòng có trong bảng. Không có bảng mức độ → {"dong":[]}.
</output_contract>"""


def _cells(line: str) -> list[str]:
    parts = [part.strip() for part in line.strip().split("|")]
    if parts and not parts[0]:
        parts = parts[1:]
    if parts and not parts[-1]:
        parts = parts[:-1]
    return parts


def table_lines(text: str) -> list[list[str]]:
    """Các dòng bảng mức độ (từ hàng tiêu đề trở đi) đã tách ô — chỉ trình bày lại OCR, không suy luận."""
    out: list[list[str]] = []
    inside = False
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if "|" in line and _HEADER.match(next((c for c in _cells(line) if c), "")):
            inside = True  # ô có chữ đầu hàng tiêu đề; bảng dạng khuyết tật phía trên có chữ "các hoạt động" giữa câu
        elif not inside or not line or _PAGE_MARK.match(line) or _SEPARATOR.match(line):
            continue
        elif "|" not in line:
            inside = False  # hết bảng: dòng chữ thường (chân đơn, chữ ký)
            continue
        out.append(_cells(line))
    return out


def render_table(rows: list[list[str]]) -> str:
    return "\n".join(
        f"L{i}: " + " | ".join(f"[{k}] {cell or '(trống)'}" for k, cell in enumerate(cells, start=1))
        for i, cells in enumerate(rows, start=1)
    )


async def read_activity_levels(documents: list[dict]) -> dict | None:
    text = "\n\n".join(str(d.get("text") or "") for d in documents if d.get("text"))
    rows = table_lines(text)
    if len(rows) < 2:
        return None  # OCR không còn cột bảng → không biết dấu nằm cột nào, giữ kết quả lượt chính
    try:
        raw = await client.chat(
            [{"role": "system", "content": PROMPT}, {"role": "user", "content": "BẢNG:\n" + render_table(rows)}],
            max_tokens=_MAX_TOKENS,
            temperature=0,
            purpose="muc_do_khuyet_tat",
        )
        data = client.extract_json_block(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Đọc bảng mức độ khuyết tật lỗi, giữ kết quả lượt chính: %s", exc)
        return None
    return levels_from(data, rows)


def _int(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _line(rows: list[list[str]], ref) -> list[str]:
    m = re.fullmatch(r"L(\d+)", str(ref or "").strip())
    return rows[int(m.group(1)) - 1] if m and 0 < int(m.group(1)) <= len(rows) else []


def levels_from(data, rows: list[list[str]]) -> dict | None:
    """JSON model → {số hoạt động: mức} theo đúng "muc" model trả. Chỉ KIỂM đáp án với bảng đã trình bày (đúng dòng,
    đúng một ô có dấu, ô đó nằm dưới đúng cột mức model trả); lệch thì bỏ dòng, không tự thay mức."""
    items = data.get("dong") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    out: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("so") or "").strip().rstrip(".")
        cells, header = _line(rows, item.get("dong")), _line(rows, item.get("tieu_de"))
        level = str(item.get("muc") or "").strip().upper()
        cell, name_end = _int(item.get("o_dau")), _int(item.get("o_ten"))
        if key not in {str(i) for i in range(1, 11)} or level not in _LEVELS or not cells or not header \
                or None in (cell, name_end):
            continue
        if not re.match(rf"{key}(?:\s*[.)]|\s|$)(?!\d)", cells[0]) and not (
                len(cells) > 1 and not cells[0] and re.match(rf"{key}(?:\s*[.)]|\s|$)(?!\d)", cells[1])):
            continue  # "so" không khớp số in đầu dòng model chỉ ra (model đánh số lại / nhầm dòng)
        h, n = len(header), len(cells)
        shift = h - min(h, n)
        real_levels = list(range(h - 3, h + 1))
        marked = [k for k, text in enumerate(cells, start=1) if k > name_end and text]
        # Đáp án model phải khớp chính bảng: đúng một ô có dấu sau ô tên (ô model chỉ ra), dòng đủ 4 ô mức sau ô tên,
        # và ô đó gióng xuống đúng cột mức model trả. Lệch → bỏ dòng (thà thiếu), không thay bằng cột khác.
        if (h < 5 or marked != [cell] or real_levels[0] - shift <= name_end
                or cell + shift not in real_levels or level != _LEVELS[real_levels.index(cell + shift)]):
            continue
        out[key] = level
    return out or None


def context_with_levels(base_context, tasks: list):
    """Bọc context_builder: lượt đọc bảng cần OCR nên khởi động ngay khi compact runner có OCR, chạy song song
    lượt trích chính."""

    async def build(documents: list[dict], options: dict) -> str:
        tasks.append(asyncio.create_task(read_activity_levels(documents)))
        return await base_context(documents, options)

    return build


async def apply_levels(res: dict, tasks: list) -> None:
    levels = await tasks[0] if tasks else None
    if levels:
        res["fields"] = [f for f in res["fields"] if f.get("name") != "MucDo_HoatDong"] + [
            {"name": "MucDo_HoatDong", "comp": "raw", "value": levels}
        ]
