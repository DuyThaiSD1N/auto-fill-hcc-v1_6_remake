"""Thanh tra GIẤY TỜ ĐĂNG KÝ: giấy hộ tịch cần sửa — nơi đăng ký gốc, số, quyển số, ngày đăng ký.

Cách kiểm riêng: mã chắt các dòng có thể mang thông tin đăng ký, model trả lời câu hỏi đóng trên đoạn hẹp đó.

Loại / tên giấy không soát ở đây: bước phân vai và mapper đã chốt theo mục yêu cầu của tờ khai.
"""

import re
from dataclasses import replace
from datetime import date

from app.config import settings
from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, alnum, fold, parse_date
from app.services.llm import client

from ..process.reason import holder_birth, labeled_value, name_match, requester_context, section

# Số của bản trích lục (bản sao) in ở đầu giấy: "<N>/TLKS-BS", "<N>/<năm>/TLKT-BS".
_COPY_NO_RE = re.compile(r"/\s*TL[A-ZĐ]{1,6}\s*-\s*BS\b", re.IGNORECASE)

RULES = """
<giay_can_cap>
Giấy hộ tịch cần sửa là giấy đã đăng ký trước đây của người có nội dung thay đổi, đúng loại ở dòng "Giấy hộ tịch cần
sửa" / "Giấy tờ hộ tịch đã đăng ký" của <phan_vai_da_xac_dinh>. Nguồn theo thứ tự: mục "Đã đăng ký ... tại ..." của
TỜ KHAI thay đổi, cải chính → CHÍNH giấy hộ tịch cùng loại và cùng người có nội dung thay đổi có trong hồ sơ. Giấy
khác loại hoặc của người khác (giấy khai sinh / khai tử của cha, mẹ kèm làm căn cứ) KHÔNG phải nguồn.
Nhận giấy khai sinh của người có nội dung thay đổi theo NGÀY / NĂM SINH và họ tên CHA, MẸ của người được khai sinh (các
dòng họ tên, ngày sinh cũng được chắt lọc), không chỉ theo họ tên: tên trên giấy có thể là tên CŨ đang xin cải chính
hoặc bị OCR đọc lệch. Giấy khai sinh có người được khai sinh sinh năm khác hẳn (của cha / mẹ) KHÔNG phải nguồn, kể cả
khi in mới, rõ chữ hơn. Giấy khai sinh mẫu cũ: số ở "Số...<N>" góc trên, ngày ở "Đăng ký ngày D tháng M năm Y", cơ
quan theo khối "ỦY BAN NHÂN DÂN / Xã, phường ... / Huyện, Quận ... / Tỉnh ..." đầu giấy.
Tiêu đề "### Tài liệu N — giấy khai sinh, người được khai sinh sinh ngày D" do mã đọc sẵn từ dòng ngày sinh của giấy:
"CÙNG năm sinh với người có nội dung thay đổi" → đó là giấy cần sửa, dù ngày lệch vài hôm hay họ tên trên giấy khác
họ tên người đó: hồ sơ cải chính HỌ TÊN thì giấy cần sửa ghi TÊN CŨ (giá trị "từ ..." của nội dung đề nghị), chữ viết
tay giấy cũ còn bị OCR đọc lệch — lấy số, ngày đăng ký, cơ quan của CHÍNH giấy đó. "KHÁC năm sinh" → giấy của người
khác, không lấy gì ở đó.
Tín hiệu mã "A lấy từ giấy khai sinh của người khác" → chọn B khi B là dòng của giấy đúng người.
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
    r"khai tu|chung thuc|ban sao|to khai|"
    # Dòng người đứng tên giấy (họ tên, ngày sinh, cha / mẹ): để model nhận giấy của đúng người.
    r"\bten\b|nam sinh|ngay sinh|nguoi me|nguoi cha|xa, phuong|huyen, quan|tinh, thanh pho")
# Dòng chú thích cuối mẫu ("(1) Ghi theo số trong Sổ ...") không mang giá trị, chỉ chiếm chỗ của dòng thật.
_FOOTNOTE_RE = re.compile(r"^\(\d\)\s*(ghi|tuy|truong hop|neu)")
_MAX_LINES = 100
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
            folded = fold(line.strip())
            if line.strip() and _CANDIDATE_LINE_RE.search(folded) and not _FOOTNOTE_RE.match(folded):
                out.append((index, line.strip()))
    return out[:_MAX_LINES]


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    """Agent chính tìm số / ngày / cơ quan giữa cả hồ sơ. Ở đây mã chắt sẵn các dòng ứng viên, model chỉ trả lời câu
    hỏi đóng "dòng số mấy" trên đoạn hẹp đó — dòng chứng cứ do mã cấp nên chắc chắn có thật."""
    lines = _candidate_lines(case)
    if not lines:
        return []
    listing, last = [], 0
    births = {index: _holder_birth(document.get("text")) for index, document in enumerate(case.documents, start=1)}
    born = parse_date(case.values.get("NguoiThayDoi_NgaySinh"))
    for number, (index, line) in enumerate(lines, start=1):
        if index != last:
            # Mã đọc sẵn ngày sinh của người được khai sinh để model nhận giấy của đúng người (tên có thể là tên cũ).
            note = ""
            if births.get(index):
                note = f" — giấy khai sinh, người được khai sinh sinh ngày {births[index].strftime('%d/%m/%Y')}"
                if born:
                    note += (" (CÙNG năm sinh với người có nội dung thay đổi)" if births[index].year == born.year
                             else " (KHÁC năm sinh với người có nội dung thay đổi: giấy của người khác)")
            listing.append(f"### Tài liệu {index}{note}")
            last = index
        listing.append(f"[{number}] {line}")
    task = _FIND_TASK.format(rules=RULES.strip(), owners="\n".join(f'- "{owner}"' for owner in _OWNERS))
    same_year = [index for index, birth in births.items() if birth and born and birth.year == born.year]
    if born and same_year:
        # Hồ sơ cải chính HỌ TÊN: giấy cần sửa ghi tên cũ nên model hay loại giấy đó vì "khác tên".
        task = (f"Đối chiếu của mã: Tài liệu {', '.join(map(str, same_year))} là giấy khai sinh có người được khai sinh "
                f"CÙNG năm sinh {born.year} với người có nội dung thay đổi. Họ tên trên giấy đó khác họ tên người này "
                f"KHÔNG phải lý do loại: đó thường là tên cũ đang xin cải chính hoặc chữ OCR đọc lệch.\n\n" + task)
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
    _back_other_holder(findings, case)
    # Giấy khai sinh có người được khai sinh sinh khác NĂM với người có nội dung thay đổi là giấy của người khác.
    findings = [finding for finding in findings
                if not (born and births.get(finding.doc) and births[finding.doc].year != born.year)]
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


_BIRTH_DATE_RE = re.compile(r"(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})")
_holder_birth = holder_birth


def _on_document(spec_key: str, ours, text: str) -> bool:
    if spec_key == "ngay_dang_ky":
        target = parse_date(ours)
        return bool(target) and any(parse_date(f"{d}/{m}/{y}") == target for d, m, y in _BIRTH_DATE_RE.findall(text))
    number = str(ours or "").strip()
    return bool(_register_no(number)) and bool(re.search(rf"(?<![\w/]){re.escape(number)}(?![\w/])", text))


def _back_other_holder(findings: list[Finding], case: Case) -> None:
    """A (số / ngày đăng ký lượt trích) chỉ có trên giấy khai sinh mà người được khai sinh sinh khác NĂM với người có
    nội dung thay đổi (giấy của cha / mẹ kèm làm căn cứ), còn B ở tài liệu khác → căn cứ mã cho B."""
    born = parse_date(case.values.get("NguoiThayDoi_NgaySinh"))
    if not born or "khai sinh" not in fold(case.values.get("HoSo_LoaiGiayTo")):
        return
    for index, finding in enumerate(findings):
        ours = case.values.get(finding.unit.fields[0].name)
        if finding.unit.key not in ("so", "ngay_dang_ky") or not ours:
            continue
        homes = [i for i, document in enumerate(case.documents, start=1)
                 if _on_document(finding.unit.key, ours, str(document.get("text") or ""))]
        if not homes or finding.doc in homes:
            continue
        holders = [_holder_birth(case.documents[i - 1].get("text")) for i in homes]
        if all(holder and holder.year != born.year for holder in holders):
            findings[index] = replace(finding, backed=True, evidence=tuple(finding.evidence) + (
                f"A lấy từ giấy khai sinh của người khác: người được khai sinh trên giấy đó sinh "
                f"{holders[0].strftime('%d/%m/%Y')}, người có nội dung thay đổi sinh {born.strftime('%d/%m/%Y')}",))


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
