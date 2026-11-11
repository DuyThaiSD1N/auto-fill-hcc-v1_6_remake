"""Lớp soát thứ hai sau lượt trích: THANH TRA đọc lại độc lập từng nhóm thông tin, TOÀ ÁN phân xử chỗ lệch.

Dây chuyền: lập hồ sơ vụ việc → các thanh tra chạy song song (không thấy kết quả agent chính) → mã đối chiếu
→ chỗ lệch / ô trống có ứng viên thành vụ án → toà án chọn A (agent chính), B (thanh tra) hoặc không đủ căn cứ
→ cổng chặn bằng mã → giá trị field sau phán quyết + biên bản.

Thanh tra và agent chính cùng một mô hình nên trùng nhau không phải hai bằng chứng: bằng chứng là dòng OCR
chép nguyên văn (mã kiểm có thật) và tín hiệu tất định do từng thủ tục khai. Không đủ căn cứ thì giữ kết quả
lượt trích. Khung này không biết nghiệp vụ; mỗi thủ tục khai thanh tra của mình trong thư mục riêng.
"""

import asyncio
import json
import logging
import time

from app.config import settings
from app.services.llm import client

from . import toa_an
from .ho_so import (Case, Dispute, Finding, Inspector, Result, Unit, alnum, compare_key, fold, is_empty, locate,
                    parse_date,
                    quote_in_documents)

logger = logging.getLogger(__name__)

_INSPECTOR_MAX_TOKENS = 900


# Phần chung của mọi thanh tra đứng trước OCR, nhiệm vụ riêng đứng SAU OCR: ba thanh tra của một hồ sơ gửi cùng
# một tiền tố dài (khung + OCR) nên máy chủ LLM dùng lại được phần đã đọc, và câu hỏi nằm sát chỗ trả lời.
_INSPECTOR_SYSTEM = """<vai_tro>
Bạn là THANH TRA của dây chuyền soát hồ sơ {title}. Một agent khác đã trích hồ sơ này; bạn KHÔNG được xem kết
quả đó và không cần đoán nó. Việc của bạn: đọc lại độc lập các tài liệu OCR, trả lời đúng các mục trong
<nhiem_vu> ở cuối, mỗi mục kèm một dòng chứng cứ chép từ OCR.
</vai_tro>

<nguyen_tac>
- Chỉ dùng chữ có trong OCR. KHÔNG sửa chính tả, không thêm / đổi dấu, không suy luận, không điền theo hiểu biết.
- Giá trị chép đúng từng ký tự trên giấy; chỉ đổi cách viết khi <nghiep_vu> nói rõ (vd ngày → dd/mm/yyyy).
- Một thông tin có ở nhiều tài liệu → xét từng tài liệu, chọn theo thứ tự nguồn trong <nghiep_vu>.
- "quote" = chép NGUYÊN VĂN đúng MỘT dòng OCR chứa giá trị đã chọn (không ghép dòng, không diễn giải, không
  thêm tên tài liệu). "doc" = số thứ tự tài liệu chứa dòng đó.
- Không có dòng nào của ĐÚNG người / ĐÚNG giấy → mục đó trả null. Thà thiếu còn hơn sai.
- Người được cấp và loại giấy theo đúng khối <phan_vai_da_xac_dinh> nếu có; không tự đổi người.
</nguyen_tac>"""

_INSPECTOR_TASK = """<nhiem_vu thanh_tra="{name}">
<nghiep_vu>
{rules}
</nghiep_vu>

<muc_can_tra>
{units}
</muc_can_tra>

<dinh_dang_tra_ve>
Chỉ trả MỘT object JSON phẳng, không markdown; khóa là khóa mục, đủ mọi mục:
{{"<khóa mục>": {{"values": {{"<tên field đúng như trong muc_can_tra>": <giá trị>}}, "quote": "<một dòng OCR>",
"doc": <số>, "thuoc_ve": "<một lựa chọn>", "note": "<vì sao chọn dòng này, tối đa 12 từ>"}}, "<khóa mục khác>": null}}
"thuoc_ve" = dòng chứng cứ nằm trong khối của ai / thuộc giấy nào. Chọn ĐÚNG MỘT lựa chọn dưới đây và chép nguyên
chữ lựa chọn đó (không viết tên người, không viết tên tài liệu); trả lời thật, kể cả khi không phải đối tượng cần lấy:
{owners}
Field không có trên giấy thì bỏ khỏi "values". Mục không có căn cứ thì để null.
</dinh_dang_tra_ve>
</nhiem_vu>"""


def _unit_lines(units: tuple[Unit, ...]) -> str:
    lines = []
    for unit in units:
        fields = "; ".join(f"{spec.name} = {spec.label}" for spec in unit.fields)
        lines.append(f'- "{unit.key}" ({unit.label}): {fields}')
    return "\n".join(lines)


def build_user_content(case: Case) -> str:
    body = "\n\n".join(
        f"### Tài liệu {index} (tên file: {document.get('name') or '(không tên)'})\n"
        f"{str(document.get('text') or '').strip()}"
        for index, document in enumerate(case.documents, start=1)
    )
    return f"{case.context.strip()}\n\nOCR hồ sơ:\n\n{body}".strip()


async def llm_findings(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    """Cách tìm ứng viên mặc định: một lượt LLM đọc lại các tài liệu của hồ sơ, không thấy kết quả lượt trích."""
    task = _INSPECTOR_TASK.format(name=inspector.title, rules=inspector.rules.strip(),
                                  units=_unit_lines(inspector.units),
                                  owners="\n".join(f'- "{owner}"' for owner in inspector.owners))
    raw = await client.chat(
        [{"role": "system", "content": _INSPECTOR_SYSTEM.format(title=title)},
         {"role": "user", "content": f"{build_user_content(case)}\n\n{task}"}],
        max_tokens=_INSPECTOR_MAX_TOKENS, temperature=0, enable_thinking=settings.agent_reasoning,
        purpose=f"thanh_tra.{inspector.key}",
    )
    answers = parse_json(raw)
    if isinstance(answers.get("units"), dict):  # model bọc thêm một lớp
        answers = answers["units"]
    findings = []
    for unit in inspector.units:
        answer = answers.get(unit.key)
        if answer is None and len(unit.fields) == 1:  # model lấy tên field làm khóa mục
            answer = answers.get(unit.fields[0].name)
        if not isinstance(answer, dict) or not isinstance(answer.get("values"), dict):
            continue
        values = _unit_values(unit, answer["values"])
        if not values:
            continue
        try:
            doc = int(answer.get("doc") or 0)
        except (TypeError, ValueError):
            doc = 0
        findings.append(Finding(inspector, unit, values, str(answer.get("quote") or "").strip(), doc,
                                str(answer.get("note") or "").strip()[:200],
                                str(answer.get("thuoc_ve") or "").strip()[:80]))
    return findings


def parse_json(raw: str) -> dict:
    """JSON model trả; thừa ngoặc đóng / chữ sau object thì vẫn lấy object đầu tiên."""
    try:
        parsed = client.extract_json_block(raw)
    except Exception:  # noqa: BLE001
        start = str(raw or "").find("{")
        if start < 0:
            return {}
        try:
            parsed, _ = json.JSONDecoder().raw_decode(raw[start:])
        except ValueError:
            return {}
    return parsed if isinstance(parsed, dict) else {}


def _unit_values(unit: Unit, raw: dict) -> dict:
    """Giá trị model trả cho một mục → theo tên field. Model đặt khóa không ổn định: bỏ tiền tố tên field, viết
    kiểu khác ("so_giay_to"), lấy luôn khóa mục, hoặc trải thẳng các khóa của object địa chỉ ra ngoài."""
    single = unit.fields[0] if len(unit.fields) == 1 else None
    if single and single.kind == "area" and single.name not in raw:
        raw = {single.name: {key: value for key, value in raw.items() if not is_empty(value)}}
    by_key = {alnum(key): value for key, value in raw.items()}
    values = {}
    for spec in unit.fields:
        name = alnum(spec.name)
        value = next((v for key, v in by_key.items() if key and name.endswith(key)), None)
        if value is None and single and len(raw) == 1:  # mục một field: khóa nào cũng là field đó
            value = next(iter(raw.values()))
        if not is_empty(value):
            values[spec.name] = value
    return values


def reject_reason(finding: Finding, case: Case) -> str:
    """Cổng chặn trước toà: ứng viên của thanh tra phải có dòng chứng cứ thật và giá trị thật trong OCR."""
    accepted = {fold(owner) for owner in finding.inspector.accepted}
    if accepted and fold(finding.owner) not in accepted:
        return f"dòng chứng cứ thuộc về: {finding.owner or '(không khai)'}"
    if not quote_in_documents(finding.quote, case.documents):
        return "dòng chứng cứ không có trong OCR"
    for spec in finding.unit.fields:
        value = finding.values.get(spec.name)
        if is_empty(value):
            continue
        if spec.kind == "date" and not parse_date(value):
            return f"{spec.name}: ngày không hợp lệ"
        if spec.kind in ("literal", "code") and not locate(spec, value, case.documents):
            return f"{spec.name}: giá trị không có nguyên văn trong OCR"
    if finding.inspector.check:
        return finding.inspector.check(finding.unit, finding.values, case) or ""
    return ""


def _dispute(finding: Finding, case: Case, number: int) -> Dispute | None:
    current = {spec.name: case.values.get(spec.name) for spec in finding.unit.fields
               if not is_empty(case.values.get(spec.name))}
    added = conflict = False
    differing = []
    for spec in finding.unit.fields:
        theirs = compare_key(spec, finding.values.get(spec.name))
        if theirs is None:
            continue  # thanh tra không thấy field này: không đủ để tranh chấp
        ours = compare_key(spec, current.get(spec.name))
        if ours is None:
            added = True
        elif ours != theirs and not (spec.same and spec.same(ours, theirs)):
            conflict = True
            differing.append(spec)
    if not (added or conflict):
        return None
    return Dispute(number, finding, current, "tranh_chap" if current else "bo_sung", conflict, tuple(differing))


def code_backed(dispute: Dispute, case: Case) -> bool:
    """Thanh tra và agent chính cùng một mô hình: hai bên lệch nhau thì chưa bên nào có thêm bằng chứng. Giá trị
    lượt trích chỉ bị đem ra xử khi MÃ đứng về phía thanh tra — giá trị lượt trích không có nguyên văn trong OCR
    còn của thanh tra thì có, hoặc tín hiệu tất định của thủ tục báo lượt trích lệch mà thanh tra không lệch."""
    finding = dispute.finding
    for spec in dispute.differing:
        # Địa chỉ và field có cách viết tương đương (cơ quan, loại giấy): lượt trích được phép viết lại nên không
        # thấy nguyên văn không chứng minh gì.
        if spec.kind == "area" or (spec.canon and spec.kind != "code"):
            continue
        if locate(spec, finding.values.get(spec.name), case.documents) and not locate(
                spec, dispute.current.get(spec.name), case.documents):
            return True
    signals = finding.inspector.signals
    if not signals:
        return False
    ours = signals(finding.unit, dispute.current, case)
    theirs = signals(finding.unit, finding.values, case)
    return any(not ok for ok, _ in ours) and all(ok for ok, _ in theirs)


def _apply(values: dict, dispute: Dispute) -> dict:
    out = dict(values)
    unit = dispute.finding.unit
    # Hai bên lệch nhau trong một cụm → lấy NGUYÊN cụm của thanh tra (không trộn hai nguồn);
    # chỉ bổ sung field còn thiếu thì giữ các field lượt trích đã có.
    if dispute.conflict and len(unit.fields) > 1:
        for spec in unit.fields:
            out.pop(spec.name, None)
    out.update(dispute.finding.values)
    return out


async def run(case: Case, inspectors: tuple[Inspector, ...], *, title: str) -> Result:
    """Chạy lớp soát. Lỗi của một thanh tra hay của toà án không làm hỏng kết quả lượt trích."""
    t0 = time.monotonic()
    answers = await asyncio.gather(*((i.find or llm_findings)(i, case, title) for i in inspectors),
                                   return_exceptions=True)
    inspect_ms = int((time.monotonic() - t0) * 1000)
    rulings: list[dict] = []
    disputes: list[Dispute] = []
    for inspector, answer in zip(inspectors, answers):
        if isinstance(answer, BaseException):
            logger.warning("Thanh tra %s lỗi, bỏ qua: %r", inspector.key, answer)
            rulings.append({"inspector": inspector.key, "outcome": "thanh_tra_loi", "reason": repr(answer)[:200]})
            continue
        for finding in answer:
            dispute = _dispute(finding, case, len(disputes) + 1)
            if not dispute:
                continue
            reason = reject_reason(finding, case)
            if reason:
                rulings.append(_record(dispute, "bac_truoc_toa", reason))
                continue
            if dispute.conflict and not (finding.backed or code_backed(dispute, case)):
                rulings.append(_record(dispute, "khong_khoi_to", "lệch nhau nhưng mã không có căn cứ nghiêng về thanh tra"))
                continue
            disputes.append(dispute)

    values = dict(case.values)
    court_ms = 0
    if disputes:
        t1 = time.monotonic()
        try:
            verdicts = await toa_an.judge(case, disputes, title=title)
        except Exception as exc:  # noqa: BLE001 — toà lỗi thì giữ nguyên lượt trích
            logger.warning("Toà án lỗi, giữ kết quả lượt trích: %r", exc)
            verdicts = {}
        court_ms = int((time.monotonic() - t1) * 1000)
        for dispute in disputes:
            choice, why = verdicts.get(dispute.id, ("", "toà không phán"))
            if choice == "B":
                values = _apply(values, dispute)
                rulings.append(_record(dispute, "bo_sung" if dispute.kind == "bo_sung" else "sua", why))
            else:
                rulings.append(_record(dispute, "giu", why))
    return Result(values, rulings, {"inspect_ms": inspect_ms, "court_ms": court_ms,
                                    "disputes": len(disputes), "inspectors": len(inspectors)})


def _record(dispute: Dispute, outcome: str, reason: str) -> dict:
    finding = dispute.finding
    return {"inspector": finding.inspector.key, "unit": finding.unit.key, "kind": dispute.kind, "outcome": outcome,
            "current": dispute.current, "proposed": finding.values, "quote": finding.quote, "doc": finding.doc,
            "note": finding.note, "owner": finding.owner, "evidence": list(finding.evidence), "reason": reason}
