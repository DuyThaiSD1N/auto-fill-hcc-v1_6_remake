"""Đính kèm [Lào Cai] đăng ký đất đai, cấp GCN LẦN ĐẦU cho hộ gia đình, cá nhân (1.115689).

Cổng `dichvucong.laocai.gov.vn` (eForm iGate). Trang đính kèm có **33 `input[type=file]`** theo thứ
tự DOM: 29 dòng thành phần hồ sơ + 3 ô "Giấy tờ khác" (29–31) + `HoSoOnline_fileGiayToKhac` (32).

29 dòng chia BA NHÓM LOẠI TRỪ NHAU, mỗi nhóm mở đầu bằng một DÒNG TIÊU ĐỀ (bản thân dòng tiêu đề
cũng có ô upload nhưng không bao giờ nhận tệp):

  0      a) hộ gia đình, cá nhân, cộng đồng dân cư          (tiêu đề)
  1–16   các thành phần của nhóm a)
  17     b) người gốc Việt Nam định cư ở nước ngoài         (tiêu đề)
  18–25  các thành phần của nhóm b)
  26     c) đã có Thông báo xác nhận kết quả đăng ký đất đai (tiêu đề)
  27–28  các thành phần của nhóm c)

⚑ BA DÒNG "Đơn đăng ký … Mẫu số 21" TRÙNG TÊN HỆT NHAU (slot 1, 18, 27) → khớp theo text là không
thể, bắt buộc dùng `slotIndex`; slotKey cố ý không nằm trong `FIXED_SLOT_KEYWORDS` của extension.

⚑ CHỌN NHÓM TẤT ĐỊNH: có "Thông báo xác nhận kết quả đăng ký đất đai" → nhóm **c**; còn lại → nhóm
**a**. KHÔNG tự chọn nhóm b: không giấy tờ nào trong hồ sơ chứng minh người sử dụng đất là người gốc
Việt Nam định cư ở nước ngoài, đoán là bịa — planner luôn cảnh báo đã xếp nhóm nào để cán bộ đổi.

⚑ Giấy tờ NGOÀI danh mục dùng `target="new"` + `needsAddComponent=True`: trang có
`input[name="HoSoOnline_giayToKhac[]"]` nên FE chạy `attachOneFileToOtherListFile` — engine điền cả
TÊN tài liệu rồi mới đính tệp.

Phân loại THUẦN LLM (không lưới keyword). Mỗi tệp chỉ đính vào MỘT dòng. Không bỏ sót tệp nào.
"""

import asyncio
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"

_NHOM_A = "a"
_NHOM_B = "b"
_NHOM_C = "c"

# Tên dòng rút gọn cho cảnh báo/hiển thị; FE đi bằng slotIndex nên không cần nguyên văn cả đoạn dài.
_SLOT_NAMES = {
    1: "Đơn đăng ký đất đai, tài sản gắn liền với đất theo Mẫu số 21 (nhóm a)",
    2: "Một trong các loại giấy tờ quy định tại Điều 137, khoản 1 khoản 5 Điều 148, Điều 149 (nhóm a)",
    3: "Văn bản cam kết/thỏa thuận của những người nhận thừa kế",
    4: "Giấy tờ về việc nhận thừa kế quyền sử dụng đất",
    5: "Giấy tờ về giao đất không đúng thẩm quyền hoặc mua, thanh lý, hóa giá, phân phối nhà ở",
    6: "Quyết định xử phạt vi phạm hành chính trong lĩnh vực đất đai",
    7: "Hợp đồng, văn bản thỏa thuận, quyết định của Tòa án về quyền đối với thửa đất liền kề",
    8: "Văn bản xác định các thành viên có chung quyền sử dụng đất của hộ gia đình",
    9: "Mảnh trích đo bản đồ địa chính thửa đất (nếu có)",
    10: "Hồ sơ thiết kế xây dựng công trình đã được thẩm định (nhóm a)",
    11: "Quyết định xử phạt theo điểm a khoản 6 Điều 25 Nghị định 101/2024/NĐ-CP",
    12: "Chứng từ đã thực hiện nghĩa vụ tài chính, giấy tờ miễn giảm (nhóm a)",
    13: "Giấy tờ về việc chuyển quyền sử dụng đất có chữ ký của bên chuyển và bên nhận",
    14: "Giấy xác nhận của cơ quan quản lý xây dựng cấp huyện về đủ điều kiện tồn tại nhà ở",
    15: "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận (nhóm a)",
    16: "Văn bản về việc đại diện theo quy định của pháp luật về dân sự (nhóm a)",
    18: "Đơn đăng ký đất đai, tài sản gắn liền với đất theo Mẫu số 21 (nhóm b)",
    19: "Một trong các loại giấy tờ quy định tại Điều 137, khoản 4 khoản 5 Điều 148, Điều 149 (nhóm b)",
    20: "Giấy tờ về việc nhận thừa kế quyền sử dụng đất (nhóm b)",
    21: "Mảnh trích đo bản đồ địa chính thửa đất (nếu có) (nhóm b)",
    22: "Hồ sơ thiết kế xây dựng công trình đã được thẩm định (nhóm b)",
    23: "Chứng từ thực hiện nghĩa vụ tài chính, giấy tờ miễn giảm (nhóm b)",
    24: "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận (nhóm b)",
    25: "Văn bản về việc đại diện theo quy định của pháp luật về dân sự (nhóm b)",
    27: "Đơn đăng ký đất đai, tài sản gắn liền với đất theo Mẫu số 21 (nhóm c)",
    28: "Thông báo xác nhận kết quả đăng ký đất đai",
}

# docType → slotIndex theo từng nhóm. Loại nào nhóm đó không có dòng thì để trống.
_ROUTES: dict[str, dict[str, int]] = {
    "don_mau_21":                  {_NHOM_A: 1, _NHOM_B: 18, _NHOM_C: 27},
    "giay_to_dieu_137":            {_NHOM_A: 2, _NHOM_B: 19},
    "van_ban_cam_ket_thua_ke":     {_NHOM_A: 3},
    "giay_to_thua_ke":             {_NHOM_A: 4, _NHOM_B: 20},
    "giao_dat_khong_dung_tham_quyen": {_NHOM_A: 5},
    "qd_xu_phat":                  {_NHOM_A: 6},
    "thua_dat_lien_ke":            {_NHOM_A: 7},
    "van_ban_thanh_vien_ho_gia_dinh": {_NHOM_A: 8},
    # Bản mô tả ranh giới, mốc giới thửa đất (Phụ lục 12) KHÔNG phải mảnh trích đo, nhưng nghiệp vụ
    # vẫn đính thay thế vào đúng dòng này và bắt buộc ghi rõ ở ô "Ghi chú".
    "manh_trich_do":               {_NHOM_A: 9, _NHOM_B: 21},
    "ban_mo_ta_ranh_gioi":         {_NHOM_A: 9, _NHOM_B: 21},
    "ho_so_thiet_ke_xay_dung":     {_NHOM_A: 10, _NHOM_B: 22},
    "chung_tu_tai_chinh":          {_NHOM_A: 12, _NHOM_B: 23},
    "giay_to_chuyen_quyen":        {_NHOM_A: 13},
    "giay_xac_nhan_nha_o":         {_NHOM_A: 14},
    "thoa_thuan_cap_chung_gcn":    {_NHOM_A: 15, _NHOM_B: 24},
    "van_ban_dai_dien":            {_NHOM_A: 16, _NHOM_B: 25},
    "thong_bao_ket_qua_dang_ky":   {_NHOM_C: 28},
}
_DISPLAY = {
    "don_mau_21": "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 21)",
    "giay_to_dieu_137": "Giấy tờ về quyền sử dụng đất theo Điều 137 Luật Đất đai",
    "van_ban_cam_ket_thua_ke": "Văn bản cam kết, thỏa thuận của những người nhận thừa kế",
    "giay_to_thua_ke": "Giấy tờ về việc nhận thừa kế quyền sử dụng đất",
    "giao_dat_khong_dung_tham_quyen": "Giấy tờ về giao đất không đúng thẩm quyền, mua, thanh lý, hóa giá nhà ở",
    "qd_xu_phat": "Quyết định xử phạt vi phạm hành chính trong lĩnh vực đất đai",
    "thua_dat_lien_ke": "Giấy tờ xác lập quyền đối với thửa đất liền kề",
    "van_ban_thanh_vien_ho_gia_dinh": "Văn bản xác định các thành viên có chung quyền sử dụng đất",
    "manh_trich_do": "Mảnh trích đo bản đồ địa chính thửa đất",
    "ban_mo_ta_ranh_gioi": "Bản mô tả ranh giới, mốc giới thửa đất",
    "ho_so_thiet_ke_xay_dung": "Hồ sơ thiết kế xây dựng công trình",
    "chung_tu_tai_chinh": "Chứng từ thực hiện nghĩa vụ tài chính",
    "giay_to_chuyen_quyen": "Giấy tờ về việc chuyển quyền sử dụng đất",
    "giay_xac_nhan_nha_o": "Giấy xác nhận đủ điều kiện tồn tại nhà ở, công trình xây dựng",
    "thoa_thuan_cap_chung_gcn": "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận",
    "van_ban_dai_dien": "Văn bản về việc đại diện",
    "thong_bao_ket_qua_dang_ky": "Thông báo xác nhận kết quả đăng ký đất đai",
}
_ALLOWED = set(_ROUTES) | {"other"}

# Thứ tự phủ dòng: Đơn Mẫu 21 là giấy tờ bắt buộc số một → tệp gộp luôn ưu tiên dòng này.
_ROW_PRIORITY = (
    "don_mau_21",
    "giay_to_dieu_137",
    "giay_to_chuyen_quyen",
    "giay_to_thua_ke",
    "manh_trich_do",
    "ban_mo_ta_ranh_gioi",
    "thong_bao_ket_qua_dang_ky",
    "van_ban_thanh_vien_ho_gia_dinh",
    "van_ban_cam_ket_thua_ke",
    "giao_dat_khong_dung_tham_quyen",
    "qd_xu_phat",
    "thua_dat_lien_ke",
    "ho_so_thiet_ke_xay_dung",
    "chung_tu_tai_chinh",
    "giay_xac_nhan_nha_o",
    "thoa_thuan_cap_chung_gcn",
    "van_ban_dai_dien",
)


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _canon(value: Any) -> str:
    return re.sub(r"[_\-\s]+", "_", _fold(value)).strip("_")


def _normalize_doc_type(value: Any) -> str:
    canon = _canon(value)
    for doc_type in _ALLOWED:
        if canon == _canon(doc_type):
            return doc_type
    return "other"


def _normalize_also(values: Any, primary: str) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        doc_type = _normalize_doc_type(value)
        if doc_type not in ("other", primary) and doc_type not in out:
            out.append(doc_type)
    return out


def _other_component_name(file_name: str) -> str:
    """Tên dòng 'Giấy tờ khác' — engine otherListFile điền chuỗi này vào ô tên tài liệu."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return normalize_document_name(stem, "Tài liệu khác kèm theo") if stem else "Tài liệu khác kèm theo"


def _chon_nhom(doc_types: list[str]) -> str:
    """Có Thông báo xác nhận kết quả đăng ký đất đai → nhóm c); còn lại mặc định nhóm a)."""
    return _NHOM_C if "thong_bao_ket_qua_dang_ky" in doc_types else _NHOM_A


async def _classify_one(document: dict[str, Any]) -> tuple[int, str, list[str]]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(
            [{"index": index, "text": str(document.get("text") or "")[:14000]}]
        )},
    ]
    raw = await client.chat(messages, max_tokens=200, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    doc_type = _normalize_doc_type(first.get("docType") or first.get("type"))
    return index, doc_type, _normalize_also(first.get("alsoTypes"), doc_type)


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, tuple[str, list[str]]]:
    if not documents:
        return {}
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, tuple[str, list[str]]] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type, also = outcome
        result[index] = (doc_type, also)
    return result


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    thay_the: list[str] = []
    by_slot: dict[int, list[str]] = {}
    da_dung: set[str] = set()

    resolved: list[tuple[int, str, str, list[str], str]] = []
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        doc_type, also = raw if isinstance(raw, tuple) else (raw, [])
        if doc_type not in _ALLOWED:
            doc_type = "other"
        also = _normalize_also(also, doc_type) if doc_type != "other" else []
        resolved.append((index, file_name, doc_type, also, "llm" if index in llm_types else "default"))

    nhom = _chon_nhom([t for _, _, t, _, _ in resolved])

    for index, file_name, doc_type, also, source in resolved:
        if doc_type == "other":
            component_name = _other_component_name(file_name)
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": component_name,
                "componentName": component_name,
                "loaiBan": _LOAI_BAN,
                # Engine otherListFile của FE điền TÊN tài liệu rồi mới đính tệp.
                "target": "new",
                "needsAddComponent": True,
                "detectedType": doc_type,
            })
            unknown.append(file_name)
            classified.append({
                "fileName": file_name, "docType": doc_type, "alsoTypes": also,
                "assignedType": None, "nhom": nhom, "source": source, "slotIndex": None,
            })
            continue

        # Mỗi tệp CHỈ một dòng; tệp gộp dùng để phủ dòng còn trống, ưu tiên Đơn Mẫu 21. Chỉ xét loại
        # có dòng trong nhóm đã chọn — nhóm a/b/c không dùng chung dòng nào.
        ung_vien = [t for t in _ROW_PRIORITY
                    if t in (doc_type, *also) and nhom in _ROUTES[t] and t not in da_dung]
        chon = ung_vien[0] if ung_vien else (doc_type if nhom in _ROUTES[doc_type] else None)

        if chon is None:
            # Loại giấy tờ có thật nhưng nhóm đang chọn không có dòng tương ứng → vẫn phải lên hồ sơ.
            component_name = _DISPLAY[doc_type]
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": component_name,
                "componentName": component_name,
                "loaiBan": _LOAI_BAN,
                "target": "new",
                "needsAddComponent": True,
                "detectedType": doc_type,
            })
            unknown.append(f"{file_name} ({component_name})")
            classified.append({
                "fileName": file_name, "docType": doc_type, "alsoTypes": also,
                "assignedType": None, "nhom": nhom, "source": source, "slotIndex": None,
            })
            continue

        slot_index = _ROUTES[chon][nhom]
        slot_name = _SLOT_NAMES[slot_index]
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            # Giữ TÊN THẬT của giấy tờ: hồ sơ mẫu có bản mô tả ranh giới đính thay cho mảnh trích đo,
            # ghi đúng tên để cán bộ biết dòng đó đang là tệp thay thế.
            "documentName": _DISPLAY[chon],
            "componentName": slot_name,
            "loaiBan": _LOAI_BAN,
            "target": "fixed-slot",
            "needsAddComponent": False,
            # Cố ý không trùng FIXED_SLOT_KEYWORDS của extension để FE đi thẳng theo slotIndex.
            "slotKey": f"laocai_lda_{chon}_{nhom}",
            "slotIndex": slot_index,
            "slotName": slot_name,
            "detectedType": doc_type,
        })
        by_slot.setdefault(slot_index, []).append(file_name)
        da_dung.add(chon)
        if chon == "ban_mo_ta_ranh_gioi":
            thay_the.append(file_name)
        classified.append({
            "fileName": file_name, "docType": doc_type, "alsoTypes": also,
            "assignedType": chon, "nhom": nhom, "source": source, "slotIndex": slot_index,
        })

    if attachments:
        warnings.append(
            f"Hồ sơ được xếp theo NHÓM {nhom.upper()}) "
            + ("(đã có Thông báo xác nhận kết quả đăng ký đất đai)." if nhom == _NHOM_C
               else "(hộ gia đình, cá nhân, cộng đồng dân cư).")
            + " Ba nhóm a) b) c) LOẠI TRỪ NHAU — cán bộ bỏ tích các dòng của nhóm còn lại. Người sử "
              "dụng đất là NGƯỜI GỐC VIỆT NAM ĐỊNH CƯ Ở NƯỚC NGOÀI thì chuyển sang nhóm b), hệ thống "
              "không tự nhận ra điều này từ giấy tờ."
        )
    if thay_the:
        warnings.append(
            "ĐÍNH KÈM THAY THẾ: " + ", ".join(thay_the) + " là Bản mô tả ranh giới, mốc giới thửa đất "
            "(không phải mảnh trích đo) nhưng được đính vào dòng \"Mảnh trích đo bản đồ địa chính thửa "
            "đất (nếu có)\" — BẮT BUỘC ghi rõ việc này vào ô \"Ghi chú\" ở phần Thông tin khác."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ hoặc nhóm đang chọn không có dòng tương ứng, đã thêm dòng "
            f"\"Giấy tờ khác\" kèm tên tài liệu để không bỏ sót: {', '.join(unknown)}."
        )
    for slot_index, names in by_slot.items():
        unique = list(dict.fromkeys(names))
        if len(unique) > 1:
            warnings.append(
                f"Dòng \"{_SLOT_NAMES[slot_index]}\" nhận {len(unique)} tệp ({', '.join(unique)}) — "
                "kiểm tra lại số bản khai trên bảng thành phần hồ sơ."
            )
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, tuple[str, list[str]]] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
