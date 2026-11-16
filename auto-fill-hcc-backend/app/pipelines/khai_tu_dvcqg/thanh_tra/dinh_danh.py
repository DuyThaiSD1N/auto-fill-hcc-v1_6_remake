"""Thanh tra ĐỊNH DANH người được đăng ký khai tử: họ tên, ngày sinh, số định danh / số giấy tờ, ngày cấp.

Người mất đã do bước phân vai chốt; thanh tra không phân vai lại, chỉ soát cách ghi của chính người đó. Mã thuần:
1. Họ tên: mọi cách viết có nguyên văn trên giấy ngoài tờ khai — cùng chữ cái khác dấu, hoặc lệch một hai chữ cái trên
   trang mang số định danh của người mất — đếm số TRANG ghi; nhiều trang hơn thắng, bằng nhau theo hạng nguồn (giấy cơ
   quan cấp > tờ khai > giấy tự lập). Chặn bản rơi dấu / "Đ" thành "D"; chặn đổi chữ cái khi chữ cái của lượt trích đã
   có trên giấy ngoài tờ khai (cách viết khác chữ thường là người khác trong gia đình).
2. Số định danh, ngày sinh: vùng MRZ của thẻ mang họ tên (không dấu) của người mất, năm sinh mã hoá trong số khớp năm
   sinh in ở MRZ — ba dòng MRZ in máy đọc ổn định hơn chữ số trên tờ khai viết tay.
3. Ngày cấp: mặt sau thẻ (khối kết thúc bằng dải MRZ mang đúng số của người mất); ngày của lượt trích có trên tờ khai /
   giấy báo tử / trích lục khai tử thì giữ theo giấy đó.
"""

import re

from app.pipelines._shared.cccd import id_birth_year, mrz_records
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold, parse_date
from app.pipelines.khai_sinh_dang_ky_lai.process.reason import _mrz_card_backs
from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra.dinh_danh import close_name
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dinh_danh as base

from . import trang

_OWNER = "người được đăng ký khai tử (người chết)"
NAME, NUMBER, ID_NUMBER, BIRTH, ISSUE = (
    "NguoiMat_HoTen", "NguoiMat_SoDinhDanh", "NguoiMat_SoGiayTo", "NguoiMat_NgaySinh", "NguoiMat_NgayCap")

UNITS = (
    Unit("nguoi_mat.ho_ten", "Họ tên người chết", (Field(NAME, "họ, chữ đệm, tên", canon=trang.name_key),)),
    Unit("nguoi_mat.so_dinh_danh", "Số định danh người chết", (Field(NUMBER, "số định danh 12 chữ số", "code"),)),
    Unit("nguoi_mat.so_giay_to", "Số giấy tờ tùy thân người chết", (Field(ID_NUMBER, "số giấy tờ", "code"),)),
    Unit("nguoi_mat.ngay_sinh", "Ngày sinh người chết", (Field(BIRTH, "ngày sinh dd/mm/yyyy", "date"),)),
    Unit("nguoi_mat.ngay_cap", "Ngày cấp giấy tờ tùy thân người chết", (Field(ISSUE, "ngày cấp dd/mm/yyyy", "date"),)),
)
_UNIT = {unit.key.split(".")[1]: unit for unit in UNITS}
_DEATH_PAPERS = ("giay bao tu", "trich luc khai tu", "giay chung tu")

RULES = """
<ho_ten>
Mã đã đếm số TRANG giấy ghi nguyên văn từng cách viết họ tên người chết (dòng "TỔNG số trang" trong tín hiệu mã). B được
nhiều trang ghi hơn A → chọn B, kể cả khi A có giấy cơ quan cấp mà B không có; số trang bằng nhau thì theo hạng: giấy
cơ quan cấp (giấy báo tử, trích lục khai tử, CCCD / CMND, sổ hộ khẩu) > tờ khai đăng ký khai tử > giấy người dân tự lập
(bản cam đoan, đơn, biên bản). Hai cách viết chỉ khác DẤU là chuyện thường (OCR đọc lệch dấu), KHÔNG phải lý do giữ A.
Mã đã tự loại cách viết là bản rơi dấu của A, chữ Đ đọc thành D, và cách viết đổi chữ cái khi chữ cái của A đã có trên
giấy ngoài tờ khai — không lấy các lý do này để giữ A. Chọn đúng từng chữ, từng dấu như trên giấy.
</ho_ten>

<so_ngay>
Số định danh / ngày sinh lấy ở vùng MRZ mặt sau thẻ mang họ tên (không dấu) của người chết, năm sinh trong số khớp ngày
sinh in ở MRZ → chọn B: ba dòng MRZ in máy đọc ổn định hơn chữ số viết tay. Tín hiệu "thẻ nhận theo ngày sinh": tờ khai
viết tay bị đọc sai cả tên nên mã nhận thẻ của người chết bằng ngày sinh MRZ trùng đủ ngày sinh và số chỉ lệch 1–2 chữ
số → số, ngày cấp, và HỌ TÊN in trên thẻ (B) thay cho A chỉ có trên tờ khai, kể cả khi B khác chữ cái A. Ngày cấp đọc ở mặt sau thẻ, trong khối kết
thúc bằng dải MRZ mang đúng số định danh của người chết → chọn B (mã đã bỏ qua khi ngày của A có trên tờ khai / giấy báo
tử / trích lục khai tử). Ngày hết
hạn ("Có giá trị đến") không phải ngày cấp.
</so_ngay>
"""


def _finding(unit: str, value: str, quote: str, doc: int, note: str, evidence: str) -> Finding:
    return Finding(INSPECTOR, _UNIT[unit], {_UNIT[unit].fields[0].name: value}, quote, doc, note, _OWNER, backed=True,
                   evidence=(evidence,))


def _line_with(case: Case, test) -> tuple[str, int]:
    for index, document in enumerate(case.documents, start=1):
        for line in str(document.get("text") or "").splitlines():
            if line.strip() and test(line):
                return line.strip(), index
    return "", 0


def _marked(name: str) -> bool:
    """Cách viết còn dấu thanh / dấu mũ / nét "Đ" ở ít nhất một chữ."""
    return fold(name) != " ".join(str(name).lower().split())


def name_finding(case: Case, page_list: list[dict]) -> Finding | None:
    current = " ".join(str(case.values.get(NAME) or "").split())
    target = fold(current).split()
    if len(target) < 2:
        return None
    ours = trang.name_key(current)
    anchors = {n for n in (trang.digits(case.values.get(NUMBER)), trang.digits(case.values.get(ID_NUMBER))) if len(n) >= 9}
    candidates: dict[str, dict] = {}
    for page in page_list:
        if page["kind"] == "to_khai":
            continue
        anchored = any(n in trang.digits(" ".join(page["lines"])) for n in anchors)
        for line in page["lines"]:
            tokens = trang.WORD_RE.findall(line)
            for start in range(len(tokens) - len(target) + 1):
                window = " ".join(tokens[start:start + len(target)])
                key = trang.name_key(window)
                letters = fold(window).split()
                if key == ours or key in candidates:
                    continue
                if letters == target:
                    candidates[key] = {"name": window.upper(), "quote": line, "doc": page["doc"], "letters": False}
                elif anchored and letters[0] == target[0] and close_name(window, current):
                    candidates[key] = {"name": window.upper(), "quote": line, "doc": page["doc"], "letters": True}
    if not candidates:
        return None
    mine = trang.support(current, page_list)
    target_words = f" {' '.join(target)} "
    letters_on_paper = any(target_words in f" {' '.join(fold(line).split())} "
                           for page in page_list if page["kind"] != "to_khai" for line in page["lines"])
    winners = []
    for key, cand in candidates.items():
        # Đề xuất là bản rơi dấu / mất nét "Đ" của lượt trích → chặn (OCR rơi dấu cả dòng: "DINH VAN HE"). Trừ khi chính
        # cách viết đó còn dấu ở chữ khác ("Võ Thị Giai": dòng không bị rơi dấu, tên viết đúng là "Giai").
        if not cand["letters"] and (base._adds_marks(key, ours) or base._lost_stroke(key, ours)) \
                and not _marked(cand["name"]):
            continue
        if cand["letters"] and letters_on_paper:
            continue
        stat = trang.support(cand["name"], page_list)
        if stat["ban_in"] + stat["the"] + stat["tu_lap"] < 1 or trang.rank(stat) <= trang.rank(mine):
            continue
        winners.append((trang.rank(stat), key, cand, stat))
    winners.sort(key=lambda item: item[0], reverse=True)
    if not winners or (len(winners) > 1 and winners[0][0] == winners[1][0]):
        return None
    _, _, cand, best = winners[0]
    return _finding("ho_ten", cand["name"], cand["quote"], cand["doc"], "giấy ghi họ tên người chết",
                    f"TỔNG số trang ghi nguyên văn: B {best['trang']}, A {mine['trang']}. B: {best['ban_in']} giấy cơ "
                    f"quan cấp, {best['the']} dòng họ tên thẻ, {best['tu_lap']} giấy tự lập, {best['to_khai']} tờ khai; "
                    f"A: {mine['ban_in']} giấy cơ quan cấp, {mine['the']} dòng thẻ, {mine['tu_lap']} giấy tự lập, "
                    f"{mine['to_khai']} tờ khai")


def _card(case: Case) -> dict | None:
    """Thẻ của người mất: MRZ mang họ tên (không dấu) của người mất, năm sinh trong số khớp năm sinh in ở MRZ. Không thẻ
    nào trùng tên (tờ khai viết tay đọc sai cả tên) → thẻ có ngày sinh MRZ trùng ĐỦ ngày sinh của lượt trích và số chỉ lệch
    1–2 chữ số với số của lượt trích (OCR đọc lệch chữ số) — đánh dấu "by_birth"."""
    name = " ".join(fold(case.values.get(NAME)).split())
    cards = [card for document in case.documents for card in mrz_records(document.get("text"))]
    cards = [card for card in cards if card.get("birth") and (id_birth_year(card["id"]) or 0) % 100 == card["birth"][0]]
    named = [card for card in cards if name and card.get("name") == name]
    if named:
        return named[0] if len({card["id"] for card in named}) == 1 else None
    birth, ours = parse_date(case.values.get(BIRTH)), trang.digits(case.values.get(NUMBER))
    if not birth or len(ours) != 12:
        return None
    near = [card for card in cards if card["birth"] == (birth.year % 100, birth.month, birth.day)
            and id_birth_year(card["id"]) == birth.year and card.get("name")
            and 0 < sum(a != b for a, b in zip(card["id"], ours)) <= 2]
    return {**near[0], "by_birth": True} if len({card["id"] for card in near}) == 1 else None


def card_name_finding(case: Case, card: dict | None, page_list: list[dict]) -> Finding | None:
    """Thẻ nhận theo ngày sinh + số (tên lượt trích không khớp MRZ): họ tên in trên mặt thẻ (dòng có dấu, cùng chữ cái
    với tên ở MRZ) thay cho tên lượt trích."""
    if not card or not card.get("by_birth"):
        return None
    target = card["name"].split()
    for page in page_list:
        if page["kind"] == "to_khai":
            continue
        for line in page["lines"]:
            tokens = trang.WORD_RE.findall(line)
            for start in range(len(tokens) - len(target) + 1):
                window = " ".join(tokens[start:start + len(target)])
                if fold(window).split() == target and _marked(window):
                    return _finding("ho_ten", window.upper(), line, page["doc"], "họ tên in trên thẻ của người chết",
                                    "thẻ của người chết nhận theo ngày sinh MRZ trùng ngày sinh và số định danh chỉ lệch "
                                    "1–2 chữ số do OCR; họ tên trên thẻ (mặt trước và vùng MRZ) khác tên lượt trích lấy ở "
                                    "tờ khai viết tay")
    return None


def _on_declaration(case: Case, value) -> bool:
    """Ngày của lượt trích có trên tờ khai đăng ký khai tử hoặc trên giấy báo tử / trích lục khai tử (dòng giấy tờ tùy
    thân của người chết): giữ theo giấy đó — mặt sau thẻ in nhỏ, OCR hay đọc lệch tháng."""
    parsed = parse_date(value)
    if not parsed:
        return False
    d, m, y = parsed.day, parsed.month, parsed.year
    pattern = re.compile(rf"(?<!\d)0?{d}\s*[/.-]\s*0?{m}\s*[/.-]\s*{y}(?!\d)|ngày\s*0?{d}\s*tháng\s*0?{m}\s*năm\s*{y}",
                         re.IGNORECASE)
    return any(pattern.search(line) for page in trang.pages(case.documents)
               if page["kind"] == "to_khai" or any(m_ in fold(" ".join(page["lines"][:12])) for m_ in _DEATH_PAPERS)
               for line in page["lines"])


def card_findings(case: Case) -> list[Finding]:
    card = _card(case)
    if not card:
        return []
    out = []
    how = ("thẻ nhận theo ngày sinh MRZ trùng ngày sinh người chết, số chỉ lệch 1–2 chữ số" if card.get("by_birth") else
           "vùng MRZ của thẻ mang họ tên người chết (không dấu), năm sinh trong số khớp ngày sinh in ở MRZ")
    quote, doc = _line_with(case, lambda line: bool(re.search(rf"I[DO]VNM\S*{card['id']}", re.sub(r"\s+", "", line))))
    if quote:
        for unit, field in (("so_dinh_danh", NUMBER), ("so_giay_to", ID_NUMBER)):
            current = trang.digits(case.values.get(field))
            # Số giấy tờ là CMND 9 số (giấy khác thẻ căn cước) thì không đụng.
            if current != card["id"] and (unit == "so_dinh_danh" or not current or len(current) == 12):
                out.append(_finding(unit, card["id"], quote, doc, "dòng MRZ ở mặt sau thẻ của người chết", how))
    year = id_birth_year(card["id"])
    yy, mm, dd = card["birth"]
    birth = f"{dd:02d}/{mm:02d}/{year}" if year and year % 100 == yy else ""
    pattern = rf"(?<!\d)0?{dd}\s*[/.-]\s*0?{mm}\s*[/.-]\s*{year}(?!\d)"
    if birth and parse_date(case.values.get(BIRTH)) != parse_date(birth):
        line, at = _line_with(case, lambda text: bool(re.search(pattern, text)))
        if line:
            out.append(_finding("ngay_sinh", birth, line, at, "ngày sinh in trên thẻ của người chết",
                                "ngày sinh khớp ngày sinh mã hoá ở MRZ thẻ của người chết"))
    back = _mrz_card_backs(case.documents).get(card["id"])
    issued = parse_date((back or {}).get("issue_date"))
    if issued and parse_date(case.values.get(ISSUE)) != issued and not _on_declaration(case, case.values.get(ISSUE)):
        value = issued.strftime("%d/%m/%Y")
        pattern = rf"(?<!\d)0?{issued.day}\s*[/.-]\s*0?{issued.month}\s*[/.-]\s*{issued.year}(?!\d)"
        line, at = _line_with(case, lambda text: bool(re.search(pattern, text)))
        if line:
            out.append(_finding("ngay_cap", value, line, at, "dòng in ở mặt sau thẻ của người chết",
                                "ngày cấp đọc ở mặt sau thẻ, khối kết thúc bằng dải MRZ mang đúng số của người chết"))
    return out


def findings_from(case: Case) -> list[Finding]:
    page_list = trang.pages(case.documents)
    name = card_name_finding(case, _card(case), page_list) or name_finding(case, page_list)
    return [*([name] if name else []), *card_findings(case)]


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    return findings_from(case)


INSPECTOR = Inspector("dinh_danh", "ĐỊNH DANH người được đăng ký khai tử (họ tên, ngày sinh, số giấy tờ, ngày cấp)",
                      UNITS, RULES, owners=(_OWNER, "người khác"), accepted=(_OWNER,), find=find)
