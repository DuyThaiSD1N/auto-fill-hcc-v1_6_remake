"""Thanh tra ĐỊNH DANH NGƯỜI NỘP — số điện thoại (thủ tục tư pháp cổng DVC mới: ô SĐT của khối người nộp).

Lượt trích hay bỏ trống số điện thoại dù giấy có ghi, hoặc lấy số của người khác trong hồ sơ (người yêu cầu ghi trên tờ
khai khi người nộp là người được ủy quyền). Cách kiểm do MÃ làm, không qua LLM: nhận chủ của từng số theo CHỖ GHI —
(a) cùng dòng với họ tên người nộp; (b) dòng "Số điện thoại / ĐT" thuộc khối có họ tên người nộp (khối người yêu cầu của
tờ khai, mục người được ủy quyền); (c) dãy số đứng riêng ngay dưới họ tên / chữ ký người nộp; (d) số không gắn với
ai khác trên tờ khai mà người nộp là người yêu cầu của chính tờ khai đó. Chỉ đề xuất khi mã nhận
được đúng MỘT số của người nộp mà lượt trích bỏ trống hoặc ghi số khác. Người nộp lấy từ khối <nguoi_nop> của bước phân
vai (người đăng nhập cổng), chỉ khi khối đó ghi "Có trong hồ sơ: Có".
"""

import difflib
import re

from .ho_so import Case, Field, Finding, Inspector, Unit, fold

FIELD = "NguoiNop_SoDienThoai"
OWNER = "người nộp"
UNIT = Unit("nguoi_nop.so_dien_thoai", "Số điện thoại người nộp",
            (Field(FIELD, "số điện thoại di động / cố định Việt Nam", "code"),))

RULES = """
<so_dien_thoai_nguoi_nop>
Vụ xét số điện thoại của NGƯỜI NỘP (người đăng nhập cổng — khối <nguoi_nop> của phân vai). Mã đã nhận chủ của số theo
CHỖ GHI trên giấy: cùng dòng với họ tên người nộp; dòng "Số điện thoại"/"ĐT" thuộc khối có họ tên người nộp (khối người
yêu cầu của tờ khai khi người nộp là người yêu cầu, mục người được ủy quyền khi người nộp là người được ủy quyền); hoặc
dãy số viết ngay dưới họ tên / chữ ký người nộp; hoặc số không gắn với người nào khác (không cùng dòng / khối họ tên
người khác) trên tờ khai mà người nộp là người yêu cầu của tờ khai đó — số đó là của người yêu cầu. Cách nhận ghi ở
dòng "Tín hiệu mã".
A trống mà B là số mã nhận cho người nộp → chọn B (giấy có ghi thì không được bỏ trống). A là số khác — không có trên
dòng nào gắn với người nộp, hoặc là số ghi cho người khác trong hồ sơ — mà B là số của người nộp → chọn B.
Dòng trích dẫn là số của người khác, của cơ quan / bệnh viện / cán bộ, hoặc là số định danh / CCCD / số hồ sơ →
KHONG_DU_CAN_CU.
</so_dien_thoai_nguoi_nop>
"""

# Dãy chữ số (cho phép một dấu cách / chấm / gạch giữa các nhóm) — lấy trọn dãy rồi mới xét độ dài, để mảnh của số
# CCCD 12 chữ số không thành số điện thoại.
_DIGIT_RUN_RE = re.compile(r"(?<![\d])\+?\d(?:[ .\-]?\d)+(?![\d])")
_VALID_RE = re.compile(r"0(?:[35789]\d{8}|2\d{9})")
_MOBILE_RE = re.compile(r"0[35789]\d{8}")
_NOT_PHONE_BEFORE_RE = re.compile(
    r"(cccd|cmnd|can cuoc|dinh danh|giay to tuy than|so ho so|ho so|ma so|mst|tai khoan|stk|so/no|so: *$|no\.? *$|"
    r"quyen so|so dang ky)[^0-9]{0,25}$")
_PHONE_LABEL_RE = re.compile(r"(so dien thoai|dien thoai|sdt|\bdt\b|\btel\b|phone)")
_PERSON_LABEL_RE = re.compile(r"(ho va ten|ho ten|ho, chu dem|chu dem, ten|toi ten|toi la|\bong\b|\bba\b|nguoi yeu cau|"
                              r"ben duoc uy quyen|nguoi duoc uy quyen|ben uy quyen|nguoi uy quyen)")
_REQUESTER_LINE_RE = re.compile(r"nguoi yeu cau\s*:")
_AUTHORIZED_RE = re.compile(r"(ben|nguoi) duoc uy quyen")
_LOOK_BACK = 8
_NEAR_NAME_RATIO = 0.84


def _label(block: str, name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*:\s*(.*)$", block or "")
    return match.group(1).strip() if match else ""


def submitter(context: str) -> dict:
    block = re.search(r"<nguoi_nop>(.*?)</nguoi_nop>", context or "", re.S)
    block = block.group(1) if block else ""
    present = fold(_label(block, "Có trong hồ sơ")) == "co"
    role = fold(_label(block, "Vai trong hồ sơ"))
    return {"present": present, "name": _label(block, "Họ tên"), "role": role}


def normalize(value) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("84") and len(digits) in (11, 12):
        digits = "0" + digits[2:]
    return digits if _VALID_RE.fullmatch(digits) else ""


def phones_in(line: str) -> list[str]:
    out = []
    for match in _DIGIT_RUN_RE.finditer(line):
        number = normalize(match.group(0))
        before = fold(line[:match.start()])
        # Nhãn điện thoại ngay trước dãy số thắng nhãn chặn ("Điện thoại số: …" có chữ "số:").
        if number and (_PHONE_LABEL_RE.search(before[-25:]) or not _NOT_PHONE_BEFORE_RE.search(before)):
            out.append(number)
    return out


def _has_name(line: str, name: str) -> bool:
    """Dòng ghi họ tên người nộp: nguyên văn (bỏ dấu), hoặc một cụm cùng số chữ gần giống (OCR chữ viết tay)."""
    target = fold(name).split()
    if len(target) < 2:
        return False
    words = re.findall(r"[0-9a-z]+", fold(line))
    joined = " ".join(target)
    if f" {joined} " in f" {' '.join(words)} ":
        return True
    size = len(target)
    return any(difflib.SequenceMatcher(None, " ".join(words[i:i + size]), joined).ratio() >= _NEAR_NAME_RATIO
               for i in range(len(words) - size + 1))


def _bare_number(line: str) -> bool:
    """Dòng chỉ có dãy số (kèm "ĐT:" / "SĐT:"): số viết tay đứng riêng dưới khối ký tên."""
    rest = _DIGIT_RUN_RE.sub("", fold(line))
    rest = _PHONE_LABEL_RE.sub("", rest)
    return not re.sub(r"[\W_]+", "", rest)


def _names_other(folded: str) -> bool:
    """Dòng nhãn người ("Họ tên: …", "Họ, chữ đệm, tên người yêu cầu: …") có ghi họ tên sau dấu ":"."""
    if ":" not in folded:
        return False
    value = folded.split(":", 1)[1]
    return len(re.findall(r"[a-z]{2,}", value)) >= 2


def owner_of(lines: list[str], at: int, person: dict) -> tuple[str, str]:
    """(chủ của số ở dòng ``at``: "self" | "other" | "", cách nhận)."""
    line = lines[at]
    folded = fold(line)
    name = person["name"]
    if _has_name(line, name):
        return "self", "số ghi cùng dòng với họ tên người nộp"
    labeled = bool(_PHONE_LABEL_RE.search(folded))
    if _REQUESTER_LINE_RE.search(folded) and "yeu cau" in person["role"]:
        # Họ tên người yêu cầu viết tay có thể bị OCR đọc lệch — vai của người nộp quyết.
        return "self", "số ghi trên dòng người yêu cầu của tờ khai, người nộp là người yêu cầu"
    if _PERSON_LABEL_RE.search(folded) and _names_other(folded):
        return "other", "số ghi cùng dòng với họ tên người khác"
    for k in range(at - 1, max(-1, at - 1 - _LOOK_BACK), -1):
        prev = lines[k]
        prev_folded = fold(prev)
        if phones_in(prev):
            return "", ""  # gặp số khác trước khi gặp chủ: không chắc của ai
        if _has_name(prev, name):
            if labeled or _bare_number(line):
                return "self", ("dòng số điện thoại thuộc khối có họ tên người nộp" if labeled else
                                "dãy số viết ngay dưới họ tên / chữ ký người nộp")
            return "", ""
        if _PERSON_LABEL_RE.search(prev_folded) and _names_other(prev_folded):
            if labeled and _REQUESTER_LINE_RE.search(prev_folded) and "yeu cau" in person["role"]:
                return "self", "dòng số điện thoại trong khối người yêu cầu của tờ khai, người nộp là người yêu cầu"
            if labeled and _AUTHORIZED_RE.search(prev_folded) and "duoc uy quyen" in person["role"]:
                return "self", "dòng số điện thoại ở mục người được ủy quyền, người nộp là người được ủy quyền"
            return "other", "dòng số điện thoại thuộc khối họ tên người khác"
    return "", ""


def _own_requester_form(lines: list[str], person: dict) -> bool:
    """Tờ khai mà dòng người yêu cầu ghi họ tên người nộp, và người nộp có vai người yêu cầu: số không gắn với ai khác
    trên tờ khai này (viết tay đầu trang, cạnh chữ ký chỉ ghi tên gọi, OCR ghép vào dòng in sẵn) là số của người yêu cầu."""
    if "yeu cau" not in person["role"]:
        return False
    return any(_REQUESTER_LINE_RE.search(fold(line)) and _has_name(line, person["name"]) for line in lines)


def phone_findings(inspector: Inspector, case: Case) -> list[Finding]:
    person = submitter(case.context)
    if not person["present"] or not person["name"]:
        return []
    own: dict[str, dict] = {}
    others: set[str] = set()
    for index, document in enumerate(case.documents, start=1):
        lines = [line.strip() for line in str(document.get("text") or "").splitlines() if line.strip()]
        own_form = _own_requester_form(lines, person)
        for at, line in enumerate(lines):
            for number in phones_in(line):
                who, how = owner_of(lines, at, person)
                # Chỉ số di động: số CCCD 12 chữ số rơi một chữ số khi OCR thành dãy 11 số "02…" giống số máy bàn.
                if not who and own_form and _MOBILE_RE.fullmatch(number):
                    who, how = "self", "số không gắn với ai khác trên tờ khai, người nộp là người yêu cầu của tờ khai đó"
                if who == "self":
                    own.setdefault(number, {"quote": line, "doc": index, "how": how})
                elif who == "other":
                    others.add(number)
    if len(own) != 1:
        return []
    number, hit = next(iter(own.items()))
    current = normalize(case.values.get(FIELD))
    if current == number:
        return []
    about_a = ("A trống" if not current else
               "A là số ghi cho người khác trong hồ sơ" if current in others else
               "A không có trên dòng nào gắn với người nộp")
    return [Finding(inspector, UNIT, {FIELD: number}, hit["quote"], hit["doc"], "số điện thoại của người nộp", OWNER,
                    backed=True, evidence=(f"mã nhận số của người nộp ({person['name']}): {hit['how']}; {about_a}",))]


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    return phone_findings(inspector, case)


INSPECTOR = Inspector("sdt_nguoi_nop", "ĐỊNH DANH người nộp — số điện thoại", (UNIT,), RULES,
                      owners=(OWNER, "người khác"), accepted=(OWNER,), find=find)
