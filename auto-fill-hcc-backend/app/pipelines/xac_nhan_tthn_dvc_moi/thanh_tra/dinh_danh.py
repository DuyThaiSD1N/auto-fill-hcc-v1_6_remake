"""Thanh tra ĐỊNH DANH người được cấp Giấy XNTTHN: họ tên, số định danh, ngày sinh; bổ sung dân tộc khi lượt trích
bỏ trống.

Tờ khai là chữ VIẾT TAY, OCR hay đọc lệch một chữ / một chữ số; thẻ căn cước, giấy kết hôn, trích lục, bản án là chữ
IN. Cách kiểm riêng, không hỏi model "ai là người được cấp":
1. Mỗi trang giấy được đọc RIÊNG: model chỉ lập danh sách nhân thân của từng người ghi trên trang (không biết kết quả
   lượt trích). Vùng MRZ của thẻ do mã đọc.
2. MÃ nhận người: một bản ghi là của người được cấp khi trùng HAI trong ba thông tin (số định danh, ngày sinh, họ
   tên gần giống) — không nhận người chỉ bằng họ tên, vì chính họ tên có thể đang sai.
3. Thông tin thứ ba mà nguồn IN ghi khác tờ khai viết tay → lấy theo nguồn in; hai nguồn in lệch nhau thì bên nhiều
   nguồn hơn; không có nguồn in nào của người đó thì không đề xuất gì.
"""

import asyncio
import difflib
import re
import unicodedata

from app.config import settings
from app.pipelines._shared.cccd import mrz_records
from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold, parse_date
from app.services.llm import client

# Luật của nhóm: TOÀ ÁN đọc để phán từng vụ (A = giá trị lượt trích, B = giá trị thanh tra đề xuất).
RULES = """
<nhan_nguoi>
Thanh tra KHÔNG nhận người bằng họ tên, vì chính họ tên có thể là chỗ đang sai. Mã đã đối chiếu từng người ghi trên
từng trang giấy với người được cấp theo ba thông tin: số định danh, ngày sinh, họ tên. Một người trên giấy chỉ được
coi là CHÍNH người được cấp khi trùng ít nhất HAI thông tin (họ tên lệch một chữ cái, số lệch tối đa hai chữ số tính
là gần trùng); họ tên khác hẳn hoặc số định danh khác hẳn thì là người khác. Căn cứ nhận người được ghi trong dòng
"Tín hiệu mã" của từng vụ — toà dùng căn cứ đó, không tự nhận lại người theo họ tên.
</nhan_nguoi>

<do_tin_cua_nguon>
Cùng một thông tin của một người có thể được ghi trên nhiều giấy, độ tin của chữ OCR đọc ra khác nhau:
1. Vùng MRZ ở mặt sau thẻ căn cước (ba dòng chữ in máy "IDVNM...") — đọc ổn định nhất cho SỐ định danh và NGÀY sinh;
   họ tên trong MRZ không có dấu nên chỉ phân biệt được chữ cái, không phân biệt được dấu.
2. Giấy ĐÁNH MÁY: giấy chứng nhận kết hôn, trích lục hộ tịch, quyết định / bản án của Tòa án, văn bản ủy quyền, mặt
   trước thẻ căn cước — đọc chính xác cao. Riêng họ tên IN HOA trên mặt thẻ đôi khi bị rơi hoặc lệch DẤU.
3. TỜ KHAI là chữ VIẾT TAY — kém tin nhất: hay lệch một chữ cái, một dấu, một chữ số.
Mã đã quy ra "điểm nguồn" cho mỗi giá trị: mỗi trang giấy in 1 điểm, tờ khai viết tay 0,5 điểm, vùng MRZ 1 điểm.
</do_tin_cua_nguon>

<cach_phan_xu>
- A chỉ có trên tờ khai viết tay, B có trên giấy in của CHÍNH người được cấp → chọn B.
- A và B đều có trên giấy in → bên có NHIỀU điểm nguồn hơn.
- A và B NGANG điểm nguồn → xét THỨ BẬC loại giấy ghi giá trị đó (dòng "Tín hiệu mã" đã nêu loại giấy của mỗi bên),
  từ cao xuống thấp: (1) giấy do cơ quan cấp — quyết định / bản án ly hôn, trích lục hộ tịch, giấy chứng nhận kết hôn,
  kết quả kiểm tra thông tin công dân, Giấy xác nhận tình trạng hôn nhân đã cấp; (2) giấy tự lập đánh máy — bản cam
  đoan, văn bản ủy quyền; (3) thẻ căn cước; (4) tờ khai. Bên có loại giấy bậc CAO hơn thì chọn, kể cả khi hai họ tên
  chỉ khác dấu; cùng bậc → KHONG_DU_CAN_CU.
- So DẤU giữa hai họ tên (bên nào đủ dấu hơn, bên nào rơi dấu) là việc của MÃ, kết quả ghi ở dòng "Tín hiệu mã". Toà
  KHÔNG tự so dấu từng chữ: tín hiệu mã không ghi "rơi dấu" thì không được lấy lý do rơi dấu để giữ A.
- Ngoại lệ ở thế ngang điểm: tín hiệu mã ghi "họ tên của B chỉ là bản rơi dấu của A" (chỗ khác nhau thì chữ của B trơ
  hẳn không dấu, ví dụ chữ "Đ" thành "D", chữ mất hết dấu) → giữ A, vì OCR hay làm rơi dấu chứ không tự thêm dấu.
- Họ tên của B chỉ khác A ở chỗ chữ "Đ" thành "D" → giữ A dù B nhiều điểm hơn: OCR rất hay đọc mất nét gạch của chữ
  "Đ", nhiều trang cùng đọc mất không làm cách viết đó đúng hơn.
- Số định danh 12 chữ số mang hai số cuối NĂM SINH ở chữ số thứ 5–6. Dòng "Tín hiệu mã" báo B không khớp mã năm sinh
  trong khi A khớp → giữ A.
- Dòng "Tín hiệu mã" ghi "B ĐỦ DẤU HƠN A" (mọi dấu của A đều có trong B, B còn thêm dấu — ví dụ A "Hân", B "Hẫn") và B
  hơn điểm A → chọn B, một giấy in là đủ: chữ viết tay và OCR hay làm RƠI dấu chứ không tự thêm dấu, nên bên đủ dấu
  hơn là bên đọc đúng. Đây KHÔNG phải trường hợp "B là bản rơi dấu của A".
- Hai họ tên chỉ khác DẤU (cùng chữ cái) mà B hơn điểm A, tín hiệu mã KHÔNG ghi "B ĐỦ DẤU HƠN A": chỉ chọn B khi B có
  từ 1,5 điểm nguồn trở lên; một mặt thẻ in hoa đơn lẻ không đủ để bỏ dấu của A.
- "Vai trên trang" (mẹ, nguyên đơn, bên ủy quyền, chủ thẻ...) chỉ là vai của người đó TRÊN TỜ GIẤY ẤY: người được cấp
  vẫn có thể là mẹ trên giấy khai sinh của con, là nguyên đơn trên bản án. Mã đã nhận cùng người thì KHÔNG dùng vai để
  loại. Chỉ chọn A vì "thuộc người khác" khi tín hiệu mã không nêu căn cứ nhận người nào.
- Không có giấy in nào của người được cấp ghi thông tin đó → KHONG_DU_CAN_CU (giữ theo tờ khai).
</cach_phan_xu>

<tung_muc>
- Họ tên: đúng từng chữ và từng dấu như trên giấy in của chính người đó; không tự sửa dấu, không viết hoa lại.
- Số định danh cá nhân: đúng 12 chữ số trên thẻ của chính người đó; số 9 chữ số là CMND cũ, không phải số định danh.
  Số trên mặt thẻ và số trong vùng MRZ trùng nhau là căn cứ mạnh nhất.
- Ngày sinh: đủ ngày, tháng, năm (dd/mm/yyyy) theo giấy in của chính người đó; giấy chỉ ghi năm sinh thì không phải
  căn cứ để đổi ngày, tháng.
- Dân tộc: chỉ thành vụ khi lượt trích BỎ TRỐNG (A trống). Thẻ căn cước mẫu mới không in dân tộc nên dòng "Dân tộc" ở
  khối người được cấp trên TỜ KHAI là nguồn chính — một tờ khai là đủ căn cứ, không áp luật "chỉ có trên tờ khai viết
  tay". Chọn B khi dòng chứng cứ là dân tộc của CHÍNH người được cấp (mã đã nhận người); dòng đó thuộc vợ/chồng, người
  yêu cầu hay người khác trên cùng trang → KHONG_DU_CAN_CU.
</tung_muc>
"""

NAME, NUMBER, BIRTHDAY = "NguoiDuocCap_HoTen", "NguoiDuocCap_SoDinhDanh", "NguoiDuocCap_NgaySinh"
ETHNIC, OTHER_ETHNIC = "NguoiDuocCap_DanToc", "GiayToKhac_DanToc"
_OWNER = "người được cấp"
_PAGE_BREAK_RE = re.compile(r"(?m)^[─\-=\s]*Trang\s+\d+\s*/\s*\d+[─\-=\s]*$")
_MAX_PAGES = 8
_MAX_TOKENS = 700
_NEAR_NAME_RATIO = 0.84
_ID_SLIP_MAX = 2  # số chữ số OCR được phép đọc lệch trên chữ viết tay mà vẫn coi là cùng một số
_SIGNATURE_LINES = 3  # số dòng sau nhãn "(Ký, ghi rõ họ, chữ đệm, tên)" còn thuộc khối chữ ký của tờ khai

# Lượt đọc MỘT trang: model chỉ lập danh sách nhân thân, không biết kết quả lượt trích và không được hỏi ai xin giấy.
_PAGE_PROMPT = """<vai_tro>
Bạn là người đọc giấy tờ của dây chuyền soát hồ sơ {title}. Bạn nhận chữ OCR của MỘT trang giấy và lập danh sách
NHÂN THÂN (họ tên, số định danh, ngày sinh) của TỪNG NGƯỜI được ghi trên trang đó. Bạn không cần biết ai là người xin
giấy và không suy luận điều đó: việc đối chiếu các trang với nhau do bước sau làm.
</vai_tro>

<ai_duoc_ghi>
Ghi MỌI người có nhân thân trên trang, mỗi người MỘT mục riêng:
- chủ thẻ căn cước / CCCD / CMND / hộ chiếu;
- người yêu cầu và người được cấp trên tờ khai — hai khối khác nhau là HAI mục, kể cả khi trùng họ tên;
- vợ và chồng trên giấy chứng nhận kết hôn; nguyên đơn, bị đơn, người yêu cầu trên quyết định / bản án;
- bên ủy quyền và bên được ủy quyền; người chết và người đi khai trên giấy khai tử; con, cha, mẹ trên giấy khai sinh.
KHÔNG ghi: cán bộ ký, chủ tịch / phó chủ tịch, thẩm phán, thư ký, công chứng viên, người dịch, người làm chứng.
</ai_duoc_ghi>

<cach_chep>
Chép ĐÚNG từng ký tự như chữ OCR của trang; không sửa chính tả, không thêm bớt dấu, không đoán chữ bị mất.
- "ho_ten": họ tên đầy đủ đứng sau nhãn họ tên của người đó ("Họ, chữ đệm, tên", "Họ và tên / Full name", "Ông / Bà",
  "tên vợ", "tên chồng"...). Thẻ căn cước hay in nhãn ở một dòng, họ tên ở dòng dưới → lấy dòng dưới. Chữ ký hay tên
  viết lại ở cuối trang không phải nguồn. Ba dòng MRZ ở mặt sau thẻ ("IDVNM...", họ tên không dấu nối bằng "<") không
  phải nguồn họ tên: không lập mục riêng từ ba dòng đó.
- "so_dinh_danh": dãy chữ số ở nhãn "Số / No.", "Số định danh cá nhân", "Căn cước số", "CCCD số", "CMND số" của người
  đó; chỉ giữ chữ số, bỏ dấu chấm và khoảng trắng chen giữa. KHÔNG lấy số ở ba dòng MRZ ("IDVNM..."), số điện thoại,
  số đăng ký, số quyển, số bản án.
- "dan_toc": chữ đứng sau nhãn "Dân tộc" của ĐÚNG người đó trên trang (tờ khai hay ghi chung dòng "Giới tính: ...
  Dân tộc: ... Quốc tịch: ..."; bỏ số chú thích kiểu "(2)" kẹp trước giá trị). Trang không ghi dân tộc của người đó
  → null; không lấy dân tộc của người khác trên cùng trang.
- "ngay_sinh": chỉ ngày SINH, viết dd/mm/yyyy ("ngày 5 tháng 3 năm 1985" → "05/03/1985"). Trang chỉ ghi "sinh năm
  1960" → null. KHÔNG lấy ngày cấp, ngày hết hạn, ngày đăng ký, ngày chết, ngày ký.
- Dòng in HAI CỘT (giấy kết hôn: "tên vợ: ... tên chồng: ..." rồi "Ngày, tháng, năm sinh: ... Ngày, tháng, năm sinh:
  ..."): giá trị thứ nhất thuộc người ở nhãn thứ nhất, giá trị thứ hai thuộc người ở nhãn thứ hai; không đổi chéo.
- Thông tin nào trang KHÔNG ghi cho người đó → null. Không lấy thông tin của người này điền cho người khác.
- "vai": vai của người đó đúng như trang thể hiện (chủ thẻ, người yêu cầu, người được cấp, vợ, chồng, người chết,
  nguyên đơn, bị đơn, bên ủy quyền, cha, mẹ...).
- "loai_giay": loại của tờ giấy ghi nhân thân của người đó, chọn MỘT mã theo tiêu đề và hình thức của giấy:
  + "co_quan_cap": giấy do cơ quan nhà nước lập và ký — quyết định / bản án của Tòa án, trích lục hộ tịch (kết hôn,
    khai sinh, khai tử, ghi chú ly hôn...), giấy chứng nhận kết hôn, giấy khai sinh, kết quả kiểm tra / tra cứu thông
    tin công dân, Giấy xác nhận tình trạng hôn nhân đã cấp;
  + "can_cuoc": thẻ căn cước / căn cước công dân / chứng minh nhân dân / hộ chiếu;
  + "tu_lap": giấy do người dân tự lập, đánh máy rồi ký — bản cam đoan, văn bản / giấy ủy quyền;
  + "to_khai": tờ khai của thủ tục;
  + "khac": không thuộc bốn loại trên hoặc không xác định được.
  Một trang chụp chung nhiều giấy: mỗi người mang mã của ĐÚNG tờ giấy ghi nhân thân của họ.
- "dong": chép NGUYÊN một dòng OCR có ghi họ tên của người đó (dòng dùng làm chứng cứ).
</cach_chep>

<dinh_dang_tra_ve>
Chỉ trả MỘT object JSON, không markdown, không giải thích:
{{"nguoi": [{{"ho_ten": "...", "so_dinh_danh": "... hoặc null", "ngay_sinh": "dd/mm/yyyy hoặc null",
"dan_toc": "... hoặc null", "vai": "...",
"loai_giay": "co_quan_cap | tu_lap | can_cuoc | to_khai | khac", "dong": "..."}}]}}
Trang không ghi nhân thân của ai → {{"nguoi": []}}.
</dinh_dang_tra_ve>"""


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


_TONE_MARKS = frozenset("\u0300\u0301\u0303\u0309\u0323")
_WORD_RE = re.compile(r"(?:[^\W\d_][\u0300-\u036f]*)+")


def _settle_tone(match: re.Match) -> str:
    word = match.group(0)
    return "".join(char for char in word if char not in _TONE_MARKS) + "".join(char for char in word if char in _TONE_MARKS)


def _name_key(value) -> str:
    """Khóa so họ tên: không phân biệt hoa thường và VỊ TRÍ đặt dấu thanh trong một chữ ("Thủy" / "Thuỷ" là một tên)."""
    text = _WORD_RE.sub(_settle_tone, unicodedata.normalize("NFD", str(value or "").casefold()))
    return " ".join(unicodedata.normalize("NFC", text).split())


def _letters(name: str) -> list[tuple[str, frozenset]]:
    """Từng chữ cái của họ tên kèm tập dấu của nó (chữ "đ" tính là "d" mang một dấu)."""
    out: list[tuple[str, frozenset]] = []
    for char in unicodedata.normalize("NFD", " ".join(name.casefold().split()).replace("đ", "d\u0335")):
        if unicodedata.combining(char) and out:
            out[-1] = (out[-1][0], out[-1][1] | {char})
        else:
            out.append((char, frozenset()))
    return out


def _lost_marks(short: str, full: str) -> bool:
    """`short` chỉ là bản RƠI DẤU của `full`: cùng chữ cái, chỗ nào khác nhau thì chữ của `short` trơ hẳn không dấu
    ("Dinh" / "Đinh", "He" / "Hẹ"). Hai chữ cùng còn dấu mà khác dấu ("Cáp" / "Cấp") là đọc nhầm, không tính."""
    a, b = _letters(short), _letters(full)
    return len(a) == len(b) and a != b and all(x[0] == y[0] and (x[1] == y[1] or not x[1]) for x, y in zip(a, b))


def _adds_marks(short: str, full: str) -> bool:
    """`full` giữ đủ mọi dấu của `short` và có thêm dấu ở ít nhất một chữ ("Dân" / "Dẫn", "Cáp" / "Cấp"). Nhận hai
    khóa họ tên (_name_key) để vị trí đặt dấu thanh không làm lệch phép so."""
    a, b = _letters(short), _letters(full)
    return len(a) == len(b) and a != b and all(x[0] == y[0] and x[1] <= y[1] for x, y in zip(a, b))


def _lost_stroke(short: str, full: str) -> bool:
    """Hai khóa họ tên chỉ khác nhau ở chỗ chữ "đ" của `full` thành "d" trong `short` (OCR đọc mất nét gạch)."""
    return len(short) == len(full) and short != full and all(
        x == y or (x == "d" and y == "đ") for x, y in zip(short, full))


_CENTURY_BY_CODE = {"0": 1900, "1": 1900, "2": 2000, "3": 2000}


def _year_code_fits(number: str, birth) -> bool | None:
    """Số định danh 12 số mang mã thế kỷ ở chữ số thứ 4 và hai số cuối năm sinh ở chữ số 5–6. None = không kiểm được."""
    century = _CENTURY_BY_CODE.get(number[3]) if len(number) == 12 else None
    if century is None or not birth:
        return None
    return century + int(number[4:6]) == birth[2]


def _ethnic(value) -> str:
    """Chữ dân tộc model chép từ trang: bỏ số chú thích "(2)" kẹp trước giá trị và dấu câu thừa."""
    text = re.sub(r"^\s*(?:\(\s*\d+\s*\)|\d+[.)])\s*", "", str(value or ""))
    return " ".join(text.strip(" .,:;-").split())


def _birth_key(value):
    parsed = parse_date(value)
    return (parsed.day, parsed.month, parsed.year) if parsed else None


UNITS = (
    Unit("ho_ten", "Họ tên người được cấp", (Field(NAME, "họ, chữ đệm, tên", canon=_name_key),)),
    Unit("so_dinh_danh", "Số định danh cá nhân người được cấp", (Field(NUMBER, "số định danh 12 chữ số", "code", canon=_digits),)),
    Unit("ngay_sinh", "Ngày sinh người được cấp", (Field(BIRTHDAY, "ngày sinh dd/mm/yyyy", "date"),)),
    Unit("dan_toc", "Dân tộc người được cấp", (Field(ETHNIC, "dân tộc", canon=fold),)),
)
_UNIT_BY_FIELD = {unit.fields[0].name: unit for unit in UNITS}


def _is_declaration(text: str) -> bool:
    """Trang tờ khai (chữ viết tay) — nguồn kém tin nhất cho chữ và số."""
    folded = fold(text)
    return "nguoi co ten duoi day" in folded or "to khai cap giay xac nhan" in folded


def _handwritten(name_line: str, page_text: str) -> bool:
    """Bản ghi nằm trong phần TỜ KHAI của trang (từ đầu tờ khai tới hết khối chữ ký) → chữ viết tay. Trang chụp chung
    tờ khai và thẻ căn cước: dòng nằm sau khối chữ ký là của giấy in."""
    if not _is_declaration(page_text):
        return False
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    end = next((i for i, line in enumerate(lines) if "ky, ghi ro ho" in fold(line)), None)
    at = next((i for i, line in enumerate(lines) if name_line and _name_key(name_line) in _name_key(line)), None)
    if end is None or at is None:
        return True
    return at <= end + _SIGNATURE_LINES


def _near_name(left, right) -> bool:
    a, b = fold(left), fold(right)
    return bool(a and b) and len(a.split()) == len(b.split()) and (
        a == b or difflib.SequenceMatcher(None, a, b).ratio() >= _NEAR_NAME_RATIO)


def _id_gap(left: str, right: str) -> int | None:
    """Số vị trí lệch giữa hai số 12 chữ số; None khi một bên không đủ 12 số."""
    if len(left) != 12 or len(right) != 12:
        return None
    return sum(a != b for a, b in zip(left, right))


def _subject(case: Case) -> dict:
    return {"name": str(case.values.get(NAME) or "").strip(), "number": _digits(case.values.get(NUMBER)),
            "birth": _birth_key(case.values.get(BIRTHDAY))}


def pages(case: Case) -> list[dict]:
    """Các trang có dấu vết của người được cấp (số định danh, ngày sinh, hoặc gần đủ các chữ của họ tên):
    {doc, text}."""
    subject = _subject(case)
    tokens = fold(subject["name"]).split()
    out = []
    for index, document in enumerate(case.documents, start=1):
        for text in _PAGE_BREAK_RE.split(str(document.get("text") or "")):
            if not text.strip():
                continue
            words = set(fold(text).split())
            has_name = len(tokens) >= 2 and sum(token in words for token in tokens) >= len(tokens) - 1
            has_number = len(subject["number"]) >= 9 and subject["number"] in _digits(text)
            has_birth = bool(subject["birth"]) and any(
                _birth_key("/".join(match)) == subject["birth"]
                for match in re.findall(r"(?<!\d)(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})(?!\d)", text))
            if has_name or has_number or has_birth:
                out.append({"doc": index, "text": text.strip()})
    return out[:_MAX_PAGES]


async def _read_page(page: dict, title: str) -> list[dict]:
    raw = await client.chat(
        [{"role": "system", "content": _PAGE_PROMPT.format(title=title)},
         {"role": "user", "content": f"Chữ OCR của trang giấy:\n\n{page['text']}"}],
        max_tokens=_MAX_TOKENS, temperature=0, enable_thinking=settings.agent_reasoning, purpose="thanh_tra.dinh_danh",
    )
    people = engine.parse_json(raw).get("nguoi")
    records = []
    for person in people if isinstance(people, list) else []:
        if not isinstance(person, dict) or not str(person.get("ho_ten") or "").strip():
            continue
        handwritten = _handwritten(str(person.get("dong") or person["ho_ten"]), page["text"])
        records.append({"name": " ".join(str(person["ho_ten"]).split()), "number": _digits(person.get("so_dinh_danh")),
                        "birth": _birth_key(person.get("ngay_sinh")), "birth_text": str(person.get("ngay_sinh") or "").strip(),
                        "ethnic": _ethnic(person.get("dan_toc")),
                        "role": str(person.get("vai") or "").strip(), "doc": page["doc"], "text": page["text"],
                        "handwritten": handwritten,
                        "tier": _LOW_TIER if handwritten else _TIERS.get(str(person.get("loai_giay") or "").strip(), _LOW_TIER)})
    return records


def _number_slip(left: str, right: str) -> bool:
    """Hai số là một số trên thẻ mà chữ viết tay bị OCR đọc lệch / rơi tối đa hai chữ số."""
    gap = _id_gap(left, right)
    if gap is not None:
        return 0 < gap <= _ID_SLIP_MAX
    short, long = sorted((left, right), key=len)
    if len(long) != 12 or not 0 < len(long) - len(short) <= _ID_SLIP_MAX:
        return False
    rest = iter(long)
    return all(digit in rest for digit in short)


def link(record: dict, subject: dict) -> tuple[float, list[str]]:
    """Điểm nhận người của một bản ghi so với người được cấp + các căn cứ. Trùng hẳn một thông tin = 1 điểm, gần giống
    (họ tên lệch một chữ, số lệch tối đa hai chữ số) = 0,5. Họ tên khác hẳn hoặc số định danh khác hẳn = người khác
    (điểm âm). Ngày sinh lệch không cộng điểm nhưng không loại, vì chính nó có thể là chỗ OCR đọc sai."""
    score, why = 0.0, []
    if record["name"] and subject["name"]:
        if fold(record["name"]) == fold(subject["name"]):
            score += 1; why.append("trùng họ tên")
        elif _near_name(record["name"], subject["name"]):
            score += 0.5; why.append("họ tên lệch một chữ")
        else:
            return -1.0, []
    if record["number"] and subject["number"]:
        if record["number"] == subject["number"]:
            score += 1; why.append("trùng số định danh")
        elif _number_slip(record["number"], subject["number"]):
            score += 0.5; why.append("số định danh lệch tối đa hai chữ số")
        else:
            return -1.0, []
    if record["birth"] and subject["birth"] and record["birth"] == subject["birth"]:
        score += 1; why.append("trùng ngày sinh")
    return score, why


def _is_subject(record: dict, subject: dict) -> str:
    """Căn cứ nhận bản ghi là của người được cấp ("" = không nhận): từ 2 điểm; trùng đủ số định danh thì họ tên lệch
    một chữ là đủ; giấy không ghi số định danh (giấy kết hôn, bản án) thì trùng ngày sinh + họ tên lệch một chữ là đủ."""
    score, why = link(record, subject)
    exact_number = "trùng số định danh" in why
    if score >= 2 or (score >= 1.5 and (exact_number or (not record["number"] and "trùng ngày sinh" in why))):
        return ", ".join(why)
    return ""


def _line_with(text: str, needle: str, *, digits_only: bool = False) -> str:
    """Dòng trên trang chứa đúng giá trị — dùng làm dòng chứng cứ nguyên văn."""
    for line in text.splitlines():
        if not line.strip():
            continue
        if (_digits(needle) in _digits(line)) if digits_only else (_name_key(needle) in _name_key(line)):
            return line.strip()
    return ""


def _date_line(text: str, birth) -> str:
    for line in text.splitlines():
        for match in re.findall(r"(?<!\d)(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})(?!\d)", line):
            if _birth_key("/".join(match)) == birth:
                return line.strip()
    return ""


_PRINTED_WEIGHT, _HANDWRITTEN_WEIGHT, _MRZ_WEIGHT = 1.0, 0.5, 1.0
# Bậc loại giấy, chỉ dùng khi hai giá trị NGANG điểm nguồn: giấy do cơ quan cấp > giấy tự lập đánh máy (cam đoan, ủy
# quyền) > thẻ căn cước > tờ khai. Loại giấy không rõ xếp bậc thấp nhất để không tạo ưu thế không có căn cứ.
_LOW_TIER, _CARD_TIER = 1, 2
_TIERS = {"co_quan_cap": 4, "tu_lap": 3, "can_cuoc": _CARD_TIER, "to_khai": _LOW_TIER, "khac": _LOW_TIER}
_TIER_LABELS = {4: "giấy do cơ quan cấp", 3: "giấy tự lập đánh máy (cam đoan, ủy quyền)", _CARD_TIER: "thẻ căn cước",
                _LOW_TIER: "tờ khai / giấy không rõ loại", 0: "không có giấy nào"}
# Hai cách viết chỉ khác DẤU ("KHÔNG" / "KHỔNG"): OCR rơi dấu cả trên chữ in hoa của thẻ, nên một nguồn chưa đủ.
_MARK_ONLY_MIN_WEIGHT = 1.5


def weigh(records: list[dict], subject: dict, mrz: list[dict]) -> dict:
    """Trọng số nguồn của từng giá trị, theo từng thông tin: {field: {khóa: {"weight", "tier", "value", "record",
    "why"}}}. "tier" = bậc cao nhất trong các loại giấy ghi giá trị đó.
    Mỗi TRANG tính một lần: giấy in 1, tờ khai viết tay 0,5; vùng MRZ của thẻ mang đúng số định danh thêm 1.
    Họ tên: tính cả bản ghi chỉ khác dấu với tên của người được cấp dù trang đó không ghi số / ngày sinh (bản án, giấy
    khai sinh của con) — cùng một hồ sơ, cùng tên không dấu là cùng người."""
    linked = [(record, _is_subject(record, subject)) for record in records]
    linked = [(record, why) for record, why in linked if why]
    names = {fold(subject["name"])} | {fold(record["name"]) for record, _ in linked}
    out = {NAME: {}, NUMBER: {}, BIRTHDAY: {}}

    def add(field: str, key, value: str, record: dict, why: str, record_is_linked: bool = True) -> None:
        slot = out[field].setdefault(key, {"weight": 0.0, "paper": 0.0, "tier": 0, "pages": set(), "value": value,
                                           "record": None, "why": why, "rank": -1})
        slot["tier"] = max(slot["tier"], record.get("tier", _LOW_TIER))
        page = (id(record["text"]), record["handwritten"])
        if page not in slot["pages"]:
            slot["pages"].add(page)
            slot["weight"] += _HANDWRITTEN_WEIGHT if record["handwritten"] else _PRINTED_WEIGHT
            slot["paper"] = slot["weight"]
        # Dòng chứng cứ đưa ra toà: ưu tiên bản ghi in đã nhận người bằng số định danh, rồi tới bản ghi nhận bằng
        # thông tin khác, cuối cùng mới tới bản ghi chỉ cùng tên không dấu.
        rank = 2 if "trùng số định danh" in why else 1 if record_is_linked else 0
        if not record["handwritten"] and rank > slot["rank"]:
            slot["value"], slot["record"], slot["why"], slot["rank"] = value, record, why, rank

    for record in records:
        why = dict((id(r), w) for r, w in linked).get(id(record), "")
        if record["name"] and (why or fold(record["name"]) in names):
            add(NAME, _name_key(record["name"]), record["name"], record, why or "cùng họ tên không dấu trong hồ sơ",
                bool(why))
        if not why:
            continue
        if len(record["number"]) == 12:
            add(NUMBER, record["number"], record["number"], record, why)
        if record["birth"]:
            day, month, year = record["birth"]
            add(BIRTHDAY, record["birth"], f"{day:02d}/{month:02d}/{year}", record, why)
    _vote_by_word(out[NAME])
    numbers = {subject["number"]} | set(out[NUMBER])
    for card in mrz:
        if card.get("id") not in numbers:
            continue
        for key, slot in out[NAME].items():
            if fold(key) == fold(card.get("name")):
                slot["weight"] += _MRZ_WEIGHT
        if card["id"] in out[NUMBER] and fold(card.get("name")) in names:
            out[NUMBER][card["id"]]["weight"] += _MRZ_WEIGHT
            out[NUMBER][card["id"]]["tier"] = max(out[NUMBER][card["id"]]["tier"], _CARD_TIER)
        for key, slot in out[BIRTHDAY].items():
            if card.get("birth") and (key[2] % 100, key[1], key[0]) == tuple(card["birth"]):
                slot["weight"] += _MRZ_WEIGHT
                slot["tier"] = max(slot["tier"], _CARD_TIER)
    return out


def _vote_by_word(slots: dict) -> None:
    """Các cách viết chỉ khác DẤU của cùng một họ tên (từ ba cách trở lên mới khác kết quả): điểm của mỗi cách viết là
    điểm của CHỮ yếu nhất trong nó, mỗi chữ được cộng điểm từ mọi cách viết ghi chữ đó y hệt. Nhờ vậy giấy A sai dấu ở
    họ, giấy B sai dấu ở tên không làm chia phiếu cho cách viết đúng cả hai chữ."""
    groups: dict[str, list[str]] = {}
    for key in slots:
        groups.setdefault(fold(key), []).append(key)
    for keys in groups.values():
        # Cách viết hoàn toàn không dấu (form in không dấu, dòng MRZ) không mang thông tin về dấu nên không góp phiếu.
        keys = [key for key in keys if not key.isascii()]
        if len(keys) < 3:
            continue
        base = {key: slots[key]["weight"] for key in keys}
        for key in keys:
            slots[key]["weight"] = slots[key]["paper"] = min(
                sum(weight for other, weight in base.items() if other.split()[index:index + 1] == [word])
                for index, word in enumerate(key.split()))


def _ethnic_finding(records: list[dict], subject: dict, case: Case) -> Finding | None:
    """Lượt trích bỏ trống dân tộc mà trang có ghi dân tộc của CHÍNH người được cấp → đề xuất bổ sung. Mỗi trang tính
    một phiếu; hai giá trị ngang phiếu thì không đề xuất."""
    if case.values.get(ETHNIC) or case.values.get(OTHER_ETHNIC):
        return None
    votes: dict[str, dict] = {}
    for record in records:
        why = _is_subject(record, subject) if record.get("ethnic") else ""
        if not why:
            continue
        slot = votes.setdefault(fold(record["ethnic"]), {"pages": set(), "record": record, "why": why})
        slot["pages"].add(id(record["text"]))
    if not votes:
        return None
    ranked = sorted(votes.values(), key=lambda slot: len(slot["pages"]), reverse=True)
    if len(ranked) > 1 and len(ranked[0]["pages"]) == len(ranked[1]["pages"]):
        return None
    best = ranked[0]
    record = best["record"]
    quote = next((line.strip() for line in record["text"].splitlines()
                  if "dan toc" in fold(line) and fold(record["ethnic"]) in fold(line)), "")
    if not quote:
        return None
    return Finding(INSPECTOR, _UNIT_BY_FIELD[ETHNIC], {ETHNIC: record["ethnic"]}, quote, record["doc"],
                   f"mã đã nhận bản ghi này là của CHÍNH người được cấp ({best['why']}); trên tờ giấy đó người này "
                   f"đứng ở vai: {record['role'] or '?'}", _OWNER, backed=True,
                   evidence=(f"lượt trích bỏ trống dân tộc; {len(best['pages'])} trang ghi dân tộc này cho người được "
                             f"cấp, {sum(len(slot['pages']) for slot in ranked[1:])} trang ghi khác",))


def _year_code_clash(field: str, key, own, weights: dict, subject: dict) -> bool:
    """Giá trị đề xuất KHÔNG khớp mã năm sinh trong số định danh, còn giá trị lượt trích thì khớp."""
    if field == NUMBER:
        births = [birth for birth in {subject["birth"], *weights[BIRTHDAY]} if birth]
        mine, theirs = ([_year_code_fits(number, birth) for birth in births] for number in (own, key))
    elif field == BIRTHDAY:
        numbers = [number for number in {subject["number"], *weights[NUMBER]} if number]
        mine, theirs = ([_year_code_fits(number, birth) for number in numbers] for birth in (own, key))
    else:
        return False
    return any(mine) and False in theirs and not any(theirs)


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    subject = _subject(case)
    if not subject["name"] or not (subject["number"] or subject["birth"]):
        return []  # không đủ hai thông tin để nhận người
    read = await asyncio.gather(*(_read_page(page, title) for page in pages(case)), return_exceptions=True)
    records = [record for answer in read if not isinstance(answer, BaseException) for record in answer]
    mrz = [card for document in case.documents for card in mrz_records(document.get("text"))]
    return findings_from(records, mrz, case)


def findings_from(records: list[dict], mrz: list[dict], case: Case) -> list[Finding]:
    """Đề xuất cho MỘT người (người ở ``case.values``) từ các bản ghi đã đọc sẵn — thủ tục có nhiều chủ thể đọc trang
    một lần rồi gọi hàm này cho từng người."""
    subject = _subject(case)
    if not subject["name"] or not (subject["number"] or subject["birth"]):
        return []
    weights = weigh(records, subject, mrz)
    current = {NAME: _name_key(subject["name"]), NUMBER: subject["number"], BIRTHDAY: subject["birth"]}
    findings = []
    for field, slots in weights.items():
        rivals = {key: slot for key, slot in slots.items() if key != current[field] and slot["record"] is not None}
        if not rivals:
            continue
        key, best = max(rivals.items(), key=lambda item: (item[1]["weight"], item[1]["tier"]))
        mine = slots.get(current[field], {"weight": 0.0, "tier": 0})
        own = mine["weight"]
        # Tên trong MRZ không dấu nên không phân xử được hai cách viết chỉ khác dấu: ngưỡng tính riêng điểm giấy.
        record = best["record"]
        quote = (_line_with(record["text"], best["value"]) if field == NAME else
                 _line_with(record["text"], best["value"], digits_only=True) if field == NUMBER else
                 _date_line(record["text"], record["birth"]))
        if not quote:
            continue
        mark_only = field == NAME and fold(key) == fold(current[field])
        tied = best["weight"] == own
        lost_marks = tied and mark_only and _lost_marks(best["value"], subject["name"])
        lost_stroke = mark_only and _lost_stroke(key, current[field])
        # Giấy in đủ dấu hơn lượt trích: rơi dấu trên mặt thẻ không giải thích được cách viết này → một giấy in là đủ.
        adds_marks = mark_only and _adds_marks(current[field], key)
        year_clash = _year_code_clash(field, key, current[field], weights, subject)
        backed = not lost_marks and not lost_stroke and not year_clash and (
            (best["tier"] > mine["tier"] and best["weight"] >= _PRINTED_WEIGHT) if tied else (
                best["weight"] > own and (
                    best["paper"] >= (_PRINTED_WEIGHT if adds_marks else _MARK_ONLY_MIN_WEIGHT) if mark_only
                    else best["weight"] >= _PRINTED_WEIGHT)))
        evidence = (f"giá trị của B có {best['weight']:g} điểm nguồn (mỗi trang giấy in 1, tờ khai viết tay 0,5, vùng MRZ "
                    f"của thẻ 1), nhận là cùng người vì: {best['why']}; giá trị của A có {own:g} điểm nguồn"
                    + (f"; hai bên NGANG điểm — loại giấy bậc cao nhất ghi B: {_TIER_LABELS[best['tier']]}, ghi A: "
                       f"{_TIER_LABELS[mine['tier']]}" if tied else "")
                    + ("; họ tên của B chỉ là bản rơi dấu của A" if lost_marks else "")
                    + ('; họ tên của B chỉ khác A ở chữ "Đ" bị đọc thành "D"' if lost_stroke else "")
                    + ("; B ĐỦ DẤU HƠN A: mọi dấu của A đều có trong B, B còn thêm dấu"
                       if adds_marks and not tied else "")
                    + ("; B KHÔNG khớp mã năm sinh trong số định danh, A khớp" if year_clash else ""),)
        findings.append(Finding(INSPECTOR, _UNIT_BY_FIELD[field], {field: best["value"]}, quote, record["doc"],
                                f"mã đã nhận bản ghi này là của CHÍNH người được cấp ({best['why']}); trên tờ giấy đó "
                                f"người này đứng ở vai: {record['role'] or '?'}", _OWNER,
                                backed=backed, evidence=evidence))
    ethnic = _ethnic_finding(records, subject, case)
    if ethnic:
        findings.append(ethnic)
    return findings


INSPECTOR = Inspector("dinh_danh", "ĐỊNH DANH người được cấp Giấy xác nhận tình trạng hôn nhân", UNITS, RULES,
                      owners=(_OWNER,), accepted=(_OWNER,), find=find)
