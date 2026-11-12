"""Bước suy luận trước khi trích field XNTTHN: phân vai (người nộp = tài khoản ↔ người yêu cầu ↔ người được cấp),
quan hệ, và CHUẨN HOÁ MỤC ĐÍCH sử dụng.

Khối người nộp trên cổng mới khóa theo tài khoản định danh nên quan hệ tính SO VỚI TÀI KHOẢN. Mục đích là câu viết tay
OCR hay đọc lệch → khôi phục ngay ở bước này để lượt trích không phải chép lại chữ hỏng. Agent chỉ trả text có thẻ;
không trả JSON.
"""

import re
import unicodedata

from app.config import settings
from app.pipelines._shared.cccd import id_birth_year, id_gender
from app.pipelines._shared.tai_khoan import matches_account
from app.services.llm import client

_REASON_MAX_TOKENS = 1400

_ROLE_PROMPT = """
<vai_tro>
Bạn là agent PHÂN VAI hồ sơ CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN (XNTTHN). Đọc TOÀN BỘ tài liệu. Không trích field
biểu mẫu, không trả JSON. Chỉ xác định:
1. NGƯỜI NỘP = chủ tài khoản đang đăng nhập cổng (cho trong <requester_context>): có mặt trong hồ sơ không, vai gì.
2. NGƯỜI YÊU CẦU ghi ở khối ĐẦU tờ khai (trước câu "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân...").
3. NGƯỜI ĐƯỢC CẤP = người cần giấy XNTTHN.
4. QUAN HỆ của NGƯỜI NỘP với NGƯỜI ĐƯỢC CẤP.
5. MỤC ĐÍCH sử dụng giấy, đã khôi phục câu chữ.
<requester_context> do MÃ đối chiếu sẵn (số định danh, họ tên, người yêu cầu trên tờ khai có phải chủ tài khoản không,
hồ sơ có thẻ của ai): dùng làm mốc, không tự đối chiếu lại theo cách khác.
</vai_tro>

<xac_dinh_nguoi_duoc_cap>
Theo thứ tự, dừng ở mục đầu tiên áp dụng được:
a. Có TỜ KHAI: người có tên SAU câu "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân cho người có tên dưới đây".
b. Không có tờ khai mà có GIẤY ỦY QUYỀN: BÊN ỦY QUYỀN (người cần giấy) là người được cấp; bên được ủy quyền là người
   đi nộp hộ.
c. Không có cả hai, có giấy XNTTHN cũ: người đứng tên trên giấy XNTTHN cũ.
d. Không có cả ba, hồ sơ có THẺ căn cước / CCCD / CMND Việt Nam: người đứng tên thẻ đó — kể cả khi đó là thẻ của
   chính chủ tài khoản.
KHÔNG BAO GIỜ là người được cấp:
- NGƯỜI ĐÃ CHẾT (người được khai tử trên giấy chứng tử, trích lục khai tử, giấy báo tử, tờ khai đăng ký khai tử). Hồ sơ
  gồm thẻ của một người + giấy khai tử của người khác → người được cấp là người đứng tên thẻ; số định danh, ngày sinh
  in trên giấy khai tử là của người chết, không dùng.
- Người đứng tên GIẤY TỜ TÙY THÂN DO NƯỚC NGOÀI CẤP (hộ chiếu / thẻ căn cước nước ngoài, họ tên nước ngoài, số không
  phải 9 hay 12 chữ số): đó là người dự định kết hôn hoặc vợ / chồng, không phải người xin giấy.
- Vợ / chồng (đã chết, đã ly hôn hay hiện tại), người làm chứng, cán bộ ký, thẩm phán.
Không mục nào áp dụng được (hồ sơ chỉ có giấy khai tử, quyết định ly hôn, giấy kết hôn, giấy tờ nước ngoài...) → mọi
nhãn của <nguoi_duoc_cap> ghi "Không xác định"; không đoán, không lấy người trong các giấy đó.
</xac_dinh_nguoi_duoc_cap>

<xac_dinh_quan_he>
Quan hệ = người nộp (chủ tài khoản) là gì CỦA người được cấp. Xét theo thứ tự, dừng ở bước đầu tiên đúng:
1. Người nộp CHÍNH LÀ người được cấp (trùng số định danh; thiếu số thì họ tên lệch tối đa một ký tự do OCR) →
   "Bản thân".
2. <requester_context> ghi người yêu cầu trên tờ khai LÀ chủ tài khoản → Kết luận = ĐÚNG CHỮ ở dòng "Quan hệ với người
   được cấp..." của tờ khai (dòng đó chính là quan hệ của người nộp). Dòng ghi "Tự khai", "Bản thân", "Chính mình"
   → "Bản thân". Dòng để trống → sang bước sau.
3. Người nộp là bên được ủy quyền trong văn bản ủy quyền của hồ sơ → "Người được ủy quyền".
4. Giấy tờ khác ghi rõ quan hệ → quan hệ đó (vd "Con", "Mẹ").
5. Không có căn cứ → "Không xác định". Không suy từ họ, tuổi, địa chỉ.
<requester_context> ghi người yêu cầu trên tờ khai KHÁC chủ tài khoản (người khác nộp hộ bằng tài khoản của mình):
dòng quan hệ trên tờ khai là của người yêu cầu đó, KHÔNG phải của người nộp → không dùng ở bước 2.
</xac_dinh_quan_he>

<muc_dich>
MỤC ĐÍCH — đọc dòng "Mục đích sử dụng Giấy xác nhận tình trạng hôn nhân" của tờ khai (không có tờ khai thì dòng "Giấy
này được sử dụng để: ..." của giấy XNTTHN cũ). Hồ sơ không có dòng nào như vậy → "Loại: không xác định", "Nội dung:
Không có"; TUYỆT ĐỐI không tự đặt mục đích. Câu VIẾT TAY, OCR hay đọc sai:
- Câu thường gồm: [mở đầu: "(Để) bổ sung (vào) hồ sơ", "Bổ túc hồ sơ", "Để làm (các thủ tục)", "Dùng để"] + [việc:
  vay vốn / vay ngân hàng; mua bán, chuyển nhượng, tặng cho, thừa kế nhà đất / quyền sử dụng đất; làm giấy tờ đất;
  mua bán, sang tên xe; thủ tục ngân hàng, hành chính; chế độ an sinh, trợ cấp] + có thể có tên người, khoảng ngày,
  nước đến.
- Khoảng 2/3 tờ khai có thêm cụm pháp lý ở cuối, dạng chuẩn "không có giá trị để đăng ký kết hôn" (một số người viết
  "giá trị sử dụng", "khi đăng ký"). OCR hay biến cụm này thành chữ nghe xuôi mà SAI nghĩa ("không có gia đình…",
  "giấy tờ để đóng kí", "giai trị"): đoạn cuối câu bắt đầu bằng "không có" + chữ giống "giá trị"/"giấy"/"gia" và kết
  thúc gần "kết hôn" → chính là cụm pháp lý. Người xin giấy ĐỂ đăng ký kết hôn thì KHÔNG có cụm này — tuyệt đối
  không thêm, sẽ lật ngược nghĩa.
- Phần việc hay đọc lệch: "tặng cho" thành "tăng cho"; "mua bán" thành "mua hàng"; "bổ sung" thành "bố xung"/"bỏ
  sung"; "chế độ" thành "chỗ để"; "trước thời kỳ hôn nhân" thành "thời hạn là hôn nhân".
- Khôi phục TỪNG CỤM: cụm giống dạng hỏng đã nêu → về cụm chuẩn; cụm có nghĩa → giữ nguyên chữ (chỉ sửa chính tả rõ
  ràng); bỏ chữ rác chen vào. KHÔNG xoá cụm có nghĩa, KHÔNG bỏ tên riêng, nước đến, số, ngày; KHÔNG thêm ý không có
  dấu vết trên OCR. Viết đúng chính tả, hoa chữ đầu câu. GIỮ TRỌN câu, kể cả cụm "không có giá trị ...".
- Loại (dòng "Nơi đăng ký kết hôn ở nước ngoài" ghi "không nêu" → Loại BẮT BUỘC là "khac"):
  "ket_hon_co_quan_dai_dien" = câu NÊU RÕ đăng ký kết hôn tại Cơ quan đại diện Việt Nam ở nước ngoài (đại sứ
  quán, lãnh sự quán Việt Nam); "ket_hon_nuoc_ngoai" = câu NÊU RÕ đăng ký kết hôn tại cơ quan có thẩm quyền CỦA NƯỚC
  NGOÀI / ở một nước ngoài; "khac" = mọi trường hợp còn lại, kể cả đăng ký kết hôn tại Việt Nam, câu không nêu nơi
  đăng ký, hay việc khác có nhắc chữ "kết hôn". Vd "Vay vốn ngân hàng để đăng ký kết hôn" → "khac" (việc là vay vốn,
  không nêu nơi đăng ký ở nước ngoài); "Để đăng ký kết hôn với công dân Hàn Quốc tại Hàn Quốc" →
  "ket_hon_nuoc_ngoai"; "Để đăng ký kết hôn tại Đại sứ quán Việt Nam tại Nhật Bản" → "ket_hon_co_quan_dai_dien".
</muc_dich>

<dinh_dang_tra_ve>
Chỉ trả TEXT theo đúng các khối dưới đây, không markdown/code fence, không JSON. Mỗi nhãn một dòng, "Căn cứ" tối đa
25 từ:
<nguoi_nop>
Họ tên: ...
Số định danh: ...
Có trong hồ sơ: Có|Không
Vai trong hồ sơ: ...
</nguoi_nop>
<nguoi_yeu_cau>
Họ tên: ...
Số định danh: ...
Quan hệ ghi trên tờ khai: ...
</nguoi_yeu_cau>
<nguoi_duoc_cap>
Họ tên: ...
Số định danh: ...
Ngày sinh: ...
Nguồn: ...
Căn cứ phân vai: ...
</nguoi_duoc_cap>
<quan_he>
Kết luận: Bản thân|<quan hệ cụ thể>|Không xác định
Căn cứ: ...
</quan_he>
<muc_dich>
Nội dung: <câu mục đích đã khôi phục>|Không có
Nơi đăng ký kết hôn ở nước ngoài nêu trong câu: <tên nước / cơ quan đại diện ở nước ngoài>|không nêu
Loại: khac|ket_hon_nuoc_ngoai|ket_hon_co_quan_dai_dien|không xác định
Độ chắc: cao|thap
</muc_dich>
</dinh_dang_tra_ve>
""".strip()

_TAGS = ("nguoi_nop", "nguoi_yeu_cau", "nguoi_duoc_cap", "quan_he", "muc_dich")


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d").lower()
    return re.sub(r"\s+", " ", text).strip()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def requester_context(options: dict | None) -> tuple[str, str]:
    ctx = (options or {}).get("formContext") or {}
    return (
        str(ctx.get("applicantFullname") or "").strip(),
        _digits(ctx.get("applicantIdentityNumber")),
    )


def _doc_text(document: dict) -> str:
    return _fold(f"{document.get('name') or ''}\n{document.get('text') or ''}")


def _is_death_doc(document: dict) -> bool:
    # "chứng từ" cũng gập thành "chung tu" → khớp cả cụm "giay chung tu". Tờ khai / giấy XNTTHN cũ hay nhắc "giấy
    # chứng tử" trong dòng tình trạng hôn nhân → không tính là giấy khai tử.
    text = _doc_text(document)
    return any(m in text for m in ("khai tu", "giay chung tu", "giay bao tu")) and "tinh trang hon nhan" not in text


def _is_identity_doc(document: dict) -> bool:
    text = _doc_text(document)
    return not _is_death_doc(document) and any(
        m in text for m in ("can cuoc", "chung minh nhan dan", "identity card"))


_SELF_WORDS = {"ban than", "tu khai", "chinh minh", "ban than toi"}
_CARD_TITLES = ("can cuoc cong dan", "can cuoc", "chung minh nhan dan", "giay chung minh nhan dan",
                "citizen identity card", "identity card")


def _is_card(document: dict) -> bool:
    """Tài liệu là THẺ căn cước / CMND Việt Nam: có dòng tiêu đề thẻ hoặc vùng MRZ, không tính giấy chỉ nhắc số thẻ."""
    text = str(document.get("text") or "")
    if "IDVNM" in text:
        return True
    return any(_fold(line).strip(" .:*#") in _CARD_TITLES for line in text.splitlines()[:40])


def _is_authorization(document: dict) -> bool:
    """Tài liệu là giấy / hợp đồng / văn bản ủy quyền: chữ "ủy quyền" nằm ở dòng tiêu đề, không tính giấy chỉ nhắc tới."""
    lines = [line for line in str(document.get("text") or "").splitlines() if line.strip()][:25]
    return any("uy quyen" in _fold(line) and len(line.strip()) <= 60 and ":" not in line for line in lines)


def _names_subject(document: dict) -> bool:
    """Tài liệu tự nó chỉ ra người được cấp: tờ khai, văn bản ủy quyền, hoặc giấy XNTTHN cũ (dòng tiêu đề). Bản án /
    quyết định chỉ nhắc cụm "tình trạng hôn nhân" trong câu thì không tính."""
    text = _doc_text(document)
    if "nguoi co ten duoi day" in text or "to khai cap giay xac nhan" in text or _is_authorization(document):
        return True
    lines = [line.strip() for line in str(document.get("text") or "").splitlines() if line.strip()][:25]
    return any(_fold(line).strip(" .:*#") == "giay xac nhan tinh trang hon nhan" for line in lines)


def declaration_requester(documents: list[dict]) -> dict:
    """Khối NGƯỜI YÊU CẦU ở đầu tờ khai (trước câu "... cho người có tên dưới đây"): {name, number, birthday, relation}.
    {} khi hồ sơ không có tờ khai hoặc không đọc được dòng họ tên người yêu cầu."""
    for document in documents:
        lines = [line.strip() for line in str(document.get("text") or "").splitlines() if line.strip()]
        end = next((i for i, line in enumerate(lines) if "nguoi co ten duoi day" in _fold(line)), None)
        if end is None:
            continue
        start = next((i for i, line in enumerate(lines[:end])
                      if ":" in line and "nguoi yeu cau" in _fold(line.split(":", 1)[0])), None)
        if start is None:
            continue
        head = lines[start:end]

        def value(marker: str) -> str:
            return next((line.split(":", 1)[1].strip(" .") for line in head
                         if ":" in line and marker in _fold(line.split(":", 1)[0])), "")

        at = next((i for i, line in enumerate(head) if "giay to tuy than" in _fold(line)), None)
        around = " ".join(head[at:at + 2]) if at is not None else ""
        numbers = [_digits(run) for run in re.findall(r"\d[\d .]{7,}\d", around)]
        return {"name": head[0].split(":", 1)[1].strip(" ."),
                "number": next((n for n in numbers if len(n) in (9, 12)), next(iter(numbers), "")),
                "birthday": value("nam sinh"), "relation": value("quan he voi nguoi duoc cap")}
    return {}


def requester_is_account(documents: list[dict], options: dict | None) -> bool | None:
    """Người yêu cầu ghi ở đầu tờ khai có phải CHỦ TÀI KHOẢN không (chữ viết tay: cho lệch một ký tự tên, hai chữ số).
    None = không có tờ khai / không có tài khoản để đối chiếu."""
    name, number = requester_context(options)
    requester = declaration_requester(documents)
    if not requester or not (name or number):
        return None
    if number and number == requester["number"]:
        return True
    return matches_account({"HoTen": name, "SoDinhDanh": number}, requester["name"], requester["number"],
                           requester["birthday"])


def _document_hints(documents: list[dict], options: dict | None) -> str:
    """Mỏ neo tất định: tài liệu nào chứa đúng số định danh của tài khoản, tài liệu nào là giấy khai tử, tài liệu
    nào là thẻ căn cước, người yêu cầu trên tờ khai có phải chủ tài khoản không."""
    name, number = requester_context(options)
    hits = [
        str(index)
        for index, document in enumerate(documents, start=1)
        if number and number in _digits(document.get("text"))
    ]
    deaths = [str(index) for index, document in enumerate(documents, start=1) if _is_death_doc(document)]
    lines = [
        "<requester_context>",
        f'Họ tên chủ tài khoản (người nộp): "{name or "không có"}".',
        f'Số định danh chủ tài khoản: "{number or "không có"}".',
        "Tài liệu chứa đúng số định danh này: " + (", ".join(hits) if hits else "không có") + ".",
        "Tài khoản là MỐC để tính quan hệ, không phải dữ liệu của người được cấp.",
    ]
    if deaths:
        lines.append(f"Giấy khai tử: tài liệu {', '.join(deaths)} — người được khai tử trong đó KHÔNG phải người được cấp.")
    cards = [str(index) for index, document in enumerate(documents, start=1) if _is_card(document)]
    if cards:
        lines.append(f"Tài liệu là thẻ căn cước / CMND Việt Nam: {', '.join(cards)}.")
    proxies = [str(index) for index, document in enumerate(documents, start=1) if _is_authorization(document)]
    lines.append("Văn bản ủy quyền trong hồ sơ: " + (f"tài liệu {', '.join(proxies)}." if proxies else "không có."))
    requester = declaration_requester(documents)
    same = requester_is_account(documents, options)
    if requester:
        if same is not None:
            lines.append(f'Người yêu cầu ghi ở đầu tờ khai: "{requester["name"]}" — đối chiếu bằng mã: '
                         + ("LÀ chủ tài khoản." if same else "KHÁC chủ tài khoản."))
        lines.append(f'Dòng quan hệ của người yêu cầu trên tờ khai: "{requester["relation"] or "để trống"}".')
    lines.append("</requester_context>")
    return "\n".join(lines)


def _dead_subject_fix(raw: str, documents: list[dict]) -> str:
    """Hồ sơ không tờ khai / ủy quyền / giấy XNTTHN cũ, gồm thẻ căn cước + giấy khai tử mà bước phân vai lại chọn người
    chỉ có mặt trong giấy khai tử (người chết) → khối <nguoi_duoc_cap> thay thế trỏ về người đứng tên thẻ. "" = giữ."""
    texts = [_doc_text(document) for document in documents]
    if not documents or any("tinh trang hon nhan" in t or "uy quyen" in t for t in texts):
        return ""
    deaths = [i for i, document in enumerate(documents) if _is_death_doc(document)]
    identities = [i for i, document in enumerate(documents) if _is_identity_doc(document)]
    if not deaths or not identities:
        return ""
    block = section(raw, "nguoi_duoc_cap")
    number = _digits(labeled_value(block, "Số định danh"))
    name = _fold(labeled_value(block, "Họ tên"))
    number = number if len(number) >= 9 else ""
    if not number and len(name) < 5:
        return ""

    def mentions(i: int) -> bool:
        if number:
            return number in _digits(documents[i].get("text"))
        return name in texts[i]

    others = [i for i in range(len(documents)) if i not in deaths]
    if not any(mentions(i) for i in deaths) or any(mentions(i) for i in others):
        return ""
    where = ", ".join(str(i + 1) for i in identities)
    return (
        f"Họ tên: người đứng tên thẻ căn cước/CCCD ở tài liệu {where}\n"
        "Số định danh: theo thẻ đó\n"
        "Ngày sinh: theo thẻ đó\n"
        f"Nguồn: thẻ căn cước tài liệu {where}\n"
        f"Căn cứ phân vai: hồ sơ không có tờ khai/ủy quyền; {labeled_value(block, 'Họ tên') or 'người đã chọn'} chỉ có "
        "trong giấy khai tử là người đã chết, không phải người được cấp."
    )


def _account_subject(raw: str, documents: list[dict], options: dict | None) -> str:
    """Bước phân vai KHÔNG chọn được ai và hồ sơ không có tờ khai / ủy quyền / giấy XNTTHN cũ / thẻ căn cước Việt Nam
    (chỉ có giấy khai tử, quyết định ly hôn, giấy kết hôn, giấy tờ nước ngoài) → người được cấp là chủ tài khoản: họ
    tự xin giấy cho mình, giấy kèm chỉ để chứng minh tình trạng hôn nhân. "" = giữ."""
    name, number = requester_context(options)
    if not name or labeled_value(section(raw, "nguoi_duoc_cap"), "Họ tên"):
        return ""
    if not documents or any(_names_subject(document) for document in documents):
        return ""
    # Thẻ của chính chủ tài khoản không cản; thẻ của người khác thì không biết ai xin giấy → để trống.
    for document in documents:
        if _is_card(document) and not ((number and number in _digits(document.get("text")))
                                       or _fold(name) in _doc_text(document)):
            return ""
    return (f"Họ tên: {name}\nSố định danh: {number or 'Không xác định'}\nNgày sinh: Không xác định\n"
            "Nguồn: tài khoản người nộp\n"
            "Căn cứ phân vai: hồ sơ không có tờ khai, ủy quyền, giấy XNTTHN cũ hay thẻ Việt Nam của ai — người nộp tự "
            "xin giấy cho mình.")


def _declared_relation(raw: str, documents: list[dict], options: dict | None) -> str:
    """Người yêu cầu trên tờ khai chính là chủ tài khoản và tờ khai ghi rõ quan hệ → khối <quan_he> chép đúng chữ của
    dòng đó (model hay bỏ trống hoặc đảo chiều thành vai của người được cấp). Model đã kết luận "Bản thân" thì giữ.
    "" = giữ."""
    if _fold(labeled_value(section(raw, "quan_he"), "Kết luận")) in _SELF_WORDS or not requester_is_account(documents, options):
        return ""
    relation = declaration_requester(documents).get("relation") or ""
    if len(_fold(relation)) < 2 or _fold(relation) in _SELF_WORDS:
        return ""
    return (f"Kết luận: {relation}\n"
            "Căn cứ: người yêu cầu trên tờ khai là chủ tài khoản (đối chiếu bằng mã); chép dòng quan hệ của tờ khai.")


_MALE_ROLES = {"chong", "cha", "bo", "anh", "ong", "trai"}
_FEMALE_ROLES = {"vo", "me", "chi", "gai"}
_ELDER_ROLES = {"cha", "bo", "me", "ong"}
_YOUNGER_ROLES = {"con", "chau"}
_GENERATION_GAP_YEARS = 12


def _unsupported_relation(raw_block: str, subject_block: str, documents: list[dict], options: dict | None) -> bool:
    """Kết luận quan hệ do model viết mà mã thấy vô căn cứ → bỏ, để trống còn hơn ghi sai:
    - "Người được ủy quyền" khi hồ sơ không có chữ ủy quyền nào; nhãn tự đặt kiểu "người khác", "nộp hộ";
    - vai LỆCH GIỚI TÍNH của chủ tài khoản (số định danh mã hoá giới tính): người nộp là nữ mà ghi "Chồng" tức model
      đảo chiều thành vai của người được cấp;
    - vai cha / mẹ mà chủ tài khoản lại trẻ hơn người được cấp (hoặc vai con mà già hơn): cũng là đảo chiều."""
    words = set(_fold(labeled_value(raw_block, "Kết luận")).split())
    if not words or words <= {"ban", "than"}:
        return False
    if {"nop", "ho"} <= words or words <= {"nguoi", "khac"}:
        return True
    if {"uy", "quyen"} <= words:
        return not any("uy quyen" in _doc_text(document) for document in documents)
    _, number = requester_context(options)
    gender = _fold(id_gender(number))
    if (gender == "nu" and words & _MALE_ROLES) or (gender == "nam" and words & _FEMALE_ROLES):
        return True
    own_year = id_birth_year(number)
    subject_year = id_birth_year(labeled_value(subject_block, "Số định danh"))
    if not subject_year:
        match = re.search(r"(\d{4})\s*$", labeled_value(subject_block, "Ngày sinh"))
        subject_year = int(match.group(1)) if match else None
    if own_year and subject_year:
        if words & _ELDER_ROLES and own_year > subject_year - _GENERATION_GAP_YEARS:
            return True
        if words & _YOUNGER_ROLES and not words & _ELDER_ROLES and own_year < subject_year + _GENERATION_GAP_YEARS:
            return True
    return False


def _build_user_content(documents: list[dict], options: dict | None) -> str:
    body = "\n\n---\n\n".join(
        f"===== Tài liệu {index}: {document.get('name') or '(không tên)'} =====\n"
        f"{str(document.get('text') or '').strip()}"
        for index, document in enumerate(documents, start=1)
    )
    return f"{_document_hints(documents, options)}\n\nOCR hồ sơ:\n\n{body}"


def section(text: str, tag: str) -> str:
    match = re.search(rf"<{tag}>\s*([\s\S]*?)\s*(?:</{tag}>|$)", str(text or ""), flags=re.IGNORECASE)
    if not match:
        return ""
    # Khối bị cắt cụt (hết token) không có thẻ đóng: chỉ giữ tới thẻ mở kế tiếp.
    return re.split(r"\n\s*<[a-z_]+>", match.group(1))[0].strip()


def labeled_value(block: str, label: str) -> str:
    # [ \t]* thay \s*: nhãn để trống không được nuốt sang dòng kế tiếp.
    match = re.search(rf"(?im)^[ \t]*{re.escape(label)}[ \t]*:[ \t]*(.*?)[ \t]*$", block or "")
    value = match.group(1).strip() if match else ""
    return "" if _fold(value) in {"", "...", "khong xac dinh", "khong co", "khong ro"} else value


def _render_context(raw: str, options: dict | None, documents: list[dict] | None = None) -> str:
    blocks = {tag: section(raw, tag) for tag in _TAGS}
    if not blocks["nguoi_duoc_cap"]:
        return ""
    fixed = _dead_subject_fix(raw, documents or [])
    if fixed:
        # Quan hệ đã tính theo người chết → bỏ, mapper đối chiếu lại tài khoản với người đứng tên thẻ.
        blocks["nguoi_duoc_cap"], blocks["quan_he"] = fixed, ""
    else:
        own = _account_subject(raw, documents or [], options)
        if own:
            blocks["nguoi_duoc_cap"] = own
            blocks["quan_he"] = "Kết luận: Bản thân\nCăn cứ: người được cấp là chủ tài khoản."
        else:
            declared = _declared_relation(raw, documents or [], options)
            if declared:
                blocks["quan_he"] = declared
            elif _unsupported_relation(blocks["quan_he"], blocks["nguoi_duoc_cap"], documents or [], options):
                blocks["quan_he"] = ""
    name, number = requester_context(options)
    body = "\n".join(f"<{tag}>\n{value or 'Không xác định'}\n</{tag}>" for tag, value in blocks.items())
    return (
        "\n\n<phan_vai_da_xac_dinh>\n"
        "Kết quả phân vai đã phân tích trước. Dùng làm chuẩn, KHÔNG tự đổi người:\n"
        f"{body}\n"
        f"Tài khoản người nộp: {name or '?'} — {number or '?'}.\n"
        "- NguoiDuocCap_* CHỈ thuộc <nguoi_duoc_cap>; không lấy của người nộp hộ, vợ/chồng, người làm chứng.\n"
        "- NguoiYeuCau_* chép từ khối người yêu cầu của tờ khai (chỉ để đối chiếu với tài khoản).\n"
        "- Mục đích đã chuẩn hoá ở <muc_dich> — không trích lại.\n"
        "</phan_vai_da_xac_dinh>"
    )


async def build_context(documents: list[dict], options: dict | None = None) -> str:
    if not documents:
        return ""
    raw = await client.chat_text(
        [
            {"role": "system", "content": _ROLE_PROMPT},
            {"role": "user", "content": _build_user_content(documents, options)},
        ],
        max_tokens=_REASON_MAX_TOKENS,
        temperature=0,
        enable_thinking=settings.agent_reasoning,
    )
    return _render_context(raw, options, documents)
