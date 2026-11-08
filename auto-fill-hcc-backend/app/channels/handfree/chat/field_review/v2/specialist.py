"""Agent CHUYÊN MÔN: đọc giá trị cho các ô được giao từ nguyên câu nói; code chỉ kiểm, không đạt thì agent đọc lại."""
import json
import logging
import re
from dataclasses import dataclass

from app.channels.handfree.chat.field_review.v2 import specialist_prompt as prompt
from app.channels.handfree.chat.field_review import agent as v1
from app.channels.handfree.chat.field_review.v2 import validator, context
from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)

RESULTS = {"gia_tri", "thieu", "mo_ho", "khong_co"}
_JOBS = {"tra_loi": "điền ô này (đang trống)", "sua": "sửa ô này",
         "goi_y": "công dân nói kèm thông tin cho ô này dù chưa hỏi tới (chỉ lấy khi câu nói rõ là của ô này)"}
_MAX_QUESTION = 200
_MAX_OPTIONS_SHOWN = 400


@dataclass
class Outcome:
    field: dict
    job: str                       # "tra_loi" | "sua"
    kind: str                      # "ok" | "ask" | "none"
    checked: validator.Checked | None = None
    confirm: bool = False
    question: str = ""


def _date_rule(field: dict) -> str:
    if field.get("partial_date"):
        return prompt.DATE_PARTIAL
    if field.get("year_only"):
        return prompt.DATE_YEAR
    return prompt.DATE_FULL


def _modules(fields: list[dict]) -> tuple[str, str]:
    names, extra = [], ""
    for f in fields:
        for name in (validator.module_of(f), "ban_sao" if f.get("copy_choice") else "",
                     "khac" if (f.get("other") or {}).get("option") else ""):
            if name and name not in names:
                names.append(name)
    blocks = []
    for name in names:
        text = prompt.MODULES[name]
        if name == "ngay":
            dates = [f for f in fields if validator.module_of(f) == "ngay"]
            rules = {_date_rule(f) for f in dates}
            text = text.replace("{date_rule}", rules.pop() if len(rules) == 1 else
                                " ".join(f"Ô {f.get('code')}: {_date_rule(f)}" for f in dates))
        blocks.append(text)
        extra += prompt.EXTRA_KEYS.get(name, "")
    return "\n\n".join(blocks), extra


def _spoken_hint(field: dict, said: str) -> str:
    """Dãy chữ số công dân đọc từng con, tách sẵn (tất định) — chỉ khi vừa khít độ dài của ô. Model nhỏ hay đếm rơi
    chữ số trong chuỗi "không bốn không hai…"; đưa sẵn bên cạnh ô để agent đối chiếu, agent vẫn là bên quyết giá trị."""
    lengths = v1.id_lengths(field)
    if lengths:
        digits = v1.spoken_digits(said)
        return f"{' '.join(digits)} ({len(digits)} số)" if v1._digits_ok(digits, lengths) else ""
    if validator.module_of(field) == "ngay":
        digits = validator.spoken_date_digits(said)
        return f"{' '.join(digits)} (8 chữ số đọc liền: ngày-tháng-năm)" if digits else ""
    return ""


def _field_block(field: dict, job: str, partial: str, said: str = "") -> str:
    head = (f"{field.get('code')} · {field.get('label') or ''} · phần {field.get('where') or 'Tờ khai'} · việc: "
            f"{_JOBS.get(job, _JOBS['tra_loi'])} · loại: {validator.module_of(field)} · giá trị "
            f"đang có: {field.get('value') or 'trống'}")
    lines = [head]
    if job == "sua" and field.get("value"):
        # Luật ghép đặt sát dữ liệu: model nhỏ bỏ qua luật chung nằm xa, hỏi lại phần công dân không nhắc tới.
        lines.append(f"   phần nào công dân CÓ nói (kể cả năm) thì lấy theo lời công dân; chỉ phần KHÔNG nhắc tới mới giữ "
                     f"theo giá trị đang có ({field['value']}), trả đủ giá trị và can_xac_nhan=true — không hỏi lại "
                     f"phần không nhắc tới")
    if field.get("role") == "diaChi":
        # Ô chi tiết của khối địa chỉ: model hay hỏi thêm số nhà khi chỉ có xóm, hoặc ghép cả tên xã vào ô này.
        lines.append("   ô này chỉ ghi phần DƯỚI xã (số nhà, đường, thôn, xóm, tổ, bản…); tỉnh, xã có ô riêng — không ghép "
                     "vào. Chỉ có thôn / xóm / bản là ĐỦ (\"gia_tri\"), không hỏi thêm số nhà, đường")
    if partial:
        lines.append(f'   lời công dân nói trước đó cho ô này: "{partial}"')
    hint = _spoken_hint(field, said)
    if hint:
        lines.append(f"   dãy chữ số công dân đọc từng con (hệ thống tách sẵn để đối chiếu): {hint}")
    options = list(field.get("options") or [])[:_MAX_OPTIONS_SHOWN]
    if options:
        lines.append("   danh sách lựa chọn:")
        lines.extend(f"   [{i}] {o}" for i, o in enumerate(options, 1))
    return "\n".join(lines)


def messages(assigned: list[tuple[dict, str]], text: str, conv: dict, st: dict,
             errors: dict[str, str] | None = None) -> list[dict]:
    fields = [f for f, _ in assigned]
    modules, extra = _modules(fields)
    partial = st.get("partial") or {}
    errors_block = prompt.RETRY.format(loi="\n".join(f"- {code}: {err}" for code, err in errors.items())) \
        if errors else ""
    thread = [str(t)[:300] for t in st.get("specialist_thread") or []]
    # Công dân trả lời từng mẩu qua mấy lượt (trợ lý hỏi lại để làm rõ): đưa cả chuỗi vào ĐÚNG khối câu nói để agent
    # ghép thành một ý — để riêng một khối phụ thì model chỉ đọc câu mới ("bên nam") rồi hỏi lại.
    said = str(text or "")[:600]
    if thread:
        said = prompt.THREAD.format(turns="\n".join(f'{i}) "{t}"' for i, t in enumerate([*thread, said], 1)))
    user = prompt.USER.format(
        o="\n".join(_field_block(f, job, partial.get(f.get("key"), ""), text) for f, job in assigned),
        retry_block=errors_block,
        hoi_thoai=context.dialogue_block(conv, context.SPECIALIST_TURNS),
        cau=said,
    )
    return [{"role": "system", "content": prompt.SYSTEM.format(modules=modules, extra_keys=extra)},
            {"role": "user", "content": user}]


def parse(raw: str) -> dict[str, dict]:
    m = re.search(r"\{[\s\S]*\}", raw or "")
    data = json.loads(m.group(0)) if m else {}
    out = {}
    for item in (data.get("o") if isinstance(data, dict) else None) or []:
        if isinstance(item, dict) and item.get("ma"):
            result = str(item.get("ket_qua") or "")
            if result not in RESULTS:
                # Model nhỏ đôi khi ghi tên lạ cho kết quả (vd "lua_chon") nhưng vẫn trả giá trị → coi là trả giá trị;
                # giá trị vẫn phải qua kiểm tra như thường.
                picked = str(item.get("lua_chon") or "0").strip()
                result = "gia_tri" if item.get("gia_tri") or (picked.isdigit() and int(picked) > 0) else "khong_co"
            item["ket_qua"] = result
            # Chịu lỗi gõ sai tên khoá câu hỏi ("caoi_hoi"…): lấy khoá có chữ "hoi".
            question = item.get("cau_hoi") or next((v for k, v in item.items() if "hoi" in str(k) and v), "")
            item["cau_hoi"] = re.sub(r"\s+", " ", str(question or "")).strip()[:_MAX_QUESTION]
            out[str(item["ma"]).strip()] = item
    return out


async def _call(assigned, text, conv, st, errors=None) -> dict[str, dict]:
    raw = await llm_chat(messages(assigned, text, conv, st, errors), temperature=0.0, max_tokens=700,
                         purpose="field_review_specialist")
    return parse(raw)


def _judge(field: dict, job: str, result: dict, text: str) -> tuple[Outcome | None, str]:
    """→ (kết quả, lỗi kiểm tra). Lỗi kiểm tra ≠ "" thì chưa có kết quả, cần agent đọc lại."""
    kind = result.get("ket_qua")
    if kind == "gia_tri":
        checked = validator.check(field, result, text)
        if checked.error:
            return None, checked.error
        return Outcome(field, job, "ok", checked, confirm=bool(result.get("can_xac_nhan"))), ""
    if kind in {"thieu", "mo_ho"}:
        error = validator.evidence_error(field, text)
        if error:
            return None, error
        return Outcome(field, job, "ask", question=result.get("cau_hoi") or ""), ""
    return Outcome(field, job, "none"), ""


async def solve(assigned: list[tuple[dict, str]], text: str, conv: dict, st: dict) -> list[Outcome]:
    """Một lượt agent cho TẤT CẢ ô được giao; ô không qua kiểm tra → agent đọc lại một lần kèm lỗi cụ thể; vẫn không
    qua → hỏi lại công dân. Lỗi gọi LLM ném ra ngoài."""
    first = await _call(assigned, text, conv, st)
    outcomes: dict[str, Outcome] = {}
    retry: dict[str, str] = {}
    for field, job in assigned:
        outcome, error = _judge(field, job, first.get(field["code"]) or {"ket_qua": "khong_co"}, text)
        if error:
            retry[field["code"]] = error
        else:
            outcomes[field["code"]] = outcome
    if retry:
        logger.info("[field_review.v2] chuyên môn đọc lại: %s", list(retry))
        again_assigned = [(f, j) for f, j in assigned if f["code"] in retry]
        second = await _call(again_assigned, text, conv, st, retry)
        for field, job in again_assigned:
            outcome, error = _judge(field, job, second.get(field["code"]) or {"ket_qua": "khong_co"}, text)
            outcomes[field["code"]] = outcome or Outcome(field, job, "ask", question="")
    result = [outcomes[f["code"]] for f, _ in assigned]
    logger.info("[field_review.v2] chuyên môn: %s", [(o.field.get("code"), o.kind, o.confirm) for o in result])
    return result
