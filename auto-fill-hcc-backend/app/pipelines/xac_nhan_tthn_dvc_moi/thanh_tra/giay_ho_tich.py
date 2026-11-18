"""Thanh tra GIẤY HỘ TỊCH kèm hồ sơ cấp Giấy XNTTHN: số / ngày / cơ quan của giấy khai tử (vợ, chồng đã chết) và
của bản án / quyết định ly hôn.

Cách kiểm riêng, không hỏi model "ô này điền gì":
1. Mỗi trang có dấu vết khai tử / ly hôn được đọc RIÊNG: model chỉ lập danh sách các BỘ (số, ngày, cơ quan) in trên
   trang, mỗi bộ gắn đúng một loại nguồn (dòng đăng ký gốc, đầu giấy, dòng nhắc lại trên tờ khai). Model không biết
   kết quả lượt trích.
2. MÃ chọn bộ theo thứ bậc nguồn rồi đối chiếu với lượt trích: lượt trích lấy bộ bậc thấp hơn, ghép số của bộ này với
   ngày của bộ khác, hoặc bỏ trống ô mà giấy có ghi → thành đề xuất, kèm căn cứ cho toà.
"""

import asyncio
import difflib
import re

from app.config import settings
from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import (Case, Field, Finding, Inspector, Unit, alnum, compare_key, fold,
                                                   is_empty, locate, parse_date)
from app.services.llm import client

from ..process import mapper

# Luật của nhóm: TOÀ ÁN đọc để phán từng vụ (A = giá trị lượt trích, B = bộ thanh tra đề xuất).
RULES = """
<bo_so_ngay_co_quan>
Số, ngày, cơ quan của một giấy là MỘT BỘ đi cùng nhau: cả ba phải lấy từ cùng một chỗ trên cùng một tờ giấy. Số của
chỗ này ghép với ngày hoặc cơ quan của chỗ khác ("số này ngày kia") là SAI, dù từng giá trị đều có trên giấy. Thanh
tra đã đọc riêng từng trang và lập các bộ in trên giấy; dòng "Tín hiệu mã" nêu mỗi giá trị nằm ở bộ nào.
</bo_so_ngay_co_quan>

<giay_khai_tu>
Cổng hỏi số / ngày / cơ quan của giấy khai tử của vợ hoặc chồng người được cấp, theo ĐÚNG LOẠI GIẤY người dân nộp: nộp
BẢN CHÍNH (trích lục khai tử bản chính, giấy chứng tử) thì điền số đăng ký gốc; nộp BẢN SAO trích lục khai tử (số đầu
trang dạng "<N>/TLKT-BS", hoặc giấy có dòng "(BẢN SAO)") thì điền số, ngày cấp, cơ quan cấp ở ĐẦU bản sao; có cả bản
chính lẫn bản sao thì theo bản chính. Thứ bậc nguồn, cao xuống thấp (mã đã xếp bậc theo loại giấy):
1. Dòng đăng ký gốc trong thân trích lục khai tử BẢN CHÍNH: "Đã được đăng ký khai tử tại: <cơ quan> ... Số: <N> ...
   ngày <D>", hoặc "Nơi ghi: <cơ quan>, Sổ đăng ký khai tử, quyển số <Q>, số <N>, ngày <D>". Cơ quan chép đủ mọi cấp
   dòng đó ghi (xã / phường, huyện, tỉnh).
2. Đầu giấy khai tử BẢN CHÍNH (trích lục bản chính thiếu dòng đăng ký gốc, giấy chứng tử).
3. Đầu BẢN SAO trích lục khai tử: số "<N>/TLKT-BS" giữ nguyên hậu tố, ngày cấp bản sao ở dòng địa danh + ngày, cơ quan
   cấp ở khối đầu trang.
4. Dòng đăng ký gốc trong thân BẢN SAO trích lục — chỉ bù field đầu bản sao không ghi.
5. Đầu giấy báo tử của bệnh viện / cơ quan (không phải giấy đăng ký khai tử).
6. Dòng tình trạng hôn nhân trên tờ khai / Giấy XNTTHN cũ nhắc lại giấy khai tử — chỉ dùng khi hồ sơ KHÔNG có giấy
   khai tử thật: chữ viết tay hay bị đọc lệch.
Tín hiệu mã nêu "cấu hình đơn vị: bản sao vẫn lấy số gốc" → đơn vị này điền số đăng ký gốc cả khi người dân nộp bản
sao: dòng đăng ký gốc trong thân bản sao xếp bậc như bản chính (bậc 1), đầu bản sao như đầu bản chính (bậc 2).
A lấy bộ bậc thấp trong khi hồ sơ có bộ bậc cao hơn → chọn B. Bộ bậc cao thiếu một giá trị thì giá trị đó lấy ở bậc kế
tiếp của CHÍNH tờ giấy đó, không để trống.
Dòng "Giấy báo tử / Giấy tờ thay thế Giấy báo tử số ... do <bệnh viện> cấp" trong thân trích lục là giấy căn cứ để
đăng ký, không phải bộ của lần đăng ký khai tử: B lấy từ dòng đó → chọn A.
</giay_khai_tu>

<ban_an_ly_hon>
Thứ bậc nguồn của số / ngày / cơ quan ly hôn, cao xuống thấp:
1. Dòng văn bản gốc trong thân TRÍCH LỤC bản án / quyết định: "Tại Bản án / Quyết định ... số <N> ngày <D>, Tòa án
   <CQ> ..." — số, ngày, Tòa án của bản án / quyết định gốc. Số, ngày, Tòa án ở đầu bản trích lục (ký hiệu "TL") là của
   chính bản trích lục, bậc thấp hơn.
2. VĂN BẢN bản án / quyết định ly hôn của Tòa án kèm trong hồ sơ (không phải trích lục): số ở nhãn "Số:" ĐẦU văn bản,
   ngày ban hành ở dòng địa danh + ngày đầu văn bản, Tòa án ban hành ở khối đầu văn bản. Trên văn bản này, số ở cụm
   dẫn chiếu ("tại quyết định số ...", "theo bản án số ..."), số thụ lý, số biên lai không phải số của văn bản.
3. Dòng tình trạng hôn nhân trên tờ khai / Giấy XNTTHN cũ — chỉ dùng khi hồ sơ KHÔNG kèm văn bản của Tòa án.
A lấy bộ bậc thấp trong khi hồ sơ có bộ bậc cao hơn ghi khác → chọn B.
</ban_an_ly_hon>

<cach_phan_xu>
- A bỏ trống ô mà bộ của B có ghi trên giấy đúng người → chọn B (bổ sung).
- A và B cùng một bộ, chỉ khác cách viết (viết tắt "UBND" / "TAND", hoa thường, dấu câu) → KHONG_DU_CAN_CU.
- Hồ sơ cấp Giấy XNTTHN kèm giấy khai tử của một người KHÁC người được cấp thì đó là giấy khai tử của vợ / chồng, KỂ
  CẢ khi giấy không ghi quan hệ và không nhắc tên người được cấp: mã đã loại giấy của chính người được cấp và giấy của
  người cùng giới, toà không loại lần nữa vì "không thấy ghi là vợ / chồng".
- Bản án phải có người được cấp là một bên ly hôn; dòng chứng cứ của B thuộc bản án của người khác → chọn A.
- Số của A nằm ở dòng "thụ lý số ..." (số thụ lý vụ án), còn B là số ở đầu văn bản của Tòa án → chọn B.
- Tín hiệu mã không nêu được A nằm ở bộ nào và B không rõ ràng đúng hơn → KHONG_DU_CAN_CU.
</cach_phan_xu>
"""

DEATH_FIELDS = ("DeathCert_Number", "DeathCert_Date", "DeathCert_Agency")
DIVORCE_FIELDS = ("BanAn_Number", "BanAn_Date", "BanAn_Agency")
_PAGE_BREAK_RE = re.compile(r"(?m)^[─\-=\s]*Trang\s+\d+\s*/\s*\d+[─\-=\s]*$")
# Lưới này chỉ để CHỌN TRANG đưa cho model đọc, không quyết định giá trị nào.
_PAGE_HINT_RE = re.compile(r"khai tu|chung tu|bao tu|ly hon|toa an nhan dan|tinh trang hon nhan")
_MAX_PAGES = 8
_MAX_TOKENS = 700
_NEAR_NAME_RATIO = 0.84

# Lượt đọc MỘT trang: model chỉ lập danh sách các bộ số / ngày / cơ quan in trên trang, không biết kết quả lượt trích.
_PAGE_PROMPT = """<vai_tro>
Bạn là người đọc giấy tờ của dây chuyền soát hồ sơ {title}. Bạn nhận chữ OCR của MỘT trang giấy và lập danh sách các
BỘ (số, ngày, cơ quan) của giấy KHAI TỬ và của bản án / quyết định LY HÔN in trên trang đó. Bạn không cần biết ô nào
trên biểu mẫu cần điền: việc chọn bộ nào do bước sau làm. Một trang có thể có nhiều bộ, hoặc không có bộ nào.
</vai_tro>

<cac_loai_bo>
Mỗi bộ thuộc đúng MỘT việc ("khai_tu" hoặc "ly_hon") và đúng MỘT loại nguồn:
- "dang_ky_goc" — CHỈ có trên trích lục khai tử: dòng thân "Đã (được) đăng ký khai tử tại: <cơ quan> ... Số: <N> ...
  ngày <D>", có giấy in "Cấp số: <N> Quyển số: ... Ngày đăng ký: <D>" (số và ngày có thể xuống dòng kế tiếp); trích
  lục lập từ cơ sở dữ liệu hộ tịch điện tử thì là dòng "Nơi ghi: <cơ quan>, Sổ đăng ký khai tử, quyển số <Q>, số <N>,
  ngày <D>" — cơ quan là phần đứng trước "Sổ đăng ký khai tử", số là <N> chứ không phải quyển số <Q>.
  "co_quan" = cơ quan đứng sau "tại:", chép ĐỦ mọi cấp dòng đó ghi (xã / phường, huyện, tỉnh); "so" = số đứng sau chữ
  "Số" / "Cấp số" của dòng đó, không phải số quyển; "ngay" = ngày đăng ký đứng sau số.
  Cũng là "dang_ky_goc" (việc "ly_hon"): trên TRÍCH LỤC bản án / quyết định ly hôn, dòng thân "Tại Bản án / Quyết định
  ... số <N> ngày <D>, Tòa án <CQ> ..." — "so" = <N> giữ nguyên ký hiệu, "ngay" = <D>, "co_quan" = <CQ>.
- "dau_giay" — số, ngày, cơ quan in ở ĐẦU của chính tờ giấy:
  + trích lục khai tử, giấy chứng tử, giấy báo tử: "so" = số ở nhãn "Số:" đầu trang, giữ nguyên hậu tố; "ngay" = ngày
    ở dòng "<địa danh>, ngày ... tháng ... năm ..." (giấy chứng tử mẫu cũ: ngày ở nhãn "Ngày, tháng, năm đăng ký");
    "co_quan" = cơ quan cấp ở khối đầu trang ("UBND XÃ ...").
  + bản án / quyết định ly hôn của Tòa án: "so" = số ở nhãn "Số:" đầu văn bản, giữ nguyên ký hiệu; "ngay" = ngày ban
    hành ở dòng địa danh + ngày đầu văn bản, hoặc nhãn "Ngày:" ngay dưới số; "co_quan" = Tòa án ban hành ở khối đầu
    văn bản, ghép đủ các dòng của khối đó. Trang KHÔNG phải trang đầu của văn bản (không có khối đầu văn bản) → không
    lập bộ "dau_giay". Số ở cụm dẫn chiếu, số thụ lý, số biên lai, số án phí không phải số của văn bản.
- "nhac_lai" — dòng tình trạng hôn nhân trên TỜ KHAI hoặc Giấy xác nhận tình trạng hôn nhân cũ nhắc lại một giấy:
  "... đã chết theo giấy chứng tử / trích lục khai tử số <N> do <cơ quan> cấp ngày <D>" → việc "khai_tu"; "... đã ly
  hôn theo bản án / quyết định số <N> ngày <D> của <Tòa án>" → việc "ly_hon".
Một trích lục khai tử / trích lục bản án, quyết định có dòng gốc trong thân thì lập HAI bộ: một bộ "dang_ky_goc" và
một bộ "dau_giay" (số, ngày, cơ quan ở đầu bản trích lục).
Dòng thân trích lục khai tử "Giấy báo tử / Giấy tờ thay thế Giấy báo tử số <N> ... do <bệnh viện / cơ quan> cấp ngày
<D>" là giấy CĂN CỨ để đăng ký khai tử, KHÔNG phải lần đăng ký → KHÔNG lập bộ nào từ dòng này. Trích lục không có dòng
"Đã (được) đăng ký khai tử tại" / "Nơi ghi ... Sổ đăng ký khai tử" / "Cấp số" thì chỉ lập bộ "dau_giay".
Số, ngày, cơ quan ở đầu của TỜ KHAI và của Giấy xác nhận tình trạng hôn nhân cũ là của chính tờ đó, KHÔNG phải bộ của
giấy khai tử hay bản án ly hôn → không lập bộ "dau_giay" từ hai loại giấy này.
</cac_loai_bo>

<cach_chep>
Chép ĐÚNG từng ký tự như chữ OCR của trang; không sửa chính tả, không đoán chữ bị mất, không lấy giá trị của bộ này
điền cho bộ khác.
- "so": chỉ phần số và ký hiệu, không kèm chữ "Số"; không lấy số định danh, số điện thoại, số quyển.
- "ngay": viết dd/mm/yyyy ("ngày 5 tháng 3 năm 2020" → "05/03/2020"). KHÔNG lấy ngày chết, ngày sinh, ngày kết hôn,
  ngày làm tờ khai. Thiếu ngày, tháng hoặc năm → null.
- "co_quan": chép như giấy ghi, không tự thêm cấp hành chính mà chỗ đó không ghi.
- "nguoi": với việc "khai_tu" là họ tên NGƯỜI CHẾT; với việc "ly_hon" là họ tên HAI bên ly hôn, cách nhau bằng dấu
  ";". Trang không ghi → null. "gioi_tinh": giới tính người chết nếu trang ghi ("Nam" / "Nữ"), không thì null.
- "dong": chép NGUYÊN một dòng OCR có ghi "so" của bộ đó; bộ không có số thì dòng có ngày của bộ đó.
- Giá trị nào chỗ đó không ghi → null. Bộ không có cả số lẫn ngày → không lập.
</cach_chep>

<dinh_dang_tra_ve>
Chỉ trả MỘT object JSON, không markdown, không giải thích:
{{"bo": [{{"viec": "khai_tu | ly_hon", "nguon": "dang_ky_goc | dau_giay | nhac_lai", "so": "... hoặc null",
"ngay": "dd/mm/yyyy hoặc null", "co_quan": "... hoặc null", "nguoi": "... hoặc null", "gioi_tinh": "Nam | Nữ | null",
"dong": "..."}}]}}
Trang không có bộ nào → {{"bo": []}}.
</dinh_dang_tra_ve>"""

_RANKS = {("khai_tu", "dang_ky_goc"): 3, ("khai_tu", "dau_giay"): 2, ("khai_tu", "nhac_lai"): 1,
          ("ly_hon", "dang_ky_goc"): 4, ("ly_hon", "dau_giay"): 3, ("ly_hon", "nhac_lai"): 1}
# Giấy khai tử xếp bậc theo LOẠI GIẤY người dân nộp (xem <giay_khai_tu>): bản chính → số đăng ký gốc; bản sao trích lục
# → số / ngày / cơ quan đầu bản sao, dòng đăng ký trong thân chỉ bù; giấy báo tử không phải giấy đăng ký khai tử.
_DEATH_RANKS = {("ban_chinh", "dang_ky_goc"): 6, ("ban_chinh", "dau_giay"): 5, ("ban_sao", "dau_giay"): 4,
                ("ban_sao", "dang_ky_goc"): 3, ("bao_tu", "dang_ky_goc"): 3, ("bao_tu", "dau_giay"): 2}
# Bậc của bộ ở đầu văn bản Tòa án / dòng đăng ký khai tử gốc: từ bậc này trở lên, số của A nằm riêng trên dòng thụ lý
# là số thụ lý vụ án.
_PRIMARY_RANK = 3
_SOURCE_LABELS = {("khai_tu", "dang_ky_goc"): "dòng đăng ký gốc trong thân trích lục khai tử",
                  ("khai_tu", "dau_giay"): "đầu giấy khai tử (số của bản trích lục / giấy chứng tử)",
                  ("ban_sao", "dang_ky_goc"): "dòng đăng ký gốc trong thân BẢN SAO trích lục khai tử",
                  ("ban_sao", "dau_giay"): "đầu BẢN SAO trích lục khai tử (giấy người dân nộp là bản sao)",
                  ("bao_tu", "dau_giay"): "đầu giấy báo tử",
                  ("khai_tu", "nhac_lai"): "dòng nhắc lại trên tờ khai / Giấy XNTTHN cũ",
                  ("ly_hon", "dang_ky_goc"): "dòng văn bản gốc trong thân trích lục bản án / quyết định",
                  ("ly_hon", "dau_giay"): "đầu văn bản bản án / quyết định của Tòa án (hoặc đầu bản trích lục)",
                  ("ly_hon", "nhac_lai"): "dòng nhắc lại trên tờ khai / Giấy XNTTHN cũ"}
_OWNERS = ("giấy khai tử của vợ / chồng người được cấp", "bản án / quyết định ly hôn của người được cấp",
           "tờ khai / Giấy XNTTHN cũ", "giấy khác")


def _authority(value) -> str:
    text = re.sub(r"\bubnd\b", "uy ban nhan dan", fold(value))
    return alnum(re.sub(r"\btand\b", "toa an nhan dan", text))


_UNIT_WORDS = ("Xã", "Phường", "Thị Trấn", "Đặc Khu", "Quận", "Huyện", "Thị Xã", "Thành Phố", "Tỉnh")


def _tidy_agency(value: str) -> str:
    """Cơ quan chép từ khối đầu giấy thường IN HOA: đưa về cách viết thường dùng trên biểu mẫu, không đổi chữ nào."""
    if not value or not value.isupper():
        return value
    text = re.sub(r"\bUBND\b", "ỦY BAN NHÂN DÂN", re.sub(r"\bTAND\b", "TÒA ÁN NHÂN DÂN", value)).title()
    text = re.sub(r"\b[ỦU][yỷ] Ban Nhân Dân\b", "Ủy ban nhân dân", text)
    text = re.sub(r"\bT(?:òa|oà) Án Nhân Dân\b", "Tòa án nhân dân", text)
    for unit in _UNIT_WORDS:
        text = re.sub(rf"\b{unit}\b(?= \S)", unit.lower(), text)
    return text


def _same_court(a: str, b: str) -> bool:
    # Cùng một Tòa án ghi kèm hay không kèm tỉnh: khối đầu bản án in tách dòng nên hai cách đều gặp → không soát.
    return a.startswith(b) or b.startswith(a)


UNITS = (
    Unit("khai_tu", "Giấy khai tử của vợ / chồng: số, ngày, cơ quan đăng ký",
         (Field(DEATH_FIELDS[0], "số đăng ký khai tử", "code"),
          Field(DEATH_FIELDS[1], "ngày đăng ký khai tử dd/mm/yyyy", "date"),
          Field(DEATH_FIELDS[2], "cơ quan đăng ký khai tử, chép đủ cấp như giấy", "free", canon=_authority))),
    Unit("ly_hon", "Bản án / quyết định ly hôn: số, ngày, Tòa án",
         (Field(DIVORCE_FIELDS[0], "số bản án / quyết định ly hôn", "code"),
          Field(DIVORCE_FIELDS[1], "ngày ban hành dd/mm/yyyy", "date"),
          Field(DIVORCE_FIELDS[2], "Tòa án ban hành", "free", canon=_authority, same=_same_court))),
)
_UNIT_BY_MATTER = {"khai_tu": UNITS[0], "ly_hon": UNITS[1]}


_PAGE_DATE = Field("ngay", "ngày", "date")


def pages(case: Case) -> list[dict]:
    """Các trang có dấu vết khai tử / ly hôn: {doc, text}."""
    out = []
    for index, document in enumerate(case.documents, start=1):
        for text in _PAGE_BREAK_RE.split(str(document.get("text") or "")):
            if text.strip() and _PAGE_HINT_RE.search(fold(text)):
                out.append({"doc": index, "text": text.strip()})
    return out[:_MAX_PAGES]


def _death_kind(page_text: str, original_number: bool = False) -> str:
    """Loại tờ giấy khai tử: "ban_sao" (bản sao trích lục), "bao_tu" (giấy báo tử, không phải giấy đăng ký khai tử),
    "ban_chinh" (trích lục bản chính, giấy chứng tử). ``original_number``: cờ đơn vị lấy số gốc kể cả bản sao → bản
    sao xếp như bản chính."""
    if mapper.is_death_copy(page_text):
        return "ban_chinh" if original_number else "ban_sao"
    title = mapper._DEATH_TITLE_RE.search(page_text)
    return "bao_tu" if title and fold(title.group(0)) == "giay bao tu" else "ban_chinh"


def _rank(matter: str, source: str, page_text: str, original_number: bool = False) -> int:
    if matter == "khai_tu" and source != "nhac_lai":
        return _DEATH_RANKS.get((_death_kind(page_text, original_number), source), 0)
    return _RANKS.get((matter, source), 0)


def _text(value) -> str:
    text = " ".join(str(value or "").split())
    return "" if text.casefold() in ("null", "none") else text


def _line_with(page_text: str, record: dict) -> str:
    """Dòng thật trên trang chứa số (hoặc ngày) của bộ — dùng làm dòng chứng cứ nguyên văn."""
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    claimed = alnum(record["line"])
    if claimed:
        for line in lines:
            if claimed == alnum(line):
                return line
    needle = alnum(record["number"])
    if len(needle) >= 2:
        hits = [line for line in lines if needle in alnum(line)]
        # Số gốc ngắn ("08") có thể nằm trong số của bản trích lục: ưu tiên dòng đúng loại nguồn.
        body = [line for line in hits if "dang ky khai tu" in fold(line) or re.match(r"(cap )?so\b", fold(line))]
        pick = (body[-1:] if record["source"] == "dang_ky_goc" else hits[:1]) or hits[:1]
        if pick:
            return pick[0]
    parsed = parse_date(record["date"])
    for line in lines if parsed else []:
        found = re.findall(r"(\d{1,2})\s*(?:[/.\-]|tháng)\s*(\d{1,2})\s*(?:[/.\-]|năm)\s*(\d{4})", line)
        if any((int(d), int(m), int(y)) == (parsed.day, parsed.month, parsed.year) for d, m, y in found):
            return line
    return ""


async def _read_page(page: dict, title: str, original_number: bool = False) -> list[dict]:
    raw = await client.chat(
        [{"role": "system", "content": _PAGE_PROMPT.format(title=title)},
         {"role": "user", "content": f"Chữ OCR của trang giấy:\n\n{page['text']}"}],
        max_tokens=_MAX_TOKENS, temperature=0, enable_thinking=settings.agent_reasoning,
        purpose="thanh_tra.giay_ho_tich",
    )
    sets = engine.parse_json(raw).get("bo")
    records = []
    for item in sets if isinstance(sets, list) else []:
        if not isinstance(item, dict):
            continue
        key = (_text(item.get("viec")), _text(item.get("nguon")))
        date = _text(item.get("ngay"))
        # Ngày model trả phải có thật trên trang: giấy không ghi ngày thì model đôi khi tự đặt một ngày giữ chỗ.
        on_page = bool(parse_date(date)) and bool(locate(_PAGE_DATE, date, [{"text": page["text"]}]))
        record = {"matter": key[0], "source": key[1], "rank": _rank(*key, page["text"], original_number),
                  "kind": _death_kind(page["text"], original_number), "number": _text(item.get("so")),
                  "date": date if on_page else "", "agency": _tidy_agency(_text(item.get("co_quan"))),
                  "people": _text(item.get("nguoi")), "gender": fold(_text(item.get("gioi_tinh"))),
                  "line": _text(item.get("dong")), "doc": page["doc"], "page": page["text"]}
        if not record["rank"] or not (record["number"] or record["date"]):
            continue
        record["line"] = _line_with(page["text"], record)
        if record["line"] and not _mislabeled_registration(page["text"], record):
            records.append(record)
    return records + _registration_by_code(page, records, original_number)


# Cụm định nghĩa của dòng đăng ký khai tử gốc (xem _PAGE_PROMPT): số / ngày có thể xuống một hai dòng dưới cụm đó. Không
# dùng "quyển số": dòng giấy báo tử của bệnh viện cũng ghi quyển số.
_REGISTRATION_MARK_RE = re.compile(r"dang ky khai tu|noi ghi|cap so|ngay[\s,]*(?:thang[\s,]*nam[\s,]*)?dang ky")


def _mislabeled_registration(page_text: str, record: dict) -> bool:
    """Bộ khai tử model gắn nhãn "dang_ky_goc" mà dòng chứng cứ (và hai dòng ngay trên) không có cụm định nghĩa của dòng
    đăng ký gốc — vd dòng "Giấy báo tử ... do bệnh viện cấp" là giấy căn cứ để đăng ký → nhãn sai, bỏ bộ."""
    if record["matter"] != "khai_tu" or record["source"] != "dang_ky_goc":
        return False
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    at = next((index for index, line in enumerate(lines) if line == record["line"]), None)
    window = lines[max(0, at - 2): at + 1] if at is not None else [record["line"]]
    return not any(_REGISTRATION_MARK_RE.search(fold(line)) for line in window)


def _registration_by_code(page: dict, records: list[dict], original_number: bool = False) -> list[dict]:
    """Dòng đăng ký gốc của trích lục khai tử có khuôn cố định nên mã cũng đọc được: model đọc sót dòng đó (chỉ lập bộ
    đầu giấy) thì bổ sung bộ do mã đọc, để thứ bậc nguồn không bị lệch vì một lượt đọc thiếu."""
    if any(record["source"] == "dang_ky_goc" for record in records):
        return []
    found = mapper._death_registration(page["text"])
    if not found.get("DeathCert_Number"):
        return []
    date = mapper._full_date(found.get("DeathCert_Date"))
    # Người chết của trang lấy theo bộ đầu giấy model đã lập, để bước lọc "giấy của ai" vẫn áp dụng.
    header = next((record for record in records if record["matter"] == "khai_tu" and record["source"] == "dau_giay"), {})
    record = {"matter": "khai_tu", "source": "dang_ky_goc", "rank": _rank("khai_tu", "dang_ky_goc", page["text"], original_number),
              "kind": _death_kind(page["text"], original_number),
              "number": found["DeathCert_Number"], "date": date, "agency": found.get("DeathCert_Agency", ""),
              "people": header.get("people", ""), "gender": header.get("gender", ""), "line": "", "doc": page["doc"],
              "page": page["text"]}
    record["line"] = _line_with(page["text"], record)
    return [record] if record["line"] else []


def _near_name(left: str, right: str) -> bool:
    a, b = fold(left), fold(right)
    return bool(a and b) and (a == b or difflib.SequenceMatcher(None, a, b).ratio() >= _NEAR_NAME_RATIO)


def _of_subject(record: dict, case: Case) -> bool:
    """Giấy khai tử thật phải là của người KHÁC người được cấp và khác giới (vợ / chồng); bản án thật phải có người được
    cấp là một bên. Trang không ghi tên thì không loại. Dòng nhắc lại trên tờ khai là lời khai của chính hồ sơ."""
    if record["source"] == "nhac_lai":
        return True
    subject = str(case.values.get("NguoiDuocCap_HoTen") or "")
    parties = [name.strip() for name in re.split(r"[;,]", record["people"]) if name.strip()]
    if record["matter"] == "khai_tu":
        gender = fold(case.values.get("NguoiDuocCap_GioiTinh"))
        if record["gender"] in ("nam", "nu") and gender in ("nam", "nu") and record["gender"] == gender:
            return False
        return not any(_near_name(name, subject) for name in parties)
    return not (subject and parties) or any(_near_name(name, subject) for name in parties)


def _on_docket_line(case: Case, number) -> bool:
    """Số đang xét chỉ xuất hiện trên dòng "thụ lý số ..." của hồ sơ (số thụ lý vụ án, không phải số bản án)."""
    needle = alnum(number)
    lines = [fold(line) for document in case.documents for line in str(document.get("text") or "").splitlines()
             if len(needle) >= 2 and re.search(rf"(?<!\d){re.escape(needle)}(?!\d)", alnum(line))]
    return bool(lines) and all("thu ly" in line for line in lines)


def _value(record: dict, field: str) -> str:
    return record["number" if field.endswith("Number") else "date" if field.endswith("Date") else "agency"]


def best_set(records: list[dict]) -> tuple[dict, dict] | None:
    """Bộ bậc cao nhất của một việc + giá trị từng field. Bộ đó thiếu field nào thì bù bằng bậc kế tiếp của CHÍNH tờ
    giấy đó, rồi mới tới dòng nhắc lại trên tờ khai. Hai bộ cùng bậc cao nhất ghi số khác nhau → không chọn được."""
    if not records:
        return None
    top_rank = max(record["rank"] for record in records)
    top = [record for record in records if record["rank"] == top_rank]
    if len({alnum(record["number"]) for record in top if record["number"]}) > 1:
        return None
    best = max(top, key=lambda record: sum(bool(record[key]) for key in ("number", "date", "agency")))
    lower = sorted((record for record in records if record["rank"] < top_rank
                    and (record["page"] is best["page"] or record["source"] == "nhac_lai")),
                   key=lambda record: -record["rank"])
    merged = {}
    for key in ("number", "date", "agency"):
        merged[key] = best[key] or next((record[key] for record in lower if record[key]), "")
    return best, merged


def _sources(records: list[dict], spec: Field, value) -> list[dict]:
    key = compare_key(spec, value)
    return [record for record in records if key is not None and compare_key(spec, _value(record, spec.name)) == key]


def _label(record: dict) -> str:
    if record["matter"] == "khai_tu" and (record.get("kind"), record["source"]) in _SOURCE_LABELS:
        return _SOURCE_LABELS[(record["kind"], record["source"])]
    return _SOURCE_LABELS[(record["matter"], record["source"])]


def _finding(unit: Unit, records: list[dict], case: Case) -> Finding | None:
    chosen = best_set(records)
    if not chosen:
        return None
    best, merged = chosen
    number, date, agency = unit.fields
    proposed = {spec.name: merged[key] for spec, key in zip(unit.fields, ("number", "date", "agency")) if merged[key]}
    current = {spec.name: case.values.get(spec.name) for spec in unit.fields if not is_empty(case.values.get(spec.name))}
    if not proposed.get(number.name) and current.get(number.name):
        return None  # giấy không ghi số thì không có căn cứ đổi cả bộ
    reasons = []
    ours_number, ours_date = current.get(number.name), current.get(date.name)
    same_number = bool(ours_number) and compare_key(number, ours_number) == compare_key(number, proposed.get(number.name))
    if ours_number and not same_number:
        traced = _sources(records, number, ours_number)
        if traced and all(record["rank"] < best["rank"] for record in traced):
            reasons.append(f"số của A nằm ở {_label(traced[0])}, bậc thấp hơn {_label(best)} của B")
        elif not traced and best["rank"] >= _PRIMARY_RANK and _on_docket_line(case, ours_number):
            reasons.append('số của A nằm ở dòng "thụ lý số" (số thụ lý vụ án), không phải số của văn bản')
    date_differs = bool(ours_date and proposed.get(date.name)) and (
        compare_key(date, ours_date) != compare_key(date, proposed[date.name]))
    if date_differs:
        traced = [record for record in _sources(records, date, ours_date) if record is not best]
        if traced and same_number:
            reasons.append(f"A ghép số của {_label(best)} với ngày của {_label(traced[0])} (số này ngày kia)")
        elif traced and all(record["rank"] < best["rank"] for record in traced):
            reasons.append(f"ngày của A nằm ở {_label(traced[0])}, bậc thấp hơn {_label(best)} của B")
    # Ô cơ quan: lượt trích được phép viết gọn tên cơ quan, còn khối đầu giấy và chữ tờ khai thì hay bị OCR đọc lệch.
    # Chỉ đổi cơ quan đang có khi B chép từ dòng đăng ký gốc, hoặc B là chính cơ quan đó ghi ĐỦ cấp hơn; ngoài hai
    # trường hợp đó giữ cơ quan của lượt trích.
    ours_agency = current.get(agency.name)
    if ours_agency and proposed.get(agency.name):
        ours_key, theirs_key = compare_key(agency, ours_agency), compare_key(agency, proposed[agency.name])
        fuller = theirs_key != ours_key and theirs_key.startswith(ours_key)
        if ours_key != theirs_key and not (best["source"] == "dang_ky_goc" or fuller):
            proposed[agency.name] = ours_agency
        elif ours_key != theirs_key and same_number and not date_differs:
            reasons.append(f"A và B cùng số, cùng ngày; cơ quan của B chép theo {_label(best)}"
                           + (", ghi đủ cấp hơn A" if fuller else ""))
    # Bộ của B thiếu field nào thì giữ giá trị lượt trích của field đó: đổi cả cụm không được làm trống ô đang có.
    values = {**{name: value for name, value in current.items() if name not in proposed}, **proposed}
    owner = _OWNERS[2] if best["source"] == "nhac_lai" else _OWNERS[0] if best["matter"] == "khai_tu" else _OWNERS[1]
    if best["matter"] == "khai_tu" and mapper.death_original_number(case.options) and mapper.is_death_copy(best["page"]):
        reasons.append("cấu hình đơn vị: bản sao vẫn lấy số gốc")
    evidence = (f"B là bộ ở {_label(best)}: số {merged['number'] or '(không ghi)'}, ngày {merged['date'] or '(không ghi)'}, "
                f"cơ quan {merged['agency'] or '(không ghi)'}" + ("; " + "; ".join(reasons) if reasons else ""),)
    return Finding(INSPECTOR, unit, values, best["line"], best["doc"],
                   f"bộ bậc cao nhất của hồ sơ: {_label(best)}", owner, backed=bool(reasons), evidence=evidence)


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    original_number = mapper.death_original_number(case.options)
    read = await asyncio.gather(*(_read_page(page, title, original_number) for page in pages(case)),
                                return_exceptions=True)
    records = [record for answer in read if not isinstance(answer, BaseException) for record in answer
               if _of_subject(record, case)]
    findings = []
    for matter, unit in _UNIT_BY_MATTER.items():
        finding = _finding(unit, [record for record in records if record["matter"] == matter], case)
        if finding:
            findings.append(finding)
    return findings


INSPECTOR = Inspector("giay_ho_tich", "GIẤY KHAI TỬ và BẢN ÁN LY HÔN kèm hồ sơ", UNITS, RULES, owners=_OWNERS,
                      accepted=_OWNERS[:3], find=find)
