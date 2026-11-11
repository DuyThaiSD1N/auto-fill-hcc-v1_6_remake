"""TOÀ ÁN: phán xử cuối cùng từng vụ án — chọn A (agent chính), B (thanh tra) hoặc không đủ căn cứ.

Toà chỉ thấy phần chắt lọc: hai ứng viên, dòng OCR do mã tìm, đoạn quanh dòng chứng cứ, tín hiệu tất định và
nghiệp vụ của nhóm. Toà không được đặt giá trị thứ ba; phán quyết sai định dạng coi như không phán.
"""

from app.config import settings
from app.services.llm import client

from .ho_so import Case, Dispute, is_empty, locate, surrounding

_BASE_TOKENS = 200
_TOKENS_PER_DISPUTE = 120

_COURT_FRAME = """<vai_tro>
Bạn là TOÀ ÁN của dây chuyền soát hồ sơ {title}. Mỗi VỤ ÁN là một ô (hoặc một cụm ô đi cùng nhau) mà AGENT
CHÍNH (A) và THANH TRA (B) đọc ra khác nhau, hoặc A bỏ trống còn B có giá trị. Bạn ra phán quyết cuối cùng.
</vai_tro>

<nguyen_tac>
- Mỗi vụ chỉ chọn một trong ba: "A", "B", "KHONG_DU_CAN_CU". KHÔNG tự đặt giá trị thứ ba, không sửa giá trị.
- Phán theo CHỨNG CỨ (các dòng OCR kèm theo) và <luat> của nhóm; không theo vẻ hợp lý, không theo thói quen.
- A và B do cùng một mô hình đọc: không bên nào mặc nhiên đúng, hai bên giống nhau cũng không phải bằng chứng.
- Chọn "B" CHỈ KHI dòng chứng cứ của B thuộc ĐÚNG người / ĐÚNG giấy theo <luat> VÀ B đúng hơn A một cách rõ
  ràng (A lấy nhầm người, nhầm dòng, nhầm nguồn, chép thiếu / thừa so với dòng trên giấy). Hai bên ngang nhau,
  chỉ khác cách viết, hoặc không rõ dòng thuộc ai → "KHONG_DU_CAN_CU" (giữ A).
- "Tín hiệu mã" là kiểm tra tất định bằng mã, đáng tin hơn suy đoán: ứng viên bị tín hiệu mã báo LỆCH thì
  không được thắng nếu ứng viên kia không bị báo.
- A trống: chọn "B" khi dòng chứng cứ của B đúng là của người / giấy đó theo <luat>; không chắc →
  "KHONG_DU_CAN_CU" (để trống, thà thiếu còn hơn sai).
- Giá trị ghi "KHÔNG thấy nguyên văn trong OCR" là dấu hiệu bị biến đổi hoặc bịa; cân nhắc mạnh bên có nguyên văn.
</nguyen_tac>

{laws}

<dinh_dang_tra_ve>
Chỉ trả JSON, không markdown, đủ mọi vụ án theo đúng "id":
{{"phan_quyet": [{{"id": <số>, "ly_do": "<tối đa 20 từ: dòng chứng cứ thuộc ai / giấy nào, bên nào đúng luật>",
"chon": "A" | "B" | "KHONG_DU_CAN_CU"}}]}}
Viết "ly_do" TRƯỚC rồi mới "chon"; "chon" phải đúng với "ly_do" (lý do nói A đúng thì chọn "A").
</dinh_dang_tra_ve>"""


def _show(value) -> str:
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key}: {val}" for key, val in value.items() if not is_empty(val)) + "}"
    return str(value)


def _candidate(tag: str, who: str, values: dict, dispute: Dispute, case: Case) -> list[str]:
    unit = dispute.finding.unit
    if not values:
        return [f"{tag} ({who}): (bỏ trống)"]
    lines = [f"{tag} ({who}):"]
    for spec in unit.fields:
        value = values.get(spec.name)
        if is_empty(value):
            continue
        hits = locate(spec, value, case.documents)
        where = "; ".join(hits) if hits else "KHÔNG thấy nguyên văn trong OCR"
        lines.append(f"  - {spec.label} = \"{_show(value)}\" — mã tìm thấy ở: {where}")
    signals = dispute.finding.inspector.signals
    for ok, text in (signals(unit, values, case) if signals else []):
        lines.append(f"  - Tín hiệu mã: {'KHỚP' if ok else 'LỆCH'} — {text}")
    return lines


def build_user_content(case: Case, disputes: list[Dispute]) -> str:
    parts = [case.context.strip()] if case.context.strip() else []
    for dispute in disputes:
        finding = dispute.finding
        block = [f'<vu_an id="{dispute.id}" nhom="{finding.inspector.key}" muc="{finding.unit.label}">']
        block += _candidate("A", "agent chính", dispute.current, dispute, case)
        block += _candidate("B", f"thanh tra {finding.inspector.title}", finding.values, dispute, case)
        for line in finding.evidence:
            block.append(f"  - Tín hiệu mã cho B: {line}")
        block.append(f'  - Dòng chứng cứ của B: "{finding.quote}"')
        around = surrounding(finding.quote, case.documents)
        if around:
            block.append(f"  - Đoạn OCR quanh dòng chứng cứ của B: {around}")
        block.append(f"  - B khai dòng chứng cứ thuộc về: {finding.owner or '(không khai)'}"
                     + (f"; lý do: {finding.note}" if finding.note else ""))
        block.append("</vu_an>")
        parts.append("\n".join(block))
    return "\n\n".join(parts)


def build_system_prompt(disputes: list[Dispute], title: str) -> str:
    laws: dict[str, str] = {}
    for dispute in disputes:
        inspector = dispute.finding.inspector
        laws.setdefault(inspector.key, f'<luat nhom="{inspector.key}">\n{inspector.rules.strip()}\n</luat>')
    return _COURT_FRAME.format(title=title, laws="\n\n".join(laws.values()))


async def judge(case: Case, disputes: list[Dispute], *, title: str) -> dict[int, tuple[str, str]]:
    """→ {id vụ án: (lựa chọn, lý do)}; vụ không có phán quyết hợp lệ thì không có trong kết quả."""
    raw = await client.chat(
        [{"role": "system", "content": build_system_prompt(disputes, title)},
         {"role": "user", "content": build_user_content(case, disputes)}],
        max_tokens=_BASE_TOKENS + _TOKENS_PER_DISPUTE * len(disputes), temperature=0,
        enable_thinking=settings.agent_reasoning, purpose="thanh_tra.toa_an",
    )
    verdicts: dict[int, tuple[str, str]] = {}
    rows = (client.extract_json_block(raw) or {}).get("phan_quyet")
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        try:
            number = int(row.get("id"))
        except (TypeError, ValueError):
            continue
        choice = str(row.get("chon") or "").strip().upper()
        if choice in ("A", "B", "KHONG_DU_CAN_CU"):
            verdicts[number] = (choice, str(row.get("ly_do") or "").strip()[:200])
    return verdicts
