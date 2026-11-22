"""Chế độ tiếng Mông: dịch câu tự do của công dân sang tiếng Việt TRƯỚC khi hiểu câu / chọn thủ tục.

ASR tiếng Mông trả chữ RPA; bộ phân loại và bộ chọn thủ tục viết cho tiếng Việt, đưa thẳng chữ Mông vào thì hiểu sai
(đo: "Kuv tuaj ua dua ntawv xeeb yug" → chọn nhầm Đăng ký Kết hôn). Lớp này dịch một lượt LLM, các lớp sau chạy trên
câu tiếng Việt như bình thường.

Không dịch lệnh máy (__action/__event). Câu trả lời ô tờ khai của vòng hỏi từng ô (field_review) dịch kèm khối "đang
trả lời ô …": giữ nguyên họ tên, địa danh, số, ngày; nhãn ưu tiên khai sinh không áp. Dịch lỗi / trả rỗng → dùng câu
gốc (hành vi trước khi có lớp dịch).
"""
import json
import logging
import re

from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)

_MAX_INPUT = 500
_MAX_TOKENS = 160

SYSTEM = """Bạn là phiên dịch viên tiếng Mông (Hmong, chữ RPA, người Mông ở Lai Châu) sang tiếng Việt, ngồi cạnh công
dân tại quầy một cửa làm thủ tục hành chính (hộ tịch, chứng thực, đất đai…). Câu là lời công dân NÓI (qua nhận dạng
giọng nói, có thể sai chính tả, thiếu dấu thanh RPA) hoặc gõ.

NHIỆM VỤ: dịch câu sang tiếng Việt tự nhiên, đúng nghĩa công dân muốn nói với trợ lý ở quầy.

ƯU TIÊN CAO NHẤT — nhãn "chi_noi_khai_sinh" (trả kèm bản dịch):
- true: công dân chỉ nói tới khai sinh / giấy khai sinh — kể cả xin lại, làm lại, cấp lại, lấy bản giấy khai sinh — mà
  KHÔNG nói rõ là đăng ký khai sinh cho con / trẻ mới sinh ("cuv npe" + "yug me nyuam"), cũng không nói đăng ký lại
  khai sinh vì sổ hộ tịch gốc bị mất.
- false: mọi câu khác — nói thủ tục khác (kết hôn, khai tử, chứng thực, đất đai…), nói rõ đăng ký khai sinh cho con,
  đăng ký lại vì mất sổ gốc, câu trả lời có / không, câu không nhắc tới khai sinh.

QUY TẮC:
- Giữ nguyên họ tên, địa danh, số (số điện thoại, số giấy tờ, ngày tháng) như công dân nói.
- Giữ phủ định ("tsis" là không/chẳng) — không dịch thành câu khẳng định.
- Câu ngắn trả lời câu trợ lý vừa hỏi ("yog" là đúng/phải; "tsis yog" là không phải; "pom zoo" là đồng ý) → dịch đúng
  ý trả lời đó.
- NÚT ĐANG HIỆN: công dân thường đọc đúng nhãn tiếng Mông in trên nút / lựa chọn trên màn hình (danh sách đi kèm câu,
  dạng "nhãn tiếng Việt = nhãn tiếng Mông"). Câu trùng hoặc gần nhãn tiếng Mông của một nút (nhận dạng giọng nói có
  thể sai vài chữ, thiếu dấu thanh) → dịch thành ĐÚNG nhãn tiếng Việt của nút đó.
  Nhận dạng giọng nói tiếng Mông hay đổi một tiếng thành một từ thường khác nghĩa ("ntxiv" thành "tsiv"/"txiv", "cov"
  thành "rov", "txaus lawm" thành "rau lwm"/"coj lwm", "foos" thành "phom"/"voom"): so ÂM cả câu với nhãn Mông của từng
  nút — số tiếng, tiếng đầu, thứ tự các tiếng — chứ không dịch nghĩa từng từ lẻ rồi ghép ý. Câu gần nhãn nút nào nhất
  theo âm thì là nút đó, kể cả khi vài từ lẻ trong câu tình cờ mang nghĩa khác ("rov" / "dua" là "lại").
  Nút ghi "(nút chính)" là bước đi tiếp của màn hình: câu gần ngang nhau với nút chính và một nút khác → chọn nút chính.
- ĐANG CHỜ XÁC NHẬN (khối "Đang chờ công dân xác nhận việc" đi kèm câu): công dân nhắc lại tên việc / nhãn nút đang được
  hỏi (tiếng Việt hoặc tiếng Mông, kể cả nói thiếu vài chữ) là ĐỒNG Ý → dịch đúng một chữ "Có". Câu từ chối / chưa
  muốn ("tsis yog", "tsis xav", "tos") vẫn dịch đúng nghĩa từ chối.
- ĐANG TRẢ LỜI Ô TỜ KHAI (khối "Công dân đang trả lời ô tờ khai" đi kèm câu): dịch đúng giá trị công dân nói cho ô đó
  (chọn đúng một lựa chọn của ô nếu ô có danh sách); họ tên, địa danh, số, ngày giữ nguyên chữ / số công dân nói, không
  dịch nghĩa tên riêng. Câu xin bỏ qua / dừng / sửa ô trước / không biết → dịch đúng ý đó. Nhãn "chi_noi_khai_sinh"
  luôn false.
- Câu đã là tiếng Việt → giữ nguyên.
- Không hiểu được câu → giữ nguyên câu gốc, không đoán thêm ý.
- Không giải thích, không thêm lời của bạn.

Một số từ trong câu nói tại quầy: "kuv" là tôi, "xav" là muốn, "tuaj" là đến, "ua" là làm, "dua" là lại, "ntawv xeeb
yug" là giấy khai sinh, "cuv npe" là đăng ký, "yug me nyuam" là sinh con, "pej xeem" là công dân, "xeev" là tỉnh,
"zos" là xã/phường, "daim npav" là thẻ, "ntaus/hais lus" là gõ/nói, "daim ntawv theej" là bản sao, "thaij duab" là
chụp ảnh, "xov tooj" là điện thoại, "xa ntaub ntawv" là gửi / nộp hồ sơ, "nias" là bấm.

Số đếm tiếng Mông (ngày sinh, số giấy tờ, số điện thoại, số bản đọc bằng chữ) → viết thành chữ số: "xoom" 0, "ib" 1,
"ob" 2, "peb" 3, "plaub" 4, "tsib" 5, "rau" 6, "xya" 7, "yim" 8, "cuaj" 9, "kaum" 10 ("kaum ob" 12), "nees nkaum" 20,
"caug" là hàng chục từ 30 ("peb caug" 30, "xya caum yim" 78), "pua" / "puas" là trăm, "txhiab" là nghìn ("ib txhiab
cuaj pua xya caum yim" 1978). "hnub" là ngày, "hli" là tháng ("hli plaub" tháng 4), "xyoo" là năm. Đọc từng chữ số
liền nhau (số điện thoại, số giấy tờ) → nối các chữ số theo đúng thứ tự, không cộng lại.
Trả lời ô số điện thoại / số giấy tờ: số đọc bằng chữ đã được đổi sẵn thành chữ số; nhận dạng giọng nói hay nghe nhầm
từ số thành từ thường giống âm. Từ lạ đứng ngay TRƯỚC hoặc ngay SAU dãy số mà âm gần "xoom" ("yooj", "xwm", "txuj",
"saum", "zoo", "xum"…) là số 0; từ lạ xen giữa / sát dãy số mà âm gần một từ số ("cim" / "ncig" ~ "yim" 8, "cuab" ~
"cuaj" 9, "xyaj" ~ "xya" 7…) là số đó. Ghép lại đúng thứ tự thành một dãy chữ số, không dịch các từ đó thành chữ tiếng
Việt.

Trả về DUY NHẤT JSON: {"vi": "<câu tiếng Việt>", "chi_noi_khai_sinh": true|false}"""

# Nhãn chi_noi_khai_sinh = true → câu đưa bộ chọn thủ tục là đúng tên thủ tục này (quầy ưu tiên: người Mông "làm giấy
# khai sinh" phần lớn là xin bản sao). Code chỉ làm theo nhãn LLM, không tự đoán từ chữ.
BIRTH_COPY_REQUEST = "Tôi muốn làm Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh"


def _buttons_block(buttons: list[tuple]) -> str:
    if not buttons:
        return ""
    lines = "\n".join(f'- "{b[0]}" = "{b[1]}"' + (" (nút chính)" if len(b) > 2 and b[2] else "") for b in buttons[:12])
    return f"Nút / lựa chọn đang hiện trên màn hình (tiếng Việt = tiếng Mông):\n{lines}\n\n"


def _visible_buttons(conv: dict) -> list[tuple[str, str, bool]]:
    """(nhãn Việt, nhãn Mông, là nút chính) — nút chính = nút tô đậm / nút cam đầu tiên của lượt."""
    out, main_taken = [], False
    for item in (conv.get("voice_options") or {}).get("items") or []:
        if isinstance(item, dict) and item.get("label") and item.get("labelHmong"):
            chip = item.get("chip") or {}
            main = not main_taken and bool(chip.get("solid") or chip.get("cta"))
            main_taken = main_taken or main
            out.append((re.sub(r"^[^\w(]+", "", str(item["label"])).strip(), str(item["labelHmong"]).strip(), main))
    return out


def _pending_confirm(conv: dict) -> tuple[str, str] | None:
    """Câu hỏi xác nhận đang chờ (nói chọn nút nộp hồ sơ) → (nhãn Việt, nhãn Mông) của việc đang được hỏi."""
    from app.channels.handfree.chat import script_mong as mong

    chip = (conv.get("voice_submit_confirm") or {}).get("chip") or {}
    label = str(chip.get("label") or "").strip()
    if not label:
        return None
    hmong_label = str(chip.get("labelHmong") or mong.CHIP_HMONG.get(label) or "").strip()
    return re.sub(r"^[^\w(]+", "", label).strip(), hmong_label


# Số đếm tiếng Mông là bộ từ đóng — LLM đổi sai (đo 7/12: "hli kaum ib" ra tháng 10, "ob txhiab thiab ob" ra 2012,
# số điện thoại đọc từng số lệch chữ số). Câu trả lời ô tờ khai đổi tất định cụm từ số sang chữ số trước khi dịch; LLM
# vẫn dịch / hiểu cả câu.
_UNITS = {"xoom": 0, "ib": 1, "ob": 2, "peb": 3, "plaub": 4, "tsib": 5, "rau": 6, "xya": 7, "yim": 8, "cuaj": 9}
_MULTIPLIERS = {"kaum", "nkaum", "caug", "caum", "pua", "puas", "txhiab"}
# Từ số đứng một mình chỉ đổi khi đứng sau từ chỉ ngày / tháng / năm, hoặc trước "daim" (tờ, bản) — trừ từ trùng nghĩa
# từ thường ("rau" = vào / cho, "peb" = chúng tôi, "plaub" = lông): "sau rau daim foos" là điền vào tờ khai.
_NUMBER_BEFORE = {"hnub", "hli", "xyoo"}
_NUMBER_AFTER = {"daim"}
_AMBIGUOUS = {"rau", "peb", "plaub"}
_MISHEARD_SIX = {"caug", "caum"}
# Từ thường mà nhận dạng giọng nói tiếng Mông trả thay cho một từ số khi công dân đọc từng chữ số (đo trên bản ghi đọc số
# điện thoại: "xoom" đầu / cuối câu → "yooj", "xwm", "txuj", "saum"; "yim" → "cim", "ncig"). Chỉ đổi khi nằm liền một dãy
# có hai từ số đứng liền nhau — đứng riêng vẫn là từ thường ("yooj yim" = dễ).
_MISHEARD = {"yooj": "xoom", "xwm": "xoom", "txuj": "xoom", "saum": "xoom", "cim": "yim", "ncig": "yim"}


def _resolve_misheard(tokens: list[str]) -> list[str]:
    low = [t.lower().strip(",.") for t in tokens]
    out, i = list(tokens), 0
    while i < len(tokens):
        if not (low[i] in _UNITS or low[i] in _MISHEARD_SIX or low[i] in _MISHEARD):
            i += 1
            continue
        j = i
        while j < len(tokens) and (low[j] in _UNITS or low[j] in _MISHEARD_SIX or low[j] in _MISHEARD):
            j += 1
        span = low[i:j]
        if any(a in _UNITS and b in _UNITS for a, b in zip(span, span[1:])):
            for k in range(i, j):
                if low[k] in _MISHEARD:
                    out[k] = _MISHEARD[low[k]]
        i = j
    return out


def _number_word(token: str) -> bool:
    return token in _UNITS or token in _MULTIPLIERS or token == "nees"


def _run_value(run: list[str]) -> str:
    if not any(t in _MULTIPLIERS for t in run):
        return "".join(str(_UNITS[t]) for t in run if t in _UNITS)  # đọc từng chữ số: số điện thoại, số giấy tờ
    total = hundreds = tens = pending = 0
    for token in run:
        if token in _UNITS:
            pending = _UNITS[token]
        elif token == "nkaum":  # "nees nkaum" = 20
            tens += 20
        elif token == "kaum":
            tens += (pending or 1) * 10
            pending = 0
        elif token in {"caug", "caum"}:
            tens += pending * 10
            pending = 0
        elif token in {"pua", "puas"}:
            hundreds += (pending or 1) * 100
            pending = 0
        elif token == "txhiab":
            total += ((hundreds + tens + pending) or 1) * 1000
            hundreds = tens = pending = 0
    return str(total + hundreds + tens + pending)


def spoken_numbers_to_digits(text: str) -> str:
    """Cụm từ số tiếng Mông → chữ số: "kaum ob hli plaub xyoo ib txhiab cuaj pua xya caum yim" → "12 hli 4 xyoo 1978"."""
    tokens = _resolve_misheard(str(text or "").split())
    out, i = [], 0
    while i < len(tokens):
        word = tokens[i].lower().strip(",.")
        if not _number_word(word) or (word == "nees" and (i + 1 >= len(tokens) or tokens[i + 1].lower() != "nkaum")):
            out.append(tokens[i])
            i += 1
            continue
        j, run = i, []
        while j < len(tokens):
            w = tokens[j].lower().strip(",.")
            nxt = tokens[j + 1].lower().strip(",.") if j + 1 < len(tokens) else ""
            if _number_word(w):
                run.append(w)
            elif w == "thiab" and run and run[-1] in _MULTIPLIERS and _number_word(nxt):
                pass  # "ob txhiab thiab ob" = 2002
            else:
                break
            j += 1
        before = tokens[i - 1].lower() if i else ""
        after = tokens[j].lower().strip(",.") if j < len(tokens) else ""
        single = len(run) == 1 and run[0] in _UNITS
        if single and before not in _NUMBER_BEFORE and (after not in _NUMBER_AFTER or run[0] in _AMBIGUOUS):
            out.append(tokens[i])
            i += 1
            continue
        if any(a in _UNITS and b in _UNITS for a, b in zip(run, run[1:])):
            # Hai từ số liền nhau → đọc từng chữ số (số đọc theo hàng không bao giờ có hai từ số liền nhau): từ hàng
            # chục / trăm lạc vào là nhận dạng giọng nói nghe nhầm một chữ số, không gộp cả dãy thành một số. "caug" /
            # "caum" là "rau" (6) bị nghe nhầm (đo trên bản ghi đọc số điện thoại); từ khác giữ nguyên chữ cho LLM.
            digits = ""
            for word in run:
                if word in _UNITS:
                    digits += str(_UNITS[word])
                elif word in _MISHEARD_SIX:
                    digits += "6"
                else:
                    out.extend([digits, word] if digits else [word])
                    digits = ""
            out.append(digits + ("," if tokens[j - 1].endswith(",") else "") if digits else "")
            out[:] = [w for w in out if w]
            i = j
            continue
        value = _run_value(run)
        out.append(value + ("," if tokens[j - 1].endswith(",") else ""))
        i = j
    return " ".join(out)


def _field_block(field: dict | None) -> str:
    if not field:
        return ""
    options = [str(o) for o in field.get("options") or []][:30]
    return (f'Công dân đang trả lời ô tờ khai: "{field.get("label") or ""}"'
            + (f' (lựa chọn: {"; ".join(options)})' if options else "") + "\n\n")


def _prompt(text: str, last_bot: str, buttons: list[tuple] | None = None,
            pending: tuple[str, str] | None = None, field: dict | None = None) -> list[dict]:
    context = f"Câu trợ lý vừa nói với công dân (tiếng Việt): {last_bot[:400]}\n\n" if last_bot else ""
    context += _field_block(field)
    context += _buttons_block(buttons or [])
    if pending:
        context += (f'Đang chờ công dân xác nhận việc: "{pending[0]}"'
                    + (f' = "{pending[1]}"' if pending[1] else "") + "\n\n")
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"{context}Câu công dân (tiếng Mông): {text[:_MAX_INPUT]}"}]


def _last_bot_text(conv: dict) -> str:
    for item in reversed(conv.get("history") or []):
        if isinstance(item, dict) and item.get("role") == "bot" and item.get("text"):
            return re.sub(r"[*_`#>]+", "", str(item["text"])).strip()
    return ""


async def translate(text: str, last_bot: str = "", buttons: list[tuple] | None = None,
                    pending: tuple[str, str] | None = None, field: dict | None = None) -> str:
    """Câu tiếng Mông → câu tiếng Việt; "" khi lỗi / không ra câu. `field`: ô tờ khai đang hỏi (nhãn, lựa chọn)."""
    if field:
        text = spoken_numbers_to_digits(text)
    try:
        raw = await llm_chat(_prompt(text, last_bot, buttons, pending, field), temperature=0.0,
                             max_tokens=_MAX_TOKENS, purpose="hmong_translate")
        match = re.search(r"\{[\s\S]*\}", raw or "")
        data = json.loads(match.group(0)) if match else {}
    except Exception as exc:  # noqa: BLE001 — dịch là best-effort, luồng phải đi tiếp với câu gốc
        logger.warning("[hmong_translate] LLM lỗi: %s", exc)
        return ""
    if data.get("chi_noi_khai_sinh") is True and not field:
        return BIRTH_COPY_REQUEST
    return " ".join(str(data.get("vi") or "").split())[:_MAX_INPUT]


async def understood_text(conv: dict, message: str, field: dict | None = None) -> str:
    """Câu đưa cho bộ hiểu câu ở lượt này: bản dịch tiếng Việt nếu có, không thì câu gốc. Lưu cả hai để soát.
    `field`: đang hỏi một ô tờ khai (vòng bổ sung) — dịch như câu trả lời cho ô đó."""
    vi = await translate(message, _last_bot_text(conv), _visible_buttons(conv), _pending_confirm(conv), field)
    conv["hmong_translation"] = {"src": str(message)[:_MAX_INPUT], "vi": vi}
    return vi or message
