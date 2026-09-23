"""Đính kèm cho thủ tục Chứng thực chữ ký — TÁCH RIÊNG khỏi chứng thực bản sao.

Form chứng thực chữ ký có 2 thành phần hồ sơ CỐ ĐỊNH:
  - STT1: Giấy tờ, văn bản cần chứng thực chữ ký (+ bản dịch nếu có).
  - STT2: Giấy tùy thân (Căn cước điện tử / Thẻ CCCD / Căn cước / Hộ chiếu / giấy tờ XNC...).

Quy tắc định tuyến (khác hẳn bản sao — bản sao chỉ có 1 ô có sẵn):
  - File KHÔNG phải giấy tùy thân → STT1: cái đầu vào ô có sẵn #1, các cái sau → thành phần mới.
  - Giấy tùy thân cùng chủ thể → gộp mặt trước/sau; mỗi chủ thể là một dòng riêng.
  - TUYỆT ĐỐI không để giấy tùy thân vào ô #1.

OCR toàn bộ file trong một batch, phân đoạn mọi trang bằng đúng một request LLM. Phần nhận dạng
trang dùng chung helper với chứng thực bản sao; logic gom và xếp STT1/STT2 là đặc thù thủ tục này.
"""
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines._shared.identity_merge import merge_identity_attachments, merge_identity_records
from app.pipelines._shared.naming import GENERIC_DOCUMENT_TYPE as _GENERIC_DOCUMENT_TYPE
from app.pipelines.chung_thuc_ban_sao.attach.planner import (
    _pdf_page_count,
    _preserve_source_file_segments,
    _segment_text,
    _source_segment,
    _split_ocr_pages,
    _validated_segments,
    _coerce_llm_document_info,
    _unique_document_name,
    canonical_document_type,
    detect_document_type,
)
from app.pipelines.chung_thuc_chu_ky.attach import preserve_prompt, prompt as chu_ky_prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

# Tên 2 ô cố định — đặt bằng đoạn text CÓ trong dòng tương ứng trên form để extension
# khớp ô theo componentTextMatches (rowText.includes(want)).
SIGNATURE_DOC_COMPONENT = "Giấy tờ, văn bản mà mình sẽ yêu cầu chứng thực chữ ký"
IDENTITY_COMPONENT = (
    "Một trong các giấy tờ sau: Căn cước điện tử; bản chính hoặc bản sao của Thẻ căn cước "
    "công dân hoặc Thẻ căn cước hoặc Giấy chứng nhận căn cước hoặc Hộ chiếu"
)

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Từ khóa giấy tùy thân — CHỈ dùng khi classifier CHƯA xác định được loại (detected generic/rỗng).
# KHÔNG dò từ khóa khi đã biết loại: văn bản ủy quyền / khai sinh / kết hôn... hay chứa số CCCD của
# đương sự → nếu dò sẽ nhận nhầm thành giấy tùy thân (đúng bẫy prompt LLM đã cảnh báo).
_IDENTITY_KEYWORDS_FOLDED = (
    "giay to tuy than",
    "can cuoc cong dan",
    "the can cuoc",
    "can cuoc dien tu",
    "giay chung nhan can cuoc",
    "cccd",
    "chung minh nhan dan",
    "ho chieu",
    "passport",
    "giay thong hanh",
    "xuat nhap canh",
    "giay to co gia tri di lai quoc te",
)


def _normalize_identity_number(value: Any) -> str:
    """Chuẩn hóa khóa ghép nhưng vẫn giữ chữ của số hộ chiếu."""
    return re.sub(r"[^0-9A-Z]+", "", str(value or "").upper())


def _validated_identity_number(value: Any, ocr_text: str) -> str:
    """Chỉ nhận số giấy tờ nếu chính OCR của file/đoạn có chứa số đó."""
    normalized = _normalize_identity_number(value)
    if len(normalized) < 6:
        return ""
    normalized_ocr = _normalize_identity_number(ocr_text)
    return normalized if normalized in normalized_ocr else ""


def _normalize_person_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _fold(str(value or "")))


def _validated_person_name(value: Any, ocr_text: str) -> str:
    """Tên là khóa phụ; không cho LLM lấy tên từ file bên cạnh trong batch."""
    name = re.sub(r"\s+", " ", str(value or "")).strip()
    name_key = _normalize_person_key(name)
    ocr_key = _normalize_person_key(ocr_text)
    return name if len(name_key) >= 5 and name_key in ocr_key else ""


def _validated_identity_holders(value: Any, ocr_text: str) -> list[dict[str, str]]:
    holders: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    if not isinstance(value, list):
        return holders
    for raw in value:
        if not isinstance(raw, dict):
            continue
        number = _validated_identity_number(raw.get("identityNumber"), ocr_text)
        name = _validated_person_name(raw.get("name"), ocr_text)
        # Không có cả số lẫn tên thì object không đủ làm khóa ghép và phải bị bỏ.
        if not number and not name:
            continue
        key = (number, _fold(name))
        if key in seen:
            continue
        seen.add(key)
        holders.append({
            "name": name,
            "identityNumber": number,
            "documentType": re.sub(r"\s+", " ", str(raw.get("documentType") or "")).strip(),
        })
    return holders


def _restore_relationship_metadata(segments: list[dict], raw_segments: list[dict]) -> list[dict]:
    """Khôi phục metadata riêng của chữ ký sau validator dùng chung.

    Validator dùng chung cố ý chỉ giữ contract phân đoạn phổ quát. Không mở rộng helper đó vì sẽ
    tác động mọi thủ tục; planner này ghép lại metadata bằng khóa file + khoảng trang đã kiểm tra.
    """
    raw_by_range: dict[tuple[int, int, int], dict] = {}
    raw_by_file: dict[int, list[dict]] = {}
    for raw in raw_segments:
        if not isinstance(raw, dict):
            continue
        try:
            file_index = int(raw.get("fileIndex", raw.get("index")))
            page_from = int(raw.get("pageFrom") or 1)
            page_to = int(raw.get("pageTo") or page_from)
        except (TypeError, ValueError):
            continue
        raw_by_range[(file_index, page_from, page_to)] = raw
        raw_by_file.setdefault(file_index, []).append(raw)

    restored: list[dict] = []
    for segment in segments:
        key = (segment["fileIndex"], segment["pageFrom"], segment["pageTo"])
        raw = raw_by_range.get(key)
        if raw is None and len(raw_by_file.get(segment["fileIndex"], [])) == 1:
            # Provider đôi lúc bỏ pageTo. Chỉ fallback theo file khi đúng một object nên không thể
            # lấy metadata của đoạn khác trong cùng file.
            raw = raw_by_file[segment["fileIndex"]][0]
        raw = raw or {}
        restored.append({
            **segment,
            "signerName": str(raw.get("signerName") or "").strip(),
            "signerIdentityNumber": str(raw.get("signerIdentityNumber") or "").strip(),
            "relatedIdentityNumbers": raw.get("relatedIdentityNumbers")
            if isinstance(raw.get("relatedIdentityNumbers"), list)
            else [],
            "identityHolders": raw.get("identityHolders")
            if isinstance(raw.get("identityHolders"), list)
            else [],
        })
    return restored


def _is_identity(detected: str, ocr_text: str, file_name: str) -> bool:
    """Có phải giấy tùy thân (route STT2) không.

    Ưu tiên TIN classifier: nhãn đúng nhóm căn cước/hộ chiếu/XNC → tùy thân; nhãn là loại KHÁC đã
    xác định (ủy quyền, khai sinh, kết hôn, hợp đồng...) → KHÔNG phải, kể cả khi text nhắc CCCD.
    Chỉ khi detected generic/rỗng mới dò từ khóa OCR/tên file.
    """
    detected_folded = _fold(detected or "")
    if any(keyword in detected_folded for keyword in _IDENTITY_KEYWORDS_FOLDED):
        return True
    if detected and detected != _GENERIC_DOCUMENT_TYPE:
        return False
    haystack = _fold((ocr_text or "") + "\n" + (file_name or ""))
    return any(kw in haystack for kw in _IDENTITY_KEYWORDS_FOLDED)


# STT2 là dòng giấy tùy thân có sẵn: chỉ chủ thể đầu dùng dòng này. Các chủ thể sau được thêm dòng;
# helper đối chiếu số định danh mặt trước với MRZ mặt sau để chỉ gộp đúng hai mặt cùng người.


def build_plan_items(
    files: list[dict], ocr_results: list[dict], llm_types: dict[int, Any] | None = None
) -> list[dict]:
    llm_types = llm_types or {}
    # OCR service trả đúng thứ tự input. Không map bằng tên vì hai file cùng tên "image.pdf"
    # vẫn là hai nguồn độc lập và phải nhận đúng OCR theo vị trí.
    by_index = {index: item for index, item in enumerate(ocr_results)}

    # 1) Nhận dạng loại + giấy tùy thân? cho từng file (giữ thứ tự gốc).
    docs: list[dict] = []
    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        ocr_item = by_index.get(idx, {})
        ocr_text = str(ocr_item.get("text") or "")

        llm_info = _coerce_llm_document_info(llm_types[idx]) if idx in llm_types else {"detectedType": "", "documentName": ""}
        llm_detected = llm_info["detectedType"]
        if llm_detected == _GENERIC_DOCUMENT_TYPE and llm_info["documentName"]:
            llm_detected = canonical_document_type(llm_info["documentName"])
        rule_detected = detect_document_type(ocr_text, file_name)
        # ƯU TIÊN LLM hơn rule: LLM đọc toàn văn OCR nên ít nhầm hơn rule keyword → LLM trả gì
        # dùng nấy; chỉ khi LLM trống mới dùng rule; cả hai trống → generic.
        detected = (
            llm_detected
            if llm_detected and llm_detected != _GENERIC_DOCUMENT_TYPE
            else rule_detected
        )
        detected = detected or _GENERIC_DOCUMENT_TYPE

        docs.append({
            "index": idx,
            "fileName": file_name,
            "detectedType": detected,
            "documentName": llm_info["documentName"] or normalize_document_name(file_name, detected),
            "componentBaseName": llm_info["documentName"] or detected,
            "isIdentity": _is_identity(detected, ocr_text, file_name),
            "ocrText": ocr_text,
        })

    # 2) Chia 2 nhóm, GIỮ THỨ TỰ: giấy tờ (STT1) và giấy tùy thân (STT2).
    doc_bucket = [d for d in docs if not d["isIdentity"]]
    id_bucket = [d for d in docs if d["isIdentity"]]

    used_document_names: set[str] = set()
    used_component_names: set[str] = set()
    items: list[dict] = []

    def _emit_unit(unit: list[dict], *, existing_index: int | None, existing_component: str) -> None:
        """Một đơn vị đính kèm. unit>1 file → FE gộp thành 1 PDF (sourceFileIndexes, mặt trước→sau).
        Tên tài liệu/thành phần lấy theo file ĐẦU unit (mặt trước, thường có tiêu đề rõ)."""
        primary = unit[0]
        source_indexes = [d["index"] for d in unit]
        document_name = _unique_document_name(
            primary.get("documentName") or primary["detectedType"], used_document_names, primary["detectedType"]
        )
        if existing_index is not None:
            component_name = existing_component
            target = "existing"
            component_index: int | None = existing_index
            needs_add = False
        else:
            base = primary.get("componentBaseName") or document_name
            if _fold(base) == _fold(_GENERIC_DOCUMENT_TYPE):
                # OCR trống/không phân loại được → base = "Tài liệu chứng thực" cho MỌI file. Đánh số tên
                # THÀNH PHẦN bằng bộ đếm RIÊNG sẽ lệch pha với documentName và sinh tên trần "Tài liệu
                # chứng thực" — bị FE (khớp substring 2 chiều ở attachmentKeyMatches) coi là trùng của
                # "Tài liệu chứng thực 2/3…" nên bỏ sót file. Dùng THẲNG documentName đã đánh số duy nhất.
                component_name = document_name
                used_component_names.add(_fold(component_name))
            else:
                component_name = _unique_document_name(
                    base, used_component_names, primary["detectedType"]
                )
            target = "new"
            component_index = None
            needs_add = True
        item = {
            "fileIndex": primary["index"],
            "fileName": primary["fileName"],
            "documentName": document_name,
            "componentName": component_name,
            "target": target,
            "componentIndex": component_index,
            "needsAddComponent": needs_add,
            "detectedType": primary["detectedType"],
        }
        # CHỈ gắn khi >1 để không đổi hành vi file lẻ (FE coi thiếu field = [fileIndex]).
        if len(source_indexes) > 1:
            item["sourceFileIndexes"] = source_indexes
        items.append(item)

    # STT1: mỗi giấy tờ 1 đơn vị (không gộp). Cái đầu → ô #1, còn lại → thành phần mới.
    for pos, doc in enumerate(doc_bucket):
        _emit_unit([doc], existing_index=1 if pos == 0 else None, existing_component=SIGNATURE_DOC_COMPONENT)
    # STT2 chỉ nhận chủ thể đầu tiên. Mặt trước/sau cùng người được helper gộp; người thứ hai trở đi
    # thành component mới, tuyệt đối không trộn hai số định danh vào cùng PDF.
    for pos, doc in enumerate(id_bucket):
        _emit_unit(
            [doc],
            existing_index=2 if pos == 0 else None,
            existing_component=IDENTITY_COMPONENT,
        )
    items = merge_identity_attachments(
        items,
        {doc["index"]: doc["ocrText"] for doc in id_bucket},
        {doc["index"] for doc in id_bucket},
    )

    # Sắp: ô có sẵn trước (theo componentIndex), rồi tới thành phần mới — theo fileIndex cho ổn định.
    items.sort(key=lambda it: (
        0 if it["target"] == "existing" else 1,
        it["componentIndex"] or 0,
        it["fileIndex"],
    ))
    return items


async def _classify_documents_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    """Phân đoạn toàn bộ file/trang bằng đúng một request LLM."""
    if not documents:
        return []
    page_total = sum(len(item.get("pages") or []) for item in documents)
    raw = await client.chat(
        [
            {"role": "system", "content": chu_ky_prompt.SYSTEM_PROMPT},
            {"role": "user", "content": chu_ky_prompt.build_user_prompt(documents)},
        ],
        max_tokens=max(settings.attach_classify_max_tokens, min(5000, page_total * 220)),
        enable_thinking=False,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) or []


async def _classify_source_files_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    """Giữ nguyên mỗi file và đặt đúng một tên bằng prompt riêng, vẫn chỉ một request LLM."""
    if not documents:
        return []
    page_total = sum(len(item.get("pages") or []) for item in documents)
    raw = await client.chat(
        [
            {"role": "system", "content": preserve_prompt.SYSTEM_PROMPT},
            {"role": "user", "content": preserve_prompt.build_user_prompt(documents)},
        ],
        max_tokens=max(settings.attach_classify_max_tokens, min(3000, page_total * 140)),
        enable_thinking=False,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) or []


def _person_keys(number: str, name: str) -> set[str]:
    keys: set[str] = set()
    if number:
        keys.add(f"id:{number}")
    name_key = _normalize_person_key(name)
    if name_key:
        keys.add(f"name:{name_key}")
    return keys


def _identity_record_keys(record: dict) -> set[str]:
    keys: set[str] = set()
    for holder in record.get("identityHolders") or []:
        keys.update(_person_keys(holder.get("identityNumber") or "", holder.get("name") or ""))
    return keys


def _build_split_bundle_plan_items(
    document_groups: list[list[dict]],
    identity_records: list[dict],
    file_meta: dict[int, dict],
    errors: list[str],
) -> tuple[list[dict], list[dict]]:
    """Dựng bundle nhiều tab bằng quan hệ người ký ↔ giấy tùy thân.

    Số tab do số văn bản quyết định. Một identity khớp cùng một signer ở nhiều văn bản là giấy dùng
    chung và chỉ được đưa vào tab đầu; identity có holder đặc trưng cho một signer chỉ đi đúng tab đó.
    """
    used_document_names: set[str] = set()
    bundles: list[dict] = []
    classified: list[dict] = []

    for position, group in enumerate(document_groups):
        primary = group[0]
        bundle_id = f"signature-{position + 1}"
        signer_numbers = {
            record.get("signerIdentityNumber") or ""
            for record in group
            if record.get("signerIdentityNumber")
        }
        signer_names = {
            record.get("signerName") or ""
            for record in group
            if record.get("signerName")
        }
        normalized_signer_names = {_normalize_person_key(name) for name in signer_names}
        inconsistent_signer = len(signer_numbers) > 1 or len(normalized_signer_names) > 1
        if inconsistent_signer:
            errors.append(f"{bundle_id}: thông tin người ký không nhất quán giữa các phần văn bản.")
        signer_number = "" if inconsistent_signer else next(iter(sorted(signer_numbers)), "")
        signer_name = "" if inconsistent_signer else next(iter(sorted(signer_names)), "")
        related_numbers = {
            number
            for record in group
            for number in (record.get("relatedIdentityNumbers") or [])
            if number
        }
        sources = [
            _source_segment(record["segment"], file_meta[record["fileIndex"]]["pageCount"])
            for record in group
        ]
        document_name = _unique_document_name(
            primary["documentName"], used_document_names, primary["detectedType"]
        )
        item = {
            "fileIndex": sources[0]["fileIndex"],
            "fileName": primary["fileName"],
            "documentName": document_name,
            "componentName": SIGNATURE_DOC_COMPONENT,
            "target": "existing",
            "componentIndex": 1,
            "needsAddComponent": False,
            "detectedType": primary["detectedType"],
            "bundleId": bundle_id,
            "bundleRole": "signature_document",
        }
        if len(sources) > 1 or sources[0].get("pageIndexes") is not None:
            item["sourceSegments"] = sources
        bundles.append({
            "bundleId": bundle_id,
            "documentItem": item,
            "signerKeys": _person_keys(signer_number, signer_name),
            "signerCanonical": (
                f"id:{signer_number}" if signer_number else f"name:{_normalize_person_key(signer_name)}"
            ),
            "relatedKeys": {f"id:{number}" for number in related_numbers},
        })
        for record in group:
            classified.append({
                "fileIndex": record["fileIndex"],
                "fileName": record["fileName"],
                "pageFrom": record["segment"]["pageFrom"],
                "pageTo": record["segment"]["pageTo"],
                "detectedType": record["detectedType"],
                "documentName": document_name,
                "logicalGroup": bundle_id,
                "target": "existing",
                "componentIndex": 1,
                "bundleId": bundle_id,
                "bundleRole": "signature_document",
            })

    # Hai mặt/rời file của cùng đúng tập chủ thể trở thành một identity unit. Ba file cùng chứa một
    # CCCD chung nhưng mỗi file có hộ chiếu khác nhau sẽ có ba tập khóa khác nhau, nên không bị gom.
    identity_units: list[list[dict]] = []
    unit_position: dict[tuple[str, ...], int] = {}
    for record in identity_records:
        keys = tuple(sorted(_identity_record_keys(record)))
        # Không có khóa thì luôn giữ độc lập; tuyệt đối không gom các file OCR lỗi với nhau.
        grouping_key = keys or (f"unknown:{record['order']}",)
        if grouping_key not in unit_position:
            unit_position[grouping_key] = len(identity_units)
            identity_units.append([])
        identity_units[unit_position[grouping_key]].append(record)

    assigned_by_bundle: dict[int, list[tuple[list[dict], str]]] = {
        index: [] for index in range(len(bundles))
    }
    unmatched_units: list[list[dict]] = []
    for unit in identity_units:
        # Quy ước nhiều hồ sơ đã chốt với extension: nếu cả batch chỉ có đúng MỘT nhóm/file giấy
        # tờ tùy thân thì đó là bộ dùng chung, chỉ đính STT2 ở tab đầu. Không bắt LLM phải suy ra
        # người ký cho các giấy như khai sinh/GCNQSDĐ vốn không có chữ ký của chủ hồ sơ; nếu ép
        # khớp người ở đây, identity sẽ rơi thành target=new và làm contract bundle bị khuyết.
        if len(identity_units) == 1 and len(bundles) > 1:
            assigned_by_bundle[0].append((unit, "shared"))
            continue

        unit_keys = set().union(*(_identity_record_keys(record) for record in unit))
        signer_matches = [
            index for index, bundle in enumerate(bundles)
            if unit_keys & bundle["signerKeys"]
        ]
        if len(signer_matches) == 1:
            assigned_by_bundle[signer_matches[0]].append((unit, "matched"))
            continue
        if len(signer_matches) > 1:
            signer_values = {bundles[index]["signerCanonical"] for index in signer_matches}
            if len(signer_values) == 1 and "" not in signer_values:
                assigned_by_bundle[signer_matches[0]].append((unit, "shared"))
            else:
                names = ", ".join(record["fileName"] for record in unit)
                errors.append(
                    f"Giấy tờ tùy thân {names} khớp nhiều người ký khác nhau; không tự ghép."
                )
                unmatched_units.append(unit)
            continue

        related_matches = [
            index for index, bundle in enumerate(bundles)
            if unit_keys & bundle["relatedKeys"]
        ]
        if len(related_matches) == 1:
            assigned_by_bundle[related_matches[0]].append((unit, "matched"))
        elif len(related_matches) > 1 and len(related_matches) == len(bundles):
            assigned_by_bundle[related_matches[0]].append((unit, "shared"))
        elif len(bundles) == 1:
            # Một hồ sơ trong splitMode không có nguy cơ chạy chéo tab; giữ khả năng tương thích khi
            # provider thiếu metadata nhưng classifier vẫn xác định đúng đây là giấy tùy thân.
            assigned_by_bundle[0].append((unit, "matched"))
        else:
            names = ", ".join(record["fileName"] for record in unit)
            errors.append(
                f"Giấy tờ tùy thân {names} không khớp người ký của văn bản nào."
            )
            unmatched_units.append(unit)

    attachments: list[dict] = []

    def _emit_identity(
        assigned: list[tuple[list[dict], str]], bundle_index: int | None
    ) -> dict:
        records = sorted(
            [record for unit, _scope in assigned for record in unit],
            key=lambda record: record["order"],
        )
        primary = records[0]
        sources = [
            _source_segment(record["segment"], file_meta[record["fileIndex"]]["pageCount"])
            for record in records
        ]
        base_name = primary["documentName"] if len(assigned) == 1 else "Giấy tờ tùy thân"
        document_name = _unique_document_name(
            base_name, used_document_names, primary["detectedType"]
        )
        matched = any(scope == "matched" for _unit, scope in assigned)
        item = {
            "fileIndex": sources[0]["fileIndex"],
            "fileName": primary["fileName"],
            "documentName": document_name,
            "componentName": IDENTITY_COMPONENT if bundle_index is not None else document_name,
            "target": "existing" if bundle_index is not None else "new",
            "componentIndex": 2 if bundle_index is not None else None,
            "needsAddComponent": bundle_index is None,
            "detectedType": primary["detectedType"],
            "bundleRole": "identity",
        }
        if bundle_index is not None:
            item["bundleId"] = bundles[bundle_index]["bundleId"]
            item["identityScope"] = "matched" if matched else "shared"
        if len(sources) > 1 or sources[0].get("pageIndexes") is not None:
            item["sourceSegments"] = sources
        for record in records:
            classified.append({
                "fileIndex": record["fileIndex"],
                "fileName": record["fileName"],
                "pageFrom": record["segment"]["pageFrom"],
                "pageTo": record["segment"]["pageTo"],
                "detectedType": record["detectedType"],
                "documentName": document_name,
                "logicalGroup": item.get("bundleId"),
                "target": item["target"],
                "componentIndex": item["componentIndex"],
                "bundleId": item.get("bundleId"),
                "bundleRole": "identity",
                "identityScope": item.get("identityScope"),
            })
        return item

    for bundle_index, bundle in enumerate(bundles):
        attachments.append(bundle["documentItem"])
        assigned = assigned_by_bundle[bundle_index]
        if assigned:
            attachments.append(_emit_identity(assigned, bundle_index))
    # Giấy tùy thân không xếp được vào hồ sơ nào: KHÔNG đẻ dòng "Thêm thành phần" như chế độ gộp.
    # Mỗi tab ở chế độ tách chỉ có đúng hai dòng cố định (STT1 văn bản, STT2 giấy tùy thân) nên dòng
    # thêm không bao giờ dùng được; giữ nó lại thì extension thấy một tệp KHÔNG có bundleId và bỏ
    # nguyên lượt đính kèm — hỏng một tệp thành mất cả hồ sơ (sự cố Nghĩa Hưng 21/09/2026).
    # Vẫn ghi vào `classified` để trang quản trị thấy tệp đã đọc được gì và vì sao bị bỏ.
    for unit in unmatched_units:
        for record in sorted(unit, key=lambda item: item["order"]):
            classified.append({
                "fileIndex": record["fileIndex"],
                "fileName": record["fileName"],
                "pageFrom": record["segment"]["pageFrom"],
                "pageTo": record["segment"]["pageTo"],
                "detectedType": record["detectedType"],
                "documentName": record["documentName"],
                "logicalGroup": None,
                "target": "skipped",
                "componentIndex": None,
                "bundleId": None,
                "bundleRole": "identity",
                "identityScope": None,
            })

    return attachments, sorted(classified, key=lambda item: (item["fileIndex"], item["pageFrom"]))


def build_segment_plan_items(
    files: list[dict],
    segments: list[dict],
    file_meta: dict[int, dict],
    page_text_by_file: dict[int, dict[int, str]],
    full_text_by_file: dict[int, str],
    *,
    split_mode: bool = False,
    errors: list[str] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Dựng kế hoạch theo tài liệu logic, nhưng giữ đúng đặc thù STT1/STT2 của chữ ký."""
    records: list[dict] = []
    for order, segment in enumerate(segments):
        file_index = segment["fileIndex"]
        file = files[file_index]
        ocr_text = _segment_text(segment, page_text_by_file, full_text_by_file)
        # Có provider đôi lúc trả documentName đúng nhưng bỏ trống detectedType. Đó vẫn là tín hiệu
        # phân loại của LLM và phải được dùng trước rule keyword.
        llm_detected = canonical_document_type(
            segment.get("detectedType") or segment.get("documentName") or ""
        )
        rule_detected = detect_document_type(ocr_text, "")
        # LLM đã đọc ngữ cảnh tài liệu là nguồn quyết định. Rule chỉ cứu trường hợp LLM để trống;
        # tuyệt đối không để một dòng nhắc CCCD biến giấy cam đoan/ủy quyền thành thẻ căn cước.
        detected = llm_detected if llm_detected != _GENERIC_DOCUMENT_TYPE else rule_detected
        detected = detected or _GENERIC_DOCUMENT_TYPE
        raw_name = str(segment.get("documentName") or "").strip()
        if not raw_name:
            raw_name = detected if detected != _GENERIC_DOCUMENT_TYPE else str(file.get("name") or "")
        signer_identity_number = _validated_identity_number(
            segment.get("signerIdentityNumber"), ocr_text
        )
        signer_name = _validated_person_name(segment.get("signerName"), ocr_text)
        related_identity_numbers: list[str] = []
        for value in segment.get("relatedIdentityNumbers") or []:
            number = _validated_identity_number(value, ocr_text)
            if number and number not in related_identity_numbers:
                related_identity_numbers.append(number)
        records.append({
            "order": order,
            "fileIndex": file_index,
            "fileName": str(file.get("name") or f"file-{file_index + 1}"),
            "segment": segment,
            "ocrText": ocr_text,
            "detectedType": detected,
            "documentName": raw_name,
            "logicalKey": str(segment.get("logicalKey") or "").strip(),
            "isIdentity": _is_identity(detected, ocr_text, ""),
            "signerName": signer_name,
            "signerIdentityNumber": signer_identity_number,
            "relatedIdentityNumbers": related_identity_numbers,
            "identityHolders": _validated_identity_holders(
                segment.get("identityHolders"), ocr_text
            ),
        })

    # Tài liệu cần ký chỉ được gom khi LLM khẳng định cùng logicalKey. Giấy tùy thân được gom riêng
    # theo số định danh; STT2 chỉ dành cho chủ thể đầu tiên.
    document_groups: list[list[dict]] = []
    group_position: dict[str, int] = {}
    identity_records: list[dict] = []
    for record in records:
        if record["isIdentity"]:
            identity_records.append(record)
            continue
        explicit = _fold(record.get("logicalKey") or "")
        key = (
            f"doc:{_fold(record['detectedType'])}:{explicit}"
            if explicit
            else f"single:{record['order']}"
        )
        if key not in group_position:
            group_position[key] = len(document_groups)
            document_groups.append([])
        document_groups[group_position[key]].append(record)

    for group in document_groups:
        group.sort(key=lambda record: record["order"])
    identity_records.sort(key=lambda record: record["order"])

    # Chỉ chế độ nhiều tab của đúng thủ tục này dùng quan hệ bundle. Chế độ một hồ sơ tiếp tục đi
    # qua toàn bộ logic cũ bên dưới, kể cả helper gộp hai mặt CCCD.
    if split_mode and document_groups:
        return _build_split_bundle_plan_items(
            document_groups,
            identity_records,
            file_meta,
            errors if errors is not None else [],
        )

    used_document_names: set[str] = set()
    used_component_names: set[str] = set()
    attachments: list[dict] = []
    classified: list[dict] = []

    def _emit(group: list[dict], *, identity: bool, document_position: int = 0) -> None:
        primary = group[0]
        detected = primary["detectedType"]
        identity_types = {_fold(record["detectedType"]) for record in group} if identity else set()
        base_name = (
            primary["documentName"] if len(identity_types) == 1 else "Giấy tờ tùy thân"
        ) if identity else primary["documentName"]
        document_name = _unique_document_name(base_name, used_document_names, detected)
        sources = [
            _source_segment(record["segment"], file_meta[record["fileIndex"]]["pageCount"])
            for record in group
        ]
        if identity:
            component_name = IDENTITY_COMPONENT
            target = "existing"
            component_index: int | None = 2
            needs_add = False
        elif document_position == 0:
            component_name = SIGNATURE_DOC_COMPONENT
            target = "existing"
            component_index = 1
            needs_add = False
        else:
            component_name = _unique_document_name(
                primary["documentName"], used_component_names, detected
            )
            target = "new"
            component_index = None
            needs_add = True

        item = {
            "fileIndex": sources[0]["fileIndex"],
            "fileName": primary["fileName"],
            "documentName": document_name,
            "componentName": component_name,
            "target": target,
            "componentIndex": component_index,
            "needsAddComponent": needs_add,
            "detectedType": detected,
        }
        if len(sources) > 1 or sources[0].get("pageIndexes") is not None:
            item["sourceSegments"] = sources
        attachments.append(item)

        logical_group = "identity:all" if identity else (
            f"doc:{_fold(primary.get('logicalKey') or '')}" if primary.get("logicalKey") else None
        )
        for record in group:
            classified.append({
                "fileIndex": record["fileIndex"],
                "fileName": record["fileName"],
                "pageFrom": record["segment"]["pageFrom"],
                "pageTo": record["segment"]["pageTo"],
                "detectedType": record["detectedType"],
                "documentName": document_name,
                "logicalGroup": logical_group,
                "target": target,
                "componentIndex": component_index,
            })

    for position, group in enumerate(document_groups):
        _emit(group, identity=False, document_position=position)
    if identity_records:
        identity_slot = (2, IDENTITY_COMPONENT)
        seed_records: list[dict] = []
        for record in identity_records:
            source = _source_segment(
                record["segment"], file_meta[record["fileIndex"]]["pageCount"]
            )
            item = {
                "fileIndex": record["fileIndex"],
                "fileName": record["fileName"],
                "documentName": record["documentName"],
                "componentName": record["documentName"],
                "target": "new",
                "componentIndex": None,
                "needsAddComponent": True,
                "detectedType": record["detectedType"],
            }
            if source.get("pageIndexes") is not None:
                item["sourceSegments"] = [source]
            seed_records.append({
                "item": item,
                "ocrText": record["ocrText"],
                "order": record["order"],
            })
        grouped_identities = merge_identity_records(
            seed_records,
            existing_slot=identity_slot,
            default_document_name="Giấy tờ tùy thân",
        )
        attachments.extend(grouped_identities)
        for record in identity_records:
            grouped = next(
                (
                    item for item in grouped_identities
                    if any(
                        source["fileIndex"] == record["fileIndex"]
                        for source in item.get("sourceSegments")
                        or [{"fileIndex": item["fileIndex"]}]
                    )
                ),
                grouped_identities[0],
            )
            classified.append({
                "fileIndex": record["fileIndex"],
                "fileName": record["fileName"],
                "pageFrom": record["segment"]["pageFrom"],
                "pageTo": record["segment"]["pageTo"],
                "detectedType": record["detectedType"],
                "documentName": grouped["documentName"],
                "logicalGroup": f"identity:{grouped['documentName']}",
                "target": grouped["target"],
                "componentIndex": grouped.get("componentIndex"),
            })

    # Cổng có sẵn STT1 rồi STT2; thành phần mới luôn dựng sau hai dòng cố định.
    attachments.sort(key=lambda item: (
        0 if item["target"] == "existing" else 1,
        item["componentIndex"] or 0,
        item["fileIndex"],
    ))
    return attachments, sorted(classified, key=lambda item: (item["fileIndex"], item["pageFrom"]))


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho chung-thuc-chu-ky (gọi qua registry.get_attach_pipeline)."""
    _ = session
    options = options or {}
    split_documents = options.get("splitDocuments") is True
    split_mode = options.get("splitMode") is True
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [
        (file_index, file)
        for file_index, file in enumerate(raw_files)
        if file.get("type") in _OCR_TYPES
    ]

    t0 = time.monotonic()
    # OCR đầy đủ một batch để nhận được header từng trang và tách file hỗn hợp.
    ocr_results = await ocr.ocr_per_file([file for _, file in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    ocr_by_index = {
        file_index: result
        for (file_index, _), result in zip(ocr_pairs, ocr_results)
    }
    file_meta: dict[int, dict[str, Any]] = {}
    page_text_by_file: dict[int, dict[int, str]] = {}
    full_text_by_file: dict[int, str] = {}
    llm_docs: list[dict[str, Any]] = []
    for file_index, file in enumerate(raw_files):
        text = str(ocr_by_index.get(file_index, {}).get("text") or "")
        page_count = _pdf_page_count(file)
        pages, boundaries_available = _split_ocr_pages(text, page_count)
        if boundaries_available and pages:
            page_count = max(page_count, max(int(page.get("pageNumber") or 1) for page in pages))
        file_meta[file_index] = {
            "pageCount": page_count,
            "pageBoundariesAvailable": boundaries_available,
        }
        full_text_by_file[file_index] = text
        page_text_by_file[file_index] = {
            int(page.get("pageNumber") or 1): str(page.get("ocrText") or "")
            for page in pages
        }
        if text.strip():
            llm_docs.append({
                "fileIndex": file_index,
                "pageCount": page_count,
                "pageBoundariesAvailable": boundaries_available,
                "pages": pages,
            })

    t1 = time.monotonic()
    raw_segments: list[dict] = []
    if llm_docs:
        try:
            raw_segments = await (
                _classify_documents_with_llm(llm_docs)
                if split_documents
                else _classify_source_files_with_llm(llm_docs)
            )
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    segments = _validated_segments(raw_segments, raw_files, file_meta, errors)
    segments = _restore_relationship_metadata(segments, raw_segments)
    if not split_documents:
        segments = _preserve_source_file_segments(
            segments,
            raw_files,
            file_meta,
            is_identity_segment=lambda segment: _is_identity(
                canonical_document_type(
                    segment.get("detectedType") or segment.get("documentName") or ""
                ),
                "",
                "",
            ),
            long_name_fallback="Hồ sơ chứng thực chữ ký",
        )
    attachments, classified = build_segment_plan_items(
        raw_files,
        segments,
        file_meta,
        page_text_by_file,
        full_text_by_file,
        split_mode=split_mode,
        errors=errors,
    )
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]
    indexed_ocr_results = []
    for file_index, file in enumerate(raw_files):
        result = ocr_by_index.get(file_index)
        if not result:
            continue
        indexed_ocr_results.append({
            **result,
            "name": f"fileIndex={file_index} · {file['name']}",
        })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [
                raw_files[file_index]["name"]
                for file_index, result in ocr_by_index.items()
                if result.get("text")
            ],
            "llmDocuments": [raw_files[doc["fileIndex"]]["name"] for doc in llm_docs],
            "skippedOcr": skipped_ocr,
            "documentSplitEnabled": split_documents,
            "documentPromptMode": "split" if split_documents else "preserve",
            "multiDossierBundleEnabled": split_mode,
            "classified": classified,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "ocr_text": join_ocr_documents(indexed_ocr_results),
        "llm_output": {"documents": raw_segments},
        "errors": errors,
    }
