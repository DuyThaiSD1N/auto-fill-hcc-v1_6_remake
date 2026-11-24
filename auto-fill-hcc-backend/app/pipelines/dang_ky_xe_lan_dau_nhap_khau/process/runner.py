"""Compact agent pipeline cho thủ tục 1.013066 (Cổng DVC Bộ Công an).

Ba ô tải ảnh đầu trang kê khai (user 24/11/2026, ảnh trang thật): "Ảnh phương tiện (*)", "Ảnh chứng từ nguồn gốc mặt
trước (*)", "Ảnh chứng từ nguồn gốc mặt sau (*)" — cổng chỉ nhận .jpg / .png dưới 2 MB. Ô comp ``bca-photo`` (extension
gắn tệp vào input như ảnh chân dung hộ chiếu 1.001456). Auto Fill gắn ở lượt điền lẫn lượt "Đính kèm" (attach/planner.py
trả ``pageFields``); trợ lý tách hai việc (user 24/11): lượt điền KHÔNG gắn (``options.pagePhotosAtAttach``), nút "Đính
kèm giấy tờ" trên trang kê khai mới gắn. Chứng từ nguồn gốc xe nhập khẩu = tờ khai hàng hóa nhập
khẩu: mặt trước = trang tờ khai đầu tiên, mặt sau = trang tờ khai kế tiếp (thiếu thì trang liền sau trong cùng tệp).
Tên ô (name) thật chưa thấy → field mang ``match`` = cụm chữ trên ô đã bỏ dấu, extension tìm ô theo chữ / placeholder.
"""

import base64
import re

from app.pipelines._shared import fold
from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process import mapper
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

# (name gửi extension, cụm chữ trên ô — đã bỏ dấu, nhãn trong câu báo, tên tệp JPEG gắn vào ô)
VEHICLE_SLOT = ("AnhPhuongTien", "anh phuong tien", "Ảnh phương tiện", "anh_phuong_tien.jpg")
ORIGIN_FRONT_SLOT = ("AnhNguonGocMatTruoc", "nguon goc mat truoc", "Ảnh chứng từ nguồn gốc mặt trước",
                     "chung_tu_nguon_goc_mat_truoc.jpg")
ORIGIN_BACK_SLOT = ("AnhNguonGocMatSau", "nguon goc mat sau", "Ảnh chứng từ nguồn gốc mặt sau",
                    "chung_tu_nguon_goc_mat_sau.jpg")
PHOTO_MAX_SIDE = 1600  # đủ nét để đọc tờ khai; 3 ảnh JPEG cộng lại chỉ vài MB (phiên trợ lý lưu cả field)

# Ảnh chụp xe gần như không có chữ (biển số, logo vài ký tự); giấy tờ chụp luôn có hàng trăm chữ. Tên tệp nói rõ là
# ảnh xe thì nới ngưỡng (ảnh có dán tem, kính có chữ).
_VEHICLE_MAX_LETTERS = 80
_VEHICLE_NAMED_MAX_LETTERS = 200
_VEHICLE_NAME_RE = re.compile(r"(phuong ?tien|anh ?xe|xe ?may|o ?to|\boto\b|vehicle|\bcar\b|\bxe\b)")
_LETTER_RE = re.compile(r"[0-9A-Za-zÀ-ỹ]")
# Trang tờ khai hàng hóa nhập khẩu (bản in VNACCS lặp tiêu đề + "Số tờ khai" ở mọi trang).
_CUSTOMS_TITLE_RE = re.compile(r"to khai hang hoa nhap khau|to khai hai quan")
_CUSTOMS_HINTS = ("so to khai", "ma loai hinh", "nguoi nhap khau", "chi cuc hai quan", "co quan hai quan")
# Trang của giấy khác trong cùng tệp gộp — không lấy làm mặt sau tờ khai.
_OTHER_DOC_RE = re.compile(r"can cuoc|hoa don|le phi truoc ba|hop dong mua ban|giay khai dang ky xe|thu hoi dang ky")


def _letters(text: str) -> int:
    return len(_LETTER_RE.findall(text or ""))


def find_vehicle_photo(files: list[dict], texts: dict[int, str]) -> int | None:
    """Chỉ số tệp ảnh chụp phương tiện, None khi không có: tệp ảnh (hoặc PDF một ảnh) gần như không có chữ OCR; tên tệp
    "xe / phương tiện / ô tô" được ưu tiên. Nhiều ảnh khớp → ảnh ít chữ nhất."""
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.mapper import _image_bytes

    best: tuple[int, int, int] | None = None
    for index, file in enumerate(files or []):
        letters = _letters(texts.get(index, ""))
        stem = re.sub(r"[_\-.]+", " ", fold(str(file.get("name") or "")).rsplit(".", 1)[0])
        by_name = bool(_VEHICLE_NAME_RE.search(stem))
        if letters > (_VEHICLE_NAMED_MAX_LETTERS if by_name else _VEHICLE_MAX_LETTERS):
            continue
        if not _image_bytes(file):
            continue
        rank = (0 if by_name else 1, letters, index)
        if best is None or rank < best:
            best = rank
    return best[2] if best else None


def _customs_page(page: str) -> bool:
    text = fold(page)
    return bool(_CUSTOMS_TITLE_RE.search(text)) or ("hai quan" in text and sum(h in text for h in _CUSTOMS_HINTS) >= 2)


def find_origin_pages(pages_by_index: dict[int, list[str]], skip: set[int] = frozenset(), *,
                      is_origin=_customs_page) -> list[tuple[int, int]]:
    """(tệp, trang 0-based) của mặt trước, mặt sau chứng từ nguồn gốc — tối đa 2 mục. ``is_origin`` nhận ra trang chứng
    từ (mặc định tờ khai hàng hóa nhập khẩu; 1.012575 truyền trang Phiếu kiểm tra chất lượng xuất xưởng)."""
    found = [(index, number) for index in sorted(pages_by_index) if index not in skip
             for number, page in enumerate(pages_by_index[index] or []) if is_origin(page)]
    if len(found) == 1:
        index, number = found[0]
        pages = pages_by_index.get(index) or []
        # Mặt sau scan không lặp tiêu đề → lấy trang liền sau trong cùng tệp, trừ khi đó là trang của giấy khác.
        if number + 1 < len(pages) and not _OTHER_DOC_RE.search(fold(pages[number + 1])):
            found.append((index, number + 1))
    return found[:2]


def _photo_field(slot: tuple[str, str, str, str], image: bytes, source_name: str) -> dict:
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.mapper import portrait_jpeg

    name, match, label, file_name = slot
    jpeg = portrait_jpeg(image, max_side=PHOTO_MAX_SIDE)
    return {
        "name": name,
        "comp": "bca-photo",
        "match": match,
        "label": label,
        "value": {"name": file_name, "type": "image/jpeg",
                  "dataUrl": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")},
        "sourceFileName": source_name,
    }


ORIGIN_LABEL = "tờ khai hàng hóa nhập khẩu"


def missing_photo_note(missing: list[str], *, retry: str = "điền lại", origin: str = ORIGIN_LABEL) -> str:
    """Câu báo các ô ảnh chưa có ảnh trong bộ giấy (``retry``: lượt điền → "điền lại", lượt đính kèm → "đính kèm lại";
    ``origin``: tên chứng từ nguồn gốc của thủ tục)."""
    return ("Chưa có ảnh cho ô " + ", ".join(missing) + f" (ảnh chụp xe; hai mặt {origin}) — tải thêm "
            f"ảnh rồi {retry} để hệ thống tự gắn, hoặc bấm Tải ảnh trên cổng (.jpg / .png dưới 2 MB).")


def photo_fields(files: list[dict], texts: dict[int, str], *, is_origin=_customs_page,
                 origin: str = ORIGIN_LABEL) -> tuple[list[dict], list[str]]:
    """(ba ô ảnh đầu trang gắn được, câu báo) — câu báo nói rõ tệp nào vào ô nào và ô nào phải tải tay."""
    fields, done, missing = photo_slots(files, texts, is_origin=is_origin)
    notes = []
    if done:
        notes.append("Đã gắn ảnh vào ô đầu biểu mẫu (dạng .jpg): " + "; ".join(done)
                     + f" — kiểm tra đúng ảnh xe và hai mặt {origin}.")
    if missing:
        notes.append(missing_photo_note(missing, origin=origin))
    return fields, notes


def photo_slots(files: list[dict], texts: dict[int, str], *,
                is_origin=_customs_page) -> tuple[list[dict], list[str], list[str]]:
    """(ô ảnh gắn được, "nguồn → ô" của từng ô gắn được, nhãn các ô chưa có ảnh)."""
    from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.attach.dinh_kem_khong_tach.planner import (
        _page_image,
    )
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.mapper import _image_bytes
    from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_khong_tach.planner import ocr_pages

    fields: list[dict] = []
    done: list[str] = []
    missing: list[str] = []

    def add(slot, image: bytes | None, source_name: str, where: str) -> None:
        try:
            field = _photo_field(slot, image, source_name) if image else None
        except Exception:  # noqa: BLE001 — ảnh hỏng thì để công dân tải tay
            field = None
        if field:
            fields.append(field)
            done.append(f"{where} → ô {slot[2]}")
        else:
            missing.append(slot[2])

    def name_of(index: int) -> str:
        return str(files[index].get("name") or f"file-{index + 1}")

    vehicle = find_vehicle_photo(files, texts)
    if vehicle is None:
        missing.append(VEHICLE_SLOT[2])
    else:
        add(VEHICLE_SLOT, _image_bytes(files[vehicle]), name_of(vehicle), f"'{name_of(vehicle)}'")

    pages = {i: ocr_pages(t) for i, t in texts.items() if (t or "").strip()}
    origin = find_origin_pages(pages, skip={vehicle} if vehicle is not None else set(), is_origin=is_origin)
    for slot, hit in zip((ORIGIN_FRONT_SLOT, ORIGIN_BACK_SLOT), [*origin, None, None]):
        if hit is None:
            missing.append(slot[2])
            continue
        index, number = hit
        image, multi_page = _page_image(files[index], number)
        where = f"trang {number + 1} của '{name_of(index)}'" if multi_page else f"'{name_of(index)}'"
        add(slot, image, name_of(index), where)
    return fields, done, missing


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.services import ocr

    files = runner.flatten(files_by_role)
    # Giữ chữ OCR theo TỪNG tệp (runner chung chỉ trả bản gộp) để nhận ra ảnh xe / trang tờ khai hải quan.
    text_by_file: dict[int, str] = {}

    async def _ocr(ocr_files: list[dict]) -> list[dict]:
        results = await ocr.ocr_per_file(ocr_files)
        for file, result in zip(ocr_files, results):
            text_by_file[id(file)] = str(result.get("text") or "")
        return results

    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        ocr_fn=_ocr,
    )
    raw_fields = res["fields"]
    res["fields"], warnings = mapper.enrich(raw_fields, options)
    # Chủ xe trên giấy là người khác chủ tài khoản VNeID → không điền; `blocked` để Auto Fill / trợ lý hiện câu báo dễ
    # hiểu thay cho thông báo chung "không đọc được giấy tờ".
    blocked = mapper.account_block(mapper._by_name(raw_fields), options) if mapper.has_account_anchor(options) else None
    if blocked:
        res["blocked"] = blocked
    else:
        # Trợ lý tách điền / đính (user 24/11): ba ô ảnh gắn ở bước "Đính kèm giấy tờ" (attach/planner.py) → lượt điền
        # không gắn ảnh. Auto Fill gắn ở cả lượt điền lẫn lượt đính kèm như ảnh chân dung hộ chiếu.
        photos, notes = ([], []) if options.get("pagePhotosAtAttach") else photo_fields(
            files, {i: text_by_file.get(id(f), "") for i, f in enumerate(files)})
        res["fields"] = [*photos, *res["fields"]]
        # Câu "Tra cứu" thôi nhắc tự tải ảnh — ảnh do hệ thống gắn (câu báo ảnh nói ô nào gắn được, ô nào phải tải tay).
        warnings = [*notes, *(mapper.TRA_CUU_NO_PHOTO_WARNING if w == mapper.TRA_CUU_WARNING else w for w in warnings)]
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
