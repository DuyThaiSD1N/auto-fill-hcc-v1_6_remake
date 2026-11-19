"""Thanh tra ĐỊNH DANH hồ sơ đăng ký khai sinh: họ tên và dân tộc của người được khai sinh, mẹ, cha, người yêu cầu.

Lỗi gặp nhiều nhất: tờ khai VIẾT TAY bị OCR đọc lệch dấu / một hai chữ cái ở họ tên cha, mẹ, trong khi giấy IN của
chính người đó trong cùng hồ sơ (trích lục khai tử, giấy khai sinh của anh chị em ở dòng cha / mẹ, bản cam đoan đánh
máy, thẻ căn cước) ghi đúng. Cách kiểm (khuôn đọc trang của thanh tra định danh thủ tục cấp Giấy XNTTHN):
1. Mỗi trang giấy được model đọc RIÊNG thành danh sách nhân thân (không biết kết quả lượt trích).
2. MÃ nhận bản ghi là của người ở vai đang xét: họ tên gần trùng (cùng số tiếng, lệch tối đa hai chữ cái khi bỏ dấu)
   kèm trùng số định danh, hoặc đứng ở đúng vai cha / mẹ trên giấy hộ tịch, hoặc trùng ngày / năm sinh. Số định danh
   khác hẳn là người khác.
3. Cách viết nào thắng do MÃ đếm thẳng số giấy OCR ghi nguyên văn từng cách viết theo hạng nguồn: giấy cơ quan cấp >
   bản cam đoan / đơn > tờ khai viết tay, cùng hạng thì nhiều giấy hơn thắng (dòng họ tên thẻ in hoa tính nửa khi chỉ
   khác dấu); cách viết đề xuất không được là bản rơi dấu của lượt trích.
Không có nguyên văn trên giấy nào thì không đề xuất (thà thiếu còn hơn sai).
"""

import asyncio
import re
from dataclasses import dataclass

from app.config import settings
from app.pipelines._shared.cccd import id_birth_year
from app.pipelines._shared.ethnic_normalize import ethnicity_for_form, normalize_ethnic
from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dinh_danh as base
from app.services.llm import client

from . import chu_the
from .chu_the import ROLES, Role

_TABLE_NOTE = "- người yêu cầu và người được cấp trên tờ khai — hai khối khác nhau là HAI mục, kể cả khi trùng họ tên;"
assert _TABLE_NOTE in base._PAGE_PROMPT
# Năm sinh cha / mẹ trên tờ khai, đơn, giấy khai sinh cũ thường chỉ ghi năm: thanh tra năm sinh cha mẹ cần chép năm.
_YEAR_ONLY_NULL = 'Trang chỉ ghi "sinh năm\n  1960" → null.'
assert _YEAR_ONLY_NULL in base._PAGE_PROMPT
# Lượt đọc một trang: thêm cách đọc tờ khai đăng ký khai sinh và các giấy hộ tịch hay đi kèm.
_PAGE_PROMPT = base._PAGE_PROMPT.replace(_TABLE_NOTE, _TABLE_NOTE + """
- TỜ KHAI ĐĂNG KÝ KHAI SINH: người yêu cầu, người được đăng ký khai sinh (mục "Đề nghị cơ quan đăng ký
  khai sinh cho người có tên dưới đây"), mẹ, cha — mỗi khối là MỘT mục, "vai" ghi "người yêu cầu" / "người được khai
  sinh" / "mẹ" / "cha", "loai_giay" là "to_khai";
- giấy khai sinh / trích lục khai sinh: người được khai sinh, mẹ, cha — mỗi người một mục, "vai" ghi "người được khai
  sinh" / "mẹ" / "cha" đúng như dòng trên giấy; trích lục khai tử: người chết ("vai" ghi "người chết");""").replace(
    _YEAR_ONLY_NULL, 'Trang chỉ ghi NĂM sinh ("sinh năm 1960", "Năm sinh:\n  1936") → chép đúng năm "yyyy" (năm sinh cha / mẹ\n  hay chỉ ghi năm).')

RULES = """
<nam_sinh>
- Ngày / năm sinh của cha / mẹ: B là năm sinh ghi cho CHÍNH người đó trên giấy IN (đơn, bản cam đoan đánh máy, trích
  lục, giấy khai sinh, thẻ), A khác NĂM và chỉ có trên tờ khai viết tay (mã đã kiểm: năm của A không có trên giấy in nào
  của người đó) → chọn B. Tờ khai viết tay hay ghi lệch năm sinh cha mẹ; đơn đề nghị / xác nhận còn hay nói rõ tờ khai
  trước đã ghi sai.
- Dòng chứng cứ là năm sinh của người khác (anh chị em, người yêu cầu) → KHONG_DU_CAN_CU.
</nam_sinh>
<bon_vai>
Hồ sơ đăng ký khai sinh có bốn vai: người được đăng ký khai sinh, mẹ, cha, người yêu cầu. Vai đã được chốt ở
bước phân vai; mỗi vụ chỉ xét MỘT vai, nêu ở tên mục. Mã đã nhận từng bản ghi là của người ở vai đó (họ tên gần trùng
kèm số định danh, hoặc đứng ở đúng dòng cha / mẹ trên giấy hộ tịch, hoặc trùng ngày / năm sinh) — căn cứ ghi ở dòng
"Tín hiệu mã". Giấy khai sinh của anh chị em ghi cùng cha / mẹ ở dòng cha / mẹ là giấy của CHÍNH cha / mẹ đó.
Người được đăng ký khai sinh CHƯA TỪNG có giấy khai sinh của mình: hồ sơ chứng minh họ tên của họ bằng giấy tờ khác —
giấy khai sinh / trích lục khai sinh của CON họ (họ đứng ở dòng "người cha" / "người mẹ" / "người đi khai sinh"), giấy
chứng nhận kết hôn (dòng chồng / vợ), giấy xác nhận của UBND / cơ quan. Các dòng đó là của CHÍNH người được đăng ký khai
sinh (cùng người yêu cầu khi tự đi làm cho mình), không phải "sai vai": dòng "Họ, chữ đệm, tên người cha: X" trên giấy
khai sinh của con mang tên NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI SINH, không phải tên cha của người đó. Mục đang xét là người được
đăng ký khai sinh / người yêu cầu mà B có trên các dòng như vậy (kèm dòng "Tín hiệu mã" nhận theo số định danh / ngày
sinh) thì đó là căn cứ đúng người, KHÔNG được giữ A với lý do "B là tên cha".
</bon_vai>

<do_tin_cua_nguon>
Họ tên trên TÀI KHOẢN ĐĂNG NHẬP CỔNG (CSDL quốc gia) của chính người ở vai đó đứng trên mọi giấy. Còn lại: cách viết
được NHIỀU giấy ghi hơn thắng; số giấy bằng nhau thì theo thứ tự tin: 1. giấy do CƠ QUAN cấp — trích lục / giấy khai tử, giấy khai sinh / trích lục khai sinh, giấy chứng tử,
CCCD / CMND, sổ hộ khẩu, phiếu thông tin dân cư (riêng họ tên IN HOA trên mặt thẻ đôi khi bị rơi DẤU); 2. bản cam đoan,
đơn, giấy ủy quyền do người dân tự lập; 3. TỜ KHAI đăng ký khai sinh viết tay — kém tin nhất, hay lệch một dấu, một
chữ cái. Mã đã đếm sẵn số giấy từng hạng ở dòng "Tín hiệu mã".
</do_tin_cua_nguon>

<ho_ten>
- B là họ tên trên tài khoản đăng nhập cổng của chính người ở vai đó → chọn B.
- B được nhiều giấy ghi hơn A (so dòng "TỔNG số giấy" trong tín hiệu mã; hạng giấy chỉ dùng khi tổng bằng nhau) của
  chính người ở vai đó → chọn B, kể cả khi A có giấy cơ quan cấp mà B không có. Hai cách viết
  chỉ khác DẤU là chuyện thường (OCR đọc lệch dấu), KHÔNG phải lý do giữ A: vẫn so số giấy, hạng giấy như trên.
- Mã đã tự loại các cách viết là bản rơi dấu của A, chữ Đ đọc thành D, và cách viết đổi chữ cái mà chữ cái của A đã có
  trên giấy khác tờ khai — B đến được toà là đã qua các phép chặn đó; không lấy các lý do này để giữ A.
- Chọn đúng từng chữ, từng dấu như trên giấy; không tự sửa dấu.
</ho_ten>

<dan_toc>
- A không có trong danh mục dân tộc (chữ OCR vô nghĩa) hoặc bỏ trống, B là dân tộc có trong danh mục ghi ở dòng "Dân
  tộc" của CHÍNH người ở vai đó trên một giấy khác của hồ sơ → chọn B.
- A có trong danh mục nhưng chỉ có trên tờ khai viết tay, B ghi trên giấy IN của chính người đó (trích lục khai tử,
  giấy khai sinh) → chọn B.
- Dòng chứng cứ là dân tộc của người khác trên cùng trang → KHONG_DU_CAN_CU.
</dan_toc>
"""

_MAX_PAGES = 10
_MAX_LETTER_SLIP = 2
_DECLARATION_TITLE = "to khai dang ky khai sinh"
_OTHER_PAPER_TITLES = ("ban cam doan", "giay cam doan", "giay cam ket", "trich luc", "giay khai sinh", "giay chung tu",
                       "giay uy quyen", "don xin", "don de nghi", "giay xac nhan", "can cuoc", "giay chung minh")


# Năm sinh chỉ soát cho cha / mẹ: tờ khai viết tay hay ghi lệch năm sinh cha mẹ, còn đơn / giấy in của chính người đó
# ghi đúng; năm sinh người được khai sinh đã có thẻ căn cước đối chiếu ở mapper.
_BIRTH_ROLES = ("me", "cha")


def _birth_canon(value) -> str:
    return " ".join(re.findall(r"\d+", str(value or "")))


def _units(role: Role) -> dict[str, Unit]:
    units = {"ho_ten": Unit(f"{role.key}.ho_ten", f"Họ tên {role.label}",
                            (Field(f"{role.prefix}_FullName", "họ, chữ đệm, tên", canon=base._name_key),))}
    if role.ethnic:
        units["dan_toc"] = Unit(f"{role.key}.dan_toc", f"Dân tộc {role.label}",
                                (Field(role.ethnic, "dân tộc", canon=fold),))
    if role.key in _BIRTH_ROLES:
        units["nam_sinh"] = Unit(f"{role.key}.nam_sinh", f"Ngày / năm sinh {role.label}",
                                 (Field(role.birth, "ngày / năm sinh", canon=_birth_canon),))
    return units


UNITS_BY_ROLE = {role.key: _units(role) for role in ROLES}
UNITS = tuple(unit for units in UNITS_BY_ROLE.values() for unit in units.values())


def _edit(a: str, b: str) -> int:
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, cb in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (ca != cb))
    return row[-1]


def close_name(a, b) -> bool:
    """Hai họ tên là một người đọc lệch: cùng số tiếng, khi bỏ dấu lệch tối đa hai chữ cái. Tiếng ngắn (≤3 chữ cái)
    chỉ cho lệch một chữ: "Nam" / "Nụ" lệch hai chữ là hai cái tên khác hẳn, từng ghép nhầm người khác trong sổ hộ khẩu."""
    left, right = fold(a).split(), fold(b).split()
    if not left or len(left) != len(right) or _edit(" ".join(left), " ".join(right)) > _MAX_LETTER_SLIP:
        return False
    return all(_edit(x, y) <= 1 for x, y in zip(left, right) if x != y and min(len(x), len(y)) <= 3)


def valid_ethnic(value) -> bool:
    chosen, _ = ethnicity_for_form(value)
    return bool(chosen) and chosen != "Khác"


def _handwritten(name_line: str, page_text: str, kind: str) -> bool:
    """Bản ghi thuộc phần tờ khai đăng ký khai sinh của trang (từ đầu tới hết khối chữ ký) → chữ viết tay."""
    if kind == "to_khai":
        return True
    if _DECLARATION_TITLE not in fold(page_text):
        return False
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    end = next((i for i, line in enumerate(lines) if "ky, ghi ro ho" in fold(line)), None)
    at = next((i for i, line in enumerate(lines) if name_line and base._name_key(name_line) in base._name_key(line)), None)
    if end is None or at is None:
        return True
    return at <= end + base._SIGNATURE_LINES


def pages(documents: list[dict], people: list[dict]) -> list[dict]:
    """Các trang có dấu vết của ít nhất một người cần soát (gần đủ các tiếng của họ tên, hoặc số định danh)."""
    out = []
    for index, document in enumerate(documents, start=1):
        for text in base._PAGE_BREAK_RE.split(str(document.get("text") or "")):
            if not text.strip():
                continue
            words, numbers = set(fold(text).split()), chu_the.digits(text)
            for person in people:
                tokens = fold(person["name"]).split()
                if (len(tokens) >= 2 and sum(token in words for token in tokens) >= len(tokens) - 1) or (
                        len(person["number"]) >= 9 and person["number"] in numbers):
                    out.append({"doc": index, "text": text.strip()})
                    break
    return out[:_MAX_PAGES]


async def _read_page(page: dict, title: str) -> list[dict]:
    raw = await client.chat(
        [{"role": "system", "content": _PAGE_PROMPT.format(title=title)},
         {"role": "user", "content": f"Chữ OCR của trang giấy:\n\n{page['text']}"}],
        max_tokens=base._MAX_TOKENS, temperature=0, enable_thinking=settings.agent_reasoning,
        purpose="thanh_tra.dinh_danh",
    )
    return records_from(engine.parse_json(raw).get("nguoi"), page)


def records_from(people, page: dict) -> list[dict]:
    records = []
    for person in people if isinstance(people, list) else []:
        if not isinstance(person, dict) or not str(person.get("ho_ten") or "").strip():
            continue
        kind = str(person.get("loai_giay") or "").strip()
        weak = _handwritten(str(person.get("dong") or person["ho_ten"]), page["text"], kind)
        records.append({"name": " ".join(str(person["ho_ten"]).split()), "number": chu_the.digits(person.get("so_dinh_danh")),
                        "birth": base._birth_key(person.get("ngay_sinh")),
                        "birth_text": str(person.get("ngay_sinh") or "").strip(),
                        "ethnic": base._ethnic(person.get("dan_toc")), "role": str(person.get("vai") or "").strip(),
                        "doc": page["doc"], "text": page["text"], "handwritten": weak})
    return records


@dataclass
class _Link:
    record: dict
    why: str
    same_number: bool


def _belongs(record: dict, role: Role, person: dict, others: list[dict]) -> _Link | None:
    """Bản ghi là của người ở vai đang xét. Họ tên phải gần trùng; số định danh khác hẳn là người khác."""
    if not close_name(record["name"], person["name"]):
        return None
    if person["number"] and record["number"]:
        if record["number"] == person["number"]:
            return _Link(record, "trùng số định danh", True)
        if base._number_slip(record["number"], person["number"]):
            return _Link(record, "số định danh lệch tối đa hai chữ số", False)
        return None
    # Họ tên trùng hẳn (bỏ dấu) với người ở vai KHÁC thì không đủ căn cứ là người này (cha con trùng tên).
    if any(fold(other["name"]).split() == fold(record["name"]).split() for other in others):
        return None
    if chu_the.plays(record["role"], role):
        return _Link(record, f"đứng ở dòng {role.label} trên giấy", False)
    # Trích lục / giấy khai tử trong hồ sơ đăng ký khai sinh là giấy của chính cha / mẹ (hoặc người được đăng ký
    # lại) — tờ khai thường không ghi năm sinh cha mẹ để đối chiếu thêm, nên cùng họ + tên gần trùng là đủ.
    if role.key != "nyc" and "chet" in fold(record["role"]).split() and (
            fold(record["name"]).split()[:1] == fold(person["name"]).split()[:1]):
        return _Link(record, "người chết trên giấy khai tử cùng họ, tên gần trùng", False)
    if person["birth"] and base._birth_key(person["birth"]) and record["birth"] == base._birth_key(person["birth"]):
        return _Link(record, "trùng ngày sinh", False)
    same_letters = fold(record["name"]).split() == fold(person["name"]).split()
    year = chu_the.birth_year(person["birth"])
    if same_letters and year and year == chu_the.birth_year(record["birth_text"]):
        return _Link(record, "trùng họ tên không dấu và năm sinh", False)
    return None


def _weigh(links: list[_Link], key_of) -> dict:
    """Điểm nguồn từng giá trị: mỗi trang tính một lần, giấy in 1, viết tay 0,5, ghi đúng số định danh nhân đôi."""
    slots: dict = {}
    for link in links:
        key = key_of(link.record)
        if not key:
            continue
        slot = slots.setdefault(key, {"weight": 0.0, "printed": 0.0, "pages": set(), "link": None})
        page = (id(link.record["text"]), link.record["handwritten"])
        if page in slot["pages"]:
            continue
        slot["pages"].add(page)
        weight = (0.5 if link.record["handwritten"] else 1.0) * (2 if link.same_number else 1)
        slot["weight"] += weight
        if not link.record["handwritten"]:
            slot["printed"] += weight
            if slot["link"] is None or slot["link"].record["handwritten"] or (link.same_number and not slot["link"].same_number):
                slot["link"] = link
        elif slot["link"] is None:
            slot["link"] = link
    return slots


def _quote(text: str, needle_key: str) -> str:
    for line in text.splitlines():
        if line.strip() and needle_key in base._name_key(line):
            return line.strip()
    return ""


def _words(value) -> str:
    # Khóa họ tên đặt dấu thanh cuối chữ (dạng tổ hợp): tách chữ phải giữ cả dấu tổ hợp đi kèm.
    return f" {' '.join(base._WORD_RE.findall(base._name_key(value)))} "


def _card_line(line: str) -> bool:
    """Dòng họ tên in hoa của thẻ căn cước / CCCD (nhãn song ngữ): OCR hay rơi / lệch dấu ở chữ in hoa."""
    return "full name" in fold(line)


def declaration_lines(document: dict) -> list[tuple[int, str, bool]]:
    """(số trang, dòng, thuộc tờ khai viết tay) của mọi dòng trong một tài liệu. Tờ khai đăng ký khai sinh có thể
    sang trang thứ hai (trang sau không in lại tiêu đề): vùng viết tay tính từ dòng tiêu đề tới hết khối chữ ký."""
    out, page, inside, tail, start = [], 0, False, -1, 0
    for raw in str(document.get("text") or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if base._PAGE_BREAK_RE.fullmatch(raw):
            page += 1
            # Không thấy khối chữ ký (OCR mất dòng nhãn): tờ khai không dài quá hai trang.
            inside = inside and page <= start + 1
            continue
        folded = fold(line)
        if _DECLARATION_TITLE in folded:
            inside, tail, start = True, -1, page
        elif inside and folded.startswith(_OTHER_PAPER_TITLES):
            # Tiêu đề một giấy khác (bản cam đoan, trích lục...) quét liền sau tờ khai trong cùng tệp: hết vùng viết tay.
            inside, tail = False, -1
        out.append((page, line, inside or tail > 0))
        if tail > 0:
            tail -= 1
        if inside and "ky, ghi ro ho" in folded:
            inside, tail = False, base._SIGNATURE_LINES
    return out


ACCOUNT_DOC_NAME = "tai-khoan-dang-nhap-cong"
_ACCOUNT_NAME_LABEL = "Họ và tên trên tài khoản"


def account_document(options: dict | None) -> dict | None:
    """Tài khoản VNeID đang đăng nhập cổng (khối người yêu cầu cổng tự đổ) thành một "tài liệu" của hồ sơ thanh tra: là
    nguồn họ tên chuẩn nhất (CSDL quốc gia), và engine chỉ nhận giá trị có nguyên văn trong tài liệu của hồ sơ."""
    ctx = (options or {}).get("formContext") or {}
    name = " ".join(str(ctx.get("applicantFullname") or "").split())
    if not name:
        return None
    number = chu_the.digits(ctx.get("applicantIdentityNumber"))
    return {"name": ACCOUNT_DOC_NAME,
            "text": f"TÀI KHOẢN ĐĂNG NHẬP CỔNG\n{_ACCOUNT_NAME_LABEL}: {name}\nSố định danh trên tài khoản: {number}"}


def _account(documents: list[dict]) -> dict | None:
    for document in documents:
        if document.get("name") == ACCOUNT_DOC_NAME:
            text = str(document.get("text") or "")
            name = re.search(rf"{_ACCOUNT_NAME_LABEL}:\s*(.+)", text)
            number = re.search(r"Số định danh trên tài khoản:\s*(\d*)", text)
            return {"name": name.group(1).strip() if name else "", "number": number.group(1) if number else ""}
    return None


def account_finding(role: Role, person: dict, documents: list[dict]) -> Finding | None:
    """Người ở vai đó chính là chủ tài khoản đăng nhập → họ tên theo tài khoản. Cùng số định danh là chắc chắn; không có
    số thì chỉ vai người yêu cầu, cùng họ và tên gần trùng (close_name). Khác hẳn thì không đụng."""
    account = _account(documents)
    if not account or not account["name"]:
        return None
    same_number = bool(person["number"] and account["number"] and person["number"] == account["number"])
    # Không trùng số thì chỉ nhận cho VAI NGƯỜI YÊU CẦU (chủ tài khoản là người đang đăng nhập) với tên gần trùng: cha / mẹ
    # cùng họ, cùng tên đệm với người con đăng nhập mà tên lệch hai chữ ("Cướng" / "Dũng") là người khác.
    near = role.key == "nyc" and close_name(person["name"], account["name"]) and (
        fold(person["name"]).split()[:1] == fold(account["name"]).split()[:1])
    if person["number"] and account["number"] and not same_number:
        return None
    if not (same_number or near) or base._name_key(account["name"]) == base._name_key(person["name"]):
        return None
    return Finding(INSPECTOR, UNITS_BY_ROLE[role.key]["ho_ten"], {f"{role.prefix}_FullName": account["name"]},
                   f"{_ACCOUNT_NAME_LABEL}: {account['name']}", len(documents), f"tài khoản đăng nhập cổng là {role.label}",
                   role.label, backed=True,
                   evidence=(f"họ tên trên tài khoản đăng nhập cổng (CSDL quốc gia) — {'trùng số định danh' if same_number else 'cùng họ, tên gần trùng'} "
                             f"với {role.label}; nguồn chuẩn nhất, đứng trên mọi giấy trong hồ sơ",))


_AGENCY_MARKERS = ("trich luc", "giay khai sinh", "giay chung tu", "giay bao tu", "chung minh nhan dan", "can cuoc",
                   "ho khau", "ket qua kiem tra thong tin", "chung nhan ket hon")
_SELF_MADE_MARKERS = ("to khai", "cam doan", "cam ket", "uy quyen")


def _agency_page(lines: list[str]) -> bool:
    """Trang do cơ quan cấp (trích lục, giấy khai sinh / chứng tử, CMND, sổ hộ khẩu, phiếu dân cư). Bản cam đoan, đơn, giấy
    ủy quyền là người dân tự viết / tự gõ."""
    head = " ".join(fold(line) for line in lines[:chu_the._HEADER_LINES])
    return any(marker in head for marker in _AGENCY_MARKERS) and not any(marker in head for marker in _SELF_MADE_MARKERS)


def spelling_support(name, documents: list[dict]) -> dict:
    """Số TÀI LIỆU ghi đúng cách viết họ tên này theo từng hạng nguồn (đếm thẳng trong OCR, không qua model): giấy do cơ
    quan cấp, dòng họ tên in hoa của thẻ, bản cam đoan / đơn người dân tự lập, tờ khai viết tay."""
    needle = _words(name)
    out = {"giay": 0, "ban_in": 0, "card": 0, "cam_doan": 0, "to_khai": 0}
    if not needle.strip():
        return out
    for document in documents:
        if document.get("name") == ACCOUNT_DOC_NAME:
            continue
        lines = declaration_lines(document)
        by_page: dict[int, list[str]] = {}
        for page, line, _ in lines:
            by_page.setdefault(page, []).append(line)
        # Mỗi TRANG là một giấy: hồ sơ hay quét cả tập vào một tệp PDF nhiều trang, đếm theo tệp thì mọi cách viết đều
        # "một giấy". Trang trùng nguyên văn (quét hai lần) chỉ tính một.
        seen_pages: set[str] = set()
        for page, page_lines in by_page.items():
            text = "\n".join(page_lines)
            if text in seen_pages:
                continue
            seen_pages.add(text)
            kinds = {
                "to_khai" if handwritten else "card" if _card_line(line)
                else "ban_in" if _agency_page(page_lines) else "cam_doan"
                for at, line, handwritten in lines if at == page and needle in _words(line)
            }
            for kind in kinds:
                out[kind] += 1
            out["giay"] += bool(kinds)
    return out


def _letters_on_paper(name, documents: list[dict]) -> bool:
    """Chữ cái (bỏ dấu) của họ tên có trên một dòng giấy nào ngoài tờ khai viết tay."""
    target = f" {' '.join(fold(name).split())} "
    return bool(target.strip()) and any(
        target in f" {' '.join(fold(line).split())} "
        for document in documents if document.get("name") != ACCOUNT_DOC_NAME
        for _, line, handwritten in declaration_lines(document) if not handwritten)


def _rank(support: dict, letters_differ: bool) -> tuple:
    """Số giấy ghi cách viết đó trước; bằng nhau thì xét hạng: giấy cơ quan cấp (kể cả thẻ) > bản cam đoan / đơn > tờ khai.
    (letters_differ giữ để nơi gọi không đổi.)"""
    return (support["giay"], support["ban_in"] + support["card"], support["cam_doan"], support["to_khai"])


def _printed_mark_variant(current, proposed, documents: list[dict]) -> bool:
    """Đề xuất ít dấu hơn lượt trích nhưng là cách viết CÓ DẤU khác hẳn (Tiên / Tiến, không phải chữ trơn "TIEN"), được
    từ 2 trang giấy cơ quan cấp / thẻ ghi nguyên văn, còn cách viết lượt trích không có trên giấy cơ quan nào → không phải
    OCR rơi dấu: hai giấy in cùng rơi đúng một dấu là hiếm, bản cam đoan / tờ khai tự viết mới hay ghi sai dấu."""
    changed = [(a, b) for a, b in zip(str(current).split(), str(proposed).split()) if a != b]
    if not changed or any(fold(b) == b.lower() for _, b in changed):
        return False
    mine, best = spelling_support(current, documents), spelling_support(proposed, documents)
    return best["ban_in"] + best["card"] >= 2 and mine["ban_in"] + mine["card"] == 0


def spelling_wins(current, proposed, documents: list[dict]) -> bool:
    """Cách viết đề xuất thắng cách viết lượt trích theo hạng nguồn. Chặn: đề xuất chỉ là bản rơi dấu của lượt trích (OCR
    hay rơi dấu chứ không tự thêm), chữ "Đ" thành "D"; đề xuất chỉ có trên tờ khai viết tay."""
    ours, theirs = base._name_key(current), base._name_key(proposed)
    if not ours or not theirs or ours == theirs:
        return False
    letters_differ = fold(ours).split() != fold(theirs).split()
    if not letters_differ and (base._adds_marks(theirs, ours) or base._lost_stroke(theirs, ours)) \
            and not _printed_mark_variant(current, proposed, documents):
        return False
    # Đổi CHỮ CÁI chỉ khi chữ cái của lượt trích không có trên giấy nào ngoài tờ khai: có rồi thì tên đúng, chỉ được sửa
    # dấu — cách viết khác chữ được nhiều giấy ghi hơn thường là tên NGƯỜI KHÁC (anh chị em, vợ / chồng) trên các giấy đó.
    if letters_differ and _letters_on_paper(current, documents):
        return False
    mine, best = spelling_support(current, documents), spelling_support(proposed, documents)
    if best["ban_in"] + best["card"] + best["cam_doan"] < 1:
        return False
    return _rank(best, letters_differ) > _rank(mine, letters_differ)


def _mark_variants(current, documents: list[dict]) -> dict[str, dict]:
    """Mọi cách viết CHỈ KHÁC DẤU của họ tên lượt trích có nguyên văn trên giấy (ngoài tờ khai viết tay) — lượt đọc
    trang có thể bỏ qua dòng phụ như "người đi khai sinh" mà chính dòng đó ghi đúng dấu."""
    target = fold(current).split()
    size = len(target)
    out: dict[str, dict] = {}
    if size < 2:
        return out
    for index, document in enumerate(documents, start=1):
        if document.get("name") == ACCOUNT_DOC_NAME:
            continue
        pages_text = base._PAGE_BREAK_RE.split(str(document.get("text") or ""))
        for page, line, handwritten in declaration_lines(document):
            if handwritten:
                continue
            words = base._WORD_RE.findall(line)
            for start in range(len(words) - size + 1):
                window = words[start:start + size]
                key = base._name_key(" ".join(window))
                if fold(" ".join(window)).split() == target and key != base._name_key(current) and key not in out:
                    text = pages_text[page] if page < len(pages_text) else line
                    out[key] = {"name": " ".join(window).upper(), "text": text, "doc": index, "handwritten": False}
    return out


def name_finding(role: Role, person: dict, links: list[_Link], documents: list[dict]) -> Finding | None:
    """Các cách viết của chính người ở vai đó (lượt đọc trang thấy trên giấy, cộng mọi cách viết chỉ khác dấu có trên
    giấy); cách viết hạng nguồn cao nhất, hơn hẳn cách viết lượt trích (spelling_wins) thì đề xuất."""
    current = base._name_key(person["name"])
    candidates: dict[str, _Link] = {}
    for link in links:
        key = base._name_key(link.record["name"])
        if key and key != current and not link.record["handwritten"]:
            if key not in candidates or (link.same_number and not candidates[key].same_number):
                candidates[key] = link
    for key, record in _mark_variants(person["name"], documents).items():
        # Câu lý do không dùng cụm "chỉ khác dấu": toà đọc thành lý do giữ A.
        candidates.setdefault(key, _Link(record, "cùng chữ cái với họ tên của vai này, có nguyên văn trên giấy", False))
    winners = [(key, link) for key, link in candidates.items()
               if spelling_wins(person["name"], link.record["name"], documents)]
    if not winners:
        return None
    ranked = sorted(
        ((_rank(spelling_support(link.record["name"], documents), fold(key).split() != fold(current).split()), key, link)
         for key, link in winners), key=lambda item: item[0], reverse=True)
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        return None
    _, key, link = ranked[0]
    quote, doc = _quote(link.record["text"], key), link.record["doc"]
    if not quote:
        # Lượt đọc trang đôi khi tự chuẩn hoá chữ (trang ghi một kiểu, bản ghi trả kiểu khác): cách viết thắng đã được
        # đếm trên giấy nên lấy dòng nguyên văn ở giấy khác của hồ sơ.
        quote, doc = next(((line, index) for index, document in enumerate(documents, start=1)
                           if document.get("name") != ACCOUNT_DOC_NAME
                           for line in [_quote(str(document.get("text") or ""), key)] if line), ("", 0))
    if not quote:
        return None
    # Dòng chứng cứ ghi kèm số định danh KHÁC số của vai → dòng của người khác cùng họ tên (anh em trong danh sách).
    numbers = set(re.findall(r"(?<!\d)\d{12}(?!\d)", quote))
    if len(person.get("number") or "") == 12 and numbers and person["number"] not in numbers:
        return None
    mine, best = spelling_support(person["name"], documents), spelling_support(link.record["name"], documents)
    return Finding(INSPECTOR, UNITS_BY_ROLE[role.key]["ho_ten"], {f"{role.prefix}_FullName": link.record["name"]}, quote,
                   doc, f"giấy ghi họ tên {role.label} ({link.why})", role.label, backed=True,
                   evidence=(f"TỔNG số giấy ghi nguyên văn: B {best['giay']}, A {mine['giay']}. "
                             f"Cách viết của B có nguyên văn trên {best['ban_in']} giấy do cơ quan cấp, {best['card']} dòng "
                             f"họ tên thẻ, {best['cam_doan']} bản cam đoan / đơn, {best['to_khai']} tờ khai viết tay (mã nhận "
                             f"là {role.label} vì: {link.why}); cách viết của A: {mine['ban_in']} giấy cơ quan cấp, "
                             f"{mine['card']} dòng thẻ, {mine['cam_doan']} bản cam đoan / đơn, {mine['to_khai']} tờ khai",))


def _ethnic_outside_declaration(value, documents: list[dict]) -> bool:
    needle = f" {fold(normalize_ethnic(value))} "
    return any("dan toc" in fold(line) and needle in f" {' '.join(re.findall(r'[0-9a-z]+', fold(line)))} "
               for document in documents for _, line, handwritten in declaration_lines(document) if not handwritten)


def ethnic_finding(role: Role, person: dict, links: list[_Link], documents: list[dict]) -> Finding | None:
    if not role.ethnic:
        return None
    current = person["ethnic"]
    canon = lambda value: fold(normalize_ethnic(value))  # noqa: E731
    slots = _weigh([link for link in links if valid_ethnic(link.record["ethnic"])],
                   lambda record: canon(record["ethnic"]))
    if not slots:
        return None
    ranked = sorted(slots.items(), key=lambda item: (item[1]["weight"], item[1]["printed"]), reverse=True)
    key, best = ranked[0]
    if len(ranked) > 1 and ranked[1][1]["weight"] == best["weight"]:
        return None
    if current and key == canon(current):
        return None
    mine = slots.get(canon(current), {"weight": 0.0, "printed": 0.0}) if current else {"weight": 0.0, "printed": 0.0}
    record = best["link"].record
    # Dân tộc lượt trích hợp lệ chỉ đổi theo giấy do cơ quan hộ tịch cấp ghi cho chính người đó, khi chữ của lượt trích
    # không có ở dòng dân tộc nào ngoài tờ khai viết tay.
    if valid_ethnic(current) and not (best["weight"] > mine["weight"] and not record["handwritten"]
                                      and chu_the.issued(record["text"].splitlines())
                                      and not _ethnic_outside_declaration(current, documents)):
        return None
    quote = next((line.strip() for line in record["text"].splitlines()
                  if "dan toc" in fold(line) and fold(record["ethnic"]) in fold(line)), "")
    if not quote:
        return None
    state = "bỏ trống" if not current else ("không có trong danh mục dân tộc" if not valid_ethnic(current)
                                             else "chỉ có trên tờ khai viết tay")
    return Finding(INSPECTOR, UNITS_BY_ROLE[role.key]["dan_toc"], {role.ethnic: record["ethnic"]}, quote, record["doc"],
                   f"dòng dân tộc của {role.label} ({best['link'].why})", role.label, backed=True,
                   evidence=(f"dân tộc của A {state}; B có {best['weight']:g} điểm nguồn ({best['printed']:g} điểm giấy in) "
                             f"ghi cho chính {role.label}",))


def _year(value) -> str:
    found = re.findall(r"(?<!\d)(1[89]\d\d|20\d\d)(?!\d)", str(value or ""))
    return found[-1] if found else ""


def _impossible_birth(year: str, person: dict, child_year: int | None) -> bool:
    """Năm đề xuất ngược số định danh của chính người đó (số mã hoá năm sinh) hoặc không hơn con đủ 15 tuổi."""
    encoded = id_birth_year(person.get("number") or "") if len(person.get("number") or "") == 12 else None
    return bool((encoded and encoded != int(year)) or (child_year and child_year - int(year) < 15))


def birth_finding(role: Role, person: dict, links: list[_Link], child_year: int | None = None) -> Finding | None:
    """Năm sinh cha / mẹ: mỗi trang ghi năm sinh cho chính người đó là một nguồn (giấy in 1 điểm, tờ khai viết tay 0,5).
    Đề xuất khi năm khác lượt trích, nhiều điểm hơn, có giấy in, và năm của lượt trích không có trên giấy in nào."""
    if role.key not in _BIRTH_ROLES:
        return None
    current = _year(person["birth"])
    # Bản ghi nhận là của người này NHỜ trùng ngày sinh thì không làm nguồn đổi chính ngày sinh đó.
    usable = [link for link in links if _year(link.record["birth_text"]) and link.why != "trùng ngày sinh"]
    slots = _weigh(usable, lambda record: _year(record["birth_text"]))
    if not slots:
        return None
    ranked = sorted(slots.items(), key=lambda item: (item[1]["weight"], item[1]["printed"]), reverse=True)
    key, best = ranked[0]
    if key == current or (len(ranked) > 1 and ranked[1][1]["weight"] == best["weight"]) or not best["printed"]:
        return None
    mine = slots.get(current, {"weight": 0.0, "printed": 0.0})
    if current and (mine["printed"] or best["weight"] <= mine["weight"]):
        return None
    record = best["link"].record
    if record["handwritten"] or _impossible_birth(key, person, child_year):
        return None
    quote = next((line.strip() for line in record["text"].splitlines() if key in line
                  and (base._name_key(record["name"]) in base._name_key(line) or "sinh" in fold(line))), "")
    if not quote:
        return None
    value = record["birth_text"] if _year(record["birth_text"]) == key else key
    state = "bỏ trống" if not current else f"năm {current} chỉ có trên tờ khai viết tay"
    return Finding(INSPECTOR, UNITS_BY_ROLE[role.key]["nam_sinh"], {role.birth: value}, quote, record["doc"],
                   f"dòng năm sinh của {role.label} ({best['link'].why})", role.label, backed=True,
                   evidence=(f"năm sinh của A: {state}; B (năm {key}) có {best['weight']:g} điểm nguồn "
                             f"({best['printed']:g} điểm giấy in) ghi cho chính {role.label}",))


def findings_from(records: list[dict], values: dict, documents: list[dict]) -> list[Finding]:
    people = {role.key: chu_the.identity(values, role) for role in ROLES}
    findings = []
    for role in ROLES:
        person = people[role.key]
        if not person["name"]:
            continue
        # Người yêu cầu trùng một vai khác (bản thân / cha / mẹ) vẫn là một người: không coi là "vai khác trùng tên".
        others = [other for key, other in people.items()
                  if key != role.key and other["name"] and not close_name(other["name"], person["name"])]
        links = [link for record in records if (link := _belongs(record, role, person, others))]
        name = account_finding(role, person, documents) or name_finding(role, person, links, documents)
        child_year = chu_the.birth_year(people["con"]["birth"])
        for finding in (name, ethnic_finding(role, person, links, documents), birth_finding(role, person, links, child_year)):
            if finding:
                findings.append(finding)
    return findings


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    people = [chu_the.identity(case.values, role) for role in ROLES]
    people = [person for person in people if person["name"]]
    if not people:
        return []
    read = await asyncio.gather(*(_read_page(page, title) for page in pages(case.documents, people)),
                                return_exceptions=True)
    records = [record for answer in read if not isinstance(answer, BaseException) for record in answer]
    return findings_from(records, case.values, case.documents)


_OWNERS = tuple(role.label for role in ROLES)
INSPECTOR = Inspector("dinh_danh", "ĐỊNH DANH (họ tên, dân tộc, năm sinh cha mẹ) các vai đăng ký khai sinh", UNITS, RULES,
                      owners=_OWNERS, accepted=_OWNERS, find=find)
