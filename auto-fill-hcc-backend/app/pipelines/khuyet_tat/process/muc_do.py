"""Lượt LLM riêng đọc bảng "Mức độ khuyết tật" (mục III.2 Mẫu số 01), chạy song song lượt trích chính.

Ô tiêu đề kẻ chéo "Mức độ thực hiện / Các hoạt động" bị OCR tách thành hai cột nên hàng tiêu đề nhiều cột hơn
hàng dữ liệu; lượt trích chính (prompt dài) hay gióng dấu X lệch một cột. Lượt này chỉ nhận OCR và buộc model
viết ra từng bước cho mỗi dòng (chép ô → bỏ ô thừa → vị trí X → mức) trong chính JSON trả về, không cần bật suy
nghĩ. Trả ``None`` khi lỗi/không đọc được để runner giữ kết quả lượt chính.
"""

import asyncio
import logging

from app.services.llm import client

logger = logging.getLogger(__name__)

_LEVELS = ("THD", "CTG", "KTHD", "KXD")
_MAX_TOKENS = 3000

PROMPT = """<task>
Đọc OCR của Đơn đề nghị xác định mức độ khuyết tật (Mẫu số 01). CHỈ đọc bảng "2. Thông tin về mức độ khuyết tật"
(cột "Các hoạt động" + các cột "Mức độ thực hiện"). Bỏ qua mọi phần khác của đơn.
</task>

<table_structure>
Trên giấy, bảng có 5 cột: [Các hoạt động] [Thực hiện được] [Thực hiện được nhưng cần trợ giúp] [Không thực hiện
được] [Không xác định được]. Ô góc trên-trái kẻ chéo ghi "Mức độ thực hiện" và "Các hoạt động" là MỘT ô tiêu đề.
OCR thường TÁCH ô chéo đó thành hai cột, nên hàng tiêu đề OCR có 6 cột trong khi mỗi dòng dữ liệu chỉ có 5 cột
(tên hoạt động + 4 ô đánh dấu). Vì vậy TUYỆT ĐỐI KHÔNG gióng dấu X theo vị trí cột của hàng tiêu đề.
Mức theo vị trí ô đánh dấu (đếm trong 4 ô đánh dấu, trái → phải):
- ô 1 = THD (Thực hiện được)
- ô 2 = CTG (Thực hiện được nhưng cần trợ giúp)
- ô 3 = KTHD (Không thực hiện được)
- ô 4 = KXD (Không xác định được)
Dòng: 1 đi lại; 2 ăn uống; 3 tiểu tiện/đại tiện; 4 vệ sinh cá nhân; 5 mặc/cởi quần áo; 6 nghe và hiểu;
7 diễn đạt ý muốn; 8 làm việc gia đình/lao động/sản xuất; 9 giao tiếp xã hội; 10 đọc, viết, tính toán.
</table_structure>

<steps>
Làm TỪNG dòng hoạt động, độc lập với dòng khác, theo đúng 5 bước và GHI KẾT QUẢ MỖI BƯỚC vào JSON:
1. "dong_ocr": chép NGUYÊN VĂN dòng OCR của hoạt động đó (bắt đầu bằng "| <số>. <tên hoạt động>").
2. "o_sau_ten": tách dòng theo dấu "|", bỏ phần rỗng trước dấu "|" đầu và sau dấu "|" cuối, bỏ ô tên hoạt động;
   các ô còn lại giữ đúng thứ tự trái → phải, ô trống ghi "" (không gộp, không bỏ ô trống ở giữa).
3. "o_danh_dau": lấy 4 ô CUỐI của "o_sau_ten" (nếu có nhiều hơn 4 ô thì các ô thừa nằm ở ĐẦU, thuộc cột tiêu đề
   chéo bị tách — bỏ đi). Nếu ít hơn 4 ô thì dòng OCR bị vỡ → bỏ dòng đó.
4. "vi_tri": số thứ tự (1–4) của ô duy nhất có dấu (X, x, ✓, ☒) trong "o_danh_dau". Không có ô nào hoặc có từ 2
   ô có dấu → bỏ dòng đó.
5. "muc": mã mức theo "vi_tri" (1=THD, 2=CTG, 3=KTHD, 4=KXD).
Không suy mức của dòng này từ dòng trên/dưới; mỗi dòng phải tự đếm lại từ đầu.
</steps>

<examples>
Các ví dụ chỉ minh hoạ HÌNH DẠNG dòng OCR, không phải đáp án của đơn đang đọc.

Ví dụ A — hàng tiêu đề bị tách thành 6 cột, dòng dữ liệu 5 cột:
| Các hoạt động | Mức độ thực hiện | Thực hiện được | Thực hiện được nhưng cần trợ giúp | Không thực hiện được | Không xác định được |
|---|---|---|---|---|---|
| 2. Ăn, uống | X | | | |
| 5. Mặc, cởi quần áo, giày dép | | | | X |
| 7. Diễn đạt được ý muốn và suy nghĩ của bản thân qua lời nói | | | X | |
→ {"dong":[
 {"so":"2","dong_ocr":"| 2. Ăn, uống | X | | | |","o_sau_ten":["X","","",""],"o_danh_dau":["X","","",""],"vi_tri":1,"muc":"THD"},
 {"so":"5","dong_ocr":"| 5. Mặc, cởi quần áo, giày dép | | | | X |","o_sau_ten":["","","","X"],"o_danh_dau":["","","","X"],"vi_tri":4,"muc":"KXD"},
 {"so":"7","dong_ocr":"| 7. Diễn đạt được ý muốn và suy nghĩ của bản thân qua lời nói | | | X | |","o_sau_ten":["","","X",""],"o_danh_dau":["","","X",""],"vi_tri":3,"muc":"KTHD"}]}

Ví dụ B — dòng dữ liệu có ô thừa đầu dòng (OCR gióng theo hàng tiêu đề 6 cột):
| 9. Giao tiếp xã hội, hòa nhập cộng đồng phù hợp với độ tuổi | | | X | | |
→ "o_sau_ten":["","","X","",""] (5 ô) → "o_danh_dau" là 4 ô cuối ["","X","",""] → "vi_tri":2 → "muc":"CTG".
</examples>

<output_contract>
Trả DUY NHẤT một JSON object, không markdown, không giải thích ngoài JSON:
{"dong":[{"so":"1","dong_ocr":"...","o_sau_ten":[...],"o_danh_dau":[...],"vi_tri":2,"muc":"CTG"}]}
Chỉ liệt kê dòng có trong OCR. Không có bảng mức độ → {"dong":[]}.
</output_contract>"""


async def read_activity_levels(documents: list[dict]) -> dict | None:
    text = "\n\n".join(str(d.get("text") or "") for d in documents if d.get("text"))
    if not text.strip():
        return None
    try:
        raw = await client.chat(
            [{"role": "system", "content": PROMPT}, {"role": "user", "content": "OCR:\n" + text}],
            max_tokens=_MAX_TOKENS,
            temperature=0,
            purpose="muc_do_khuyet_tat",
        )
        data = client.extract_json_block(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Đọc bảng mức độ khuyết tật lỗi, giữ kết quả lượt chính: %s", exc)
        return None
    rows = data.get("dong") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return None
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("so") or "").strip()
        cells = row.get("o_danh_dau")
        if key not in {str(i) for i in range(1, 11)} or not isinstance(cells, list) or len(cells) != 4:
            continue
        marked = [i for i, cell in enumerate(cells) if str(cell or "").strip()]
        # Mức suy từ chính 4 ô model đã chép; lệch với "muc" model ghi thì tin ô đã chép.
        if len(marked) == 1:
            out[key] = _LEVELS[marked[0]]
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
