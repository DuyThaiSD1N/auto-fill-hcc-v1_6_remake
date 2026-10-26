"""Sinh PDF biên bản ghi nhận chấp thuận xử lý dữ liệu cá nhân — dùng chung Auto Fill và Handfree.

Trình bày theo thể thức Phụ lục I Nghị định 30/2020/NĐ-CP: A4, lề trên/dưới 20 mm, trái 30 mm, phải 15 mm; Times New
Roman; Quốc hiệu in hoa 12 đậm, Tiêu ngữ 13 đậm có gạch dưới dài bằng dòng chữ; tên cơ quan in hoa 12 đậm có gạch dưới
1/3–1/2 dòng chữ; số và địa danh, ngày tháng (nghiêng) cùng một hàng; tên loại in hoa đậm, trích yếu đậm có gạch dưới;
nội dung 13, canh đều, lùi đầu dòng 1 cm, cách đoạn 6 pt, giãn dòng 1,2; số trang canh giữa lề trên từ trang 2.

Nội dung chép NGUYÊN VĂN những gì thẻ xác nhận đã hiển thị (app/consent/texts.py, chụp lúc ghi nhận) cùng toàn văn
Điều 4 Luật 91/2025/QH15. BE tự sinh (không nhận PDF từ client) để bằng chứng không bị sửa; mã SHA-256 của nội dung in
cuối biên bản và lưu kèm bản ghi Mongo để đối chiếu.
"""
import hashlib
import html as _html
import io
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fitz

from app.consent import texts

logger = logging.getLogger(__name__)

VN_TZ = timezone(timedelta(hours=7))
ISSUER = "TRỢ LÝ NHÂN DÂN"
TITLE = "BIÊN BẢN"
SUBJECT = "Ghi nhận chấp thuận xử lý dữ liệu cá nhân"

_MM = 72 / 25.4
_PAGE = fitz.paper_rect("a4")
_BODY = fitz.Rect(30 * _MM, 20 * _MM, _PAGE.width - 15 * _MM, _PAGE.height - 20 * _MM)
# Ô 1 (Quốc hiệu, Tiêu ngữ, địa danh ngày tháng) rộng vừa dòng Quốc hiệu cỡ 12 đậm; ô 2 (tên cơ quan, số) phần còn lại.
_RIGHT_W = 262
_LEFT_BOX = fitz.Rect(_BODY.x0, _BODY.y0, _BODY.x1 - _RIGHT_W, _BODY.y0 + 120)
_RIGHT_BOX = fitz.Rect(_BODY.x1 - _RIGHT_W, _BODY.y0, _BODY.x1, _BODY.y0 + 120)

# Times New Roman không được đóng kèm mã nguồn (giấy phép Microsoft): image BE cài gói ttf-mscorefonts-installer
# (Dockerfile), máy dev macOS có sẵn. Thiếu font thì vẫn sinh biên bản bằng font có sẵn của MuPDF, ghi cảnh báo.
_FONT_DIRS = (Path("/usr/share/fonts/truetype/msttcorefonts"), Path("/System/Library/Fonts/Supplemental"))
_FONT_FILES = {
    "regular": ("times.ttf", "Times New Roman.ttf"),
    "bold": ("timesbd.ttf", "Times New Roman Bold.ttf"),
    "italic": ("timesi.ttf", "Times New Roman Italic.ttf"),
    "bolditalic": ("timesbi.ttf", "Times New Roman Bold Italic.ttf"),
}


def _find_fonts() -> tuple[Path, dict[str, str]] | None:
    for folder in _FONT_DIRS:
        found = {style: next((n for n in names if (folder / n).is_file()), None) for style, names in _FONT_FILES.items()}
        if all(found.values()):
            return folder, found
    return None


def _font_css() -> tuple[str, fitz.Archive | None, str | None]:
    fonts = _find_fonts()
    if not fonts:
        logger.warning("[consent] không thấy Times New Roman — biên bản dùng font dự phòng của MuPDF")
        return "body{font-family:serif;}", None, None
    folder, names = fonts
    faces = {"regular": "", "bold": "font-weight:bold;", "italic": "font-style:italic;",
             "bolditalic": "font-weight:bold;font-style:italic;"}
    css = "".join(f'@font-face{{font-family:TNR;src:url("{names[s]}");{extra}}}' for s, extra in faces.items())
    return css + "body{font-family:TNR;}", fitz.Archive(str(folder)), str(folder / names["regular"])


def _bold_font_file() -> str | None:
    fonts = _find_fonts()
    return str(fonts[0] / fonts[1]["bold"]) if fonts else None


_CSS = """
body{font-size:13pt;color:#000;margin:0;padding:0;}
p{margin:0 0 6pt 0;line-height:1.2;text-align:justify;text-indent:1cm;}
.c{text-align:center;text-indent:0;}
.qh{font-size:12pt;font-weight:bold;margin:0;line-height:1.15;}
.tn{font-size:13pt;font-weight:bold;margin:0;line-height:1.15;}
.cq{font-size:12pt;font-weight:bold;margin:0;line-height:1.15;}
.so{font-size:13pt;margin:10pt 0 0 0;}
.dd{font-size:13pt;font-style:italic;margin:10pt 0 0 0;}
.title{font-size:14pt;font-weight:bold;margin:18pt 0 0 0;}
.sub{font-size:14pt;font-weight:bold;margin:0 0 14pt 0;}
.cancu{font-style:italic;}
.h{font-weight:bold;margin-top:6pt;}
.q{font-style:italic;}
.small{font-size:11pt;text-align:left;text-indent:0;}
"""


def _esc(s) -> str:
    return _html.escape(str(s or ""))


def _rich(s) -> str:
    """Chữ thẻ xác nhận → HTML: thoát ký tự rồi giữ nhấn **đậm** như trên thẻ."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", _esc(s))


def _date_line(place: str, at: datetime) -> str:
    return f"{place}, ngày {at:%d} tháng {at:%m} năm {at:%Y}" if place else f"Ngày {at:%d} tháng {at:%m} năm {at:%Y}"


def content_hash(record: dict) -> str:
    """SHA-256 của toàn bộ nội dung biên bản (trừ chính mã băm) — in cuối PDF, lưu kèm bản ghi."""
    payload = {k: v for k, v in record.items() if k != "content_sha256"}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _body_html(record: dict, digest: str) -> str:
    at: datetime = record["at"]
    parts = [
        f'<p class="c title">{TITLE}</p>',
        f'<p class="c sub" id="subject">{_esc(SUBJECT)}</p>',
        '<p class="cancu">Căn cứ Luật Bảo vệ dữ liệu cá nhân ngày 26 tháng 6 năm 2025.</p>',
        f"<p>Hồi {at:%H} giờ {at:%M} phút, ngày {at:%d} tháng {at:%m} năm {at:%Y}, hệ thống Trợ lý nhân dân ghi nhận "
        "việc chủ thể dữ liệu chấp thuận cho xử lý dữ liệu cá nhân với các nội dung như sau:</p>",
        '<p class="h">I. THÔNG TIN GHI NHẬN</p>',
        *(f"<p>- {_esc(label)}: {_esc(value)}</p>" for label, value in record["info"]),
        '<p class="h">II. NỘI DUNG ĐÃ THÔNG BÁO CHO CHỦ THỂ DỮ LIỆU</p>',
    ]
    notice = record.get("notice")
    if notice:
        parts.append("<p>Nguyên văn nội dung hiển thị trên màn hình xác nhận"
                     f"{' (phiên bản ' + _esc(record['version']) + ')' if record.get('version') else ''}:</p>")
        if notice.get("title"):
            parts.append(f'<p class="q">“{_rich(notice["title"])}”</p>')
        if notice.get("intro"):
            parts.append(f'<p class="q">{_rich(notice["intro"])}</p>')
        if notice.get("documents"):
            parts.append(f'<p class="q">{_rich(notice.get("documents_title") or "Giấy tờ được đọc trong thủ tục này:")}</p>')
            parts.extend(f'<p class="q">- {_rich(d)}</p>' for d in notice["documents"])
        for key in ("scope", "purpose"):
            if notice.get(key):
                parts.append(f'<p class="q">{_rich(notice[key])}</p>')
        parts.append("<p>Màn hình xác nhận có mục xem đầy đủ quyền, nghĩa vụ của chủ thể dữ liệu (toàn văn tại Mục IV "
                     "Biên bản này).</p>")
    else:
        parts.append(f"<p>Hệ thống không có bản lưu nguyên văn nội dung xác nhận phiên bản {_esc(record.get('version'))}; "
                     "Mục III ghi đúng các câu chủ thể dữ liệu đã xác nhận.</p>")
    parts.append('<p class="h">III. NỘI DUNG CHỦ THỂ DỮ LIỆU ĐÃ XÁC NHẬN</p>')
    for i, (statement, checked) in enumerate(record["statements"], 1):
        mark = "Đã đánh dấu" if checked else "Không đánh dấu"
        parts.append(f"<p>{i}. “{_esc(statement)}” — <b>{mark}</b>.</p>")
    if record.get("optional"):
        statement, agreed = record["optional"]
        parts.append(f"<p>Mục tùy chọn (không bắt buộc): “{_esc(statement)}” — "
                     f"<b>{'Đồng ý' if agreed else 'Không đồng ý'}</b>.</p>")
    if record.get("prechecked"):
        parts.append("<p>Các ô cam kết được đánh dấu sẵn trên màn hình; chủ thể dữ liệu xác nhận bằng thao tác nêu tại "
                     "Mục V.</p>")
    parts += [
        '<p class="h">IV. QUYỀN, NGHĨA VỤ CỦA CHỦ THỂ DỮ LIỆU</p>',
        f'<p class="q">{_esc(texts.LEGAL_SOURCE)}</p>',
        f"<p><b>{_esc(texts.LEGAL_ARTICLE_TITLE)}</b></p>",
    ]
    for clause, points in texts.LEGAL_ARTICLE_4:
        parts.append(f"<p>{_esc(clause)}</p>")
        parts.extend(f"<p>{_esc(point)}</p>" for point in points)
    parts.append('<p class="h">V. KẾT QUẢ XÁC NHẬN</p>')
    parts.extend(f"<p>- {_esc(label)}: <b>{_esc(value)}</b></p>" if label == "Kết quả"
                 else f"<p>- {_esc(label)}: {_esc(value)}</p>" for label, value in record["result"])
    if record.get("lang_note"):
        parts.append(f"<p>{_esc(record['lang_note'])}</p>")
    parts += [
        "<p>Biên bản do hệ thống tự động lập ngay khi chủ thể dữ liệu xác nhận và được lưu trữ để đối soát khi cần; "
        "nội dung tại Mục II, Mục III là nguyên văn đã hiển thị cho chủ thể dữ liệu tại thời điểm xác nhận.</p>",
        f'<p class="small">Mã kiểm tra nội dung (SHA-256):<br/>{digest}</p>',
    ]
    return "".join(parts)


def _header_html(record: dict) -> tuple[str, str]:
    left = (f'<p class="c cq" id="issuer">{_esc(ISSUER)}</p>'
            f'<p class="c so">Số: {_esc(record["so"])}</p>')
    right = ('<p class="c qh">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</p>'
             '<p class="c tn" id="motto">Độc lập - Tự do - Hạnh phúc</p>'
             f'<p class="c dd">{_esc(_date_line(record.get("place") or "", record["at"]))}</p>')
    return left, right


def _collect(positions: dict, story: fitz.Story) -> None:
    def keep(pos):
        if getattr(pos, "id", "") and getattr(pos, "open_close", 0) & 2:
            positions[pos.id] = fitz.Rect(pos.rect)
    story.element_positions(keep)


def _decorate(pdf: bytes, positions: dict, font_file: str | None, bold_file: str | None,
              record: dict, digest: str) -> bytes:
    doc = fitz.open("pdf", pdf)
    # Times New Roman gán "-" và gạch mềm vào cùng một hình chữ → chữ trích từ trang ra gạch mềm ở mã "TLND-…", tìm theo
    # mã có thể hụt. Ghi mã biên bản + mã băm vào thông tin tệp để tra cứu, đối chiếu không phụ thuộc chữ trên trang.
    doc.set_metadata({"title": f"{TITLE} {SUBJECT}", "author": "Trợ lý nhân dân", "subject": str(record["so"]),
                      "keywords": f"{record['so']}; SHA-256 {digest}", "creator": "Trợ lý nhân dân",
                      "producer": "Trợ lý nhân dân"})
    first = doc[0]
    bold = fitz.Font(fontfile=bold_file) if bold_file else fitz.Font("tibo")
    # Gạch dưới: Tiêu ngữ dài bằng dòng chữ; tên cơ quan và trích yếu khoảng 2/5 dòng chữ, đặt cân giữa.
    for key, text, size, ratio in (("motto", "Độc lập - Tự do - Hạnh phúc", 13, 1.0),
                                   ("issuer", ISSUER, 12, 0.4), ("subject", SUBJECT, 14, 0.4)):
        rect = positions.get(key)
        if not rect:
            continue
        width = bold.text_length(text, fontsize=size) * ratio
        mid, y = (rect.x0 + rect.x1) / 2, rect.y1 + 2.5
        first.draw_line((mid - width / 2, y), (mid + width / 2, y), color=(0, 0, 0), width=0.6)
    for number, page in enumerate(doc, 1):
        if number == 1:
            continue
        box = fitz.Rect(_BODY.x0, 8 * _MM, _BODY.x1, _BODY.y0 - 2 * _MM)
        if font_file:
            page.insert_textbox(box, str(number), fontsize=13, fontname="tnr", fontfile=font_file, align=1)
        else:
            page.insert_textbox(box, str(number), fontsize=13, fontname="tiro", align=1)
    return doc.tobytes(garbage=3, deflate=True)


def render(record: dict) -> tuple[bytes, str]:
    """record: so, place, at (giờ VN), info, version, notice, statements, optional, prechecked, result, lang_note.
    Trả (PDF, mã SHA-256 nội dung)."""
    digest = content_hash(record)
    font_css, archive, font_file = _font_css()
    css = font_css + _CSS
    left_html, right_html = _header_html(record)
    positions: dict[str, fitz.Rect] = {}
    buf = io.BytesIO()
    writer = fitz.DocumentWriter(buf)
    device = writer.begin_page(_PAGE)
    bottom = _BODY.y0
    for html_part, box in ((left_html, _LEFT_BOX), (right_html, _RIGHT_BOX)):
        head = fitz.Story(html_part, user_css=css, archive=archive)
        _, filled = head.place(box)
        _collect(positions, head)
        head.draw(device)
        bottom = max(bottom, fitz.Rect(filled).y1)
    story = fitz.Story(_body_html(record, digest), user_css=css, archive=archive)
    where = fitz.Rect(_BODY.x0, bottom, _BODY.x1, _BODY.y1)
    while True:
        more, _ = story.place(where)
        _collect(positions, story)
        story.draw(device)
        writer.end_page()
        if not more:
            break
        device = writer.begin_page(_PAGE)
        where = _BODY
    writer.close()
    return _decorate(buf.getvalue(), positions, font_file, _bold_font_file(), record, digest), digest


def principal_text(cccd: str | None, name: str | None) -> str:
    # Chủ thể dữ liệu = tài khoản VNeID đọc từ cổng: có CCCD thì ghi CCCD (+ tên); chỉ có tên thì ghi rõ cổng không cung
    # cấp số; không có gì → ghi nhận theo mã phiên, để biên bản trung thực.
    if cccd:
        return cccd + (f" — {name}" if name else "")
    if name:
        return f"{name} (cổng không cung cấp số định danh)"
    return "Không xác định được từ cổng (ghi nhận theo mã phiên)"


def build_consent_pdf(*, log_id: str, username: str | None, name: str | None, place: str | None,
                      procedure_label: str | None, version: str, statements: list[str],
                      optimize: bool = False, client_time: str | None, created_at: datetime,
                      principal_cccd: str | None = None, principal_name: str | None = None) -> tuple[bytes, dict]:
    """Biên bản kênh Auto Fill. Trả (PDF, phần lưu kèm bản ghi: notice + mã băm)."""
    notice = texts.autofill_notice(version, procedure_label)
    sent = list(statements or [])
    if notice:
        rows = [(s, s in sent) for s in notice["statements"]]
        optional = (notice["optional_statement"], bool(optimize))
        accept = notice["accept_label"]
    else:
        rows, optional, accept = [(s, True) for s in sent], None, "Đồng ý"
    at = created_at.astimezone(VN_TZ)
    record = {
        "so": log_id,
        "place": place or "",
        "at": at,
        "version": version,
        "info": [
            ("Chủ thể dữ liệu (VNeID)", principal_text(principal_cccd, principal_name)),
            ("Thủ tục", procedure_label or "(chưa xác định)"),
            ("Đơn vị tiếp nhận", name or ""),
            ("Tài khoản thực hiện", username or ""),
            ("Kênh thực hiện", "Auto Fill — cán bộ thao tác trên tiện ích trình duyệt"),
        ],
        "notice": notice,
        "statements": rows,
        "optional": optional,
        "result": [
            ("Kết quả", "ĐỒNG Ý"),
            ("Phương thức xác nhận", f"Bấm nút “{accept}” trên màn hình xác nhận"),
            ("Thời điểm phía người dùng", client_time or "(không gửi)"),
            ("Thời điểm máy chủ ghi nhận", f"{at:%H:%M:%S} ngày {at:%d/%m/%Y} (giờ Việt Nam)"),
        ],
    }
    pdf, digest = render(record)
    return pdf, {"notice": notice, "content_sha256": digest, "pdf_sha256": hashlib.sha256(pdf).hexdigest()}
