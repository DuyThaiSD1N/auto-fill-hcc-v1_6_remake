"""Thanh tra GIẤY TỜ ĐĂNG KÝ: giấy hộ tịch cần sửa — nơi đăng ký gốc, số, quyển số, ngày đăng ký.

Cách kiểm riêng: mã chắt các dòng có thể mang thông tin đăng ký, model trả lời câu hỏi đóng trên đoạn hẹp đó.

Loại / tên giấy không soát ở đây: bước phân vai và mapper đã chốt theo mục yêu cầu của tờ khai.
"""

import re
from datetime import date

from app.config import settings
from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, alnum, fold, parse_date
from app.services.llm import client

from ..process.reason import labeled_value, name_match, requester_context, section

# Số của bản trích lục (bản sao) in ở đầu giấy: "<N>/TLKS-BS", "<N>/<năm>/TLKT-BS".
_COPY_NO_RE = re.compile(r"/\s*TL[A-ZĐ]{1,6}\s*-\s*BS\b", re.IGNORECASE)

RULES = """
<giay_can_cap>
Giấy hộ tịch cần sửa là giấy đã đăng ký trước đây của người có nội dung thay đổi, đúng loại ở dòng "Giấy hộ tịch cần
sửa" / "Giấy tờ hộ tịch đã đăng ký" của <phan_vai_da_xac_dinh>. Nguồn theo thứ tự: mục "Đã đăng ký ... tại ..." của
TỜ KHAI thay đổi, cải chính → CHÍNH giấy hộ tịch cùng loại và cùng người có nội dung thay đổi có trong hồ sơ. Giấy
khác loại hoặc của người khác (giấy khai sinh / khai tử của cha, mẹ kèm làm căn cứ) KHÔNG phải nguồn.
Trang CHỨNG THỰC ("Số chứng thực: ... quyển số ... SCT", ngày chứng thực) là sổ chứng thực → không lấy gì ở đó.
</giay_can_cap>

<tung_muc>
- Cơ quan đăng ký: chép ĐÚNG NGUYÊN chữ sau nhãn "Đã đăng ký tại" / "Đã được đăng ký ... tại" / "Đăng ký ...
  tại" / "Nơi đăng ký ..." / "Nơi ghi:", ĐỦ mọi cấp mà dòng đó ghi (xã / phường, huyện, tỉnh); giấy không có
  nhãn thì chép dòng cơ quan ở tiêu đề đầu văn bản hoặc khối ký tên cuối ("TM. UBND ..."). TRÍCH LỤC (bản sao)
  có dòng đăng ký gốc trong thân → cơ quan ở dòng đó, không phải cơ quan đầu giấy (nơi cấp bản trích lục). Không
  tự ghép chữ từ nhiều dòng, không đổi cách viết. Không lấy cơ quan cấp thẻ căn cước, không lấy nơi chứng thực.
  Hai bên cùng một cơ quan, chỉ khác số cấp hành chính ghi kèm (có / không huyện, tỉnh) → KHONG_DU_CAN_CU.
- Số đăng ký = số của LẦN ĐĂNG KÝ GỐC. TRÍCH LỤC (bản sao) in hai số: số của bản trích lục ở đầu giấy
  ("<N>/TL..-BS", "<N>/<năm>/TLKT-BS") và số đăng ký gốc ở dòng thân ngay dưới nơi đăng ký ("Đã được đăng ký ...
  tại: ..." rồi "Số: <N> ngày ..."; "Nơi ghi: ..., Sổ đăng ký ..., quyển số <Q>, số <N>, ngày ...") → số ở dòng
  thân; trích lục không có dòng thân đó mới lấy số đầu giấy. A là số "-BS" đầu giấy, B là số ở dòng đăng ký gốc
  của cùng giấy → chọn B. Giấy khai sinh / giấy chứng nhận kết hôn bản chính: dòng "Số: <mã>/<năm>" sát tiêu
  đề, GIỮ NGUYÊN mã và năm; giấy mẫu cũ là ô "Số:" ở góc trên bên phải, ngay dưới "Mẫu ..." và trên "Quyển số".
  Chỉ chép phần số / mã, không kèm chữ "Số", không kèm ngày. KHÔNG lấy số căn cước, số định danh, số trang, số chứng thực. Dòng "Số:" nằm dưới
  "Giấy CMND / Giấy tờ hợp lệ thay thế" / "Giấy tờ tùy thân" trong thân giấy là số thẻ của vợ / chồng / người
  đi khai. Ô đọc ra không phải chữ số → null, không lấy dòng "Số:" khác thay vào.
- Quyển số: chỉ khi nhãn "Quyển số" có giá trị thật ngay sau nhãn. "Số bộ", "sổ bộ", "số hiệu", "Trang số"
  không phải quyển số.
- Ngày đăng ký: dd/mm/yyyy. Trên tờ khai là ngày theo mẫu "ngày D tháng M năm Y" ngay trước "số ... Quyển số"
  trong mục "Đã đăng ký tại"; trên giấy hộ tịch là "Ngày, tháng, năm đăng ký" / "Ngày đăng ký" / ngày ở nơi ký.
  Trên TRÍCH LỤC (BẢN SAO), dòng "<nơi>, ngày ... tháng ... năm ..." ở ĐẦU giấy cạnh "Số: .../TL..-BS" là ngày
  cấp bản trích lục, KHÔNG phải ngày đăng ký; ngày đăng ký là ngày ở dòng "Số: ... ngày ... tháng ... năm ..."
  trong thân giấy (mục đã đăng ký tại). KHÔNG lấy ngày sinh, ngày chết, ngày cấp thẻ, ngày chứng thực, ngày làm
  tờ khai. Thiếu ngày, tháng hoặc năm → null.
</tung_muc>
"""


def _authority(value) -> str:
    return alnum(re.sub(r"\bubnd\b", "uy ban nhan dan", fold(value)))


_BIRTH_REGISTER_MAX_DAYS = 10 * 365
_FAR_FROM_BIRTH = "ngày đăng ký khai sinh cách ngày sinh quá xa, nhiều khả năng là ngày cấp bản sao"


def _register_no(value) -> str:
    # Cùng một số ghi kèm hay không kèm "/<năm>" ("34" / "34/2013") là một: cán bộ dùng cả hai cách, không soát.
    return alnum(re.sub(r"\s*/\s*(19|20)\d{2}\s*$", "", str(value or "").strip()))


UNITS = (
    Unit("co_quan", "Cơ quan đã đăng ký",
         (Field("HoSo_NoiDangKy", "cơ quan đã đăng ký sự kiện hộ tịch, chép đúng chữ trên giấy", "literal",
                canon=_authority),)),
    Unit("so", "Số đăng ký", (Field("HoSo_So", "số đăng ký", "code", canon=_register_no),)),
    Unit("quyen_so", "Quyển số", (Field("HoSo_QuyenSo", "quyển số", "code", canon=_register_no),)),
    Unit("ngay_dang_ky", "Ngày đăng ký", (Field("HoSo_NgayDangKy", "ngày đăng ký dd/mm/yyyy", "date"),)),
)


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def check(unit: Unit, values: dict, case: Case) -> str:
    if unit.key == "so":
        number = _digits(values.get("HoSo_So"))
        cards = {_digits(case.values.get("NguoiThayDoi_SoDinhDanh")), _digits(case.values.get("NguoiThayDoi_SoGiayTo")),
                 requester_context(case.options)[1]} - {""}
        if number and number in cards:
            return "số đăng ký trùng số CMND / căn cước trong hồ sơ"
        if re.search(r"\b(ngay|quyen|so|thang|nam)\b", fold(values.get("HoSo_So"))):
            return "số đăng ký lẫn chữ của nhãn khác (ngày / quyển số)"
    if unit.key == "ngay_dang_ky":
        registered = parse_date(values.get("HoSo_NgayDangKy"))
        born = parse_date(case.values.get("NguoiThayDoi_NgaySinh"))
        if registered and (registered > date.today() or (born and registered < born)):
            return "ngày đăng ký ở tương lai hoặc trước ngày sinh"
        if registered and registered in {born, parse_date(case.values.get("NguoiThayDoi_NgayCap"))}:
            return "ngày đăng ký trùng ngày sinh / ngày cấp thẻ"
        # Khai sinh đăng ký sau ngày sinh quá lâu: gần như luôn là ngày cấp bản trích lục / bản sao in đầu giấy.
        if (registered and born and "khai sinh" in fold(case.values.get("HoSo_LoaiGiayTo"))
                and (registered - born).days > _BIRTH_REGISTER_MAX_DAYS):
            return _FAR_FROM_BIRTH
    return ""


# Dòng có thể mang thông tin đăng ký hộ tịch: tiêu đề giấy, dòng số / quyển số, dòng ngày, dòng cơ quan. Lưới
# này chỉ để CHẮT LỌC dòng đưa cho model xem, không quyết định giá trị nào.
_CANDIDATE_LINE_RE = re.compile(
    r"\bso\b|quyen|ngay\s*\d|thang\s*\d|dang ky|uy ban nhan dan|ubnd|\btm\b|trich luc|khai sinh|ket hon|"
    r"khai tu|chung thuc|ban sao|to khai")
_MAX_LINES = 60
_FIND_MAX_TOKENS = 500

_FIND_SYSTEM = """<vai_tro>
Bạn là THANH TRA GIẤY HỘ TỊCH của dây chuyền soát hồ sơ {title}. Bạn không được xem kết quả của agent đã trích hồ
sơ. Bạn chỉ thấy các DÒNG đã chắt lọc từ OCR, mỗi dòng có số thứ tự trong ngoặc vuông; dòng không được chắt lọc
coi như không có.
</vai_tro>

<nguyen_tac>
- Với mỗi mục, chọn ĐÚNG MỘT dòng chứa thông tin đó của giấy hộ tịch cần sửa, trả số thứ tự dòng và giá trị
  chép đúng từng ký tự trong dòng (ngày đổi sang dd/mm/yyyy). Không ghép chữ từ hai dòng.
- Không dòng nào chứa thông tin của ĐÚNG giấy cần sửa → mục đó null. Thà thiếu còn hơn sai.
- Người có nội dung thay đổi và loại giấy theo đúng khối <phan_vai_da_xac_dinh> nếu có.
</nguyen_tac>"""

_FIND_TASK = """<nghiep_vu>
{rules}
</nghiep_vu>

<dinh_dang_tra_ve>
Chỉ trả MỘT object JSON phẳng, không markdown, đủ bốn khóa:
{{"co_quan": {{"dong": <số thứ tự dòng>, "value": "<cơ quan đã đăng ký>", "thuoc_ve": "<một lựa chọn>"}} hoặc null,
"so": {{"dong": <số>, "value": "<số đăng ký>", "thuoc_ve": "<một lựa chọn>"}} hoặc null,
"quyen_so": {{"dong": <số>, "value": "<quyển số>", "thuoc_ve": "<một lựa chọn>"}} hoặc null,
"ngay_dang_ky": {{"dong": <số>, "value": "dd/mm/yyyy", "thuoc_ve": "<một lựa chọn>"}} hoặc null}}
"thuoc_ve" BẮT BUỘC ở MỌI mục khác null = dòng đó thuộc giấy nào; chọn ĐÚNG MỘT lựa chọn dưới đây và chép nguyên
chữ, trả lời thật:
{owners}
</dinh_dang_tra_ve>"""


def _candidate_lines(case: Case) -> list[tuple[int, str]]:
    out = []
    for index, document in enumerate(case.documents, start=1):
        for line in str(document.get("text") or "").splitlines():
            if line.strip() and _CANDIDATE_LINE_RE.search(fold(line)):
                out.append((index, line.strip()))
    return out[:_MAX_LINES]


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    """Agent chính tìm số / ngày / cơ quan giữa cả hồ sơ. Ở đây mã chắt sẵn các dòng ứng viên, model chỉ trả lời câu
    hỏi đóng "dòng số mấy" trên đoạn hẹp đó — dòng chứng cứ do mã cấp nên chắc chắn có thật."""
    lines = _candidate_lines(case)
    if not lines:
        return []
    listing, last = [], 0
    for number, (index, line) in enumerate(lines, start=1):
        if index != last:
            listing.append(f"### Tài liệu {index}")
            last = index
        listing.append(f"[{number}] {line}")
    task = _FIND_TASK.format(rules=RULES.strip(), owners="\n".join(f'- "{owner}"' for owner in _OWNERS))
    raw = await client.chat(
        [{"role": "system", "content": _FIND_SYSTEM.format(title=title)},
         {"role": "user", "content": f"{case.context.strip()}\n\nCác dòng đã chắt lọc:\n" + "\n".join(listing)
                                     + f"\n\n{task}"}],
        max_tokens=_FIND_MAX_TOKENS, temperature=0, enable_thinking=settings.agent_reasoning,
        purpose="thanh_tra.giay_to",
    )
    answers = engine.parse_json(raw)
    findings = []
    for unit in UNITS:
        answer = answers.get(unit.key)
        if not isinstance(answer, dict) or answer.get("value") in (None, ""):
            continue
        try:
            index, line = lines[int(answer.get("dong")) - 1]
        except (TypeError, ValueError, IndexError):
            continue
        findings.append(Finding(INSPECTOR, unit, {unit.fields[0].name: answer["value"]}, line, index,
                                owner=str(answer.get("thuoc_ve") or "").strip()[:80],
                                **_code_basis(unit, case.values.get(unit.fields[0].name), answer["value"], line)))
    # Ngày đăng ký của một tài liệu cách ngày sinh quá xa → tài liệu đó không phải giấy hộ tịch cần sửa của người này
    # (giấy của người khác / bản sao cấp lại): bỏ mọi mục đọc từ tài liệu đó.
    wrong_docs = {finding.doc for finding in findings if finding.unit.key == "ngay_dang_ky"
                  and check(finding.unit, finding.values, case) == _FAR_FROM_BIRTH}
    return [finding for finding in findings if finding.doc not in wrong_docs and _of_subject(finding, case)]


_HOLDER_HEADING_RE = re.compile(
    r"^\s*(giay khai sinh|trich luc khai sinh|trich luc khai tu|giay chung nhan ket hon|trich luc ket hon|to khai)")
_NAME_LINE_RE = re.compile(r"^\s*(\d+\.\s*)?(ho,? chu dem,?( va)? ten|ho va ten|ho ten)")
# Nhãn họ tên của người KHÁC trên giấy khai sinh / khai tử: cha, mẹ, người đi khai, người yêu cầu.
_OTHER_ROLE_RE = re.compile(r"\b(me|cha|bo|di khai|yeu cau|nguoi khai)\b")


def _of_subject(finding: Finding, case: Case) -> bool:
    """Dòng đăng ký thuộc giấy của CHÍNH người có nội dung thay đổi: giấy khai sinh / khai tử thì người đứng tên giấy
    (khối người được khai sinh / người chết, không tính cha, mẹ, người đi khai) là người đó; giấy kết hôn thì người đó là
    vợ hoặc chồng. Tờ khai và giấy không nhận ra loại thì không chặn."""
    subject = (labeled_value(section(case.context, "nguoi_thay_doi"), "Họ tên")
               or str(case.values.get("NguoiThayDoi_HoTen") or ""))
    document = case.documents[finding.doc - 1] if 0 < finding.doc <= len(case.documents) else {}
    lines = [line.strip() for line in str(document.get("text") or "").splitlines() if line.strip()]
    at = next((i for i, line in enumerate(lines) if line == finding.quote.strip()), None)
    if not subject or at is None:
        return True
    heading = next((i for i in range(at, -1, -1) if _HOLDER_HEADING_RE.match(fold(lines[i]))), None)
    if heading is None or fold(lines[heading]).strip().startswith("to khai"):
        return True
    block = lines[heading + 1:at + 1]
    if "ket hon" in fold(lines[heading]):
        return any(name_match(subject, line) for line in block if re.search(r"\b(vo|chong)\b", fold(line)))
    for line in block:
        label = fold(line.split(":", 1)[0])
        if _NAME_LINE_RE.match(label) and not _OTHER_ROLE_RE.search(label):
            return bool(name_match(subject, line))
    return True


def _code_basis(unit: Unit, ours, theirs, line: str) -> dict:
    """Căn cứ bằng MÃ để thay lượt trích: A là số của bản trích lục ("-BS") còn B là số khác in trên dòng chứng cứ
    (dòng đăng ký gốc). Cơ quan ghi thêm / bớt cấp hành chính không phải căn cứ: cán bộ ghi cả hai cách."""
    if not ours or not theirs:
        return {}
    if unit.key == "so" and _COPY_NO_RE.search(str(ours)) and not _COPY_NO_RE.search(str(theirs)) and (
            alnum(theirs) and alnum(theirs) in alnum(line)):
        return {"backed": True, "evidence": ("A là số của bản trích lục in ở đầu giấy (dạng .../TL..-BS); B là số "
                                             "in trên dòng chứng cứ",)}
    return {}


_OWNERS = ("giấy hộ tịch cần sửa của người có nội dung thay đổi", "mục Đã đăng ký tại của tờ khai",
           "giấy hộ tịch khác loại hoặc của người khác", "trang chứng thực", "thẻ căn cước", "giấy khác")

INSPECTOR = Inspector("giay_to", "GIẤY TỜ ĐĂNG KÝ (giấy hộ tịch cần sửa)", UNITS, RULES, check, owners=_OWNERS,
                      accepted=_OWNERS[:2], find=find)
