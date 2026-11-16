"""Thanh tra QUAN HỆ người nộp với người được đăng ký khai tử.

Chỉ soát khi người nộp (chủ tài khoản) chính là người yêu cầu trên tờ khai — ô quan hệ chép dòng "Quan hệ với người đã
chết" của tờ khai. Mã kiểm dòng đó bằng năm sinh (năm sinh chủ tài khoản mã hoá trong số định danh; năm sinh người mất,
thiếu thì lấy năm chết làm mốc):
- người nộp là cha / mẹ / ông / bà / cụ / bác / chú... thì phải sinh TRƯỚC người mất;
- là con / cháu / chắt / dâu / rể thì sinh SAU người mất ít nhất ~10 năm;
- là vợ / chồng / anh / chị / em thì cùng lứa.
Mâu thuẫn → (0) lượt trích ghi khác chữ của chính dòng tờ khai mà dòng tờ khai hợp năm sinh → theo tờ khai; (1) giấy khác
(giấy báo tử...) có dòng "Quan hệ với người chết" hợp năm sinh → đề xuất dòng đó; (2) dòng
tờ khai là vai của NGƯỜI MẤT (ghi "Ông ngoại" mà người nộp sinh sau) → đề xuất vai ngược lại của người nộp. Không có căn cứ
thì giữ tờ khai. Năm sinh chỉ dùng để KIỂM dòng đã ghi, không tự suy ra quan hệ.
"""

import re

from app.pipelines._shared.cccd import id_birth_year
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold

from ..process import mapper
from ..process.reason import requester_context
from . import trang

_OWNER = "người nộp (chủ tài khoản)"
RELATION = "NguoiYeuCau_QuanHe"
UNITS = (Unit("quan_he", "Quan hệ người nộp với người mất", (Field(RELATION, "quan hệ", "free"),)),)

_OLDER = ("bo", "cha", "me", "ong", "ba", "cu", "bac", "chu", "co", "di", "cau", "thim", "mo", "duong")
_YOUNGER = ("con", "chau", "chat", "dau", "re")
_PEER = ("vo", "chong", "anh", "chi", "em")
# Vai của người mất ghi nhầm vào dòng quan hệ → vai của người nộp (đọc theo từ đầu của dòng, đã bỏ dấu).
_INVERSE = (
    (("cu", "cha co", "ong co", "ba co", "me co"), "Chắt"),
    # "Cha nội / mẹ nội" (cách gọi ông bà nội) → cháu nội.
    (("ong noi", "ba noi", "cha noi", "me noi"), "Cháu nội"),
    (("ong ngoai", "ba ngoai", "cha ngoai", "me ngoai"), "Cháu ngoại"),
    (("ong", "ba", "bac", "chu", "co", "di", "cau", "thim", "mo", "duong"), "Cháu"),
    (("bo", "cha", "me"), "Con đẻ"),
)
_LINE_RE = re.compile(r"quan\s*h[eệ]\s*v[oớ]i\s*ng[uư][oờ]i\s*(?:đã\s*)?ch[eế]t\s*[:：]\s*(.+)", re.IGNORECASE)

RULES = """
<quan_he>
Ô quan hệ là VAI CỦA NGƯỜI NỘP đối với người mất. Mã đã kiểm dòng quan hệ của tờ khai (A) bằng năm sinh: người nộp là
cha / mẹ / ông / bà / cụ / bác / chú thì sinh trước người mất; con / cháu / chắt / dâu / rể thì sinh sau người mất; vợ /
chồng / anh / chị / em thì cùng lứa. A mâu thuẫn năm sinh và:
- B là đúng chữ dòng "Quan hệ với người đã chết" của tờ khai (A ghi khác chữ đó), B hợp năm sinh → chọn B;
- B là dòng "Quan hệ với người chết" trên giấy khác (giấy báo tử...) hợp năm sinh → chọn B;
- A là vai của NGƯỜI MẤT ghi nhầm (vd "Ông ngoại" mà người nộp sinh sau người mất mấy chục năm), B là vai ngược lại của
  người nộp → chọn B. Ở trường hợp này B do MÃ đổi chiều từ chính dòng tờ khai nên KHÔNG có nguyên văn trên giấy — đó là
  bình thường, không phải lý do giữ A; dòng trích dẫn là dòng quan hệ của tờ khai.
Năm sinh / số liệu trong dòng "Tín hiệu mã" là căn cứ của mã; dòng trích dẫn là dòng quan hệ trên giấy. Dòng trích dẫn
là quan hệ của người khác (người đi khai tử không phải người nộp) → KHONG_DU_CAN_CU.
</quan_he>
"""


def kind(relation) -> str:
    words = [w for w in fold(relation).replace("/", " ").replace("-", " ").split() if w not in ("la", "nguoi")]
    head = words[0] if words else ""
    # "Bố con", "mẹ con", "ông cháu", "anh em": cặp quan hệ, không rõ ai là vai nào → không kiểm.
    # ("cố" bỏ dấu trùng "cô": "cha cố", "bà cố" là một vai.)
    if len(words) > 1 and words[1] in _OLDER + _YOUNGER + _PEER and words[1] not in ("noi", "ngoai", "co"):
        return ""
    if head in _YOUNGER:
        return "younger"
    if head in _PEER:
        return "peer"
    if head in _OLDER:
        return "older"
    return ""


def consistent(relation, submitter: int, deceased: int | None, died: int | None) -> bool | None:
    """None = không đủ năm sinh để kiểm."""
    role = kind(relation)
    if not role:
        return None
    if deceased:
        if role == "older":
            return submitter < deceased
        if role == "younger":
            return submitter >= deceased + 10
        return abs(submitter - deceased) < 30
    if died and role == "older":
        return submitter < died  # sinh sau khi người mất đã chết thì không thể là cha / mẹ / ông / bà
    return None


def _inverse(relation) -> str:
    text = " ".join(fold(relation).split())
    for keys, value in _INVERSE:
        if any(text == key or text.startswith(key + " ") for key in keys):
            return value
    return ""


def _years(case: Case) -> tuple[int | None, int | None, int | None]:
    _, account = requester_context(case.options)
    submitter = id_birth_year(account) if account else None
    birth = re.findall(r"(1[89]\d{2}|20\d{2})", str(case.values.get("NguoiMat_NgaySinh") or ""))
    deceased = int(birth[-1]) if birth else id_birth_year(trang.digits(case.values.get("NguoiMat_SoDinhDanh")))
    death = re.findall(r"(1[89]\d{2}|20\d{2})", str(case.values.get("NguoiMat_NgayMat") or ""))
    return submitter, deceased, int(death[-1]) if death else None


def findings_from(case: Case) -> list[Finding]:
    declared = str(case.values.get(RELATION) or "").strip()
    account_name, account_id = requester_context(case.options)
    same, _ = mapper._same_person(account_name, account_id, case.values.get("NguoiYeuCau_HoTen"),
                                  case.values.get("NguoiYeuCau_SoDinhDanh"))
    submitter, deceased, died = _years(case)
    if not declared or not same or not submitter or consistent(declared, submitter, deceased, died) is not False:
        return []
    signal = (f"năm sinh người nộp {submitter}, người mất {deceased or '?'}"
              + (f", chết năm {died}" if died else "") + f": dòng tờ khai \"{declared}\" mâu thuẫn năm sinh")
    pages = trang.pages(case.documents)
    # (0) lượt trích đổi khác chữ của dòng quan hệ trên tờ khai, mà chính dòng tờ khai hợp năm sinh → theo tờ khai.
    for page in pages:
        if page["kind"] != "to_khai":
            continue
        for line in page["lines"]:
            match = _LINE_RE.search(line)
            written = match.group(1).strip(" .;,") if match else ""
            if written and fold(written) != fold(declared) and consistent(written, submitter, deceased, died):
                return [Finding(INSPECTOR, UNITS[0], {RELATION: written}, line, page["doc"], "dòng quan hệ trên tờ khai",
                                _OWNER, backed=True, evidence=(signal + f"; chính dòng tờ khai ghi \"{written}\", hợp năm sinh",))]
    # (1) dòng quan hệ trên giấy khác tờ khai, hợp năm sinh.
    for page in pages:
        if page["kind"] == "to_khai":
            continue
        for line in page["lines"]:
            match = _LINE_RE.search(line)
            other = match.group(1).strip(" .;,") if match else ""
            if other and fold(other) != fold(declared) and consistent(other, submitter, deceased, died):
                return [Finding(INSPECTOR, UNITS[0], {RELATION: other}, line, page["doc"], "dòng quan hệ trên giấy khác",
                                _OWNER, backed=True, evidence=(signal + f"; dòng \"{other}\" hợp năm sinh",))]
    # (2) dòng tờ khai ghi vai của người mất → vai ngược lại của người nộp.
    inverse = _inverse(declared)
    if inverse and kind(declared) == "older" and consistent(inverse, submitter, deceased, died) is not False:
        quote = next(((line, page["doc"]) for page in pages if page["kind"] == "to_khai" for line in page["lines"]
                      if _LINE_RE.search(line)), None)
        if quote:
            return [Finding(INSPECTOR, UNITS[0], {RELATION: inverse}, quote[0], quote[1],
                            "dòng quan hệ tờ khai ghi vai của người mất", _OWNER, backed=True,
                            evidence=(signal + f"; người nộp sinh sau người mất nên \"{declared}\" là vai của người mất, vai "
                                               f"của người nộp là \"{inverse}\"",))]
    return []


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    return findings_from(case)


INSPECTOR = Inspector("quan_he", "QUAN HỆ người nộp với người được đăng ký khai tử", UNITS, RULES,
                      owners=(_OWNER, "người khác"), accepted=(_OWNER,), find=find)
