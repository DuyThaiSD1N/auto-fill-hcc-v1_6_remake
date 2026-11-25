"""Thanh tra TÊN HỘ KINH DOANH — dấu của tên viết tay ở mục "1. Tên hộ kinh doanh".

OCR chữ viết tay hay lệch dấu một chữ của tên (ra từ vô nghĩa, hoặc ra một từ có nghĩa nhưng lạc với cả tên); lượt sửa dấu
ở lượt trích (process/ten_ho.py) chỉ thấy chữ OCR nên không gỡ được chữ OCR đọc thành từ có nghĩa. Nguồn độc lập là lượt
Qwen đọc thẳng ảnh giấy đề nghị (process/vision.py): ứng viên chỉ nhận khi cách viết của lượt đọc ảnh CHỈ khác A ở dấu (bỏ
dấu hai bên trùng nhau từng chữ cái). Chọn bên nào là việc của toà, theo nghĩa của cả tên.
"""

import re
import unicodedata

from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold

from ..process import mapper
from . import trang

FIELD = Field("HoKinhDoanh_Ten", "Tên hộ kinh doanh", "free")
UNIT = Unit("ten_ho", "Tên hộ kinh doanh viết bằng tiếng Việt", (FIELD,))
_NAME_LINE = re.compile(r"(?i)t[eê]n\s*h[oộ]\s*kinh\s*doanh\s*vi[eế]t\s*b[aằ]ng\s*ti[eế]ng\s*vi[eệ]t")

RULES = """
<ten_ho>
A là tên OCR đọc chữ viết tay; B là tên lượt đọc thẳng ảnh giấy đề nghị đọc được — hai bên CHỈ khác dấu ở một vài chữ.
B lấy từ ẢNH chứ không từ OCR, nên giá trị của B KHÔNG có nguyên văn trong OCR là đương nhiên — điều đó không nghiêng về bên
nào; dòng chứng cứ là chính dòng tên đó trên giấy (OCR đọc theo cách viết của A).
Cách xét theo CỤM, không theo từng chữ đứng riêng: ghép chữ khác dấu với chữ liền trước / liền sau, đọc cụm theo cách viết
của A rồi theo cách viết của B.
- Cụm của A là tên món, mặt hàng, dịch vụ hay cụm thông dụng hợp với cả tên → "A", dù cụm của B ra sao.
- Cụm của A không dùng được trong tên (chữ vô nghĩa, hoặc chữ tự nó có nghĩa mà ghép với chữ bên cạnh thì vô nghĩa / lạc
  nghĩa với cả tên), còn cụm của B là cụm thông dụng hợp với cả tên → "B".
- Chữ là tên người, thương hiệu, từ nước ngoài, hoặc không chắc → KHONG_DU_CAN_CU (giữ A).
</ten_ho>
"""


def _bare(text) -> str:
    return " ".join(unicodedata.normalize("NFC", mapper._strip_household_prefix(text)).split())


def _letters(text) -> str:
    """Bỏ dấu, giữ chữ cái: hai cách viết chỉ khác dấu thì trùng nhau."""
    return " ".join(re.findall(r"[0-9a-z]+", fold(text)))


def _accented(ours: str, seen: str) -> str:
    """Tên của A, mỗi chữ lấy dấu theo chữ tương ứng của lượt đọc ảnh — giữ kiểu chữ (thường in hoa), dấu câu và khoảng
    trắng của A: lượt đọc ảnh hay chèn / bớt dấu cách quanh dấu gạch, dấu phẩy."""
    words = re.findall(r"[^\W_]+", ours)
    other = re.findall(r"[^\W_]+", seen)
    if len(words) != len(other) or any(fold(a) != fold(b) or len(a) != len(b) for a, b in zip(words, other)):
        return ""
    marks = iter("".join(y.upper() if x.isupper() else y.lower() for x, y in zip(a, b)) for a, b in zip(words, other))
    return re.sub(r"[^\W_]+", lambda _: next(marks), ours)


def _quote(page_list: list[dict], name: str) -> tuple[str, int]:
    """Dòng OCR mang tên hộ (dòng nhãn mục 1 hoặc dòng ngay dưới nó)."""
    key = _letters(name)
    for page in page_list:
        if page["kind"] != "don":
            continue
        for at, line in enumerate(page["lines"]):
            if not _NAME_LINE.search(line):
                continue
            for candidate in (line, *page["lines"][at + 1:at + 2]):
                if key and key in _letters(candidate):
                    return candidate, page["doc"]
    return "", 0


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    ours = _bare(case.values.get("HoKinhDoanh_Ten"))
    if not ours:
        return []
    seen = _bare((await trang.vision(case.options)).get("ten_ho"))
    if not ours or not seen or seen.casefold() == ours.casefold() or _letters(seen) != _letters(ours):
        return []
    line, doc = _quote(trang.pages(case.documents, case.values), ours)
    if not line:
        return []
    value = _accented(ours, seen)
    if not value:
        return []
    return [Finding(INSPECTOR, UNIT, {FIELD.name: value}, line, doc, "mục 1 tên hộ kinh doanh của giấy đề nghị",
                    "tên hộ kinh doanh", backed=True,
                    evidence=(f'lượt đọc thẳng ảnh giấy đề nghị đọc tên là "{seen}"; OCR đọc "{ours}"; hai cách viết chỉ '
                              f'khác dấu',))]


INSPECTOR = Inspector("ten_ho", "TÊN HỘ KINH DOANH (dấu của tên viết tay)", (UNIT,), RULES,
                      owners=("tên hộ kinh doanh", "giấy khác"), accepted=("tên hộ kinh doanh",), find=find)
