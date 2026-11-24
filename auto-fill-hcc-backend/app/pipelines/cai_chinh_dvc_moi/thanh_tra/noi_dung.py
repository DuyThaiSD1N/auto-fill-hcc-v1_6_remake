"""Thanh tra NỘI DUNG ĐỀ NGHỊ: nội dung thay đổi, lý do, loại việc đăng ký, tên giấy tờ hộ tịch đã đăng ký.

Cách kiểm riêng: một lượt model đọc lại TỜ KHAI (không có thì BẢN CAM ĐOAN) và viết lại các mục thành câu đủ nghĩa.
Ô chữ tự do thì hai lần viết gần như luôn khác chữ nhau, nên giá trị lượt trích chỉ bị đem ra toà khi MÃ chỉ ra được
lỗi của nó: mục "từ A thành A", lẫn nhãn / câu lý do vào nội dung, giá trị cũ / mới không có trên giấy nào, lý do là
câu cam đoan in sẵn, tên giấy trái dòng tờ khai ghi. Không có tờ khai lẫn bản cam đoan thì không soát:
cán bộ tự ghi các ô này.
"""

import re
import unicodedata

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, alnum, fold

from ..process.mapper import _FROM_TO_RE, _GIAY_TO_OPTIONS, _VIEC_OPTIONS, _drop_no_change, _option
from ..process.reason import _SUBJECT_ANCHOR_RE, section

RULES = """
<nguon>
CHỈ lấy từ TỜ KHAI thay đổi, cải chính (dòng "Đề nghị cơ quan đăng ký việc", "Đã đăng ký ... tại", "Nội dung",
"Lý do"); không có tờ khai thì từ BẢN CAM ĐOAN. Giấy hộ tịch, CCCD, giấy căn cứ chỉ dùng để ĐỐI CHIẾU giá trị cũ /
mới. Không có cả tờ khai lẫn bản cam đoan → mọi mục null.
</nguon>

<noi_dung>
- Gồm các mục thay đổi, nối bằng dấu chấm phẩy. Mỗi mục là một câu đủ nghĩa: "<Cải chính / Thay đổi / Bổ sung>
  <thông tin> của <ai> từ <giá trị cũ> thành <giá trị mới>"; "của <ai>" (người cha, người mẹ, vợ, chồng...) chỉ ghi
  khi tờ khai nêu. Bổ sung thông tin còn trống thì "Bổ sung <thông tin>: <giá trị>".
- Giá trị cũ = giá trị ĐANG GHI trên giấy hộ tịch cần sửa; giá trị mới = giá trị đúng theo tờ khai / giấy căn cứ.
  Giấy cần sửa có trong hồ sơ thì giá trị cũ phải đúng chữ in trên giấy đó; chữ viết tay trên tờ khai OCR đọc lệch
  thì lấy theo chữ in của giấy hộ tịch / giấy căn cứ. Giá trị mới là họ tên một người có giấy in của cơ quan (trích lục
  khai tử, giấy khai sinh, CCCD của chính người đó) → đúng chữ in trên giấy đó. So cả dấu thanh: hai cách viết chỉ
  khác dấu là hai tên khác nhau, chọn đúng cách in. Tín hiệu mã báo tên của A chỉ lệch dấu với chữ in trên giấy, B
  theo chữ in → chọn B.
- Họ tên ở hai bên viết ĐỦ họ, chữ đệm, tên — kể cả khi chỉ sửa một chữ.
- BỎ mục mà giá trị cũ và mới giống hệt nhau; bỏ nhãn "Lý do", câu cam đoan, phần lý do lạc vào nội dung.
- Câu trên giấy đã đủ nghĩa thì GIỮ NGUYÊN câu đó, chỉ sửa lỗi OCR ở từ thông thường (vd "nam sinh" → "năm sinh");
  không đặt dấu ngoặc kép.
</noi_dung>

<ly_do>
Câu ngắn nêu VÌ SAO cần sửa theo dòng "Lý do" (vd sai sót khi đăng ký, khai nhầm, không khớp giấy tờ tùy thân).
KHÔNG lấy câu "Tôi cam đoan ..." in sẵn, dòng "Đề nghị cơ quan ...", không chép lại nội dung. Không có tờ khai mà có
bản cam đoan → câu ngắn tóm căn cứ trong bản cam đoan. Dòng "Lý do" trống và không có bản cam đoan → null.
</ly_do>

<viec>
Một trong "Cải chính", "Thay đổi", "Bổ sung", "Xác định lại dân tộc": theo dòng "Đề nghị cơ quan đăng ký việc ..."
của tờ khai khi dòng đó nêu một trong bốn việc; dòng đó trống → theo bản chất nội dung (sai sót → Cải chính; theo
nguyện vọng → Thay đổi; ghi thêm thông tin còn trống → Bổ sung; "Xác định lại dân tộc" CHỈ khi nội dung là dân tộc).
</viec>

<loai_giay>
Một trong "khai sinh", "khai tử", "kết hôn", "giám hộ", "giám sát giám hộ", "nhận cha mẹ con": theo dòng "Đã đăng
ký <loại> tại ..." của tờ khai, hoặc loại của chính giấy hộ tịch cần sửa có trong hồ sơ.
</loai_giay>
"""


def _text_key(value) -> str:
    return alnum(value)


def _spelled(value) -> str:
    """Chữ cái + chữ số GIỮ dấu: "Tạm" / "Tâm" là hai giá trị khác nhau."""
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFC", str(value or "")).casefold())


def _viec_key(value) -> str:
    return _option(value, _VIEC_OPTIONS) or alnum(value)


def _giay_key(value) -> str:
    return _option(value, _GIAY_TO_OPTIONS) or alnum(value)


UNITS = (
    Unit("noi_dung", "Nội dung đề nghị thay đổi, cải chính, bổ sung",
         # So GIỮ dấu: hai cách viết tên chỉ khác dấu là hai tên khác nhau (vụ chữ in của tên mới mở được).
         (Field("NoiDung", "các mục thay đổi, mỗi mục một câu đủ nghĩa", "free", canon=_spelled),)),
    Unit("ly_do", "Lý do", (Field("LyDo", "câu ngắn nêu lý do", "free", canon=_text_key),)),
    Unit("viec", "Loại việc đăng ký",
         (Field("ViecDangKy", '"Cải chính" / "Thay đổi" / "Bổ sung" / "Xác định lại dân tộc"', "free",
                canon=_viec_key),)),
    Unit("loai_giay", "Tên giấy tờ hộ tịch đã đăng ký",
         (Field("HoSo_LoaiGiayTo", '"khai sinh" / "khai tử" / "kết hôn" / "giám hộ" / "giám sát giám hộ" / '
                                   '"nhận cha mẹ con"', "free", canon=_giay_key),)),
)

_OWNERS = ("tờ khai thay đổi, cải chính", "bản cam đoan", "giấy hộ tịch", "giấy khác")
_COMMITMENT_RE = re.compile(r"ban cam doan|cam doan")
_BOILERPLATE_RE = re.compile(r"toi cam doan|chiu trach nhiem truoc phap luat|de nghi co quan|noi dung khai tren")
_REASON_LABEL_RE = re.compile(r"\bly do\b")
_REGISTERED_LINE_RE = re.compile(r"đã\s*(?:được\s*)?đăng\s*ký(.*)", re.IGNORECASE)


def _has_source(case: Case) -> bool:
    """Hồ sơ có tờ khai (khối "cho người có tên dưới đây") hoặc bản cam đoan."""
    text = "\n".join(str(document.get("text") or "") for document in case.documents)
    return bool(_SUBJECT_ANCHOR_RE.search(text)) or bool(_COMMITMENT_RE.search(fold(text)))


def _items(text) -> list[tuple[str, str]]:
    out = []
    for part in str(text or "").split(";"):
        match = _FROM_TO_RE.search(part.strip().rstrip("."))
        if match:
            out.append((match.group(1), match.group(2)))
    return out


def _word_key(word: str) -> str:
    """Khóa một từ: bỏ dấu, bỏ dấu câu; số bỏ chữ số 0 đứng đầu ("03" / "3")."""
    key = re.sub(r"[^0-9a-z]+", "", fold(word))
    return key.lstrip("0") or key if key.isdigit() else key


def _off_paper(text, case: Case) -> list[str]:
    """Giá trị cũ / mới của các mục "từ … thành …" có SỐ hoặc TÊN RIÊNG (chữ viết hoa đầu) không xuất hiện trên giấy
    nào của hồ sơ. Chữ thường người viết tự thêm ("tuổi", "tương đương") không xét."""
    paper = " ".join(str(document.get("text") or "") for document in case.documents)
    words = {_word_key(word) for word in re.split(r"[\s/.,;:()\-]+", paper)}
    out = []
    for value in (value for item in _items(text) for value in item):
        tokens = [token for token in re.split(r"[\s/.,;:()\-]+", value)
                  if token and (any(ch.isdigit() for ch in token) or token[0].isupper())]
        if any(_word_key(token) and _word_key(token) not in words for token in tokens):
            out.append(value)
    return out


def _line_value(case: Case, pattern: re.Pattern) -> str:
    for document in case.documents:
        for line in str(document.get("text") or "").splitlines():
            match = pattern.search(line)
            if match and match.group(1).strip(" .:…()0123456789"):
                return match.group(1)
    return ""


def faults(unit: Unit, ours, theirs, case: Case) -> list[str]:
    """Lỗi của giá trị lượt trích (A) mà MÃ chỉ ra được, so với giá trị thanh tra (B)."""
    out = []
    if unit.key == "noi_dung":
        same = [old for old, new in _items(ours) if _spelled(old) and _spelled(old) == _spelled(new)]
        if same and not any(_spelled(old) == _spelled(new) for old, new in _items(theirs)):
            out.append(f'A có mục giá trị cũ và mới giống hệt nhau ("{same[0][:40]}")')
        if _REASON_LABEL_RE.search(fold(ours)) and not _REASON_LABEL_RE.search(fold(theirs)):
            out.append("A lẫn nhãn / phần lý do vào nội dung")
        missing = _off_paper(ours, case)
        if missing and not _off_paper(theirs, case):
            out.append(f'giá trị "{missing[0][:40]}" của A không có trên giấy nào, mọi giá trị của B đều có')
    elif unit.key == "ly_do":
        if _BOILERPLATE_RE.search(fold(ours)) and not _BOILERPLATE_RE.search(fold(theirs)):
            out.append("A là câu cam đoan / dòng đề nghị in sẵn, không phải lý do")
    elif unit.key == "loai_giay":
        # Loại việc không soát theo dòng (4): cán bộ hay chốt theo bản chất nội dung dù dòng đó ghi việc khác.
        line = _line_value(case, _REGISTERED_LINE_RE)
        want = _option(line, _GIAY_TO_OPTIONS)
        if want and _option(theirs, _GIAY_TO_OPTIONS) == want and _option(ours, _GIAY_TO_OPTIONS) != want:
            out.append(f'dòng tờ khai "{line.strip()[:60]}" ghi đúng giá trị của B, không phải của A')
    return out


def _printed_names(case: Case) -> list[tuple[str, str, int]]:
    """(cụm chữ IN HOA ≥2 tiếng, dòng, số tài liệu): họ tên in máy trên giấy hộ tịch / giấy căn cứ."""
    out = []
    for index, document in enumerate(case.documents, start=1):
        for line in str(document.get("text") or "").splitlines():
            run: list[str] = []
            for word in re.split(r"[\s,.:;()\-]+", unicodedata.normalize("NFC", line)) + [""]:
                if word.isalpha() and word.isupper():
                    run.append(word)
                    continue
                if len(run) >= 2:
                    out.append((" ".join(run), line.strip(), index))
                run = []
    return out


def _printed_hit(value: str, printed: list[tuple[str, str, int]]) -> tuple[str, str, int] | None:
    """Cách viết in hoa DUY NHẤT trên giấy trùng ``value`` khi bỏ dấu mà khác dấu; None khi chính ``value`` có bản in,
    không có hoặc có nhiều cách viết in."""
    words = value.split()
    if len(words) < 2 or not all(word[:1].isupper() for word in words):
        return None
    hits = {}
    for run, line, index in printed:
        parts = run.split()
        for start in range(len(parts) - len(words) + 1):
            window = " ".join(parts[start:start + len(words)])
            if fold(window) == fold(value):
                hits.setdefault(window, (line, index))
    if len(hits) != 1 or unicodedata.normalize("NFC", value).upper() in hits:
        return None
    window, (line, index) = next(iter(hits.items()))
    return (window if value.isupper() else " ".join(word.capitalize() for word in window.split())), line, index


def _shared_kept(old: str, new: str, old_fixed: str, new_fixed: str) -> bool:
    """Tiếng hai bên cùng ghi (trùng khi bỏ dấu, trùng cả dấu) phải vẫn trùng sau khi thay."""
    before = {fold(w): w for w in old.split()}
    after_old = {fold(w): w for w in old_fixed.split()}
    after_new = {fold(w): w for w in new_fixed.split()}
    return all(after_old.get(key) == after_new.get(key)
               for key, word in before.items() if word in new.split())


def _printed_spelling(text, case: Case) -> tuple[str, str, int, list[str]] | None:
    """Họ tên trong mục "từ … thành …" (chữ viết tay trên tờ khai / cam đoan) chỉ lệch DẤU với đúng MỘT cách viết in hoa
    trên giấy, còn chính nó không có bản in nào → thay bằng chữ in. Mục mà việc sửa chính là đổi dấu (hai bên trùng khi
    bỏ dấu) không đụng; thay làm lệch tiếng chung của hai bên thì bỏ. Trả (nội dung đã thay, dòng in, tài liệu, ghi chú)."""
    printed = _printed_names(case)
    out, quote, doc, notes = str(text or ""), "", 0, []
    for old, new in _items(text):
        if fold(old) == fold(new):
            continue
        hit_old, hit_new = _printed_hit(old, printed), _printed_hit(new, printed)
        old_fixed = hit_old[0] if hit_old else old
        new_fixed = hit_new[0] if hit_new else new
        if not (hit_old or hit_new) or not _shared_kept(old, new, old_fixed, new_fixed):
            continue
        for value, hit in ((old, hit_old), (new, hit_new)):
            if hit:
                out = out.replace(value, hit[0], 1)
                quote, doc = quote or hit[1], doc or hit[2]
                notes.append(f'"{value}" chỉ lệch dấu với chữ in "{hit[0]}" trên giấy, cách viết của A không có bản in nào')
    return (out, quote, doc, notes) if notes else None


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    if not _has_source(case):
        return []
    # Nội dung dựng từ bản cam đoan thì mapper đã bỏ mục "từ A thành A" trước khi điền: xét lỗi trên đúng giá trị form
    # sẽ hiện, không trên bản thô của lượt trích.
    from_commitment = "thông tin cần sửa" in section(case.context, "viec_dang_ky").lower()
    out = []
    for finding in await engine.llm_findings(inspector, case, title):
        spec = finding.unit.fields[0]
        ours = case.values.get(spec.name)
        if spec.name == "NoiDung" and from_commitment:
            ours = _drop_no_change(ours)
        reasons = faults(finding.unit, ours, finding.values.get(spec.name), case)
        out.append(Finding(finding.inspector, finding.unit, finding.values, finding.quote, finding.doc, finding.note,
                           finding.owner, backed=bool(reasons), evidence=tuple(reasons)))
    # Hai lượt model cùng chép tên theo chữ viết tay / cam đoan dù giấy hộ tịch in rõ: mã thay theo chữ in.
    ours = case.values.get("NoiDung")
    printed = None if any(f.unit.key == "noi_dung" and f.backed for f in out) else _printed_spelling(ours, case)
    if printed:
        fixed, quote, doc, notes = printed
        out = [f for f in out if f.unit.key != "noi_dung"]
        out.append(Finding(inspector, UNITS[0], {"NoiDung": fixed}, quote, doc, "họ tên in trên giấy hộ tịch / giấy căn cứ",
                           _OWNERS[0], backed=True, evidence=tuple(notes)))
    return out


INSPECTOR = Inspector("noi_dung", "NỘI DUNG ĐỀ NGHỊ (nội dung, lý do, loại việc, tên giấy tờ)", UNITS, RULES,
                      owners=_OWNERS, accepted=_OWNERS[:2], find=find)
