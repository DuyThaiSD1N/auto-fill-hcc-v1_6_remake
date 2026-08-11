"""Gộp giấy tùy thân (CCCD/CMND/hộ chiếu) CÙNG NGƯỜI thành 1 PDF — dùng chung cho thủ tục hộ tịch.

Người dân thường chụp CCCD 2 mặt thành 2 file rời (nhất là khi tải qua QR). Hàm này HẬU XỬ LÝ danh
sách attachments planner đã dựng: gom các item giấy tùy thân THEO SỐ ĐỊNH DANH rồi hợp mỗi người thành
1 item mang `sourceFileIndexes` (mặt trước→sau) để FE gộp bằng pdf-lib.

Khóa gom = SỐ ĐỊNH DANH (mặt trước có số 12 chữ số đứng riêng; mặt sau MRZ nhúng cả số đó trong dãy dài
nên ghép bằng cách "số mặt trước có nằm trong dãy số mặt sau"). → TUYỆT ĐỐI không gộp CCCD của 2 người
khác nhau. File không xác định được người (mặt sau OCR lỗi, thiếu số) → giữ nguyên item lẻ (an toàn).

Mỗi planner chỉ cần: thu `identity_indexes` (fileIndex là giấy tùy thân) + `ocr_text_by_index`, rồi gọi
`attachments = merge_identity_attachments(attachments, ocr_text_by_index, identity_indexes)` ở cuối.
"""
import re
import unicodedata

# Số định danh = đúng 12 chữ số ĐỨNG RIÊNG (MRZ mặt sau dính chuỗi dài → không khớp regex này).
_CCCD_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")

_FACE_FRONT_MARKERS = (
    "can cuoc cong dan", "citizen identity", "ho va ten", "full name",
    "ngay sinh", "date of birth", "gia tri den", "date of expiry",
)
_FACE_BACK_MARKERS = (
    "dac diem nhan dang", "personal identification", "cuc truong cuc canh sat",
    "director general", "idvnm",
)

# Nhận diện file LÀ thẻ CCCD/căn cước từ OCR (không tin phân loại của LLM). Bắt buộc phải riêng của THẺ
# thật để không dính tờ khai (tờ khai chỉ ghi "Thẻ CCCD số ..." bằng tiếng Việt, KHÔNG có các marker này):
#  - mặt trước: tiêu đề tiếng Anh "citizen identity"/"identity card" (chỉ in trên mặt thẻ);
#  - mặt sau: MRZ "idvnm" hoặc mục "đặc điểm nhận dạng" (chỉ có ở mặt sau thẻ).
_CCCD_FRONT_TITLE = ("citizen identity", "identity card")
_CCCD_BACK_TITLE = ("idvnm", "dac diem nhan dang")


def _looks_like_cccd(text: str) -> bool:
    folded = _fold(text)
    return any(m in folded for m in _CCCD_FRONT_TITLE) or any(m in folded for m in _CCCD_BACK_TITLE)


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value: str) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _cccd_number(text: str) -> str:
    """Số định danh 12 chữ số đứng riêng (mặt trước). Mặt sau chỉ có MRZ → thường rỗng."""
    m = _CCCD_RE.search(text or "")
    return m.group(0) if m else ""


def _id_in_digits(id_num: str, digits: str) -> bool:
    """Số định danh mặt trước có nằm trong dãy số của file (mặt sau MRZ nhúng cả số) — hoặc khớp 9 số cuối."""
    if not id_num or not digits:
        return False
    if id_num in digits:
        return True
    tail = id_num[-9:]
    return len(tail) >= 9 and tail in digits


def _face_rank(text: str) -> int:
    """Sắp thứ tự gộp trong 1 người: mặt trước (0) → mặt sau (1); không rõ (2, giữ theo index)."""
    folded = _fold(text)
    has_front = any(m in folded for m in _FACE_FRONT_MARKERS)
    has_back = any(m in folded for m in _FACE_BACK_MARKERS)
    if has_front and not has_back:
        return 0
    if has_back and not has_front:
        return 1
    return 2


def _person_of(text: str, persons: list[str]) -> str | None:
    """Gán file cho 1 người: file có số riêng (mặt trước) → chính số đó; file không số (mặt sau) → người
    mà số định danh của họ nằm trong dãy số của file. Không khớp ai → None (giữ lẻ)."""
    num = _cccd_number(text)
    if num:
        return num
    digits = _digits(text)
    for p in persons:
        if _id_in_digits(p, digits):
            return p
    return None


def merge_identity_attachments(
    attachments: list[dict],
    ocr_text_by_index: dict[int, str],
    identity_indexes,
) -> list[dict]:
    """Gộp các item giấy tùy thân CÙNG NGƯỜI. Trả list attachments MỚI.

    - attachments: list item planner đã dựng (mỗi item 1 file), cần có 'fileIndex'.
    - ocr_text_by_index: {fileIndex: ocr_text}.
    - identity_indexes: tập fileIndex là giấy tùy thân.

    Item không phải giấy tùy thân giữ nguyên. Giấy tùy thân cùng người: giữ item ĐẦU (ưu tiên item đã
    vào ô CÓ SẴN để không mất slot), gắn sourceFileIndexes = các file người đó (mặt trước→sau), bỏ item
    dư. File không khớp người nào → giữ nguyên item lẻ.
    """
    # Ứng viên = giấy tùy thân planner gắn (identity_indexes) HỢP với file TỰ nhận diện là thẻ CCCD từ
    # OCR. Cần vế sau vì LLM hay phân loại MẶT SAU CCCD (chỉ có MRZ, thiếu tiêu đề "Căn cước công dân")
    # thành 'other' → nếu chỉ dựa identity_indexes sẽ sót mặt sau, không gộp được.
    id_set = set(identity_indexes or [])
    for a in attachments:
        fi = a.get("fileIndex")
        if fi is not None and fi not in id_set and _looks_like_cccd(ocr_text_by_index.get(fi, "")):
            id_set.add(fi)
    id_items = [a for a in attachments if a.get("fileIndex") in id_set]
    if len(id_items) < 2:
        return attachments  # 0/1 giấy tùy thân → không có gì để gộp

    # Danh sách "người" = các số định danh đọc được ở mặt trước (theo thứ tự xuất hiện).
    persons: list[str] = []
    for a in id_items:
        num = _cccd_number(ocr_text_by_index.get(a["fileIndex"], ""))
        if num and num not in persons:
            persons.append(num)

    person_by_file: dict[int, str | None] = {
        a["fileIndex"]: _person_of(ocr_text_by_index.get(a["fileIndex"], ""), persons)
        for a in id_items
    }

    # Gom item theo người (bỏ qua file không khớp người → giữ lẻ).
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for a in id_items:
        p = person_by_file[a["fileIndex"]]
        if p is None:
            continue
        if p not in groups:
            groups[p] = []
            order.append(p)
        groups[p].append(a)

    def _merge_group(items: list[dict]) -> dict:
        if len(items) == 1:
            return items[0]
        ordered = sorted(
            items,
            key=lambda a: (_face_rank(ocr_text_by_index.get(a["fileIndex"], "")), a["fileIndex"]),
        )
        source_indexes = [a["fileIndex"] for a in ordered]
        # Giữ item đã vào ô CÓ SẴN (target 'existing') để không mất slot; nếu không có thì lấy item ĐẦU
        # theo thứ tự gốc — item này mang tên GỐC (chưa bị dedup thêm hậu tố " 2"), tên gộp sẽ sạch.
        primary = next((a for a in items if a.get("target") == "existing"), items[0])
        return {**primary, "fileIndex": source_indexes[0], "sourceFileIndexes": source_indexes}

    merged_by_person = {p: _merge_group(groups[p]) for p in order}

    # Dựng lại theo thứ tự gốc: mỗi người chỉ phát 1 item gộp (tại vị trí item đầu tiên của người đó).
    emitted: set[str] = set()
    out: list[dict] = []
    for a in attachments:
        if a.get("fileIndex") not in id_set:
            out.append(a)
            continue
        p = person_by_file.get(a["fileIndex"])
        if p is None:
            out.append(a)  # không khớp người → giữ item lẻ
            continue
        if p in emitted:
            continue  # đã phát item gộp cho người này
        emitted.add(p)
        out.append(merged_by_person[p])
    return out
